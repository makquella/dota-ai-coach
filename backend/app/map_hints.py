"""
map_hints.py - the overlay's one-line map hint: timers and role tips.

A second channel next to the advice card: it never replaces advice, never
goes through the scheduler and never speaks over it (the overlay reads timers
marked "speak" only when the voice reads every advice).

1. Timers (data/meta/map_timers.json, checked against a patch): runes, wisdom
   shrines, lotuses, the Tormentor, neutral item tiers. Each event is shown from
   `lead_seconds` before it until `grace_seconds` after, and only to the
   positions it matters for (app/live_role.py).
2. Role tips: "no TP scroll" for any hero the carry advisor does not follow
   (it has its own); mid: the level-6 rotation window, the last-hit pace at
   5:00 and 8:00, no Bottle in the first minutes, and with level 6 the power
   rune reads "take it and go to a side lane"; offlane: the level-6 pressure
   window and a lost lane (two deaths, or level 4 at 6:00) → pull the big camp
   and survive for experience; supports: leave the last hits to the carry,
   stack a camp in given minutes, pull the small camp at :15 / :45 in the safe
   lane, "no observer ward on you" at most every 5 minutes, and 1500+ gold
   kept after 8:00 → spend it. A tip wins over a minor timer (runes, lotus:
   the stack window always comes before a power rune).

Texts are built in the request language here (like game_plan.py); the file's
events carry both languages.
"""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from app.config import DATA_DIR

TIMERS_PATH = DATA_DIR / "meta" / "map_timers.json"

# Support tip: stack a camp in these minutes (pull at :53-:55).
STACK_MINUTES = (4, 7, 10, 13, 16)
STACK_FROM_SECOND = 38
STACK_UNTIL_SECOND = 53
# Support tip: no observer ward in the inventory.
WARD_FROM_CLOCK = 150
WARD_EVERY = 5 * 60
WARD_SHOW = 20

WARD_ITEMS = {"item_ward_observer", "item_ward_dispenser"}
# Any role without the carry advisor (which has its own TP advice): no TP scroll.
TP_EVERY = 4 * 60
TP_SHOW = 20
# Support tip: a support farming the lane like a core leaves its carry poor.
LAST_HITS_FROM = 3 * 60
LAST_HITS_UNTIL = 10 * 60
SUPPORT_LH_PER_MIN = 2.5
LAST_HITS_EVERY = 3 * 60
# Level 6 before this clock: the mid's rotation window, the offlaner's pressure.
POWER_SPIKE_LEVEL = 6
POWER_SPIKE_UNTIL = 12 * 60
POWER_SPIKE_SHOW = 25
# Mid: last hits at these clocks against a good pace (a core's 55 at 10:00).
MID_LAST_HIT_CHECKS = {5 * 60: 25, 8 * 60: 44}
MID_LAST_HIT_SHOW = 20
# Mid: no Bottle in these minutes (most mids live on it and the runes).
BOTTLE_FROM = 3 * 60 + 30
BOTTLE_UNTIL = 6 * 60
BOTTLE_SHOW = 20
BOTTLE_ITEMS = {"item_bottle"}
# Offlane: a lost lane — this many deaths, or below this level at 6:00.
HARD_LANE_FROM = 4 * 60
HARD_LANE_UNTIL = 9 * 60
HARD_LANE_DEATHS = 2
HARD_LANE_LEVEL_AT = 6 * 60
HARD_LANE_LEVEL = 5
HARD_LANE_SHOW = 25
# Safe-lane support: pull the small camp so the wave meets at the own tower.
PULL_FROM = 2 * 60
PULL_UNTIL = 8 * 60
PULL_WINDOWS = ((5, 15), (35, 45))  # (from second, pull at second)
PULL_EVERY = 2 * 60
PULL_SHOW = 10
# Cores: the hero's key item (OpenDota's most bought, with its typical finish
# time) — late by this much, or finished this much before the typical time.
KEY_ITEM_LATE = 2 * 60
KEY_ITEM_EARLY = 2 * 60
KEY_ITEM_SHOW = 25
CORE_ROLES = {"carry", "mid", "offlane"}
# Support: gold kept instead of wards, dust, smoke and a save item.
SPEND_FROM = 8 * 60
SPEND_GOLD = 1500
SPEND_EVERY = 4 * 60
SPEND_SHOW = 20

