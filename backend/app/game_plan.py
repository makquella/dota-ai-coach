"""
game_plan.py - "plan for this game": shown on the overlay from hero pick to 1:30.

Three short lines built from data the app already has, nothing guessed:

- the last-hit target at 10:00 for the player's usual role on this hero, with
  their own average on it when they have played it;
- the key item most players buy on this hero and when most of them finish it
  (OpenDota public matches, cached), with the win rate at that timing;
- how pro players level the hero: the ability they max first and second
  (app/skill_build.py, recent pro games);
- the enemy heroes the player loses to most (lineups of their own reviewed
  OpenDota matches, met 3+ times: on this hero when it has such records, else
  on any hero), so they know what to watch for once they see the enemy draft;
- the mistake that keeps coming back in their reviews (on this hero if it has
  enough reviewed games, else overall).

Next to the hero's name: the player's record on it over the last 20 matches
(`record`, "6–4"), from 3 finished games.

Every line is optional; with nothing to say there is no plan.
"""

from __future__ import annotations

from collections import Counter
from statistics import mean
from typing import Any

from app.analysis_texts import clock
from app.career_analysis import analyze_career, opponents
from app.hero_meta import popular_build, timing_verdict
from app.hero_profiles import get_hero_position
from app.post_match_analysis import TARGETS
from app.schemas import is_supported_hero

# The window: from 20 s before the horn (the first bounty runes) until this
# game time. Earlier the card is the first skill point's (players asked for
# time to read it; the plan used to replace it right after the pick).
SHOW_FROM_CLOCK = -20
SHOW_UNTIL_CLOCK = 90
MIN_HERO_REVIEWS_FOR_REMINDER = 3
MIN_RECORD_GAMES = 3
RECORD_GAMES = 20
HARD_OPPONENTS_SHOWN = 2

TEXT = {
    "ru": {
        "title": "План на игру",
        "lh": "К 10:00 — {target} добиваний",
        "lh_avg": "К 10:00 — {target} добиваний (ваш средний: {avg})",
        "item": "{item} к {time}, как у большинства: побед {winrate}%",
        "item_plain": "Ключевой предмет: {item}",
        "reminder": "Частая ошибка: {title}",
        "focus": "Ваш фокус: {title}",
        "hard": "Тяжело против: {heroes}",
        "skills": "Прокачка у про: сначала {first}, потом {second}",
    },
    "en": {
        "title": "Plan for this game",
        "lh": "{target} last hits by 10:00",
        "lh_avg": "{target} last hits by 10:00 (your average: {avg})",
        "item": "{item} by {time}, like most players: {winrate}% wins",
        "item_plain": "Key item: {item}",
        "reminder": "Common mistake: {title}",
        "focus": "Your focus: {title}",
        "hard": "Hard matchups: {heroes}",
        "skills": "Pros max {first} first, then {second}",
    },
}


def _sentence_tail(title: str) -> str:
    """ "Lost the last-hit race" -> "lost the last-hit race" after a colon
    (an acronym such as "GPM below…" keeps its capitals)."""
    if len(title) > 1 and title[0].isupper() and title[1].islower():
        return title[0].lower() + title[1:]
    return title


def _usual_role(history: list[dict[str, Any]], hero: str) -> str | None:
    """The role most of the player's reviewed games on the hero had. Without
    reviews only the carry-advisor heroes are assumed core; for any other hero
    (a first Lion game) the role is unknown and there is no last-hit target."""
    roles = Counter(
        m["analysis"].get("role")
        for m in history
        if m.get("analysis") and m["analysis"].get("role") in TARGETS
    )
    if roles:
        return roles.most_common(1)[0][0]
    if not is_supported_hero(hero):
        return None
    position = get_hero_position(hero)
    return position if position in ("offlane", "support") else "core"


def _record(history: list[dict[str, Any]]) -> str | None:
    """ "6–4": wins and losses of the last RECORD_GAMES finished games on the hero
    (rows without a result are skipped, older ones fill their place)."""
    results = [m.get("win") for m in history if m.get("win") is not None][:RECORD_GAMES]
    if len(results) < MIN_RECORD_GAMES:
        return None
    wins = sum(1 for won in results if won)
    return f"{wins}–{len(results) - wins}"


def key_item(meta: dict[str, Any] | None) -> dict[str, Any] | None:
    """The hero's key item with its typical timing (live tip «Maelstrom is late»)."""
    return _key_item(meta)


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
            "key": item["key"],
            "name": item["name"],
            "typical_t": verdict["typical_bucket"],
            "winrate": verdict["typical_winrate"],
        }
    return {"key": item["key"], "name": item["name"], "typical_t": None, "winrate": None}


def build_game_plan(
    *,
    focus: str | None = None,
    hero: str,
    history: list[dict[str, Any]],
    all_recent: list[dict[str, Any]],
    meta: dict[str, Any] | None,
    lang: str,
    record_history: list[dict[str, Any]] | None = None,
    skills: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """`history`: the player's recent matches on this hero (store rows with analysis);
    `all_recent`: recent matches on any hero (for the reminder); `meta`: cached hero meta;
    `record_history`: more rows on the hero for the record (default: `history`);
    `skills`: the pro skill order (app/skill_build.skill_order)."""
    record_rows = history if record_history is None else record_history
    lang = "ru" if lang == "ru" else "en"
    text = TEXT[lang]
    lines: list[str] = []

    role = _usual_role(history, hero)
    if role is not None and role != "support":
        target = int(TARGETS[role]["lh10_good"])
        lh10 = [m["lh_10"] for m in history if isinstance(m.get("lh_10"), int)]
        if lh10:
            lines.append(text["lh_avg"].format(target=target, avg=round(mean(lh10))))
        else:
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

    order = (skills or {}).get("order") or []
    if len(order) >= 2:
        names = (skills or {}).get("names") or {}
        lines.append(
            text["skills"].format(
                first=names.get(order[0], order[0]), second=names.get(order[1], order[1])
            )
        )

    if focus:
        # The problem the player chose to work on beats the most frequent one.
        lines.append(text["focus"].format(title=_sentence_tail(focus)))
    else:
        reviewed_on_hero = [m for m in history if m.get("analysis")]
        source = (
            reviewed_on_hero
            if len(reviewed_on_hero) >= MIN_HERO_REVIEWS_FOR_REMINDER
            else all_recent
        )
        recurring = analyze_career(source, lang).get("recurring") or [] if source else []
        if recurring:
            lines.append(text["reminder"].format(title=_sentence_tail(recurring[0]["title"])))

    # Last: the overlay clamps the lines under the first one, so a wrapped line
    # cuts the end — the matchups, never the focus.
    hard = _hard_opponents(record_rows, all_recent)
    if hard:
        heroes = ", ".join(f"{row['hero']} {row['wins']}–{row['losses']}" for row in hard)
        lines.append(text["hard"].format(heroes=heroes))

    if not lines:
        return None
    return _plan(text, hero, role, lines, record_rows)


def _hard_opponents(
    on_hero: list[dict[str, Any]], all_recent: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """The enemy heroes with the worst record (met 3+ times, under 50 % wins):
    on this hero when it has such records, else on any hero."""
    for rows in (on_hero, all_recent):
        found = (opponents([m for m in rows if m.get("analysis")]) or {}).get("hard") or []
        if found:
            return found[:HARD_OPPONENTS_SHOWN]
    return []


def _plan(text, hero, role, lines, history) -> dict[str, Any]:
    plan = {"title": text["title"], "hero": hero, "role": role, "lines": lines}
    record = _record(history)
    if record:
        plan["record"] = record
    return plan
