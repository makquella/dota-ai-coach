"""
cosmetics.py - profile looks bought with sparks (the «Профіль» tab's shop).

Four kinds, one item of each equipped at a time: an avatar frame, a banner,
the name's colour and a title under the name. An item has a price in sparks
and may need a level or an achievement tier (player_profile.py) — the rare
ones are something to show. The visuals are CSS classes in the launcher
(`cos-<id>`); this module only knows ids, prices and conditions.

State in meta `cosmetics:<account>` (JSON): {"owned": [ids], "equipped":
{kind: id}}. Spent sparks are the prices of the owned items, so the balance
can never be spent twice. Free items (price 0) are owned by everyone.
"""

from __future__ import annotations

import json
from typing import Any

KINDS = ("frame", "banner", "name", "title")

# id, kind, price, level needed, (achievement id, tier) needed, uk / en name.
CATALOG: list[dict[str, Any]] = [
    # Avatar frames.
    {"id": "frame_plain", "kind": "frame", "price": 0, "uk": "Звичайна", "en": "Plain"},
    {"id": "frame_bronze", "kind": "frame", "price": 150, "uk": "Бронза", "en": "Bronze"},
    {"id": "frame_silver", "kind": "frame", "price": 300, "uk": "Срібло", "en": "Silver"},
    {"id": "frame_gold", "kind": "frame", "price": 600, "level": 5, "uk": "Золото", "en": "Gold"},
    {"id": "frame_ice", "kind": "frame", "price": 800, "level": 8, "uk": "Лід", "en": "Ice"},
    {
        "id": "frame_fire",
        "kind": "frame",
        "price": 1200,
        "level": 12,
        "uk": "Полум'я",
        "en": "Flame",
    },
    {
        "id": "frame_arcana",
        "kind": "frame",
        "price": 2500,
        "level": 20,
        "uk": "Аркана",
        "en": "Arcana",
    },
    {
        "id": "frame_champion",
        "kind": "frame",
        "price": 0,
        "achievement": ("app_wins", 3),
        "uk": "Чемпіон",
        "en": "Champion",
    },
    # Banners.
    {"id": "banner_plain", "kind": "banner", "price": 0, "uk": "Штрихи", "en": "Strokes"},
    {"id": "banner_dusk", "kind": "banner", "price": 200, "uk": "Сутінки", "en": "Dusk"},
    {"id": "banner_radiant", "kind": "banner", "price": 350, "uk": "Світло", "en": "Radiant"},
    {"id": "banner_dire", "kind": "banner", "price": 350, "uk": "Темрява", "en": "Dire"},
    {
        "id": "banner_aurora",
        "kind": "banner",
        "price": 900,
        "level": 8,
        "uk": "Північне сяйво",
        "en": "Aurora",
    },
    {
        "id": "banner_ember",
        "kind": "banner",
        "price": 1400,
        "level": 15,
        "uk": "Жарини",
        "en": "Embers",
    },
    {
        "id": "banner_climb",
        "kind": "banner",
        "price": 0,
        "achievement": ("mmr_gain", 3),
        "uk": "Сходження",
        "en": "Ascent",
    },
    # Name colours.
    {"id": "name_plain", "kind": "name", "price": 0, "uk": "Звичайний", "en": "Plain"},
    {"id": "name_gold", "kind": "name", "price": 250, "uk": "Золотий", "en": "Gold"},
    {"id": "name_ice", "kind": "name", "price": 250, "uk": "Крижаний", "en": "Ice"},
    {"id": "name_toxic", "kind": "name", "price": 250, "uk": "Отруйний", "en": "Toxic"},
    {
        "id": "name_prism",
        "kind": "name",
        "price": 1500,
        "level": 15,
        "uk": "Призма",
        "en": "Prism",
    },
    # Titles under the name.
    {"id": "title_none", "kind": "title", "price": 0, "uk": "Без титулу", "en": "No title"},
    {"id": "title_farmer", "kind": "title", "price": 120, "uk": "Фармило", "en": "Farmer"},
    {
        "id": "title_support",
        "kind": "title",
        "price": 120,
        "uk": "Саппорт від бога",
        "en": "Born support",
    },
    {"id": "title_tryhard", "kind": "title", "price": 120, "uk": "Трайхардер", "en": "Tryhard"},
    {
        "id": "title_immortal",
        "kind": "title",
        "price": 0,
        "achievement": ("few_deaths", 2),
        "uk": "Невбиваний",
        "en": "Unkillable",
    },
    {
        "id": "title_coached",
        "kind": "title",
        "price": 0,
        "achievement": ("app_games", 3),
        "uk": "Учень тренера",
        "en": "Coached",
    },
    {
        "id": "title_legend",
        "kind": "title",
        "price": 3000,
        "level": 25,
        "uk": "Легенда Wardly",
        "en": "Wardly legend",
    },
]
BY_ID = {item["id"]: item for item in CATALOG}
DEFAULTS = {
    "frame": "frame_plain",
    "banner": "banner_plain",
    "name": "name_plain",
    "title": "title_none",
}


