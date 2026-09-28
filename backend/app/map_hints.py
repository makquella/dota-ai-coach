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
   (it has its own), and for supports: leave the last hits to the carry, stack
   a camp in given minutes, "no observer ward on you" at most every 5 minutes. A tip wins over a minor timer
   (runes, lotus: the stack window always comes before a power rune).

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
    ) -> dict[str, Any] | None:
        if not alive or role is None:
            return None
        if tp_missing and not carry_advisor:
            start = self._every("tp", clock, TP_EVERY, TP_SHOW)
            if start is not None:
                return _tip("tp", f"tp@{start}", lang)
        if role in ("mid", "offlane") and level is not None:
            key = f"{role}_six"
            if level >= POWER_SPIKE_LEVEL and clock <= POWER_SPIKE_UNTIL:
                # Once per match, from the moment the level is reached.
                start = self._shown.setdefault(key, clock)
                if 0 <= clock - start <= POWER_SPIKE_SHOW:
                    return _tip(key, f"{key}@{start}", lang)
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
        if has_ward is False and clock >= WARD_FROM_CLOCK:
            start = self._every("wards", clock, WARD_EVERY, WARD_SHOW)
            if start is not None:
                return _tip("wards", f"wards@{start}", lang)
        return None


def _tip(
    key: str, hint_id: str, lang: str, at: int | None = None, clock: int | None = None
) -> dict[str, Any]:
    title, hint = TIPS[key]["ru" if lang == "ru" else "en"]
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
) -> dict[str, Any] | None:
    """A timer, but a role tip over a minor one (runes, lotus); None before the
    horn or without a role."""
    if clock is None or clock < 0 or role is None:
        return None
    timer = next_timer(clock, role, lang)
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
    )
    return tip or timer