TIPS = {
    "stack": {
        "en": ("Stack a camp", "Pull the camp at :53 so the next spawn stacks on top."),
        "ru": ("Застакайте лагерь", "Отведите крипов на :53 — сверху появится новый лагерь."),
    },
    "tp": {
        "en": ("No TP scroll", "Buy one now: without it you cannot join a fight or save a tower."),
        "ru": (
            "Нет свитка телепортации",
            "Купите его сейчас: без ТП не успеть на драку и к вышке.",
        ),
    },
    "last_hits": {
        "en": (
            "Leave the last hits to your carry",
            "A support's gold comes from runes, stacks and kills.",
        ),
        "ru": ("Оставьте добивания керри", "Золото саппорта — руны, стаки и убийства."),
    },
    "wards": {
        "en": ("No observer wards on you", "Take wards from the shop and light up the next fight."),
        "ru": ("Нет вардов", "Возьмите варды в лавке и подсветите место следующей драки."),
    },
    "mid_six": {
        "en": (
            "Level 6: look for a rotation",
            "Push the wave first, then check the side lanes with the next rune.",
        ),
        "ru": (
            "6-й уровень: время ротации",
            "Сначала запушьте волну, потом с руной посмотрите на боковые линии.",
        ),
    },
    "mid_last_hits": {
        "en": (
            "{last_hits} last hits by {time}",
            "A good mid has {target}+: last-hit and deny under your tower, trade only with the wave on your side.",
        ),
        "ru": (
            "{last_hits} {last_hits_word} к {time}",
            "Хороший мид — {target}+: добивайте и денайте под своей вышкой, размены — когда волна на вашей стороне.",
        ),
    },
    "mid_bottle": {
        "en": (
            "No Bottle yet",
            "Most mids live on it: every rune refills it, and it keeps you in the lane without going to base.",
        ),
        "ru": (
            "Нет бутылки",
            "Большинство мидеров живёт на ней: руна заполняет её, и не нужно ходить на базу.",
        ),
    },
    "mid_rune": {
        "en": ("", "Take it and go straight to a side lane: the best moment to rotate."),
        "ru": ("", "Заберите её и сразу идите на боковую линию: лучший момент для ротации."),
    },
    "offlane_hard_lane": {
        "en": (
            "A hard lane",
            "Stop feeding under their tower: pull the big camp into your wave and take the experience safely.",
        ),
        "ru": (
            "Тяжёлая линия",
            "Не умирайте под их вышкой: подтяните большой лагерь в свою волну и берите опыт без риска.",
        ),
    },
    "pull": {
        "en": (
            "Pull at {at_label}",
            "Pull the small camp into your wave so it meets at your tower.",
        ),
        "ru": (
            "Пул на {at_label}",
            "Отведите малый лагерь в свою волну: линия встанет у вашей вышки.",
        ),
    },
    "item_late": {
        "en": (
            "{item} is late",
            "Most players finish it by {time}. Farm camps between waves and skip fights until you have it.",
        ),
        "ru": (
            "{item} опаздывает",
            "Обычно его собирают к {time}. Фармите лагеря между волнами и не лезьте в драки без него.",
        ),
    },
    "item_early": {
        "en": (
            "{item} ahead of time",
            "Most players have it by {time}: this is your window — push and look for fights.",
        ),
        "ru": (
            "{item} раньше обычного",
            "Обычно его собирают к {time}: сейчас ваше окно — давите и ищите драки.",
        ),
    },
    "spend_gold": {
        "en": (
            "{gold} gold unspent",
            "Spend it now: wards, dust, a smoke or a save item such as Force Staff or Glimmer Cape.",
        ),
        "ru": (
            "{gold} золота не потрачено",
            "Потратьте сейчас: варды, дасты, смок или спасающий предмет — Force Staff, Glimmer Cape.",
        ),
    },
    "offlane_six": {
        "en": (
            "Level 6: pressure the lane",
            "With your support, go for the enemy carry or their tower while the wave is close.",
        ),
        "ru": (
            "6-й уровень: давите линию",
            "Вместе с саппортом идите на вражеского керри или вышку, пока волна рядом.",
        ),
    },
}


