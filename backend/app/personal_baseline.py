"""
personal_baseline.py - this match against the player's usual numbers on the same hero.

Norms and the lane opponent say how a game went in general; the player's own
average on the hero says whether it was a good or a bad day for them. Needs a
few other reviewed matches on the hero, otherwise there is no baseline.
"""

from __future__ import annotations

from statistics import mean
from typing import Any

MIN_GAMES = 3
MAX_GAMES = 20
# (key, lower is better)
METRICS = (("score", False), ("gpm", False), ("lh_10", False), ("deaths", True))
# Differences this small read as "as usual".
SAME_ABSOLUTE = {"score": 3, "gpm": 15, "lh_10": 3, "deaths": 0.5}


def _value(match: dict[str, Any], key: str) -> float | None:
    if key == "score":
        headline = (match.get("analysis") or {}).get("headline") or {}
        value = headline.get("score", match.get("score"))
    else:
        value = match.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def personal_baseline(match: dict[str, Any], others: list[dict[str, Any]]) -> dict[str, Any] | None:
    """`others`: the player's other matches on the hero, newest first."""
    others = [m for m in others if m.get("match_id") != match.get("match_id")][:MAX_GAMES]
    if len(others) < MIN_GAMES:
        return None
    metrics = []
    for key, lower_is_better in METRICS:
        mine = _value(match, key)
        values = [v for v in (_value(m, key) for m in others) if v is not None]
        if mine is None or len(values) < MIN_GAMES:
            continue
        average = mean(values)
        delta = mine - average
        same = abs(delta) <= max(SAME_ABSOLUTE[key], 0.05 * abs(average))
        metrics.append(
            {
                "key": key,
                "value": mine,
                "average": round(average, 1),
                "delta": round(delta, 1),
                "tone": "same" if same else ("good" if (delta < 0) == lower_is_better else "bad"),
                "games": len(values),
            }
        )
    if not metrics:
        return None
    return {"hero": match.get("hero"), "games": len(others), "metrics": metrics}
