"""
next_item.py - the next build item for the live farm advice of a core.

«Black King Bar is next in most builds: 1250 gold to go, about 3 minutes at
your pace» instead of a plain «keep farming». Everything comes from data the
app already has:

- the build: the hero's most bought mid- and late-game items (OpenDota item
  popularity, cached by PlayerService like the game plan's key item);
- what the player owns: item names of the live GSI inventory, backpack and stash;
- the price: the item constants' cost and components, so parts already bought
  (Ogre Axe for Black King Bar) are not counted again.

Nothing is guessed: no cached build, no components in the cached constants
(older caches) or no items block in GSI -> no item.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from app.hero_meta import item_key, item_name, popular_build

# Nested recipes are a few levels deep; this only stops a broken table.
MAX_DEPTH = 6


def _info(key: str, constants: dict[str, Any]) -> dict[str, Any] | None:
    info = (constants.get("items") or {}).get(key)
    return info if isinstance(info, dict) else None


def _cost(key: str, constants: dict[str, Any]) -> int:
    info = _info(key, constants) or {}
    cost = info.get("cost")
    return int(cost) if isinstance(cost, (int, float)) and cost > 0 else 0


def _components(key: str, constants: dict[str, Any]) -> list[str]:
    parts = (_info(key, constants) or {}).get("components")
    return [item_key(p) for p in parts if isinstance(p, str)] if isinstance(parts, list) else []


def _contains(parent: str, key: str, constants: dict[str, Any], depth: int = 0) -> bool:
    """Whether `key` is a part (at any depth) of `parent`."""
    if depth > MAX_DEPTH:
        return False
    for part in _components(parent, constants):
        if part == key or _contains(part, key, constants, depth + 1):
            return True
    return False


def gold_left(key: str, owned: Counter[str], constants: dict[str, Any], depth: int = 0) -> int:
    """The gold still needed for `key` when the parts in `owned` are used
    (they are taken out of `owned`, so one part is never counted twice)."""
    if owned.get(key, 0) > 0:
        owned[key] -= 1
        return 0
    cost = _cost(key, constants)
    parts = _components(key, constants)
    if not parts or depth > MAX_DEPTH:
        return cost
    recipe = max(0, cost - sum(_cost(part, constants) for part in parts))
    return recipe + sum(gold_left(part, owned, constants, depth + 1) for part in parts)


def missing_parts(
    key: str, owned: Counter[str], constants: dict[str, Any], depth: int = 0
) -> list[tuple[str, int]]:
    """The parts of `key` still to buy with their prices, in the order the shop
    lists them: a part the player has (or has built) is taken out of `owned`; a
    part with parts of its own gives those (Mithril Hammer is never the step when
    Ogre Axe is); when only a recipe is left, the item comes with the recipe's price."""
    if owned.get(key, 0) > 0:
        owned[key] -= 1
        return []
    parts = _components(key, constants)
    if not parts or depth > MAX_DEPTH:
        return [(key, _cost(key, constants))]
    result: list[tuple[str, int]] = []
    for part in parts:
        result.extend(missing_parts(part, owned, constants, depth + 1))
    recipe = _cost(key, constants) - sum(_cost(part, constants) for part in parts)
    if recipe > 0 and not result:
        return [(key, recipe)]
    return result


def buy_now(
    key: str, owned_names: list[str], constants: dict[str, Any], gold: int
) -> dict[str, Any] | None:
    """The quick-buy step: the most expensive missing part of `key` that `gold`
    already buys ({key, name, cost}); None when no part fits the gold."""
    parts = missing_parts(key, Counter(item_key(n) for n in owned_names), constants)
    affordable = [(part, cost) for part, cost in parts if 0 < cost <= gold]
    if not affordable:
        return None
    part, cost = max(affordable, key=lambda row: row[1])
    return {"key": part, "name": item_name(part, constants), "cost": cost}


def has_components(constants: dict[str, Any] | None) -> bool:
    """Whether the cached item constants carry the components (kept since 0.12)."""
    items = (constants or {}).get("items") or {}
    return any(isinstance(info, dict) and "components" in info for info in items.values())


def next_build_item(
    meta: dict[str, Any] | None, owned_names: list[str] | None
) -> dict[str, Any] | None:
    """{key, name, cost, gold_left} of the first popular mid/late item the player
    neither owns nor has already built into something bigger; None when unknown."""
    if not meta or owned_names is None:
        return None
    constants = meta.get("constants") or {}
    # Without the components (constants cached by an older version) the price
    # of the missing parts cannot be told.
    if not has_components(constants):
        return None
    build = popular_build(meta.get("popularity"), constants)
    owned = [item_key(name) for name in owned_names]
    for entry in (build.get("mid") or []) + (build.get("late") or []):
        key = entry["key"]
        if key in owned or any(_contains(have, key, constants) for have in owned):
            continue
        cost = _cost(key, constants)
        if cost <= 0:
            continue
        return {
            "key": key,
            "name": item_name(key, constants),
            "cost": cost,
            "gold_left": gold_left(key, Counter(owned), constants),
        }
    return None


# How many items per phase the save item is looked for in: a support's build
# lists boots and wards first, so the top four can miss it.
SAVE_SEARCH = 10


def save_build_item(
    meta: dict[str, Any] | None, owned_names: list[str] | None, candidates: set[str]
) -> dict[str, Any] | None:
    """{key, name, cost, gold_left} of the save item (one of `candidates`) most
    bought on the hero, mid game first; None when the build is unknown, the
    player owns one or none of them is in the build."""
    if not meta or owned_names is None:
        return None
    constants = meta.get("constants") or {}
    if not has_components(constants):
        return None
    candidates = {item_key(name) for name in candidates}
    owned = [item_key(name) for name in owned_names]
    if any(
        key in candidates or any(_contains(key, c, constants) for c in candidates) for key in owned
    ):
        return None  # a save item (or one built from it, Hurricane Pike) is there
    build = popular_build(meta.get("popularity"), constants, per_phase=SAVE_SEARCH)
    for entry in (build.get("mid") or []) + (build.get("early") or []) + (build.get("late") or []):
        key = entry["key"]
        cost = _cost(key, constants)
        if key in candidates and cost > 0:
            return {
                "key": key,
                "name": item_name(key, constants),
                "cost": cost,
                "gold_left": gold_left(key, Counter(owned), constants),
            }
    return None
