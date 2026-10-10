"""
situational_items.py - the next item picked by how the player dies in this
match, before the hero's usual build (next_item.py).

The live recording already knows the last seconds of every death
(last_moments.py): how many of the last 5 seconds the hero was free to act
(`free_s`) and whether it went from 70 %+ health to dead in 3 seconds or less
(`burst_s`). Two such deaths in one match are a pattern with a known answer:

- disabled to death (stunned or hexed on all but at most 1 recorded second of
  the last 5, with at least 3 seconds recorded; a mute alone does not count —
  the hero still moves and casts, and BKB cannot be pressed muted): Black King
  Bar — magic immunity, no stun holds you;
- burst down: Aeon Disk — the next burst triggers it instead of killing.

`draft_item` is the same counter to the enemy lineup, read early (DRAFT_MIN_ENEMIES
heroes seen) as an item to plan for, without the minute gates.

Cores only (the carry advisor): a support's item advice is the save item tip.
Nothing when the item (or something built from it) is already owned.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from app.hero_meta import item_key, item_name
from app.next_item import _contains, _cost, gold_left, has_components

MIN_DEATHS = 2
FREE_WINDOW = 5
MIN_RECORDED = 3
MAX_FREE = 1

RULES = (
    # (why, item key, English name when the item constants are not cached)
    ("disabled", "black_king_bar", "Black King Bar"),
    ("burst", "aeon_disk", "Aeon Disk"),
)


def death_kind(last: Any) -> str | None:
    """'disabled', 'burst' or None for one death's last-moments summary."""
    if not isinstance(last, dict):
        return None
    hp = last.get("hp") if isinstance(last.get("hp"), list) else []
    recorded = [p for p in hp if isinstance(p, list) and len(p) == 2 and -FREE_WINDOW <= p[0] <= 0]
    held = last.get("held_s")  # older records have none: say nothing
    if len(recorded) >= MIN_RECORDED and isinstance(held, int) and len(recorded) - held <= MAX_FREE:
        return "disabled"
    if isinstance(last.get("burst_s"), int):
        return "burst"
    return None


# Counters to the enemy heroes seen in the match (enemy_heroes.py), by the
# player's usual position: a right-click carry against evasion, an offlaner
# against heavy healing; from these minutes on, when the build usually has room.
EVASION_MINUTE = 15
HEALING_MINUTE = 12
ILLUSION_MINUTE = 12
# A lineup of magic damage (draft_analysis.MAGIC_DAMAGE, 3+ seen): Pipe of
# Insight for an offlaner, Black King Bar for a carry or a mid.
MAGIC_MINUTE = 14
# Heroes whose strength is a passive that break (Silver Edge) turns off; for a
# carry or a mid from this minute on.
BREAK_PASSIVES = {
    "Bristleback": "Bristleback",
    "Spectre": "Dispersion",
    "Huskar": "Berserker's Blood",
}
BREAK_MINUTE = 18
CORE_POSITIONS = {"carry", "mid", "offlane"}
# The early read of the enemy draft: once this many enemy heroes are seen.
DRAFT_MIN_ENEMIES = 4
# Past every minute gate above: the draft read names the item to plan for.
_ANY_MINUTE = 60


def _candidates(
    kinds: Counter[str | None],
    enemies: list[str],
    position: str | None,
    minute: int | None,
) -> list[tuple[str, str, str, int, str | None, str | None]]:
    """(why, item key, fallback name, deaths, enemy, spell), in priority order."""
    from app.draft_analysis import (
        COUNTERS,
        MAGIC_DAMAGE,
        MAGIC_LINEUP_MIN,
        TARGETED_DISABLES,
        TARGETED_ITEM,
        TARGETED_NAME,
    )

    rows: list[tuple[str, str, str, int, str | None, str | None]] = []
    targeted = next((e for e in enemies if e in TARGETED_DISABLES), None)
    if targeted and position in CORE_POSITIONS and kinds.get("disabled", 0) >= MIN_DEATHS:
        # Held to death with a single-target disable in the enemy team: Linken's
        # blocks it (Primal Roar, Duel and Doom go through BKB).
        rows.append(
            (
                "targeted",
                TARGETED_ITEM,
                TARGETED_NAME,
                kinds["disabled"],
                targeted,
                TARGETED_DISABLES[targeted],
            )
        )
    for why, key, fallback in RULES:
        if kinds.get(why, 0) >= MIN_DEATHS:
            rows.append((why, key, fallback, kinds[why], None, None))
    evasive = next((e for e in enemies if e in COUNTERS["evasion"][0]), None)
    if evasive and position == "carry" and (minute or 0) >= EVASION_MINUTE:
        rows.append(("evasion", "monkey_king_bar", "Monkey King Bar", 0, evasive, None))
    illusionist = next((e for e in enemies if e in COUNTERS["illusions"][0]), None)
    if illusionist and position == "carry" and (minute or 0) >= ILLUSION_MINUTE:
        rows.append(("illusions", "maelstrom", "Maelstrom", 0, illusionist, None))
    healer = next((e for e in enemies if e in COUNTERS["healing"][0]), None)
    if healer and position == "offlane" and (minute or 0) >= HEALING_MINUTE:
        rows.append(("healing", "spirit_vessel", "Spirit Vessel", 0, healer, None))
    passive = next((e for e in enemies if e in BREAK_PASSIVES), None)
    if passive and position in ("carry", "mid") and (minute or 0) >= BREAK_MINUTE:
        rows.append(("break", "silver_edge", "Silver Edge", 0, passive, BREAK_PASSIVES[passive]))
    magic = [e for e in enemies if e in MAGIC_DAMAGE]
    if len(magic) >= MAGIC_LINEUP_MIN and (minute or 0) >= MAGIC_MINUTE:
        if position == "offlane":
            rows.append(("magic", "pipe", "Pipe of Insight", len(magic), magic[0], None))
        elif position in ("carry", "mid"):
            rows.append(("magic", "black_king_bar", "Black King Bar", len(magic), magic[0], None))
    return rows


