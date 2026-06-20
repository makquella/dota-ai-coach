"""
item_timing.py - editable item timing classification for offline imports.

The rules live in data/meta/item_timing_rules.json so carry timing decisions can
be tuned without changing Python code.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
RULES_PATH = REPO_ROOT / "data" / "meta" / "item_timing_rules.json"

DEFAULT_RULES: dict[str, Any] = {
    "ignore_items": [
        "Branches",
        "Iron Branch",
        "Tango",
        "Magic Stick",
        "Magic Wand",
        "Boots",
        "Boots of Speed",
        "Power Treads",
        "Orb of Venom",
        "Blight Stone",
        "Ogre Axe",
        "Mithril Hammer",
        "Ring of Health",
        "Void Stone",
        "Pers",
    ],
    "meaningful_items": {
        "farming_timings": ["Battle Fury", "Maelstrom", "Mjollnir", "Radiance"],
        "fight_timings": ["Black King Bar", "Mage Slayer", "Desolator", "Disperser"],
        "defensive_timings": ["Black King Bar", "Manta Style", "Satanic", "Butterfly"],
        "mobility_timings": ["Blink Dagger", "Silver Edge", "Disperser"],
        "damage_timings": ["Daedalus", "Monkey King Bar", "Desolator"],
        "late_game_timings": ["Abyssal Blade", "Satanic", "Butterfly", "Disperser"],
        "situational_timings": ["Nullifier", "Monkey King Bar", "Linken's Sphere"],
    },
    "component_items": [],
    "min_meaningful_item_cost": 2500,
    "category_priority": [
        "defensive_timings",
        "farming_timings",
        "mobility_timings",
        "damage_timings",
        "late_game_timings",
        "fight_timings",
        "situational_timings",
    ],
    "item_aliases": {
        "bfury": "Battle Fury",
        "bkb": "Black King Bar",
        "manta": "Manta Style",
        "mkb": "Monkey King Bar",
        "skadi": "Eye of Skadi",
    },
    "item_ids": {
        "116": "Black King Bar",
        "145": "Battle Fury",
        "147": "Manta Style",
        "168": "Desolator",
        "598": "Mage Slayer",
        "1097": "Disperser",
    },
    "item_costs": {
        "Black King Bar": 4050,
        "Battle Fury": 3900,
        "Desolator": 3500,
        "Disperser": 6100,
        "Mage Slayer": 3100,
    },
}


def normalize_item_name(raw_item: Any) -> str:
    """Normalize OpenDota keys, ids, and display names into canonical item names."""

    if raw_item is None:
        return ""

    raw = str(raw_item).strip()
    if not raw:
        return ""

    rules = load_item_timing_rules()
    if raw.isdigit():
        item_from_id = rules.get("item_ids", {}).get(str(int(raw)))
        if item_from_id:
            return normalize_item_name(item_from_id)
        return f"Item {int(raw)}"

    key = normalize_item_key(raw)
    aliases = _normalized_aliases(rules)
    if key in aliases:
        return aliases[key]

    canonical = _canonical_names_by_key(rules)
    if key in canonical:
        return canonical[key]

    if key.startswith("recipe_") or key == "recipe":
        return "Recipe"

    return _title_from_key(key)


def normalize_item_key(raw_item: Any) -> str:
    raw = str(raw_item or "").strip().lower().replace("'", "")
    raw = raw.removeprefix("item_recipe_")
    raw = raw.removeprefix("recipe_")
    raw = raw.removeprefix("item_")
    raw = re.sub(r"[^a-z0-9]+", "_", raw)
    return raw.strip("_")


def classify_item_timing(raw_item: Any) -> dict[str, Any]:
    item = normalize_item_name(raw_item)
    if not item or is_ignored_item(raw_item) or is_ignored_item(item):
        return {"item": item, "is_meaningful": False, "category": None, "cost": 0}

    category = item_timing_category(item)
    cost = item_cost(item)
    if category:
        return {"item": item, "is_meaningful": True, "category": category, "cost": cost}

    min_cost = int(load_item_timing_rules().get("min_meaningful_item_cost", 2500))
    if cost >= min_cost:
        return {
            "item": item,
            "is_meaningful": True,
            "category": "situational_timings",
            "cost": cost,
        }

    return {"item": item, "is_meaningful": False, "category": None, "cost": cost}


def is_meaningful_item_timing(raw_item: Any) -> bool:
    return bool(classify_item_timing(raw_item)["is_meaningful"])


def item_timing_category(raw_item: Any) -> str | None:
    item_key = normalize_item_key(normalize_item_name(raw_item))
    if not item_key:
        return None

    rules = load_item_timing_rules()
    matches: list[str] = []
    for category, items in rules.get("meaningful_items", {}).items():
        if item_key in {normalize_item_key(item) for item in items}:
            matches.append(category)

    if not matches:
        return None

    for category in rules.get("category_priority", []):
        if category in matches:
            return category
    return matches[0]


def item_cost(raw_item: Any) -> int:
    item = normalize_item_name(raw_item)
    key = normalize_item_key(item)
    for configured_item, cost in load_item_timing_rules().get("item_costs", {}).items():
        if normalize_item_key(configured_item) == key:
            try:
                return int(cost)
            except (TypeError, ValueError):
                return 0
    return 0


def is_ignored_item(raw_item: Any) -> bool:
    original = str(raw_item or "").strip().lower()
    if original.startswith("recipe") or original.startswith("item_recipe"):
        return True
    if original.startswith("neutral") or original.startswith("item_neutral"):
        return True

    raw_key = normalize_item_key(raw_item)
    item_key = normalize_item_key(normalize_item_name(raw_item))
    if not item_key:
        return True
    if raw_key.startswith("recipe") or item_key == "recipe":
        return True
    if raw_key.startswith("neutral") or raw_key.startswith("item_neutral"):
        return True

    rules = load_item_timing_rules()
    ignored = {normalize_item_key(item) for item in rules.get("ignore_items", [])}
    components = {normalize_item_key(item) for item in rules.get("component_items", [])}
    return item_key in ignored or item_key in components


def contains_meaningful_item_reference(text: str, items: list[Any] | None = None) -> bool:
    if items and any(is_meaningful_item_timing(item) for item in items):
        return True

    normalized_text = normalize_item_key(text)
    if not normalized_text:
        return False

    for item in meaningful_item_names():
        key = normalize_item_key(item)
        if key and key in normalized_text:
            return True
    return False


def meaningful_item_names() -> list[str]:
    rules = load_item_timing_rules()
    names: list[str] = []
    seen: set[str] = set()
    for items in rules.get("meaningful_items", {}).values():
        for item in items:
            name = normalize_item_name(item)
            key = normalize_item_key(name)
            if key and key not in seen:
                names.append(name)
                seen.add(key)
    return names


@lru_cache(maxsize=1)
def load_item_timing_rules() -> dict[str, Any]:
    if not RULES_PATH.exists():
        return DEFAULT_RULES

    try:
        loaded = json.loads(RULES_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return DEFAULT_RULES

    if not isinstance(loaded, dict):
        return DEFAULT_RULES
    return {**DEFAULT_RULES, **loaded}


@lru_cache(maxsize=1)
def _canonical_names_by_key_cached() -> dict[str, str]:
    return _canonical_names_by_key(load_item_timing_rules())


def _canonical_names_by_key(rules: dict[str, Any]) -> dict[str, str]:
    canonical: dict[str, str] = {}
    collections: list[Any] = [
        rules.get("ignore_items", []),
        rules.get("component_items", []),
        rules.get("item_costs", {}).keys(),
        rules.get("item_aliases", {}).values(),
    ]
    collections.extend(rules.get("meaningful_items", {}).values())

    for collection in collections:
        for item in collection:
            name = _title_from_key(normalize_item_key(item))
            canonical[normalize_item_key(item)] = _display_name_fix(str(item), name)
    return canonical


def _normalized_aliases(rules: dict[str, Any]) -> dict[str, str]:
    aliases: dict[str, str] = {}
    for key, value in rules.get("item_aliases", {}).items():
        aliases[normalize_item_key(key)] = normalize_item_name_without_alias(value, rules)
    return aliases


def normalize_item_name_without_alias(raw_item: Any, rules: dict[str, Any]) -> str:
    key = normalize_item_key(raw_item)
    canonical = _canonical_names_by_key(rules)
    if key in canonical:
        return canonical[key]
    return _title_from_key(key)


def _title_from_key(key: str) -> str:
    if not key:
        return ""
    words = key.replace("_", " ").split()
    lowered = {"and", "of", "the"}
    title = " ".join(word if word in lowered else word.capitalize() for word in words)
    return _display_name_fix(key, title)


def _display_name_fix(raw: str, name: str) -> str:
    fixes = {
        "Bkb": "Black King Bar",
        "Mkb": "Monkey King Bar",
        "Bfury": "Battle Fury",
        "Aghanims Scepter": "Aghanim's Scepter",
        "Aghanims Shard": "Aghanim's Shard",
        "Greater Crit": "Daedalus",
        "Lesser Crit": "Crystalys",
        "Pers": "Pers",
    }
    return fixes.get(name, name)
