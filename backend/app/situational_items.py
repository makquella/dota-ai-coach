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


def situational_item(
    deaths: list[dict[str, Any]] | None,
    owned_names: list[str] | None,
    meta: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """{key, name, cost, gold_left (None when the price is unknown), why, count}
    for the first rule with MIN_DEATHS deaths of its kind; None otherwise."""
    if not deaths or owned_names is None:
        return None
    kinds = Counter(death_kind(death.get("last")) for death in deaths if isinstance(death, dict))
    constants = (meta or {}).get("constants") or {}
    priced = has_components(constants)
    owned = [item_key(name) for name in owned_names]
    for why, key, fallback in RULES:
        count = kinds.get(why, 0)
        if count < MIN_DEATHS:
            continue
        if key in owned or (priced and any(_contains(have, key, constants) for have in owned)):
            continue
        cost = _cost(key, constants) if priced else 0
        return {
            "key": key,
            "name": item_name(key, constants) if priced else fallback,
            "cost": cost or None,
            "gold_left": gold_left(key, Counter(owned), constants) if cost else None,
            "why": why,
            "count": count,
        }
    return None
