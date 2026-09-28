"""
post_game.py - the overlay card on Dota's score screen right after a match.

The live-recorded match is reviewed as soon as it ends (GSI timeline), so the
overlay can show the result while the player still looks at the scoreboard:
the review score, the top thing to improve with its drill, the top strength,
and whether the focus problem was avoided. Built in the request language, like
the game plan; the full review stays in the app.
"""

from __future__ import annotations

from typing import Any

from app.analysis_texts import render_finding

TEXT = {
    "ru": {
        "title": "Итог матча",
        "win": "Победа",
        "loss": "Поражение",
        "score": "{score}/100",
        "tip": "Главное: {title}",
        "strength": "Получилось: {title}",
        "focus_met": "Фокус выполнен.",
        "focus_missed": "Фокус не выполнен.",
        "more": "Полный разбор — в приложении.",
    },
    "en": {
        "title": "Match summary",
        "win": "Win",
        "loss": "Loss",
        "score": "{score}/100",
        "tip": "Main point: {title}",
        "strength": "Went well: {title}",
        "focus_met": "Focus met.",
        "focus_missed": "Focus missed.",
        "more": "The full review is in the app.",
    },
}


def post_game_card(
    analysis: dict[str, Any], lang: str, *, focus_met: bool | None = None
) -> dict[str, Any] | None:
    """The card fits the overlay window (176 px): a top row (hero, result, score),
    one main line (the top tip, else the top strength) and a short detail (the
    focus result, the tip's drill, a pointer to the full review)."""
    lang = "ru" if lang == "ru" else "en"
    text = TEXT[lang]
    headline = analysis.get("headline") or {}
    score = headline.get("score")
    if not isinstance(score, (int, float)):
        return None
    win = headline.get("win") if isinstance(headline.get("win"), bool) else None
    improvements = analysis.get("improvements") or []
    strengths = analysis.get("strengths") or []
    # The focus result first: short, and the text may be cut at three lines.
    detail: list[str] = []
    if focus_met is not None:
        detail.append(text["focus_met" if focus_met else "focus_missed"])
    if improvements:
        tip = render_finding(improvements[0], lang)
        main = text["tip"].format(title=tip["title"])
        if tip.get("drill"):
            detail.append(tip["drill"])
    elif strengths:
        main = text["strength"].format(title=render_finding(strengths[0], lang)["title"])
    else:
        main = text["more"]
    if improvements or strengths:
        detail.append(text["more"])
    result = text["win"] if win is True else text["loss"] if win is False else None
    return {
        "title": text["title"],
        "hero": headline.get("hero"),
        "result": result,
        "win": win,
        "score": round(score),
        "score_text": text["score"].format(score=round(score)),
        "grade": headline.get("grade"),
        "main": main,
        "detail": detail,
    }
