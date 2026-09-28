"""
rank_history.py - the player's rank medal over time.

OpenDota only knows the current medal (rank_tier), and a match does not carry
the player's rank at that time. So every sync notes the medal with the date
when it changed (meta `rank_history:<account>`, JSON), and Progress shows the
steps: from which medal to which, and when.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from app.analysis_texts import rank_label

MAX_ENTRIES = 120
MAX_SHOWN = 8


def _valid(tier: Any) -> int | None:
    if isinstance(tier, bool) or not isinstance(tier, int):
        return None
    return tier if 10 <= tier <= 80 else None


def load(raw: str | None) -> list[dict[str, Any]]:
    try:
        entries = json.loads(raw or "[]")
    except (TypeError, ValueError):
        return []
    return [
        {"date": str(e["date"]), "tier": e["tier"]}
        for e in entries
        if isinstance(e, dict) and _valid(e.get("tier")) and e.get("date")
    ]


def note(raw: str | None, tier: Any, *, today: str | None = None) -> str | None:
    """The new meta value when the medal changed (or is the first one), else None."""
    tier = _valid(tier)
    if tier is None:
        return None
    entries = load(raw)
    if entries and entries[-1]["tier"] == tier:
        return None
    entries.append({"date": today or datetime.now(UTC).date().isoformat(), "tier": tier})
    return json.dumps(entries[-MAX_ENTRIES:])


def summary(raw: str | None, lang: str) -> dict[str, Any] | None:
    """For Progress: the current medal, the first one noted and the last steps."""
    entries = load(raw)
    if not entries:
        return None
    first, current = entries[0], entries[-1]
    steps = [
        {"date": e["date"], "tier": e["tier"], "label": rank_label(e["tier"], lang)}
        for e in entries[-MAX_SHOWN:]
    ]
    return {
        "current": rank_label(current["tier"], lang),
        "current_tier": current["tier"],
        "since": first["date"],
        "first": rank_label(first["tier"], lang),
        "change": current["tier"] - first["tier"],
        "steps": steps,
    }
