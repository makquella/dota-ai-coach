"""
enemy_heroes.py - the enemy heroes of the live match, for counter items.

A player's GSI has no draft (that block is for spectators), but its `minimap`
block lists the units on the player's minimap — the enemy heroes the team can
see among them (`unitname` npc_dota_hero_*, `team` 2 Radiant / 3 Dire). Every
enemy hero seen once is remembered for the match (MatchMemory resets it), so
the list fills up as the enemies show themselves. No minimap block (an older
GSI config, or a client that does not send it) → nothing is known and no
counter advice is given.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

TEAMS = {"radiant": 2, "dire": 3}
MAX_ENEMIES = 5
HERO_PREFIX = "npc_dota_hero_"


def visible_enemy_heroes(
    minimap: Any, team_name: Any, normalize: Callable[[Any], str]
) -> list[str] | None:
    """Enemy hero names on this tick's minimap; None without a minimap block
    or a known team."""
    own = TEAMS.get(str(team_name or "").strip().lower())
    if not isinstance(minimap, dict) or own is None:
        return None
    names: list[str] = []
    for unit in minimap.values():
        if not isinstance(unit, dict):
            continue
        raw = unit.get("unitname")
        team = unit.get("team")
        if not isinstance(raw, str) or not raw.lower().startswith(HERO_PREFIX):
            continue
        if isinstance(team, bool) or team not in (2, 3) or team == own:
            continue
        name = normalize(raw)
        if name and name not in names:
            names.append(name)
    return names


class EnemyHeroes:
    """The enemy heroes seen so far in the match (first seen first, at most 5)."""

    def __init__(self) -> None:
        self._seen: list[str] = []

    def observe(self, names: Any) -> None:
        if not isinstance(names, list):
            return
        for name in names:
            if isinstance(name, str) and name not in self._seen and len(self._seen) < MAX_ENEMIES:
                self._seen.append(name)

    def heroes(self) -> list[str]:
        return list(self._seen)