def situational_item(
    deaths: list[dict[str, Any]] | None,
    owned_names: list[str] | None,
    meta: dict[str, Any] | None,
    *,
    enemies: list[str] | None = None,
    position: str | None = None,
    minute: int | None = None,
) -> dict[str, Any] | None:
    """{key, name, cost, gold_left (None when the price is unknown), why, count,
    enemy, spell} for the first rule that holds: MIN_DEATHS deaths of its kind
    (a single-target disabler among the enemies turns BKB into Linken's), else
    a counter to an enemy hero seen; None otherwise."""
    if owned_names is None:
        return None
    kinds = Counter(
        death_kind(death.get("last")) for death in deaths or [] if isinstance(death, dict)
    )
    constants = (meta or {}).get("constants") or {}
    priced = has_components(constants)
    known = (constants.get("items") or {}) if priced else {}
    owned = [item_key(name) for name in owned_names]
    enemy_list = [e for e in enemies or [] if isinstance(e, str)]
    for why, key, fallback, count, enemy, spell in _candidates(kinds, enemy_list, position, minute):
        if key in owned or (priced and any(_contains(have, key, constants) for have in owned)):
            continue
        cost = _cost(key, constants) if priced else 0
        return {
            "key": key,
            "name": item_name(key, constants) if key in known else fallback,
            "cost": cost or None,
            "gold_left": gold_left(key, Counter(owned), constants) if cost else None,
            "why": why,
            "count": count,
            "enemy": enemy,
            "spell": spell,
        }
    return None


def draft_item(
    enemies: list[str] | None,
    owned_names: list[str] | None,
    meta: dict[str, Any] | None,
    position: str | None,
) -> dict[str, Any] | None:
    """The counter item to plan for against the enemy lineup (situational_item's
    enemy counters, no deaths and no minute gates) once DRAFT_MIN_ENEMIES enemy
    heroes are seen; cores only. None otherwise or when it is already owned."""
    seen = [e for e in enemies or [] if isinstance(e, str)]
    if position not in CORE_POSITIONS or len(seen) < DRAFT_MIN_ENEMIES:
        return None
    return situational_item(
        [], owned_names, meta, enemies=seen, position=position, minute=_ANY_MINUTE
    )


def lineup_save_item(
    enemies: list[str] | None,
    owned_names: list[str] | None,
    meta: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """The support's save item against the enemy lineup: Glimmer Cape against
    MAGIC_LINEUP_MIN heroes of magic damage, Ghost Scepter against
    PHYSICAL_LINEUP_MIN right-click carries — {key, name, cost, gold_left
    (None without priced constants), why, count, enemy}; None otherwise or when
    the player already has it (or something built from it)."""
    from app.draft_analysis import (
        MAGIC_DAMAGE,
        MAGIC_LINEUP_MIN,
        PHYSICAL_CARRIES,
        PHYSICAL_LINEUP_MIN,
    )

    if owned_names is None:
        return None
    seen = [e for e in enemies or [] if isinstance(e, str)]
    magic = [e for e in seen if e in MAGIC_DAMAGE]
    physical = [e for e in seen if e in PHYSICAL_CARRIES]
    if len(magic) >= MAGIC_LINEUP_MIN:
        why, key, fallback, heroes = "magic", "glimmer_cape", "Glimmer Cape", magic
    elif len(physical) >= PHYSICAL_LINEUP_MIN:
        why, key, fallback, heroes = "physical", "ghost", "Ghost Scepter", physical
    else:
        return None
    constants = (meta or {}).get("constants") or {}
    priced = has_components(constants)
    owned = [item_key(name) for name in owned_names]
    if key in owned or (priced and any(_contains(have, key, constants) for have in owned)):
        return None
    known = (constants.get("items") or {}) if priced else {}
    cost = _cost(key, constants) if priced else 0
    return {
        "key": key,
        "name": item_name(key, constants) if key in known else fallback,
        "cost": cost or None,
        "gold_left": gold_left(key, Counter(owned), constants) if cost else None,
        "why": why,
        "count": len(heroes),
        "enemy": heroes[0],
    }
