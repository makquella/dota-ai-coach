"""
last_moments.py - the last seconds before each death, from live GSI.

The match timeline keeps a sample every 15 s, too coarse to say how a death
happened. MatchTracker feeds every GSI tick here; a ring buffer keeps one entry
per second of match clock for the last WINDOW seconds: HP and mana percent,
whether the hero was disabled (stunned, hexed or muted: no items then), and
which saving items were ready (SAVERS: castable, off cooldown; a Magic Wand
from WAND_CHARGES charges).

At a death, summarize() turns the buffer into a small record kept with the
death on the timeline:
- hp: the HP curve (seconds before the death, percent), at most WINDOW points;
- ready: the saving items that were ready at the last alive tick;
- usable: the saving items that were ready on a second of the last
  FREE_WINDOW when the hero was not disabled — readiness and the chance to
  press it on the same sample, so only these count as "not used";
- free_s: seconds of the last FREE_WINDOW the hero was not disabled;
- burst_s: seconds from BURST_FROM % HP or more to the death (a burst kill),
  when that is BURST_SECONDS or less.

GSI only: OpenDota matches have no such record, and a missing value stays out.
"""

from __future__ import annotations

from collections import deque
from typing import Any

WINDOW = 20
FREE_WINDOW = 5
BURST_FROM = 70
BURST_SECONDS = 3
WAND_CHARGES = 10

# Items that save a life when pressed in time (escape, dispel, spell immunity,
# a big heal or a save). Names as Dota's GSI reports them.
SAVERS: dict[str, dict[str, str]] = {
    "item_black_king_bar": {"ru": "Black King Bar", "en": "Black King Bar"},
    "item_blink": {"ru": "Blink Dagger", "en": "Blink Dagger"},
    "item_overwhelming_blink": {"ru": "Overwhelming Blink", "en": "Overwhelming Blink"},
    "item_swift_blink": {"ru": "Swift Blink", "en": "Swift Blink"},
    "item_arcane_blink": {"ru": "Arcane Blink", "en": "Arcane Blink"},
    "item_force_staff": {"ru": "Force Staff", "en": "Force Staff"},
    "item_hurricane_pike": {"ru": "Hurricane Pike", "en": "Hurricane Pike"},
    "item_glimmer_cape": {"ru": "Glimmer Cape", "en": "Glimmer Cape"},
    "item_ghost": {"ru": "Ghost Scepter", "en": "Ghost Scepter"},
    "item_ethereal_blade": {"ru": "Ethereal Blade", "en": "Ethereal Blade"},
    "item_cyclone": {"ru": "Eul's Scepter", "en": "Eul's Scepter"},
    "item_wind_waker": {"ru": "Wind Waker", "en": "Wind Waker"},
    "item_manta": {"ru": "Manta Style", "en": "Manta Style"},
    "item_satanic": {"ru": "Satanic", "en": "Satanic"},
    "item_lotus_orb": {"ru": "Lotus Orb", "en": "Lotus Orb"},
    "item_invis_sword": {"ru": "Shadow Blade", "en": "Shadow Blade"},
    "item_silver_edge": {"ru": "Silver Edge", "en": "Silver Edge"},
    "item_sphere": {"ru": "Linken's Sphere", "en": "Linken's Sphere"},
    "item_bloodstone": {"ru": "Bloodstone", "en": "Bloodstone"},
    "item_guardian_greaves": {"ru": "Guardian Greaves", "en": "Guardian Greaves"},
    "item_disperser": {"ru": "Disperser", "en": "Disperser"},
    "item_magic_wand": {"ru": "Magic Wand", "en": "Magic Wand"},
}
# Passive or needing a target: never "not used" from GSI alone.
_NOT_PRESSED = {"item_sphere"}
_ITEM_SLOTS = ("slot",)


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if value != value or abs(value) > 10_000_000:  # NaN or broken GSI
        return None
    return float(value)


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def ready_savers(items: dict[str, Any]) -> list[str]:
    """Saving items in the inventory that could be used right now."""
    ready: list[str] = []
    for slot, value in items.items():
        if not str(slot).startswith(_ITEM_SLOTS):
            continue
        item = _dict(value)
        name = item.get("name")
        if name not in SAVERS or name in _NOT_PRESSED or name in ready:
            continue
        if item.get("passive") is True:
            continue
        can_cast = item.get("can_cast")
        cooldown = _number(item.get("cooldown"))
        # Only what GSI says: castable, or at least off cooldown when the field
        # is missing; an item without either field is not claimed ready.
        if can_cast is False or (can_cast is None and cooldown != 0):
            continue
        if cooldown is not None and cooldown > 0:
            continue
        if name == "item_magic_wand" and (_number(item.get("charges")) or 0) < WAND_CHARGES:
            continue
        ready.append(name)
    return ready


def is_disabled(hero: dict[str, Any]) -> bool:
    return any(hero.get(flag) is True for flag in ("stunned", "hexed", "muted"))


class LastSeconds:
    """One entry per second of match clock, the last WINDOW seconds."""

    def __init__(self) -> None:
        self._entries: deque[dict[str, Any]] = deque(maxlen=WINDOW + 1)

    def reset(self) -> None:
        self._entries.clear()

    def observe(self, clock: int, hero: dict[str, Any], items: dict[str, Any]) -> None:
        if hero.get("alive") is not True:
            return
        hp = _number(hero.get("health_percent"))
        if hp is None:
            return
        entry = {
            "t": clock,
            "hp": round(hp),
            "mp": round(_number(hero.get("mana_percent")) or 0),
            "disabled": is_disabled(hero),
            "ready": ready_savers(items),
        }
        if self._entries and self._entries[-1]["t"] == clock:
            self._entries[-1] = entry  # the latest tick of that second
        elif self._entries and clock < self._entries[-1]["t"]:
            self._entries.clear()  # the clock went back (a reconnect, a replay)
            self._entries.append(entry)
        else:
            self._entries.append(entry)

    def summarize(self, death_clock: int) -> dict[str, Any] | None:
        entries = [e for e in self._entries if 0 <= death_clock - e["t"] <= WINDOW]
        if not entries:
            return None
        last = entries[-1]
        recent = [e for e in entries if death_clock - e["t"] <= FREE_WINDOW]
        usable: list[str] = []
        for entry in recent:
            if not entry["disabled"]:
                usable.extend(name for name in entry["ready"] if name not in usable)
        result: dict[str, Any] = {
            "hp": [[e["t"] - death_clock, e["hp"]] for e in entries],
            "ready": list(last["ready"]),
            "usable": usable,
            "free_s": sum(1 for e in recent if not e["disabled"]),
        }
        high = [e for e in entries if e["hp"] >= BURST_FROM]
        if high:
            burst = death_clock - high[-1]["t"]
            if burst <= BURST_SECONDS:
                result["burst_s"] = max(burst, 1)
        self._entries.clear()
        return result


def saver_label(name: str, lang: str) -> str:
    names = SAVERS.get(name)
    return names["ru" if lang == "ru" else "en"] if names else name
