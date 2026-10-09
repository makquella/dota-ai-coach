"""
skill_build.py - which ability to level next, from how pro players level the
hero (OpenDota: the hero's recent pro matches, each player's
`ability_upgrades_arr`).

The exact order of the first points changes with the lane, so only the order
in which the basic abilities are maxed is kept — the part of a skill build that
stays: for each game, the point at which every ability got its 4th level;
a hero with a skill of more ranks (Invoker's orbs) gets no order at all;
abilities sorted by the median of that point. Ultimates (3 levels), talents and
the attribute bonus never get a 4th level in a game's upgrades, so they drop
out by themselves; so does an innate, which is never levelled by hand.

Live: `next_skill` picks the first ability of that order the hero can still put
a point in (below level 4 and below what the hero level allows: level n of a
basic ability needs hero level 2n - 1); the ultimate is named by skill_tips
before this.
"""

from __future__ import annotations

import re
from collections import Counter
from statistics import median
from typing import Any

from app.ability_normalization import normalize_abilities

MIN_GAMES = 3
MAX_GAMES = 5  # pro games read per hero (each is one large OpenDota request)
MAX_TRIES = 8  # recent pro matches tried: some are not parsed yet
MAX_LEVEL = 4
TALENT_PREFIX = "special_bonus_"
TALENT_LEVELS = (10, 15, 20, 25)
# A talent row is named when the pros agree on one of its two in this share.
TALENT_AGREE = 0.6
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
    openings: list[str] = []
    for order in games:
        opening = next((ALIASES.get(n, n) for n in order if not n.startswith(TALENT_PREFIX)), None)
        if opening:
            openings.append(opening)
        counts: dict[str, int] = {}
        game_first = None
        for index, name in enumerate(order):
            if name.startswith(TALENT_PREFIX):
                continue
            name = ALIASES.get(name, name)
            counts[name] = counts.get(name, 0) + 1
            if counts[name] > MAX_LEVEL:
                return None  # Invoker's orbs (7 ranks): a 4th point is not the max
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
    tiers = data.get("talents") if isinstance(data, dict) else None
    return {
        "talents": _pro_talents(games, tiers if isinstance(tiers, dict) else {}, names),
        "order": order,
        # Every ability of these games with a name (the ultimate too: skill_tips
        # names it), and a readable fallback for the ones of the order.
        "names": {
            **{str(k): v for k, v in names.items() if isinstance(v, str) and v},
            **{name: str(names.get(name) or label(name)) for name in order},
        },
        "first_agree": sum(1 for name in firsts if name == order[0]),
        "games": len(games),
        # The level-1 skill when OPENING_AGREE of the games start with it.
        "opening": _opening(openings, len(games)),
    }


OPENING_AGREE = 0.6


def _opening(openings: list[str], games: int) -> dict[str, Any] | None:
    """{name, agree, games}: the skill most pro games level first, when
    OPENING_AGREE of them agree; None otherwise."""
    if not openings:
        return None
    name, agree = Counter(openings).most_common(1)[0]
    if agree < OPENING_AGREE * games:
        return None
    return {"name": name, "agree": agree, "games": games}


def _pro_talents(
    games: list[list[str]], tiers: dict[str, Any], names: dict[str, Any]
) -> dict[int, dict[str, Any]]:
    """{hero level: {name, label, picked, games}} for the talent rows where the
    pros agree (TALENT_AGREE of the games that took that row, MIN_GAMES+)."""
    taken: dict[int, list[str]] = {}
    for order in games:
        rows: dict[int, str] = {}
        for name in order:
            level = tiers.get(name)
            # The first talent of each row: at high levels the other one of the
            # pair can be taken too, and one game must count once.
            if isinstance(level, int) and isinstance(names.get(name), str):
                rows.setdefault(level, name)
        for level, name in rows.items():
            taken.setdefault(level, []).append(name)
    result: dict[int, dict[str, Any]] = {}
    for level, picks in taken.items():
        if len(picks) < MIN_GAMES:
            continue
        name, picked = max(
            ((n, picks.count(n)) for n in set(picks)), key=lambda pair: (pair[1], pair[0])
        )
        if picked >= TALENT_AGREE * len(picks):
            result[level] = {
                "name": name,
                "label": names[name],
                "picked": picked,
                "games": len(picks),
            }
    return result


def talent_label(dname: str) -> str:
    """A talent's text without the numbers the constants leave as placeholders:
    "-{s:bonus_AbilityCooldown}s Blade Fury Cooldown" → "Blade Fury Cooldown";
    a text with its numbers stays ("+15% Blade Dance Crit Damage")."""
    if "{" not in dname:
        return dname.strip()
    text = re.sub(r"[+-]?\{[^}]*\}[%sx]?", " ", dname)
    return re.sub(r"\s+", " ", text).strip(" :+-")


def label(raw_name: str, hero_key: str | None = None) -> str:
    """A readable name when the constants gave none: the GSI name table
    (juggernaut_blade_fury → Blade Fury), else the raw name title-cased without
    the hero's own prefix (`hero_key` "juggernaut": juggernaut_omni_slash →
    Omni Slash) and a slot number (nevermore_shadowraze1 → Shadowraze)."""
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
    if any((levels.get(name) or 0) > MAX_LEVEL for name in build.get("order") or []):
        return None  # a skill with more ranks than the pro games showed: the caps differ
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
    """The player's skill order against the pro one: {yours, pro, same, in_order,
    order, agree, games} (in-game names), or None when either side is unknown, the pros
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
        # The player's skill may be one the pros rarely max (not in `order`):
        # the review card then shows it apart from the pro chips.
        "in_order": yours in build["order"],
        "order": [labels.get(name) or label(name) for name in build["order"]],
        # The game names behind `yours` and `order`: the card's ability icons
        # (reviews stored before 0.49 lack them and show plain chips).
        "yours_key": yours,
        "keys": list(build["order"]),
        "agree": build["first_agree"],
        "games": build["games"],
    }
