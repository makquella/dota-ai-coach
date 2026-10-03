"""
skill_tips.py - прокачка: an unspent skill point, the ultimate at 6/12/18 and a
talent at 10/15/20/25, from the live GSI hero and abilities blocks.

Counting the points spent from scratch is not safe: innate abilities (7.36+)
level up by themselves, and a talent or the attribute bonus may be missing from
the payload. So the tracker works on changes: from the first tick it sees, a
level gained must be followed by one more level in the abilities, talents or
attributes. A level spent that it cannot see (an innate levelling with the
ultimate) only moves the base, so the error is always towards saying nothing.

One tip per new hero level, after the point has stayed unspent for
UNSPENT_WAIT seconds of game clock while alive; after 10 without talent fields
in the payload only the ultimate is named (a talent taken would read as a
point left unspent).
"""

from __future__ import annotations

import math
from typing import Any

from app.skill_build import label, next_skill

ULTIMATE_LEVELS = (6, 12, 18)
TALENT_LEVELS = (10, 15, 20, 25)
UNSPENT_WAIT = 15  # seconds of game clock with the point unspent
# A point "unspent" for this long is a miscount (a talent or the attribute bonus
# the payload does not show), not a forgotten point: start counting again.
UNSPENT_STALE = 180
TIP_SHOW = 20  # seconds the tip stays on the card
# Ultimates that are never levelled at 6/12/18: Invoke has one level from the
# start, so a point owed at 12 would read as «learn your ultimate».
FIXED_ULTIMATES = frozenset({"invoker_invoke"})

TEXTS = {
    "ultimate": {
        "en": ("Learn your ultimate", "{name} is ready to learn: level {level} opens it."),
        "ru": ("Изучите ультимейт", "{name} можно изучить: его открывает {level}-й уровень."),
    },
    "talent": {
        "en": ("Pick a talent", "The level-{tier} talent is waiting: open the talent tree."),
        "ru": ("Выберите талант", "Талант {tier}-го уровня ждёт: откройте дерево талантов."),
    },
    "talent_pro": {
        "en": (
            "Pick a talent",
            "Level {tier}: pros on this hero take «{name}» ({picked} of {games}).",
        ),
        "ru": (
            "Выберите талант",
            "Талант {tier}-го уровня: про-игроки на этом герое берут «{name}» ({picked} из {games}).",
        ),
    },
    "skill": {
        "en": ("Put the point in {name}", "The pro order on this hero: {order}."),
        "ru": ("Вложите очко в {name}", "Порядок прокачки у про-игроков на этом герое: {order}."),
    },
    "opening": {
        "en": (
            "First point: {name}",
            "Pros on this hero start with {name} ({agree} of {games} games).",
        ),
        "ru": (
            "Первое очко: {name}",
            "Про-игроки на этом герое начинают с {name} ({agree} из {games} игр).",
        ),
    },
    "point": {
        "en": (
            "Unspent skill point",
            "A level without the point spent is a weaker hero in the next fight.",
        ),
        "ru": (
            "Не вложено очко навыков",
            "Уровень без вложенного очка — герой слабее в следующей драке.",
        ),
    },
}


