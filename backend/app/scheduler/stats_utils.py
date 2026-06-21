"""
scheduler.stats_utils - stateless numeric helpers and session-id extraction.

Pure functions, no scheduler state, no ``self``. Extracted verbatim from
advice_scheduler.py as part of the Phase 2 split (no behavior change).
"""

from __future__ import annotations

from statistics import mean
from typing import Any


def _average(values: list[float]) -> float | None:
    if not values:
        return None
    return round(mean(values), 3)


def _minimum(values: list[float]) -> float | None:
    if not values:
        return None
    return round(min(values), 3)


def _maximum(values: list[float]) -> float | None:
    if not values:
        return None
    return round(max(values), 3)


def _p95(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, int(round((len(ordered) - 1) * 0.95))))
    return round(ordered[index], 3)


def _rate(part: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round(part / total, 3)


def _session_id_from_state(state: dict[str, Any]) -> str | None:
    extra_context = (
        state.get("extra_context") if isinstance(state.get("extra_context"), dict) else {}
    )
    value = extra_context.get("match_session_id") or extra_context.get("match_id")
    if value in {None, ""}:
        return None
    return str(value)
