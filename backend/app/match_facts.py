"""
match_facts.py - one shape for "what happened in this match" from any source.

Post-match analysis works on MatchFacts, built from:

- the OpenDota match (trimmed by opendota.trim_match): full data when the
  replay was parsed (per-minute last hits/gold/XP, purchase and kill logs,
  benchmarks), totals only otherwise;
- the app's own GSI timeline (match_tracker.py): the local player's
  last hits/gold/K/D/A every 15 s, deaths with unspent gold, items by time.

When both exist they are merged: OpenDota wins for totals, logs and
benchmarks; GSI adds what OpenDota does not know (unspent gold at each death).

Map positions use the absolute replay coordinates (centre 16384): GSI samples
and deaths carry them already, OpenDota logs use 128-unit cells.
"""

from __future__ import annotations

from typing import Any

from app.dota_constants import hero_name, hero_name_from_npc
from app.opendota import my_player


def _int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _num(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def empty_facts(match_id: int) -> dict[str, Any]:
    return {
        "match_id": int(match_id),
        "sources": [],
        "parsed": False,
        "hero": None,
        "hero_id": None,
        "duration": None,
        "win": None,
        "is_radiant": None,
        "lane_role": None,
        "is_roaming": False,
        "kills": None,
        "deaths": None,
        "assists": None,
        "last_hits": None,
        "denies": None,
        "gpm": None,
        "xpm": None,
        "level": None,
        "net_worth": None,
        "hero_damage": None,
        "tower_damage": None,
        "hero_healing": None,
        "team_kills": None,
        "kill_participation": None,
        "teamfight_participation": None,
        "lane_efficiency_pct": None,
        "obs_placed": None,
        "sen_placed": None,
        "camps_stacked": None,
        "rune_pickups": None,
        "stuns": None,
        "time_dead": None,
        "benchmarks": {},
        # Cumulative values at minute 0, 1, 2, … (index = minute).
        "lh_t": [],
        "dn_t": [],
        "gold_t": [],
        "xp_t": [],
        "deaths_log": [],
        "items_log": [],
        "buybacks": [],
        "killed_by": {},
        "final_items": [],
        # Map: the hero every 15 s (GSI), wards placed and lane position (parsed replay).
        "path": [],
        "wards": [],
        "lane_pos": [],
        # Live advice the app showed during the match (GSI recording only).
        "advice_log": [],
    }


CELL = 128  # OpenDota position logs are in 128-unit cells


def _wards(me: dict[str, Any]) -> list[dict[str, Any]]:
    wards = []
    for kind, key in (("obs", "obs_log"), ("sen", "sen_log")):
        for entry in me.get(key) or []:
            if not isinstance(entry, dict):
                continue
            t, x, y = _int(entry.get("time")), _num(entry.get("x")), _num(entry.get("y"))
            if t is not None and x is not None and y is not None:
                wards.append({"t": t, "x": round(x * CELL), "y": round(y * CELL), "kind": kind})
    return sorted(wards, key=lambda ward: ward["t"])


def _lane_pos(raw: Any) -> list[list[int]]:
    """{"x": {"y": count}} in cells -> [[x, y, count]] in map units."""
    points = []
    if isinstance(raw, dict):
        for x, column in raw.items():
            if not isinstance(column, dict):
                continue
            for y, count in column.items():
                cx, cy, n = _num(x), _num(y), _int(count)
                if cx is not None and cy is not None and n:
                    points.append([round(cx * CELL), round(cy * CELL), n])
    return points


def facts_from_opendota(trimmed: dict[str, Any]) -> dict[str, Any] | None:
    me = my_player(trimmed)
    if not me:
        return None
    facts = empty_facts(_int(trimmed.get("match_id")) or 0)
    facts["sources"] = ["opendota"]
    facts["parsed"] = bool(trimmed.get("parsed"))
    radiant = bool(me.get("isRadiant", True))
    radiant_win = trimmed.get("radiant_win")
    team = [p for p in trimmed.get("players") or [] if bool(p.get("isRadiant", True)) == radiant]
    team_kills = sum(_int(p.get("kills")) or 0 for p in team)
    kills = _int(me.get("kills")) or 0
    assists = _int(me.get("assists")) or 0
    facts.update(
        {
            "hero": me.get("hero") or hero_name(me.get("hero_id")),
            "hero_id": _int(me.get("hero_id")),
            "duration": _int(trimmed.get("duration")),
            "win": None if radiant_win is None else bool(radiant_win) == radiant,
            "is_radiant": radiant,
            "lane_role": _int(me.get("lane_role")),
            "is_roaming": bool(me.get("is_roaming")),
            "kills": _int(me.get("kills")),
            "deaths": _int(me.get("deaths")),
            "assists": _int(me.get("assists")),
            "last_hits": _int(me.get("last_hits")),
            "denies": _int(me.get("denies")),
            "gpm": _int(me.get("gold_per_min")),
            "xpm": _int(me.get("xp_per_min")),
            "level": _int(me.get("level")),
            "net_worth": _int(me.get("net_worth")),
            "hero_damage": _int(me.get("hero_damage")),
            "tower_damage": _int(me.get("tower_damage")),
            "hero_healing": _int(me.get("hero_healing")),
            "team_kills": team_kills,
            "kill_participation": (kills + assists) / team_kills if team_kills else None,
            "teamfight_participation": _num(me.get("teamfight_participation")),
            "lane_efficiency_pct": _num(me.get("lane_efficiency_pct")),
            "obs_placed": _int(me.get("obs_placed")),
            "sen_placed": _int(me.get("sen_placed")),
            "camps_stacked": _int(me.get("camps_stacked")),
            "rune_pickups": _int(me.get("rune_pickups")),
            "stuns": _num(me.get("stuns")),
            "time_dead": _int(me.get("life_state_dead")),
            "benchmarks": _benchmarks(me.get("benchmarks")),
            "lh_t": _series(me.get("lh_t")),
            "dn_t": _series(me.get("dn_t")),
            "gold_t": _series(me.get("gold_t")),
            "xp_t": _series(me.get("xp_t")),
            "killed_by": {
                hero_name_from_npc(npc): _int(count) or 0
                for npc, count in _dict(me.get("killed_by")).items()
                if str(npc).startswith("npc_dota_hero_")
            },
            "final_items": [
                me.get(key)
                for key in (
                    "item_0",
                    "item_1",
                    "item_2",
                    "item_3",
                    "item_4",
                    "item_5",
                    "backpack_0",
                    "backpack_1",
                    "backpack_2",
                )
                if me.get(key)
            ],
        }
    )
    facts["deaths_log"] = _with_fight_positions(
        _deaths_from_kill_logs(trimmed, me), trimmed.get("teamfights")
    )
    facts["items_log"] = [
        {"t": _int(entry.get("time")), "item": str(entry.get("key"))}
        for entry in _list(me.get("purchase_log"))
        if isinstance(entry, dict) and entry.get("key") and _int(entry.get("time")) is not None
    ]
    facts["buybacks"] = [
        _int(entry.get("time"))
        for entry in _list(me.get("buyback_log"))
        if isinstance(entry, dict) and _int(entry.get("time")) is not None
    ]
    facts["wards"] = _wards(me)
    facts["lane_pos"] = _lane_pos(me.get("lane_pos"))
    return facts


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _benchmarks(raw: Any) -> dict[str, float]:
    """OpenDota benchmarks: {"gold_per_min": {"raw": 612, "pct": 0.78}, …} -> {name: pct}."""
    result: dict[str, float] = {}
    if isinstance(raw, dict):
        for key, value in raw.items():
            pct = _num(value.get("pct")) if isinstance(value, dict) else None
            if pct is not None:
                result[key] = max(0.0, min(1.0, pct))
    return result


def _series(raw: Any) -> list[int]:
    if not isinstance(raw, list):
        return []
    return [_int(value) or 0 for value in raw]


def _deaths_from_kill_logs(trimmed: dict[str, Any], me: dict[str, Any]) -> list[dict[str, Any]]:
    npc = me.get("hero_npc")
    if not npc:
        return []
    deaths = []
    for player in trimmed.get("players") or []:
        if player.get("me"):
            continue
        for entry in _list(player.get("kills_log")):
            if isinstance(entry, dict) and entry.get("key") == npc:
                deaths.append({"t": _int(entry.get("time")), "killer": player.get("hero")})
    return sorted((d for d in deaths if d["t"] is not None), key=lambda d: d["t"])


def _with_fight_positions(deaths: list[dict[str, Any]], fights: Any) -> list[dict[str, Any]]:
    """Adds x/y (map units) to the deaths that happened in a team fight of a parsed
    replay: the fight's death positions, in order, to the deaths inside its time
    (a few seconds of slack). Deaths outside fights keep no position."""
    for fight in _list(fights):
        if not isinstance(fight, dict):
            continue
        start, end = _int(fight.get("start")), _int(fight.get("end"))
        if start is None or end is None:
            continue
        points = [p for x, y, n in _lane_pos(fight.get("deaths_pos")) for p in [(x, y)] * n]
        inside = [
            d
            for d in deaths
            if d.get("x") is None and d["t"] is not None and start - 3 <= d["t"] <= end + 3
        ]
        for death, (x, y) in zip(inside, points, strict=False):
            death["x"], death["y"] = x, y
    return deaths


def facts_from_timeline(timeline: dict[str, Any]) -> dict[str, Any]:
    facts = empty_facts(_int(timeline.get("match_id")) or 0)
    facts["sources"] = ["gsi"]
    samples = [s for s in timeline.get("samples") or [] if isinstance(s, dict)]
    final = timeline.get("final") or {}
    duration = _int(timeline.get("duration"))
    kills = _int(final.get("kills"))
    facts.update(
        {
            "hero": timeline.get("hero"),
            "hero_id": _int(timeline.get("hero_id")),
            "duration": duration,
            "win": timeline.get("win"),
            "is_radiant": (str(timeline.get("team") or "").lower() == "radiant")
            if timeline.get("team")
            else None,
            "kills": kills,
            "deaths": _int(final.get("deaths")),
            "assists": _int(final.get("assists")),
            "last_hits": _int(final.get("last_hits")),
            "denies": _int(final.get("denies")),
            "gpm": _int(final.get("gpm")),
            "xpm": _int(final.get("xpm")),
            "level": _int(final.get("level")),
            "lh_t": _per_minute(samples, "lh", duration),
            "dn_t": _per_minute(samples, "dn", duration),
            "gold_t": _earned_gold_per_minute(samples, duration),
            "deaths_log": [
                {
                    "t": _int(death.get("t")),
                    "gold": _int(death.get("gold")),
                    "respawn": _int(death.get("respawn")),
                    "level": _int(death.get("level")),
                    "x": _int(death.get("x")),
                    "y": _int(death.get("y")),
                    "last": _last_moments(death.get("last")),
                }
                for death in timeline.get("deaths") or []
                if isinstance(death, dict) and _int(death.get("t")) is not None
            ],
            "advice_log": [
                {key: item.get(key) for key in ("t", "dp", "action", "reason", "mode")}
                for item in timeline.get("advice") or []
                if isinstance(item, dict) and _int(item.get("t")) is not None
            ],
            "path": [
                {"t": s["t"], "x": s["x"], "y": s["y"]}
                for s in samples
                if s.get("t") is not None and s.get("x") is not None and s.get("y") is not None
            ],
            "items_log": [
                {"t": _int(item.get("t")), "item": str(item.get("item"))}
                for item in timeline.get("items") or []
                if isinstance(item, dict) and item.get("item")
            ],
            "buybacks": [
                _int(entry.get("t"))
                for entry in timeline.get("buybacks") or []
                if isinstance(entry, dict) and _int(entry.get("t")) is not None
            ],
        }
    )
    team = str(timeline.get("team") or "").lower()
    team_kills = _int((timeline.get("scores") or {}).get(team))
    if team_kills:
        facts["team_kills"] = team_kills
        facts["kill_participation"] = min(
            1.0, ((kills or 0) + (facts["assists"] or 0)) / team_kills
        )
    respawns = [d.get("respawn") for d in facts["deaths_log"] if d.get("respawn")]
    if respawns:
        facts["time_dead"] = sum(respawns)
    return facts


def _per_minute(samples: list[dict[str, Any]], key: str, duration: int | None) -> list[int]:
    """Value at the start of each minute, from 15-second samples."""
    points = [
        (s["t"], s[key]) for s in samples if s.get(key) is not None and s.get("t") is not None
    ]
    if not points:
        return []
    last_minute = (duration if duration is not None else points[-1][0]) // 60
    result, index, value = [], 0, 0
    for minute in range(last_minute + 1):
        while index < len(points) and points[index][0] <= minute * 60:
            value = points[index][1]
            index += 1
        result.append(value)
    return result


def _earned_gold_per_minute(samples: list[dict[str, Any]], duration: int | None) -> list[int]:
    """GSI has no net worth; GPM x minutes is the gold earned so far."""
    earned = [
        {"t": s["t"], "earned": round((s["gpm"] or 0) * s["t"] / 60)}
        for s in samples
        if s.get("gpm") is not None and s.get("t") is not None
    ]
    return _per_minute(earned, "earned", duration)


def merge_facts(
    opendota: dict[str, Any] | None, gsi: dict[str, Any] | None
) -> dict[str, Any] | None:
    if opendota is None:
        return gsi
    if gsi is None:
        return opendota
    merged = dict(opendota)
    merged["sources"] = sorted(set(opendota["sources"]) | set(gsi["sources"]))
    for key, value in gsi.items():
        if merged.get(key) in (None, [], {}) and value not in (None, [], {}):
            merged[key] = value
    # OpenDota knows who killed us, GSI knows how much gold we lost.
    if gsi.get("deaths_log"):
        merged["deaths_log"] = _merge_deaths(opendota.get("deaths_log") or [], gsi["deaths_log"])
    return merged


def _last_moments(value: Any) -> dict[str, Any] | None:
    """The stored last seconds before a death (last_moments.py), re-checked."""
    if not isinstance(value, dict):
        return None
    hp = [
        [int(point[0]), int(point[1])]
        for point in value.get("hp") or []
        if isinstance(point, list)
        and len(point) == 2
        and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in point)
    ]
    if not hp:
        return None
    result: dict[str, Any] = {
        "hp": hp,
        "ready": [str(name) for name in value.get("ready") or [] if isinstance(name, str)],
        "usable": [str(name) for name in value.get("usable") or [] if isinstance(name, str)],
        "free_s": _int(value.get("free_s")) or 0,
    }
    if _int(value.get("burst_s")):
        result["burst_s"] = _int(value.get("burst_s"))
    return result


def _merge_deaths(
    od_deaths: list[dict[str, Any]], gsi_deaths: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    if not od_deaths:
        return gsi_deaths
    result = []
    for death in od_deaths:
        near = min(
            gsi_deaths,
            key=lambda item: abs((item.get("t") or 0) - (death.get("t") or 0)),
            default=None,
        )
        entry = dict(death)
        if near and abs((near.get("t") or 0) - (death.get("t") or 0)) <= 20:
            for key in ("gold", "respawn", "level", "x", "y", "last"):
                if entry.get(key) is None and near.get(key) is not None:
                    entry[key] = near[key]
        result.append(entry)
    return result