def load(raw: str | None) -> dict[str, Any]:
    """{owned: [ids], equipped: {kind: id}} with unknown ids dropped."""
    try:
        data = json.loads(raw or "{}")
    except (TypeError, ValueError):
        data = {}
    if not isinstance(data, dict):
        data = {}
    owned = [i for i in data.get("owned") or [] if isinstance(i, str) and i in BY_ID]
    equipped_raw = data.get("equipped") if isinstance(data.get("equipped"), dict) else {}
    equipped = {
        kind: value
        for kind, value in equipped_raw.items()
        if kind in KINDS and isinstance(value, str) and BY_ID.get(value, {}).get("kind") == kind
    }
    return {"owned": sorted(set(owned)), "equipped": equipped}


def dump(state: dict[str, Any]) -> str:
    return json.dumps({"owned": state["owned"], "equipped": state["equipped"]})


def spent(state: dict[str, Any]) -> int:
    return sum(BY_ID[i]["price"] for i in state["owned"])


def _unlocked(item: dict[str, Any], level: int, tiers: dict[str, int]) -> str | None:
    """None when the item can be had, else why not: "level" or "achievement"."""
    if level < int(item.get("level") or 0):
        return "level"
    need = item.get("achievement")
    if need and tiers.get(need[0], 0) < need[1]:
        return "achievement"
    return None


def owns(state: dict[str, Any], item: dict[str, Any], level: int, tiers: dict[str, int]) -> bool:
    """Free items come with the player (an achievement one once it is reached)."""
    if item["id"] in state["owned"]:
        return True
    return item["price"] == 0 and _unlocked(item, level, tiers) is None


def equipped(state: dict[str, Any], level: int, tiers: dict[str, int]) -> dict[str, str]:
    """The equipped id per kind; an item no longer owned falls back to the default."""
    result = {}
    for kind in KINDS:
        item = BY_ID.get(state["equipped"].get(kind, ""))
        if item is None or not owns(state, item, level, tiers):
            item = BY_ID[DEFAULTS[kind]]
        result[kind] = item["id"]
    return result


def shop(
    state: dict[str, Any], *, balance: int, level: int, tiers: dict[str, int], lang: str
) -> list[dict[str, Any]]:
    lang = "uk" if lang == "uk" else "en"
    worn = equipped(state, level, tiers)
    rows = []
    for item in CATALOG:
        locked = _unlocked(item, level, tiers)
        have = owns(state, item, level, tiers)
        need = item.get("achievement")
        rows.append(
            {
                "id": item["id"],
                "kind": item["kind"],
                "name": item[lang],
                "price": item["price"],
                "level": item.get("level"),
                "achievement": {"id": need[0], "tier": need[1]} if need else None,
                "owned": have,
                "equipped": worn[item["kind"]] == item["id"],
                "locked": locked if not have else None,
                "affordable": have or (locked is None and balance >= item["price"]),
            }
        )
    return rows


def buy(
    state: dict[str, Any], item_id: str, *, balance: int, level: int, tiers: dict[str, int]
) -> dict[str, Any]:
    """The new state with the item owned and worn; ValueError(code) when it cannot be."""
    item = BY_ID.get(item_id)
    if item is None:
        raise ValueError("unknown_item")
    if owns(state, item, level, tiers):
        raise ValueError("owned")
    locked = _unlocked(item, level, tiers)
    if locked:
        raise ValueError(f"locked_{locked}")
    if balance < item["price"]:
        raise ValueError("not_enough")
    return {
        "owned": sorted({*state["owned"], item_id}),
        "equipped": {**state["equipped"], item["kind"]: item_id},
    }


def equip(
    state: dict[str, Any], item_id: str, *, level: int, tiers: dict[str, int]
) -> dict[str, Any]:
    item = BY_ID.get(item_id)
    if item is None:
        raise ValueError("unknown_item")
    if not owns(state, item, level, tiers):
        raise ValueError("not_owned")
    return {"owned": state["owned"], "equipped": {**state["equipped"], item["kind"]: item_id}}
