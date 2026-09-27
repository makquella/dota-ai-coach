"""
friend_compare.py - the player next to a friend, on the same kind of data.

Both sides are OpenDota match summaries (/players/{id}/matches: the rows the
player's own match table is built from), reviewable modes only
(dota_constants.is_reviewable_match), the last GAMES of the chosen group:

- all: every game;
- core / support: by the farm pace (a support takes under SUPPORT_LH_PER_MIN
  last hits a minute), since OpenDota knows the lane only for parsed matches.

Per game averages (win rate, K/D/A, deaths, GPM, XPM, last hits and hero damage
a minute) with the better side of each, the heroes both played, and the
friend's most played heroes. Differences under SAME_SHARE count as equal.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from app.dota_constants import hero_name

GAMES = 20
MIN_GAMES = 3
SUPPORT_LH_PER_MIN = 2.0
SAME_SHARE = 0.05
MIN_MINUTES = 10
GROUPS = ("all", "core", "support")
# (key, higher is better)
METRICS = (
    ("win_rate", True),
    ("kills", True),
    ("deaths", False),
    ("assists", True),
    ("gpm", True),
    ("xpm", True),
    ("lh_per_min", True),
    ("damage_per_min", True),
)
TOP_HEROES = 3
COMMON_HEROES = 6


def _minutes(row: dict[str, Any]) -> float | None:
    duration = row.get("duration")
    if not isinstance(duration, (int, float)) or duration < MIN_MINUTES * 60:
        return None
    return duration / 60


def group_of(row: dict[str, Any]) -> str | None:
    """ "core" or "support" by the farm pace; None for a very short game."""
    minutes = _minutes(row)
    last_hits = row.get("last_hits")
    if minutes is None or not isinstance(last_hits, (int, float)):
        return None
    return "support" if last_hits / minutes < SUPPORT_LH_PER_MIN else "core"


def _pick(rows: list[dict[str, Any]], group: str) -> list[dict[str, Any]]:
    rows = sorted(rows, key=lambda r: r.get("start_time") or 0, reverse=True)
    if group != "all":
        rows = [r for r in rows if group_of(r) == group]
    return rows[:GAMES]


def _average(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Averages per game of `rows` (None where no game has the number)."""
    decided = [r for r in rows if r.get("win") is not None]

    def per_game(key: str) -> float | None:
        return _average([float(r[key]) for r in rows if isinstance(r.get(key), (int, float))])

    def per_minute(key: str) -> float | None:
        values = []
        for row in rows:
            minutes = _minutes(row)
            if minutes and isinstance(row.get(key), (int, float)):
                values.append(row[key] / minutes)
        return _average(values)

    result: dict[str, Any] = {
        "games": len(rows),
        "win_rate": round(100 * sum(1 for r in decided if r["win"]) / len(decided))
        if decided
        else None,
    }
    for key in ("kills", "deaths", "assists"):
        value = per_game(key)
        result[key] = None if value is None else round(value, 1)
    for key in ("gpm", "xpm"):
        value = per_game(key)
        result[key] = None if value is None else round(value)
    lh = per_minute("last_hits")
    result["lh_per_min"] = None if lh is None else round(lh, 1)
    damage = per_minute("hero_damage")
    result["damage_per_min"] = None if damage is None else round(damage)
    return result


def _better(me: Any, friend: Any, higher: bool) -> str | None:
    if not isinstance(me, (int, float)) or not isinstance(friend, (int, float)):
        return None
    scale = max(abs(me), abs(friend), 1e-9)
    if abs(me - friend) / scale < SAME_SHARE:
        return "same"
    return "me" if (me > friend) == higher else "friend"


def _heroes(rows: list[dict[str, Any]]) -> dict[int, dict[str, int]]:
    table: dict[int, dict[str, int]] = defaultdict(lambda: {"games": 0, "wins": 0})
    for row in rows:
        hero_id = row.get("hero_id")
        if not isinstance(hero_id, int) or hero_id <= 0:
            continue
        table[hero_id]["games"] += 1
        table[hero_id]["wins"] += 1 if row.get("win") else 0
    return table


def _hero_row(hero_id: int, stats: dict[str, int]) -> dict[str, Any]:
    return {
        "hero_id": hero_id,
        "hero": hero_name(hero_id),
        "games": stats["games"],
        "win_rate": round(100 * stats["wins"] / stats["games"]) if stats["games"] else None,
    }


def compare(
    mine: list[dict[str, Any]], theirs: list[dict[str, Any]], group: str = "all"
) -> dict[str, Any]:
    """Both players' reviewable match summaries -> the comparison of `group`."""
    group = group if group in GROUPS else "all"
    me_rows, friend_rows = _pick(mine, group), _pick(theirs, group)
    me, friend = summary(me_rows), summary(friend_rows)
    enough = me["games"] >= MIN_GAMES and friend["games"] >= MIN_GAMES
    rows = [
        {
            "key": key,
            "me": me.get(key),
            "friend": friend.get(key),
            "better": _better(me.get(key), friend.get(key), higher) if enough else None,
        }
        for key, higher in METRICS
    ]
    my_heroes, their_heroes = _heroes(me_rows), _heroes(friend_rows)
    common = sorted(
        set(my_heroes) & set(their_heroes),
        key=lambda h: -(my_heroes[h]["games"] + their_heroes[h]["games"]),
    )[:COMMON_HEROES]
    top = sorted(their_heroes, key=lambda h: -their_heroes[h]["games"])[:TOP_HEROES]
    groups = {
        name: {
            "me": len(_pick(mine, name)),
            "friend": len(_pick(theirs, name)),
        }
        for name in GROUPS
    }
    return {
        "group": group,
        "groups": groups,
        "enough": enough,
        "min_games": MIN_GAMES,
        "games": {"me": me["games"], "friend": friend["games"]},
        "rows": rows,
        "common_heroes": [
            {
                "hero_id": h,
                "hero": hero_name(h),
                "me": _hero_row(h, my_heroes[h]),
                "friend": _hero_row(h, their_heroes[h]),
            }
            for h in common
        ],
        "friend_heroes": [_hero_row(h, their_heroes[h]) for h in top],
    }
