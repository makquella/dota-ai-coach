"""
stratz_builds.py - what high-rank players buy on a hero (data/meta/stratz_builds.json).

The file is written once a week by scripts/build_stratz_builds.py (the STRATZ
token lives in a repository secret, never in the app) and travels with the app:
per hero and position (pos1 carry … pos5 hard support) the starting purchase
[[item key, copies]] and the build [[item key, usual minute, % of games, win %]]
of the Divine–Immortal bracket. No file, an unknown hero or a position nobody
plays it in → nothing, and the callers fall back to OpenDota's popularity.
"""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from app.config import DATA_DIR
from app.hero_profiles import get_support_position
from app.item_timing import normalize_item_name

PATH = DATA_DIR / "meta" / "stratz_builds.json"
ROLE_POSITION = {"carry": "pos1", "mid": "pos2", "offlane": "pos3"}


@lru_cache(maxsize=1)
def _data() -> dict[str, Any]:
    try:
        data = json.loads(PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _name(key: str) -> str:
    names = _data().get("names") or {}
    return str(names.get(key) or normalize_item_name(key))


def _entry(hero_id: int | None, hero: str, role: str | None) -> dict[str, Any] | None:
    """The hero's data for the player's role: carry pos1, mid pos2, offlane pos3,
    support the hero's support position (4 or 5) else the busier of the two;
    no role → the position the hero is played in most."""
    if hero_id is None:
        return None
    positions = (_data().get("heroes") or {}).get(str(hero_id))
    if not isinstance(positions, dict) or not positions:
        return None
    if role in ROLE_POSITION:
        return positions.get(ROLE_POSITION[role])
    if role == "support":
        own = get_support_position(hero) if hero else None
        if own in (4, 5) and f"pos{own}" in positions:
            return positions[f"pos{own}"]
        supports = [positions[p] for p in ("pos4", "pos5") if p in positions]
        return max(supports, key=lambda e: e.get("games", 0)) if supports else None
    return max(positions.values(), key=lambda e: e.get("games", 0))


def start_items(hero_id: int | None, hero: str, role: str | None) -> list[dict[str, Any]]:
    """[{key, name, count}] of the usual start; a second copy is named «Iron Branch ×2»."""
    entry = _entry(hero_id, hero, role)
    rows = []
    for row in (entry or {}).get("start") or []:
        if not isinstance(row, list) or not row or not isinstance(row[0], str):
            continue
        count = int(row[1]) if len(row) > 1 and isinstance(row[1], int) else 1
        name = _name(row[0])
        rows.append(
            {"key": row[0], "name": f"{name} ×{count}" if count > 1 else name, "count": count}
        )
    return rows


def build(hero_id: int | None, hero: str, role: str | None) -> list[dict[str, Any]]:
    """[{key, name, minute, share, win}] in the order the items are finished."""
    entry = _entry(hero_id, hero, role)
    rows = []
    for row in (entry or {}).get("build") or []:
        if not isinstance(row, list) or len(row) < 4 or not isinstance(row[0], str):
            continue
        rows.append(
            {"key": row[0], "name": _name(row[0]), "minute": row[1], "share": row[2], "win": row[3]}
        )
    return rows


def bracket() -> str | None:
    """The bracket of the data (for the card's wording), None without a file."""
    value = _data().get("bracket")
    return str(value) if value else None
