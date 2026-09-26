"""
peer_analysis.py - compare the player with players of the same rank and role.

OpenDota has no per-rank benchmarks, but every match it returns holds the
stats of all ten players, and matchmaking puts players of similar rank
together. So "players of your rank" are the other players of the same role in
the player's own matches:

- per match: the player vs the same-role players of that match (usually the
  direct lane opponent), with findings when the gap is large;
- over many matches (career): averages of the player vs those peers.
"""

from __future__ import annotations

from statistics import mean, median
from typing import Any

from app.hero_meta import rank_bracket
from app.opendota import my_player

ROLES = ("carry", "mid", "offlane", "support")
METRICS = ("gpm", "xpm", "lh_10", "lh_per_min", "deaths", "kda", "damage_per_min", "net_worth")
# Lower is better for these.
LOWER_IS_BETTER = {"deaths"}


def player_role(player: dict[str, Any], duration: int | None) -> str:
    minutes = max(1.0, (duration or 0) / 60)
    wards = (player.get("obs_placed") or 0) + (player.get("sen_placed") or 0)
    lh_rate = (player.get("last_hits") or 0) / minutes
    if wards >= 8 or (lh_rate < 2.0 and minutes >= 20):
        return "support"
    lane_role = player.get("lane_role")
    if lane_role == 2:
        return "mid"
    if lane_role == 3:
        return "offlane"
    return "carry"


def player_metrics(player: dict[str, Any], duration: int | None) -> dict[str, float | None]:
    minutes = max(1.0, (duration or 0) / 60)
    deaths = player.get("deaths")
    kills = player.get("kills")
    assists = player.get("assists")
    return {
        "gpm": player.get("gold_per_min"),
        "xpm": player.get("xp_per_min"),
        "lh_10": player.get("lh_10"),
        "lh_per_min": round((player.get("last_hits") or 0) / minutes, 2)
        if player.get("last_hits") is not None
        else None,
        "deaths": deaths,
        "kda": round(((kills or 0) + (assists or 0)) / max(1, deaths or 0), 2)
        if deaths is not None
        else None,
        "damage_per_min": round((player.get("hero_damage") or 0) / minutes)
        if player.get("hero_damage") is not None
        else None,
        "net_worth": player.get("net_worth"),
    }


def _tidy(value: float) -> float | int:
    """5.0 -> 5, 4.33 -> 4.3 for texts."""
    value = round(value, 1)
    return int(value) if value == int(value) else value


def _avg(values: list[Any]) -> float | None:
    numbers = [float(v) for v in values if isinstance(v, (int, float)) and not isinstance(v, bool)]
    return round(mean(numbers), 2) if numbers else None


def match_peers(trimmed: dict[str, Any] | None) -> dict[str, Any] | None:
    """The player vs same-role players of this match, or None without OpenDota data."""
    if not trimmed:
        return None
    me = my_player(trimmed)
    if not me:
        return None
    duration = trimmed.get("duration")
    role = player_role(me, duration)
    my_side = bool(me.get("isRadiant", True))
    peers = []
    for player in trimmed.get("players") or []:
        if player is me or player.get("me") or player_role(player, duration) != role:
            continue
        peers.append(
            {
                "hero": player.get("hero"),
                "enemy": bool(player.get("isRadiant", True)) != my_side,
                "rank_tier": player.get("rank_tier"),
                "metrics": player_metrics(player, duration),
            }
        )
    # Direct opponents first.
    peers.sort(key=lambda p: not p["enemy"])
    tiers = [p.get("rank_tier") for p in trimmed.get("players") or [] if p.get("rank_tier")]
    return {
        "role": role,
        "lobby_rank_tier": int(median(tiers)) if tiers else None,
        "me": player_metrics(me, duration),
        "peers": peers,
        "avg": {key: _avg([p["metrics"][key] for p in peers]) for key in METRICS},
    }


def peer_findings(block: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not block or not block.get("peers"):
        return []
    me, avg, role = block["me"], block["avg"], block["role"]
    heroes = ", ".join(p["hero"] for p in block["peers"][:2] if p.get("hero"))
    findings: list[dict[str, Any]] = []
    gpm, peer_gpm = me.get("gpm"), avg.get("gpm")
    if gpm is not None and peer_gpm:
        gap = max(60.0, 0.12 * peer_gpm)
        if gpm < peer_gpm - gap and role != "support":
            findings.append(
                _finding(
                    "peer_gpm_behind",
                    "improve",
                    "farm",
                    2,
                    (peer_gpm - gpm) / 60,
                    role=role,
                    heroes=heroes,
                    gpm=gpm,
                    peer_gpm=round(peer_gpm),
                )
            )
        elif gpm > peer_gpm + gap:
            findings.append(
                _finding(
                    "peer_gpm_ahead",
                    "strength",
                    "farm",
                    1,
                    0.8,
                    role=role,
                    heroes=heroes,
                    gpm=gpm,
                    peer_gpm=round(peer_gpm),
                )
            )
    lh10, peer_lh10 = me.get("lh_10"), avg.get("lh_10")
    if role != "support" and lh10 is not None and peer_lh10 is not None and lh10 < peer_lh10 - 10:
        findings.append(
            _finding(
                "peer_lh10_behind",
                "improve",
                "laning",
                2,
                (peer_lh10 - lh10) / 8,
                role=role,
                heroes=heroes,
                lh10=lh10,
                peer_lh10=round(peer_lh10),
            )
        )
    deaths, peer_deaths = me.get("deaths"), avg.get("deaths")
    if deaths is not None and peer_deaths is not None and deaths >= peer_deaths + 3:
        findings.append(
            _finding(
                "peer_deaths_more",
                "improve",
                "survival",
                2,
                deaths - peer_deaths,
                role=role,
                heroes=heroes,
                deaths=deaths,
                peer_deaths=_tidy(peer_deaths),
            )
        )
    return findings


def career_peers(analyses: list[dict[str, Any]], rank_tier: Any = None) -> dict[str, Any] | None:
    """Averages of the player vs same-role peers over the analysed matches."""
    blocks = [a["peers"] for a in analyses if a and a.get("peers") and a["peers"].get("peers")]
    if not blocks:
        return None
    roles = [b["role"] for b in blocks]
    main_role = max(set(roles), key=roles.count)
    rows = []
    for key in METRICS:
        you = _avg([b["me"].get(key) for b in blocks])
        peers = _avg([b["avg"].get(key) for b in blocks])
        if you is None or peers is None:
            continue
        diff = round(you - peers, 2)
        better = None
        if abs(diff) > max(0.01, abs(peers) * 0.03):
            better = (diff < 0) if key in LOWER_IS_BETTER else (diff > 0)
        rows.append(
            {
                "key": key,
                "you": you,
                "peers": peers,
                "diff": diff,
                "diff_pct": round(100 * diff / peers) if peers else None,
                "better": better,
            }
        )
    lobby_tiers = [b.get("lobby_rank_tier") for b in blocks if b.get("lobby_rank_tier")]
    lobby_tier = int(median(lobby_tiers)) if lobby_tiers else None
    return {
        "matches": len(blocks),
        "role": main_role,
        "rank_tier": rank_tier or lobby_tier,
        "lobby_rank_tier": lobby_tier,
        "bracket": rank_bracket(rank_tier or lobby_tier),
        "metrics": rows,
    }


def _finding(
    finding_id: str, kind: str, section: str, severity: int, weight: float, **params: Any
) -> dict[str, Any]:
    return {
        "id": finding_id,
        "kind": kind,
        "section": section,
        "severity": severity,
        "weight": weight,
        "params": params,
    }
