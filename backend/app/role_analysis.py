"""
role_analysis.py - what a mid and a support are judged by beyond farm and fights.

Parsed replays only (OpenDota counts runes, stacks and wards from the replay):

- mid: power / bounty / wisdom runes picked up (rune_pickups) per 10 minutes and
  against the enemy mid of the same match (player_roles); runes are the mid's
  tempo, so the findings sit in the laning section;
- support: camps stacked and sentry wards over the whole game (a support with
  no sentries cannot answer invisible heroes or dewarding);
- offlane: seconds of stuns and damage to buildings against the enemy offlaner
  of the same match (control in fights and pressure on towers are the
  offlaner's job; heroes without stuns compare low on both sides, so only a
  clear gap counts).

Returns (block, findings): the block is stored as analysis["role_play"] and shown
in the review's laning / vision facts; the findings use _finding's shape.
"""

from __future__ import annotations

from typing import Any

from app.peer_analysis import player_roles

RUNES_GOOD_PER_10 = 3.0
RUNES_LOW_PER_10 = 1.5
RUNES_BEHIND_BY = 4
MIN_MINUTES = 20
STACKS_LOW_MAX = 1
STACKS_MIN_MINUTES = 25
STUNS_GAP_SECONDS = 15
TOWER_GAP = 2000


def _finding(
    finding_id: str, kind: str, section: str, severity: int = 1, weight: float = 1.0, **params
):
    return {
        "id": finding_id,
        "kind": kind,
        "section": section,
        "severity": severity,
        "weight": weight,
        "params": params,
    }


def _enemy_same_role(
    opendota: dict[str, Any] | None, role_name: str, field: str
) -> tuple[str | None, float | None]:
    """The enemy player of this role in the match: (hero, value of `field`).
    A dual lane can give two enemies the role (a farming support on the
    offlane); the one with more last hits is the core who plays it."""
    if not opendota:
        return None, None
    players = opendota.get("players") or []
    me = next((p for p in players if p.get("me")), None)
    if me is None:
        return None, None
    roles = player_roles(players, opendota.get("duration"))
    my_side = bool(me.get("isRadiant", True))
    candidates = [
        player
        for player, role in zip(players, roles, strict=True)
        if role == role_name and bool(player.get("isRadiant", True)) != my_side
    ]
    if not candidates:
        return None, None
    player = max(candidates, key=lambda p: _last_hits(p))
    value = player.get(field)
    return player.get("hero"), float(value) if isinstance(value, (int, float)) else None


def _last_hits(player: dict[str, Any]) -> float:
    value = player.get("last_hits")
    return float(value) if isinstance(value, (int, float)) else 0.0


def _enemy_mid_runes(opendota: dict[str, Any] | None) -> tuple[str | None, int | None]:
    hero, runes = _enemy_same_role(opendota, "mid", "rune_pickups")
    return hero, None if runes is None else int(runes)


def analyze_role(
    facts: dict[str, Any], opendota: dict[str, Any] | None, position: str | None
) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    minutes = (facts.get("duration") or 0) / 60
    if not facts.get("parsed") or minutes < MIN_MINUTES:
        return None, []
    if position == "offlane":
        return _offlane(facts, opendota)
    if position not in ("mid", "support"):
        return None, []
    findings: list[dict[str, Any]] = []
    if position == "mid":
        runes = facts.get("rune_pickups")
        if not isinstance(runes, int):
            return None, []
        per10 = round(runes / (minutes / 10), 1)
        enemy_hero, enemy_runes = _enemy_mid_runes(opendota)
        block: dict[str, Any] = {"runes": runes, "runes_per_10": per10}
        if enemy_runes is not None:
            block.update(enemy_mid=enemy_hero, enemy_runes=enemy_runes)
        if enemy_runes is not None and enemy_runes >= runes + RUNES_BEHIND_BY:
            findings.append(
                _finding(
                    "runes_behind",
                    "improve",
                    "laning",
                    severity=2,
                    weight=1.3,
                    runes=runes,
                    enemy_runes=enemy_runes,
                    hero=enemy_hero,
                )
            )
        elif per10 < RUNES_LOW_PER_10:
            findings.append(
                _finding(
                    "runes_low",
                    "improve",
                    "laning",
                    severity=1,
                    runes=runes,
                    minutes=round(minutes),
                )
            )
        elif per10 >= RUNES_GOOD_PER_10 and (enemy_runes is None or runes > enemy_runes):
            findings.append(_finding("runes_good", "strength", "laning", weight=1.2, runes=runes))
        return block, findings

    stacks, sentries = facts.get("camps_stacked"), facts.get("sen_placed")
    block = {"camps_stacked": stacks, "sen_placed": sentries}
    if isinstance(stacks, int) and stacks <= STACKS_LOW_MAX and minutes >= STACKS_MIN_MINUTES:
        findings.append(
            _finding("stacks_low", "improve", "vision", stacks=stacks, minutes=round(minutes))
        )
    if sentries == 0:
        findings.append(
            _finding("sentries_none", "improve", "vision", weight=1.2, minutes=round(minutes))
        )
    return block, findings


def _offlane(
    facts: dict[str, Any], opendota: dict[str, Any] | None
) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    stuns = facts.get("stuns")
    if not isinstance(stuns, (int, float)):
        return None, []
    enemy_hero, enemy_stuns = _enemy_same_role(opendota, "offlane", "stuns")
    mine = round(stuns)
    block: dict[str, Any] = {"stuns": mine}
    findings: list[dict[str, Any]] = []
    findings.extend(_offlane_towers(facts, opendota, block))
    if enemy_stuns is None:
        return block, findings
    theirs = round(enemy_stuns)
    block.update(enemy_offlane=enemy_hero, enemy_stuns=theirs)
    if theirs >= mine + STUNS_GAP_SECONDS and theirs >= 2 * max(mine, 1):
        findings.append(
            _finding(
                "stuns_behind",
                "improve",
                "fights",
                severity=1,
                stuns=mine,
                enemy_stuns=theirs,
                hero=enemy_hero,
            )
        )
    elif mine >= theirs + STUNS_GAP_SECONDS and mine >= 2 * max(theirs, 1):
        findings.append(
            _finding("stuns_good", "strength", "fights", stuns=mine, enemy_stuns=theirs)
        )
    return block, findings


def _offlane_towers(
    facts: dict[str, Any], opendota: dict[str, Any] | None, block: dict[str, Any]
) -> list[dict[str, Any]]:
    """Damage to buildings against the enemy offlaner: a clear gap only."""
    towers = facts.get("tower_damage")
    enemy_hero, enemy_towers = _enemy_same_role(opendota, "offlane", "tower_damage")
    if not isinstance(towers, int) or enemy_towers is None:
        return []
    theirs = round(enemy_towers)
    block.update(tower_damage=towers, enemy_tower_damage=theirs)
    if theirs >= towers + TOWER_GAP and theirs >= 2 * max(towers, 1):
        return [
            _finding(
                "towers_behind",
                "improve",
                "fights",
                severity=1,
                weight=0.8,
                damage=towers,
                enemy_damage=theirs,
                hero=enemy_hero,
            )
        ]
    return []