def _int(value: Any) -> int | None:
    """A whole number from GSI; NaN, infinity or a huge value count as missing."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if not math.isfinite(value) or abs(value) > 1000:
        return None
    return int(value)


# Real GSI lists the Dota Plus wheel among the abilities (plus_high_five,
# plus_guild_banner, level 1 from the start): not the hero's, never a skill point.
NOT_HERO_ABILITY_PREFIXES = ("plus_",)


def not_hero_ability(name: Any) -> bool:
    return isinstance(name, str) and name.startswith(NOT_HERO_ABILITY_PREFIXES)


def read_skills(payload: Any) -> dict[str, Any] | None:
    """Hero level, the levels spent (abilities + talents + attributes), the
    ultimate and whether the talent fields are there; None without the blocks."""
    if not isinstance(payload, dict):
        return None
    hero = payload.get("hero")
    abilities = payload.get("abilities")
    if not isinstance(hero, dict) or not isinstance(abilities, dict) or not abilities:
        return None
    level = _int(hero.get("level"))
    if level is None or not 1 <= level <= 30:
        return None
    spent = 0
    ultimate = None
    levels: dict[str, int] = {}
    for key in sorted(abilities):
        ability = abilities[key]
        if not isinstance(ability, dict) or not_hero_ability(ability.get("name")):
            continue
        ability_level = _int(ability.get("level")) or 0
        if 0 <= ability_level <= 10:
            spent += ability_level
            raw_name = ability.get("name")
            if isinstance(raw_name, str) and raw_name:
                levels.setdefault(raw_name, ability_level)
        if ability.get("ultimate") is True and ultimate is None:
            ultimate = {"raw_name": str(ability.get("name") or ""), "level": ability_level}
    talent_keys = [key for key in hero if str(key).startswith("talent_")]
    talents = sum(1 for key in talent_keys if hero.get(key) is True)
    attributes = _int(hero.get("attributes_level")) or 0
    return {
        "level": level,
        "spent": spent + talents + attributes,
        "ultimate": ultimate,
        "has_talents": bool(talent_keys),
        "talents": {key: hero.get(key) is True for key in talent_keys},
        "levels": levels,
        "hero_key": _hero_key(hero.get("name")),
    }


def _hero_key(value: Any) -> str | None:
    """npc_dota_hero_juggernaut → juggernaut (the prefix of its ability names)."""
    prefix = "npc_dota_hero_"
    if isinstance(value, str) and value.startswith(prefix) and len(value) > len(prefix):
        return value[len(prefix) :]
    return None


def _ultimate_allowed(level: int) -> int:
    return sum(1 for need in ULTIMATE_LEVELS if level >= need)


def _talent_due(skills: dict[str, Any]) -> int | None:
    """The lowest talent tier reached with neither of its two talents taken."""
    talents = skills["talents"]
    for index, tier in enumerate(TALENT_LEVELS):
        if skills["level"] < tier:
            return None
        pair = (f"talent_{index * 2 + 1}", f"talent_{index * 2 + 2}")
        if not any(talents.get(key) for key in pair):
            return tier
    return None


class SkillTips:
    """Per-match state (reset with MatchMemory)."""

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self._base: tuple[int, int] | None = None  # (level, spent) seen last with nothing owed
        self._unspent_since: int | None = None
        self._shown: dict[int, int] = {}  # hero level -> clock the tip started
        self._skills: dict[str, Any] | None = None

    def observe(self, clock: int | None, skills: dict[str, Any] | None) -> None:
        if clock is None or skills is None:
            return
        level, spent = skills["level"], skills["spent"]
        if self._base is None or level < self._base[0]:
            # First tick or a new match: all spent — except a level-1 hero with
            # nothing learned, whose first point is plainly still to spend.
            self._base = (0, 0) if (level, spent) == (1, 0) else (level, spent)
        owed = (level - self._base[0]) - (spent - self._base[1])
        if owed <= 0:
            # Caught up (or more levels than points: an innate) → a new base.
            self._base = (level, spent)
            self._unspent_since = None
        elif self._unspent_since is None:
            self._unspent_since = clock
        elif clock - self._unspent_since > UNSPENT_STALE:
            self._base = (level, spent)
            self._unspent_since = None
            owed = 0
        self._skills = {**skills, "owed": max(0, owed)}

    def tip(
        self,
        clock: int | None,
        lang: str,
        *,
        alive: bool,
        build: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """`build`: the hero's pro skill order (app/skill_build.skill_order), which
        names the ability for an unspent point and the ultimate."""
        skills = self._skills
        if clock is None or not alive or skills is None or not skills["owed"]:
            return None
        if self._unspent_since is None or clock - self._unspent_since < UNSPENT_WAIT:
            return None
        level = skills["level"]
        start = self._shown.setdefault(level, clock)
        if not 0 <= clock - start <= TIP_SHOW:
            return None
        ultimate = skills["ultimate"]
        if (
            ultimate
            and ultimate["raw_name"] not in FIXED_ULTIMATES
            and ultimate["level"] < _ultimate_allowed(level)
        ):
            names = (build or {}).get("names") or {}
            name = names.get(ultimate["raw_name"]) or label(
                ultimate["raw_name"], skills.get("hero_key")
            )
            need = ULTIMATE_LEVELS[ultimate["level"]] if ultimate["level"] < 3 else level
            return _hint("ultimate", f"skill-ult@{level}", lang, name=name, level=need)
        if not skills["has_talents"]:
            if level >= TALENT_LEVELS[0]:
                return None  # a talent taken would look like a point left unspent
            return self._point(level, lang, build)
        tier = _talent_due(skills)
        if tier is not None:
            pro = ((build or {}).get("talents") or {}).get(tier)
            if pro:
                return _hint(
                    "talent_pro",
                    f"skill-talent@{level}",
                    lang,
                    tier=tier,
                    name=pro["label"],
                    picked=pro["picked"],
                    games=pro["games"],
                )
            return _hint("talent", f"skill-talent@{level}", lang, tier=tier)
        return self._point(level, lang, build)

    def _point(self, level: int, lang: str, build: dict[str, Any] | None) -> dict[str, Any]:
        """The unspent point: the ability the pro order puts it in, when known."""
        skills = self._skills or {}
        opening = (build or {}).get("opening")
        levels = skills.get("levels") or {}
        if level == 1 and opening and not any(levels.values()):
            names = (build or {}).get("names") or {}
            return _hint(
                "opening",
                "skill-point@1",
                lang,
                name=names.get(opening["name"]) or label(opening["name"], skills.get("hero_key")),
                agree=opening["agree"],
                games=opening["games"],
            )
        name = next_skill(build, skills.get("levels"), level)
        if build and name:
            names = build.get("names") or {}
            key = skills.get("hero_key")
            order = " → ".join(str(names.get(n) or label(n, key)) for n in build["order"])
            return _hint(
                "skill",
                f"skill-point@{level}",
                lang,
                name=names.get(name) or label(name, key),
                order=order,
            )
        return _hint("point", f"skill-point@{level}", lang)


def _hint(key: str, hint_id: str, lang: str, **params: Any) -> dict[str, Any]:
    title, text = TEXTS[key]["ru" if lang == "ru" else "en"]
    return {
        "kind": "tip",
        "id": hint_id,
        "at": None,
        "at_label": None,
        "in_seconds": None,
        "title": title.format(**params),
        "hint": text.format(**params),
        "speak": True,
        # Kept on the overlay over the game plan (overlay/app.js).
        "over_plan": True,
    }
