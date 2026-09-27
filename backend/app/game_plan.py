"""
game_plan.py - "plan for this game": shown on the overlay from hero pick to 1:30.

Three short lines built from data the app already has, nothing guessed:

- the last-hit target at 10:00 for the player's usual role on this hero, with
  their own average on it when they have played it;
- the key item most players buy on this hero and when most of them finish it
  (OpenDota public matches, cached), with the win rate at that timing;
- the mistake that keeps coming back in their reviews (on this hero if it has
  enough reviewed games, else overall).

Every line is optional; with nothing to say there is no plan.
"""

from __future__ import annotations

from collections import Counter
from statistics import mean
from typing import Any

from app.analysis_texts import clock
from app.career_analysis import analyze_career
from app.hero_meta import popular_build, timing_verdict
from app.post_match_analysis import TARGETS

# The window: from hero pick (negative clock) until this game time.
SHOW_UNTIL_CLOCK = 90
MIN_HERO_REVIEWS_FOR_REMINDER = 3

TEXT = {
    "ru": {
        "title": "План на игру",
        "lh": "К 10:00 — {target} добиваний",
        "lh_avg": "К 10:00 — {target} добиваний (ваш средний: {avg})",
        "item": "{item} к {time}, как у большинства: побед {winrate}%",
        "item_plain": "Ключевой предмет: {item}",
        "reminder": "Частая ошибка: {title}",
        "focus": "Ваш фокус: {title}",
    },
    "en": {
        "title": "Plan for this game",
        "lh": "{target} last hits by 10:00",
        "lh_avg": "{target} last hits by 10:00 (your average: {avg})",
        "item": "{item} by {time}, like most players: {winrate}% wins",
        "item_plain": "Key item: {item}",
        "reminder": "Common mistake: {title}",
        "focus": "Your focus: {title}",
    },
}


def _sentence_tail(title: str) -> str:
    """ "Lost the last-hit race" -> "lost the last-hit race" after a colon
    (an acronym such as "GPM below…" keeps its capitals)."""
    if len(title) > 1 and title[0].isupper() and title[1].islower():
        return title[0].lower() + title[1:]
    return title


def _usual_role(history: list[dict[str, Any]]) -> str:
    roles = Counter(
        m["analysis"].get("role")
        for m in history
        if m.get("analysis") and m["analysis"].get("role") in TARGETS
    )
    return roles.most_common(1)[0][0] if roles else "core"


def _key_item(meta: dict[str, Any] | None) -> dict[str, Any] | None:
    if not meta:
        return None
    build = popular_build(meta.get("popularity"), meta.get("constants"))
    candidates = (build.get("mid") or []) + (build.get("early") or [])
    if not candidates:
        return None
    item = candidates[0]
    verdict = timing_verdict(meta.get("timings"), item["key"], 0)
    if verdict:
        return {
            "name": item["name"],
            "typical_t": verdict["typical_bucket"],
            "winrate": verdict["typical_winrate"],
        }
    return {"name": item["name"], "typical_t": None, "winrate": None}


def build_game_plan(
    *,
    focus: str | None = None,
    hero: str,
    history: list[dict[str, Any]],
    all_recent: list[dict[str, Any]],
    meta: dict[str, Any] | None,
    lang: str,
) -> dict[str, Any] | None:
    """`history`: the player's recent matches on this hero (store rows with analysis);
    `all_recent`: recent matches on any hero (for the reminder); `meta`: cached hero meta."""
    lang = "ru" if lang == "ru" else "en"
    text = TEXT[lang]
    lines: list[str] = []

    role = _usual_role(history)
    target = int(TARGETS[role]["lh10_good"])
    lh10 = [m["lh_10"] for m in history if isinstance(m.get("lh_10"), int)]
    if lh10 and role != "support":
        lines.append(text["lh_avg"].format(target=target, avg=round(mean(lh10))))
    elif role != "support":
        lines.append(text["lh"].format(target=target))

    item = _key_item(meta)
    if item and item["typical_t"] is not None:
        lines.append(
            text["item"].format(
                item=item["name"], time=clock(item["typical_t"]), winrate=item["winrate"]
            )
        )
    elif item:
        lines.append(text["item_plain"].format(item=item["name"]))

    if focus:
        # The problem the player chose to work on beats the most frequent one.
        lines.append(text["focus"].format(title=_sentence_tail(focus)))
        return {"title": text["title"], "hero": hero, "role": role, "lines": lines}

    reviewed_on_hero = [m for m in history if m.get("analysis")]
    source = (
        reviewed_on_hero if len(reviewed_on_hero) >= MIN_HERO_REVIEWS_FOR_REMINDER else all_recent
    )
    recurring = analyze_career(source, lang).get("recurring") or [] if source else []
    if recurring:
        lines.append(text["reminder"].format(title=_sentence_tail(recurring[0]["title"])))

    if not lines:
        return None
    return {"title": text["title"], "hero": hero, "role": role, "lines": lines}
