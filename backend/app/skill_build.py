"""
skill_build.py - which ability to level next, from how pro players level the
hero (OpenDota: the hero's recent pro matches, each player's
`ability_upgrades_arr`).

The exact order of the first points changes with the lane, so only the order
in which the basic abilities are maxed is kept — the part of a skill build that
stays: for each game, the point at which every ability got its 4th level;
abilities sorted by the median of that point. Ultimates (3 levels), talents and
the attribute bonus never get a 4th level in a game's upgrades, so they drop
out by themselves; so does an innate, which is never levelled by hand.

Live: `next_skill` picks the first ability of that order the hero can still put
a point in (below level 4 and below what the hero level allows: level n of a
basic ability needs hero level 2n - 1); the ultimate is named by skill_tips
before this.
"""

from __future__ import annotations

from statistics import median
from typing import Any

MIN_GAMES = 3
MAX_GAMES = 5  # pro games read per hero (each is one large OpenDota request)
MAX_TRIES = 8  # recent pro matches tried: some are not parsed yet
MAX_LEVEL = 4
TALENT_PREFIX = "special_bonus_"
# One skill logged under several ability ids (the upgrade goes to whichever slot
# was pressed); GSI shows every slot at the same level.
ALIASES = {
    "nevermore_shadowraze2": "nevermore_shadowraze1",
    "nevermore_shadowraze3": "nevermore_shadowraze1",
}


def upgrade_names(upgrades: Any, ability_ids: dict[str, str] | None) -> list[str]:
    """`ability_upgrades_arr` (ability ids) → ability names; unknown ids dropped."""
    if not isinstance(upgrades, list) or not ability_ids:
        return []
    names = []
    for ability_id in upgrades:
        name = ability_ids.get(str(ability_id))
        if isinstance(name, str) and name:
            names.append(ALIASES.get(name, name))
    return names


def skill_order(data: dict[str, Any] | None) -> dict[str, Any] | None:
    """The cached pro games ({orders, names}) → {order: [ability names, maxed
    first → last], names: {ability name: in-game name}, first_agree, games}; None with
    fewer than MIN_GAMES games or no ability maxed."""
    orders = data.get("orders") if isinstance(data, dict) else None
    raw_names = data.get("names") if isinstance(data, dict) else None
    games = [order for order in orders or [] if isinstance(order, list) and order]
    if len(games) < MIN_GAMES:
        return None
    maxed_at: dict[str, list[int]] = {}
    firsts: list[str] = []
    for order in games:
        counts: dict[str, int] = {}
        game_first = None
        for index, name in enumerate(order):
            if name.startswith(TALENT_PREFIX):
                continue
            name = ALIASES.get(name, name)
            counts[name] = counts.get(name, 0) + 1
            if counts[name] == MAX_LEVEL:
                maxed_at.setdefault(name, []).append(index)
                game_first = game_first or name
        if game_first:
            firsts.append(game_first)
    # An ability maxed in under half of the games is not part of the usual build.
    usual = {name: spots for name, spots in maxed_at.items() if len(spots) * 2 >= len(games)}
    if not usual:
        return None
    order = sorted(usual, key=lambda name: (median(usual[name]), name))
    names = raw_names if isinstance(raw_names, dict) else {}
    return {
        "order": order,
        # Every ability of these games with a name (the ultimate too: skill_tips
        # names it), and a readable fallback for the ones of the order.
        "names": {
            **{str(k): v for k, v in names.items() if isinstance(v, str) and v},
            **{name: str(names.get(name) or label(name)) for name in order},
        },
        "first_agree": sum(1 for name in firsts if name == order[0]),
        "games": len(games),
    }


def label(raw_name: str, hero_key: str | None = None) -> str:
    """A readable name when the constants gave none: the GSI name table
    (juggernaut_blade_fury → Blade Fury), else the raw name title-cased without
    the hero's own prefix (`hero_key` "juggernaut": juggernaut_omni_slash →
    Omni Slash) and a slot number (nevermore_shadowraze1 → Shadowraze)."""
    from app.gsi_state import normalize_abilities  # avoid an import cycle

    known = str(normalize_abilities([raw_name])[0]["name"])
    if known.lower().replace(" ", "_") != raw_name.lower():
        return known  # from the name table
    rest = raw_name
    if hero_key and rest.startswith(f"{hero_key}_") and len(rest) > len(hero_key) + 1:
        rest = rest[len(hero_key) + 1 :]
    words = [word for word in rest.rstrip("0123456789").split("_") if word]
    return " ".join(word.capitalize() for word in words) or known


def next_skill(
    build: dict[str, Any] | None, levels: dict[str, int] | None, hero_level: int
) -> str | None:
    """The raw name of the first ability of the pro order the hero can level now."""
    if not build or not levels:
        return None
    allowed = min(MAX_LEVEL, (hero_level + 1) // 2)
    for name in build.get("order") or []:
        level = levels.get(name)
        if level is None:
            continue  # not this hero's ability in this game (a facet, a rework)
        if level < allowed:
            return name
    return None


# The review: the pros agree on the first skill to max in this share of games.
REVIEW_AGREE = 0.6
REVIEW_MIN_UPGRADES = 8  # a game long enough to have maxed a first skill


def first_maxed(names: list[str]) -> str | None:
    """The first ability the game's upgrades took to its 4th level."""
    counts: dict[str, int] = {}
    for name in names:
        if name.startswith(TALENT_PREFIX):
            continue
        counts[name] = counts.get(name, 0) + 1
        if counts[name] == MAX_LEVEL:
            return name
    return None


def review_skills(upgrades: list[int] | None, data: dict[str, Any] | None) -> dict[str, Any] | None:
    """The player's skill order against the pro one: {yours, pro, same, order,
    agree, games} (in-game names), or None when either side is unknown, the pros
    do not agree on a first skill or the player maxed none."""
    build = skill_order(data)
    ids = (data or {}).get("ids")
    names = upgrade_names(upgrades, ids if isinstance(ids, dict) else None)
    if build is None or len(names) < REVIEW_MIN_UPGRADES:
        return None
    if build["first_agree"] < REVIEW_AGREE * build["games"]:
        return None
    yours = first_maxed(names)
    if yours is None:
        return None
    labels = build["names"]
    pro = build["order"][0]
    return {
        "yours": labels.get(yours) or label(yours),
        "pro": labels.get(pro) or label(pro),
        "same": yours == pro,
        "order": [labels.get(name) or label(name) for name in build["order"]],
        "agree": build["first_agree"],
        "games": build["games"],
    }