@lru_cache(maxsize=1)
def timers() -> dict[str, Any]:
    try:
        return json.loads(TIMERS_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"events": []}


def item_names(items: Any) -> list[str] | None:
    """Item names in the inventory, backpack and stash of a raw GSI items block
    (None without one; the TP and neutral slots are left out)."""
    if not isinstance(items, dict) or not items:
        return None
    names = []
    for slot, item in items.items():
        name = item.get("name") if isinstance(item, dict) else item
        if str(slot).startswith(("slot", "stash")) and isinstance(name, str) and name != "empty":
            names.append(name)
    return names


def has_observer_ward(items: Any) -> bool | None:
    """From a raw GSI items block; None without one (stash and neutral slots skipped)."""
    if not isinstance(items, dict) or not items:
        return None
    for slot, item in items.items():
        name = item.get("name") if isinstance(item, dict) else item
        if str(slot).startswith("slot") and str(name or "") in WARD_ITEMS:
            return True
    return False


def _times(event: dict[str, Any], until: int) -> list[int]:
    if "times" in event:
        return [int(t) for t in event["times"] if int(t) <= until]
    first, every = int(event.get("first", 0)), int(event.get("every", 0))
    if every <= 0:
        return [first] if first <= until else []
    return list(range(first, until + 1, every))


def clock_label(seconds: int) -> str:
    return f"{seconds // 60}:{seconds % 60:02d}"


def next_timer(clock: int, role: str | None, lang: str) -> dict[str, Any] | None:
    """The event about to happen (or just happened) for this position."""
    data = timers()
    lead = int(data.get("lead_seconds", 20))
    grace = int(data.get("grace_seconds", 5))
    # The soonest event; at the same second a major one (Tormentor) wins.
    candidates = [
        (at, bool(event.get("minor")), index, event)
        for index, event in enumerate(data.get("events") or [])
        if (until := (event.get("roles") or {}).get(role or "")) is not None
        for at in _times(event, int(until))
        if at - lead <= clock <= at + grace
    ]
    if not candidates:
        return None
    at, _minor, _index, event = min(candidates, key=lambda row: row[:3])
    ru = lang == "ru"
    return {
        "kind": "timer",
        "id": f"{event['id']}@{at}",
        "at": at,
        "at_label": clock_label(at),
        "in_seconds": at - clock,
        "title": event["ru" if ru else "en"],
        "hint": event.get("hint_ru" if ru else "hint_en") or "",
        "speak": bool(event.get("speak")),
        "minor": bool(event.get("minor")),
        "patch": data.get("patch"),
    }


