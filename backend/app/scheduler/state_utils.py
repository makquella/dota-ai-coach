"""
scheduler.state_utils - stateless state-parsing and time helpers.

Pure functions, no scheduler state, no ``self``. Extracted verbatim from
advice_scheduler.py as part of the Phase 2 split (no behavior change).

Note: _active_advice_duration is intentionally LEFT in advice_scheduler.py
because it references DEATH_REVIEW_DECISIONS (a module constant there) and
moving it would create a circular import (advice_scheduler -> state_utils ->
advice_scheduler).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


def _utcnow(value: datetime | None) -> datetime:
    if value is None:
        return datetime.now(UTC)
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


def _ctx_value(state: dict[str, Any], key: str, default: Any = None) -> Any:
    if key in state:
        return state.get(key)
    extra_context = (
        state.get("extra_context") if isinstance(state.get("extra_context"), dict) else {}
    )
    return extra_context.get(key, default)


def _ctx_int(state: dict[str, Any], key: str, default: int) -> int:
    return _to_int(_ctx_value(state, key), default)


def _to_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _optional_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _state_game_time_seconds(state: dict[str, Any]) -> float | None:
    extra_context = (
        state.get("extra_context") if isinstance(state.get("extra_context"), dict) else {}
    )
    for key in (
        "game_time",
        "clock_time",
        "timestamp_seconds",
        "simulated_timestamp_seconds",
        "demo_timestamp_seconds",
    ):
        value = extra_context.get(key) if key in extra_context else state.get(key)
        parsed = _optional_float(value)
        if parsed is not None:
            return max(0.0, parsed)
    return None


def _is_dead_or_respawning(state: dict[str, Any]) -> bool:
    alive = _ctx_value(state, "alive", True)
    respawn_seconds = _ctx_int(state, "respawn_seconds", 0)
    return (
        alive is False or str(alive).strip().lower() in {"false", "0", "no"} or respawn_seconds > 0
    )
