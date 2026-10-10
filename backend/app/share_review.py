"""
share_review.py - the public part of a match review, for «Поділитися розбором».

Only what a page for other people needs, picked field by field from the
rendered review (never passed through as a whole): hero, result, score,
the headline numbers, section scores, the top strengths and improvements with
their drills, the death summary, the AI coach's summary when the player agreed.

Never in it: the match id (anyone could find the account from it on OpenDota),
Steam IDs, nicknames, the scoreboard with other players, the live advice log,
keys. The Worker (services/api/src/share.js) checks the same shape again.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.dota_constants import hero_key

MAX_STRENGTHS = 3
MAX_IMPROVEMENTS = 4
SECTION_ORDER = ("laning", "farm", "survival", "fights", "items", "vision")
TEXT_LIMITS = {"title": 120, "text": 400, "drill": 300, "summary": 800}


def _text(value: Any, limit: int) -> str:
    return str(value or "").strip()[:limit]


def _int(value: Any) -> int | None:
    return int(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def _hero_key(hero_id: Any) -> str | None:
    """The portrait key of Valve's CDN (npc_dota_hero_<key>)."""
    return hero_key(_int(hero_id))


def _finding(finding: dict[str, Any], *, drill: bool) -> dict[str, Any]:
    row = {
        "title": _text(finding.get("title"), TEXT_LIMITS["title"]),
        "text": _text(finding.get("text"), TEXT_LIMITS["text"]),
    }
    if drill and finding.get("drill"):
        row["drill"] = _text(finding.get("drill"), TEXT_LIMITS["drill"])
    return row


def public_review(detail: dict[str, Any], lang: str, *, with_coach: bool) -> dict[str, Any] | None:
    """The shareable review, or None when the match has no review yet."""
    analysis = detail.get("analysis")
    if not analysis:
        return None
    headline = analysis.get("headline") or {}
    summary = detail.get("summary") or {}
    start = _int(summary.get("start_time"))
    sections = analysis.get("sections") or {}
    result: dict[str, Any] = {
        "lang": "uk" if lang == "uk" else "en",
        "hero": _text(headline.get("hero"), 40),
        "hero_key": _hero_key(headline.get("hero_id") or summary.get("hero_id")),
        "win": headline.get("win") if isinstance(headline.get("win"), bool) else None,
        "duration": _int(headline.get("duration")),
        "played_on": datetime.fromtimestamp(start, UTC).date().isoformat() if start else None,
        "score": _int(headline.get("score")),
        "grade": _text(headline.get("grade"), 2) or None,
        "role": _text(analysis.get("role_label"), 30) or None,
        "parsed": bool(analysis.get("parsed")),
        "stats": {
            key: _int(headline.get(key))
            for key in (
                "kills",
                "deaths",
                "assists",
                "gpm",
                "xpm",
                "last_hits",
                "denies",
                "net_worth",
                "hero_damage",
            )
        },
        "sections": [
            {
                "label": _text(sections[name].get("label"), 30),
                "score": _int(sections[name].get("score")),
            }
            for name in SECTION_ORDER
            if isinstance(sections.get(name), dict)
        ],
        "strengths": [
            _finding(f, drill=False) for f in (analysis.get("strengths") or [])[:MAX_STRENGTHS]
        ],
        "improvements": [
            _finding(f, drill=True) for f in (analysis.get("improvements") or [])[:MAX_IMPROVEMENTS]
        ],
    }
    deaths = analysis.get("death_review") or {}
    if deaths.get("deaths"):
        notes = deaths.get("notes") or {}
        result["deaths"] = {
            "count": len(deaths["deaths"]),
            "enemy_half": _int(notes.get("enemy_half")) or 0,
            "unspent_gold": _int(notes.get("unspent_gold")) or 0,
        }
    coach = detail.get("coach") or {}
    review = coach.get("review") or {}
    if with_coach and coach.get("state") == "ready" and review.get("summary"):
        result["coach"] = _text(review.get("summary"), TEXT_LIMITS["summary"])
    return result
