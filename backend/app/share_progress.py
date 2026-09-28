"""
share_progress.py - the public part of Progress, for «Поделиться прогрессом».

Like share_review.py, only what a page for other people needs, picked field by
field from the rendered career (never passed through as a whole): the number
of matches, wins and losses, averages, last 10 vs the 10 before, the top
heroes, what keeps going well, what keeps coming back with its drill, the
focus with its result, and the AI coach's summary when the player agreed.

Never in it: match ids, Steam IDs, nicknames, the per-match series, other
players, the rank of the lobby, the questions asked to the coach, keys. The
Worker (services/api/src/share.js, validateProgress) checks the same shape.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.share_review import _hero_key, _int, _text

MAX_HEROES = 5
MAX_STRENGTHS = 3
MAX_PROBLEMS = 3
TREND_KEYS = ("score", "winrate", "gpm", "lh_10", "deaths")
AVERAGE_KEYS = ("kda", "gpm", "xpm", "lh_10", "deaths", "score")


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return round(float(value), 1)


def _day(timestamp: Any) -> str | None:
    value = _int(timestamp)
    return datetime.fromtimestamp(value, UTC).date().isoformat() if value else None


def _recurring(row: dict[str, Any], *, drill: bool) -> dict[str, Any]:
    item = {
        "title": _text(row.get("title"), 120),
        "count": _int(row.get("count")),
        "of": _int(row.get("of")),
    }
    if drill and row.get("drill"):
        item["drill"] = _text(row.get("drill"), 300)
    return item


def public_progress(
    career: dict[str, Any], lang: str, *, with_coach: bool
) -> dict[str, Any] | None:
    """The shareable Progress, or None before the first reviewed match."""
    if not career.get("linked") or not career.get("analyzed"):
        return None
    # Every counted match, not the chart's series (the last 20 only).
    period = career.get("period") or {}
    averages = career.get("averages") or {}
    trend = career.get("trend") or {}
    result: dict[str, Any] = {
        "kind": "progress",
        "lang": "ru" if lang == "ru" else "en",
        "matches": _int(career.get("matches")),
        "analyzed": _int(career.get("analyzed")),
        "wins": _int(career.get("wins")),
        "losses": _int(career.get("losses")),
        "winrate": _int(career.get("winrate")),
        "rank": _text(career.get("rank_bracket_label"), 30) or None,
        "period": {"from": _day(period.get("from")), "to": _day(period.get("to"))}
        if period
        else None,
        "averages": {key: _number(averages.get(key)) for key in AVERAGE_KEYS},
        "trend": [
            {
                "key": key,
                "recent": _number(trend[key].get("recent")),
                "previous": _number(trend[key].get("previous")),
                "better": trend[key].get("better")
                if isinstance(trend[key].get("better"), bool)
                else None,
            }
            for key in TREND_KEYS
            if trend.get("enough") and isinstance(trend.get(key), dict)
        ],
        "heroes": [
            {
                "hero": _text(row.get("hero"), 40),
                "hero_key": _hero_key(row.get("hero_id")),
                "matches": _int(row.get("matches")),
                "winrate": _int(row.get("winrate")),
            }
            for row in (career.get("heroes") or [])[:MAX_HEROES]
        ],
        "strengths": [
            _recurring(row, drill=False)
            for row in (career.get("recurring_strengths") or [])[:MAX_STRENGTHS]
        ],
        "problems": [
            _recurring(row, drill=True) for row in (career.get("recurring") or [])[:MAX_PROBLEMS]
        ],
    }
    focus = career.get("focus") or {}
    if focus.get("title"):
        result["focus"] = {
            "title": _text(focus.get("title"), 120),
            "met": _int(focus.get("met")) or 0,
            "total": _int(focus.get("total")) or 0,
        }
    coach = career.get("coach") or {}
    review = coach.get("review") or {}
    if with_coach and coach.get("state") == "ready" and review.get("summary"):
        result["coach"] = _text(review.get("summary"), 800)
    return result
