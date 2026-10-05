"""
death_screen.py - the overlay card while the player waits to respawn.

Built from the match recording (the death just stored by MatchTracker with its
last seconds) and the live state, in the request language, only facts:
- how the death happened: a burst from high HP (last_moments `burst_s`);
- a rescue item or ability that was ready and not pressed (`usable`);
- the same place again (PlayerService._death_place: 2+ deaths there lately);
- what to buy now: the next build item when its missing parts fit the gold,
  else "buy parts of it", keeping the buyback cost after minute 30.
Title: «Возрождение через 23 с». Nothing to say → no card.
"""

from __future__ import annotations

from typing import Any

from app.analysis_texts import PLACE_SIDES, PLACE_ZONES
from app.last_moments import saver_label
from app.live_tools import MATCH_PLACE_MIN

BUYBACK_RESERVE_MINUTE = 30
SPEND_MIN_GOLD = 500

TEXT = {
    "ru": {
        "title": "Возрождение через {s} с",
        "title_plain": "Пока ждёте возрождения",
        "burst": "Убили за {s} с при высоком HP: поймали, когда вы были одни или на виду.",
        "unpressed": "Готово, но не нажато: {name} — в следующий раз жмите при первом ударе.",
        "place": "{n}-я смерть {place} за {m} мин — после возрождения идите в другое место.",
        "place_match": "{n}-я смерть {place} за игру — после возрождения идите в другое место.",
        "buy_item": "Купите {item} сейчас: золота хватает, курьер принесёт.",
        "buy_parts": "Купите части {item}: не хватает {need} золота.",
        "spend": "Потратьте {gold} золота на следующий предмет — у фонтана это быстрее.",
        "reserve": " Оставьте {cost} на байбэк.",
        "why_disabled": "Почему {item}: смертей под контролем — {n}, с ним контроль вас не удержит.",
        "why_burst": "Почему {item}: смертей за пару секунд с высокого здоровья — {n}, он даст время.",
        "why_targeted": "Почему {item}: смертей под контролем против {enemy} — {n}, он блокирует {spell}.",
        "why_evasion": "Почему {item}: {enemy} уклоняется от атак, а он бьёт без промаха.",
        "why_healing": "Почему {item}: {enemy} много лечится, а он режет лечение.",
        "why_illusions": "Почему {item}: {enemy} дерётся иллюзиями, а он бьёт их всех сразу.",
        "why_magic": "Почему {item}: героев врага с магическим уроном — {n}, он защитит от него.",
    },
    "en": {
        "title": "Respawn in {s} s",
        "title_plain": "While you wait to respawn",
        "burst": "Killed within {s} s from high HP: caught alone or in the open.",
        "unpressed": "{name} was ready and not pressed: next time use it at the first hit.",
        "place": "Death number {n} {place} in {m} min: after respawn, go somewhere else.",
        "place_match": "Death number {n} {place} this game: after respawn, go somewhere else.",
        "buy_item": "Buy {item} now: you have the gold, the courier brings it.",
        "buy_parts": "Buy parts of {item}: {need} gold to go.",
        "spend": "Spend {gold} gold on your next item: at the fountain it is quicker.",
        "reserve": " Keep {cost} for buyback.",
        "why_disabled": "Why {item}: {n} deaths under stuns, and with it no disable holds you.",
        "why_burst": "Why {item}: {n} deaths in seconds from high health, and it buys you time.",
        "why_targeted": "Why {item}: {n} deaths under stuns against {enemy}, and it blocks {spell}.",
        "why_evasion": "Why {item}: {enemy} dodges attacks, and it never misses.",
        "why_healing": "Why {item}: {enemy} heals a lot, and it cuts the healing.",
        "why_illusions": "Why {item}: {enemy} fights with illusions, and it hits them all.",
        "why_magic": "Why {item}: {n} enemy heroes deal magic damage, and it protects you.",
    },
}


def _int(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value != value:
        return None
    return int(value)


def _place(place: dict[str, Any] | None, lang: str) -> str | None:
    if not place:
        return None
    zone, side = place.get("zone"), place.get("side")
    sides = PLACE_SIDES[lang]
    if lang == "ru":
        zones = PLACE_ZONES["ru"]["in"]
        return f"{zones[zone]} {sides[side]}" if zone in zones and side in sides else None
    names = PLACE_ZONES["en"]["name"]
    return f"in the {names[zone]} {sides[side]}" if zone in names and side in sides else None


def build_death_screen(
    *,
    death: dict[str, Any] | None,
    place: dict[str, Any] | None,
    respawn: Any,
    gold: Any,
    buyback_cost: Any,
    minute: Any,
    next_item: dict[str, Any] | None,
    lang: str,
) -> dict[str, Any] | None:
    lang = "ru" if lang == "ru" else "en"
    text = TEXT[lang]
    lines: list[str] = []
    death = death or {}
    burst = _int(death.get("burst_s"))
    if burst:
        lines.append(text["burst"].format(s=burst))
    usable = [n for n in death.get("usable") or [] if isinstance(n, str)]
    if usable:
        lines.append(text["unpressed"].format(name=saver_label(usable[0], lang)))
    where = _place(place, lang)
    count = _int((place or {}).get("count"))
    if where and count and count >= 2:
        minutes = _int((place or {}).get("minutes")) or 1
        lines.append(text["place"].format(n=count, place=where, m=minutes))
    elif where and (_int((place or {}).get("in_match")) or 0) >= MATCH_PLACE_MIN:
        lines.append(text["place_match"].format(n=_int((place or {}).get("in_match")), place=where))
    buy = _buy_line(text, gold, buyback_cost, minute, next_item)
    if buy:
        lines.append(buy)
        why = (next_item or {}).get("why")
        enemy = (next_item or {}).get("enemy")
        count = _int((next_item or {}).get("count"))
        if (why in ("disabled", "burst", "magic") and count) or (
            why == "targeted" and count and enemy and next_item.get("spell")
        ):
            lines.append(
                text[f"why_{why}"].format(
                    item=next_item["name"], n=count, enemy=enemy, spell=next_item.get("spell")
                )
            )
        elif why in ("evasion", "healing", "illusions") and enemy:
            lines.append(text[f"why_{why}"].format(item=next_item["name"], enemy=enemy))
    if not lines:
        return None
    seconds = _int(respawn)
    title = text["title"].format(s=seconds) if seconds and seconds > 0 else text["title_plain"]
    return {"title": title, "respawn": seconds, "lines": lines}


def _buy_line(
    text: dict[str, str], gold: Any, buyback_cost: Any, minute: Any, next_item: Any
) -> str | None:
    gold = _int(gold)
    if gold is None:
        return None
    reserve = 0
    if (_int(minute) or 0) >= BUYBACK_RESERVE_MINUTE:
        reserve = _int(buyback_cost)
        if reserve is None:
            return None  # can't tell what to keep for buyback
    spare = gold - reserve
    suffix = text["reserve"].format(cost=reserve) if reserve else ""
    if spare < SPEND_MIN_GOLD:
        return None
    if isinstance(next_item, dict) and isinstance(next_item.get("name"), str):
        left = _int(next_item.get("gold_left")) or 0
        if left > 0 and spare >= left:
            return text["buy_item"].format(item=next_item["name"]) + suffix
        if left > 0:
            return text["buy_parts"].format(item=next_item["name"], need=left - spare) + suffix
    return text["spend"].format(gold=spare) + suffix
