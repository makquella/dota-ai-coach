"""
home_summary.py - the one card at the top of Home: the last match, the day, the
goals and the focus, from the stored match table and reviews (no network).

- last: the newest analysed match — hero, result, score, K/D/A, when, its top tip
  (the first thing to improve, with its drill) and its top strength;
- today: matches since local midnight (PlayerService._today), with the tilt
  warning and the streak goals of the status;
- focus: the problem the player works on, its last results as marks and how
  many were met, or None.

Texts are rendered in the request language here, like the week.
"""

from __future__ import annotations

from typing import Any

from app.analysis_texts import render_finding
from app.focus_goal import focus_summary

FOCUS_MARKS = 5


def _top(analysis: dict[str, Any], key: str, lang: str) -> dict[str, Any] | None:
    findings = analysis.get(key) or []
    if not findings:
        return None
    rendered = render_finding(findings[0], lang)
    return {
        "id": rendered.get("id"),
        "title": rendered.get("title"),
        "text": rendered.get("text"),
        "drill": rendered.get("drill"),
    }


def last_match(matches: list[dict[str, Any]], lang: str) -> dict[str, Any] | None:
    """`matches`: newest first with their analysis (PlayerStore.matches_for_career)."""
    match = next((m for m in matches if m.get("analysis")), None)
    if match is None:
        return None
    analysis = match["analysis"]
    return {
        "match_id": match["match_id"],
        "hero": match.get("hero"),
        "hero_id": match.get("hero_id"),
        "win": match.get("win"),
        "score": match.get("score"),
        "start_time": match.get("start_time"),
        "duration": match.get("duration"),
        "kills": match.get("kills"),
        "deaths": match.get("deaths"),
        "assists": match.get("assists"),
        "role": analysis.get("role"),
        "tip": _top(analysis, "improvements", lang),
        "strength": _top(analysis, "strengths", lang),
    }


def focus_block(
    focus: dict[str, Any] | None, matches: list[dict[str, Any]], lang: str
) -> dict[str, Any] | None:
    if focus is None:
        return None
    plan = focus_summary(focus, matches, lang)
    results = plan["results"][-FOCUS_MARKS:]
    return {
        "id": plan["id"],
        "title": plan["title"],
        "drill": plan["drill"],
        "results": results,
        "met": sum(1 for r in results if r["met"]),
        "total": len(results),
    }


def home_summary(
    matches: list[dict[str, Any]],
    lang: str,
    *,
    today: dict[str, Any] | None,
    goals: list[dict[str, Any]],
    tilt: dict[str, Any] | None,
    focus: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """None before the first reviewed match (Home then shows the first steps)."""
    last = last_match(matches, lang)
    if last is None:
        return None
    return {
        "last": last,
        "today": today,
        "goals": goals,
        "tilt": tilt,
        "focus": focus_block(focus, matches, lang),
    }