class RoleTips:
    """Per-match memory of the tips shown (reset with MatchMemory)."""

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self._shown: dict[str, int] = {}
        # Level 6 counts as reached only after a level below 6 was seen: a
        # backend started mid-game at level 8 must not call it a new spike.
        self._armed = False

    def observe_level(self, level: int | None) -> None:
        """Every hint request (also while a timer shows): arms the level-6 tip."""
        if level is not None and level < POWER_SPIKE_LEVEL:
            self._armed = True

    def _every(self, key: str, clock: int, every: int, show: int) -> int | None:
        """Shown for `show` seconds, then again `every` seconds later: the start."""
        shown = self._shown.get(key)
        if shown is None or clock - shown >= every or clock < shown:
            self._shown[key] = shown = clock
        return shown if clock - shown <= show else None

    def tip(
        self,
        clock: int,
        role: str | None,
        *,
        alive: bool,
        has_ward: bool | None,
        lang: str,
        tp_missing: bool = False,
        carry_advisor: bool = False,
        last_hits: int | None = None,
        level: int | None = None,
        deaths: int | None = None,
        gold: int | None = None,
        lane: str | None = None,
        items: list[str] | None = None,
        key_item: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        if not alive or role is None:
            return None
        if tp_missing and not carry_advisor:
            start = self._every("tp", clock, TP_EVERY, TP_SHOW)
            if start is not None:
                return _tip("tp", f"tp@{start}", lang)
        if role in ("mid", "offlane") and level is not None:
            key = f"{role}_six"
            if level >= POWER_SPIKE_LEVEL and clock <= POWER_SPIKE_UNTIL and self._armed:
                # Once per match, from the moment the level is reached.
                start = self._shown.setdefault(key, clock)
                if 0 <= clock - start <= POWER_SPIKE_SHOW:
                    return _tip(key, f"{key}@{start}", lang)
        if role in CORE_ROLES and key_item and items is not None:
            timing = self._key_item(clock, lang, key_item, items)
            if timing is not None:
                return timing
        if role == "mid":
            return self._mid(clock, lang, last_hits, items)
        if role == "offlane":
            return self._offlane(clock, lang, deaths, level)
        if role != "support":
            return None
        if (
            last_hits is not None
            and LAST_HITS_FROM <= clock <= LAST_HITS_UNTIL
            and last_hits / (clock / 60) >= SUPPORT_LH_PER_MIN
        ):
            start = self._every("last_hits", clock, LAST_HITS_EVERY, TP_SHOW)
            if start is not None:
                return _tip("last_hits", f"last_hits@{start}", lang)
        minute, second = divmod(clock, 60)
        if minute in STACK_MINUTES and STACK_FROM_SECOND <= second <= STACK_UNTIL_SECOND:
            at = minute * 60 + STACK_UNTIL_SECOND
            return _tip("stack", f"stack@{minute}", lang, at=at, clock=clock)
        if lane == "safe" and PULL_FROM <= clock <= PULL_UNTIL:
            for window_from, pull_at in PULL_WINDOWS:
                if window_from <= second <= pull_at:
                    start = self._every("pull", clock, PULL_EVERY, PULL_SHOW)
                    if start is not None:
                        at = minute * 60 + pull_at
                        label = clock_label(at)
                        return _tip("pull", f"pull@{at}", lang, at=at, clock=clock, at_label=label)
        if has_ward is False and clock >= WARD_FROM_CLOCK:
            start = self._every("wards", clock, WARD_EVERY, WARD_SHOW)
            if start is not None:
                return _tip("wards", f"wards@{start}", lang)
        if gold is not None and gold >= SPEND_GOLD and clock >= SPEND_FROM:
            start = self._every("spend_gold", clock, SPEND_EVERY, SPEND_SHOW)
            if start is not None:
                # Rounded down to hundreds, as the player reads it on screen.
                return _tip("spend_gold", f"spend_gold@{start}", lang, gold=gold // 100 * 100)
        return None

    def _once(self, key: str, clock: int, show: int) -> int | None:
        """Once per match: the start while within `show` seconds of it."""
        start = self._shown.setdefault(key, clock)
        return start if 0 <= clock - start <= show else None

    def _key_item(
        self, clock: int, lang: str, item: dict[str, Any], items: list[str]
    ) -> dict[str, Any] | None:
        """Once per match: the key item finished 2+ minutes before its typical
        time, or not finished 2 minutes after it."""
        typical = int(item["typical_t"])
        params = {"item": item["name"], "time": clock_label(typical)}
        for key in ("item_early", "item_late"):
            if key in self._shown:
                start = self._once(key, clock, KEY_ITEM_SHOW)
                return _tip(key, f"{key}@{start}", lang, **params) if start is not None else None
        has_it = f"item_{item['key']}" in items
        if has_it and clock <= typical - KEY_ITEM_EARLY:
            key = "item_early"
        elif not has_it and clock >= typical + KEY_ITEM_LATE:
            key = "item_late"
        else:
            if has_it:
                self._shown["item_on_time"] = clock  # bought: never "late" later on
            return None
        if "item_on_time" in self._shown:
            return None
        start = self._once(key, clock, KEY_ITEM_SHOW)
        return _tip(key, f"{key}@{start}", lang, **params) if start is not None else None

    def _mid(
        self, clock: int, lang: str, last_hits: int | None, items: list[str] | None
    ) -> dict[str, Any] | None:
        if last_hits is not None:
            for at, target in MID_LAST_HIT_CHECKS.items():
                if at <= clock <= at + MID_LAST_HIT_SHOW and last_hits < target:
                    key = f"mid_last_hits@{at}"
                    # The count of the first second shown stays on the card.
                    shown = self._shown.setdefault(key, last_hits)
                    return _tip(
                        "mid_last_hits",
                        key,
                        lang,
                        last_hits=shown,
                        last_hits_word=_ru_plural(shown, "добивание", "добивания", "добиваний"),
                        time=clock_label(at),
                        target=target,
                    )
        if items is not None and BOTTLE_FROM <= clock <= BOTTLE_UNTIL:
            if not BOTTLE_ITEMS & set(items):
                start = self._once("mid_bottle", clock, BOTTLE_SHOW)
                if start is not None:
                    return _tip("mid_bottle", f"mid_bottle@{start}", lang)
        return None

    def _offlane(
        self, clock: int, lang: str, deaths: int | None, level: int | None
    ) -> dict[str, Any] | None:
        key = "offlane_hard_lane"
        if key not in self._shown:
            if not HARD_LANE_FROM <= clock <= HARD_LANE_UNTIL:
                return None
            lost = (deaths is not None and deaths >= HARD_LANE_DEATHS) or (
                clock >= HARD_LANE_LEVEL_AT and level is not None and level < HARD_LANE_LEVEL
            )
            if not lost:
                return None
        start = self._once(key, clock, HARD_LANE_SHOW)
        return _tip(key, f"{key}@{start}", lang) if start is not None else None


def _ru_plural(count: int, one: str, few: str, many: str) -> str:
    if count % 10 == 1 and count % 100 != 11:
        return one
    if 2 <= count % 10 <= 4 and not 12 <= count % 100 <= 14:
        return few
    return many


def _tip(
    key: str,
    hint_id: str,
    lang: str,
    at: int | None = None,
    clock: int | None = None,
    **params: Any,
) -> dict[str, Any]:
    title, hint = TIPS[key]["ru" if lang == "ru" else "en"]
    if params:
        title, hint = title.format(**params), hint.format(**params)
    return {
        "kind": "tip",
        "id": hint_id,
        "at": at,
        "at_label": clock_label(at) if at is not None else None,
        "in_seconds": at - clock if at is not None and clock is not None else None,
        "title": title,
        "hint": hint,
        "speak": False,
    }


def map_hint(
    clock: int | None,
    role: str | None,
    tips: RoleTips,
    *,
    alive: bool,
    has_ward: bool | None,
    lang: str,
    tp_missing: bool = False,
    carry_advisor: bool = False,
    last_hits: int | None = None,
    level: int | None = None,
    deaths: int | None = None,
    gold: int | None = None,
    lane: str | None = None,
    items: list[str] | None = None,
    key_item: dict[str, Any] | None = None,
    objective: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """A timer, but a role tip over a minor one (runes, lotus); None before the
    horn or without a role. `objective`: a Roshan / Aegis timer (roshan_timer.py),
    which wins over a scheduled timer that is not sooner."""
    if clock is None or clock < 0 or role is None:
        return None
    tips.observe_level(level)
    timer = next_timer(clock, role, lang)
    if objective is not None and (
        timer is None or timer["minor"] or objective["in_seconds"] <= timer["in_seconds"]
    ):
        timer = objective
    if (
        timer is not None
        and role == "mid"
        and timer["id"].startswith("power_rune@")
        and level is not None
        and level >= POWER_SPIKE_LEVEL
    ):
        # With level 6 a power rune is the mid's rotation.
        timer["hint"] = TIPS["mid_rune"]["ru" if lang == "ru" else "en"][1]
    if timer is not None and not timer["minor"]:
        return timer
    tip = tips.tip(
        clock,
        role,
        alive=alive,
        has_ward=has_ward,
        lang=lang,
        tp_missing=tp_missing,
        carry_advisor=carry_advisor,
        last_hits=last_hits,
        level=level,
        deaths=deaths,
        gold=gold,
        lane=lane,
        items=items,
        key_item=key_item,
    )
    return tip or timer
