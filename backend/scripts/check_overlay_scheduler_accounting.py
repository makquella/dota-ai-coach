#!/usr/bin/env python3
"""
Small regression check for overlay scheduler accounting.

It uses the in-memory scheduler directly, so it does not require a running
backend, Dota, GSI, httpx, or external APIs.
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.advice_scheduler import AdviceScheduler  # noqa: E402
from app.schemas import GameSituationRequest  # noqa: E402


def main() -> int:
    scheduler = AdviceScheduler(enable_llm=False)
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)

    soft_state = _state(match_id="accounting_match_a", hp_percent=90)
    scheduler.observe_state(soft_state, "SOFT_STATUS", now=now)
    _assert_equal(scheduler.stats(now)["advice_count"], 0, "SOFT_STATUS must not increment advice_count")

    full_request = GameSituationRequest(**_state(match_id="accounting_match_a", hp_percent=42))
    first = scheduler.evaluate(full_request, "LOW_HP_WARNING", [], now=now + timedelta(seconds=1))
    _assert_equal(first.status, "advice", "full advice should be shown")
    _assert_equal(first.advice_count, 1, "full advice should increment advice_count")

    duplicate = scheduler.evaluate(full_request, "LOW_HP_WARNING", [], now=now + timedelta(seconds=2))
    _assert_equal(duplicate.status, "active_advice", "duplicate full advice should keep the visible card active")
    _assert_equal(duplicate.advice_count, 1, "active advice must not increment advice_count")
    _assert_equal(duplicate.suppressed_reason, "cooldown_keep_visible", "active advice should explain cooldown visibility")

    no_advice = scheduler.evaluate(full_request, "NO_ADVICE", [], now=now + timedelta(seconds=3))
    _assert_equal(no_advice.status, "active_advice", "NO_ADVICE should keep active advice visible during its window")
    _assert_equal(no_advice.advice_count, 1, "NO_ADVICE must not increment advice_count")

    switched_request = GameSituationRequest(**_state(match_id="accounting_match_b", hp_percent=42))
    switched = scheduler.evaluate(switched_request, "LOW_HP_WARNING", [], now=now + timedelta(seconds=4))
    _assert_equal(switched.status, "advice", "new match should allow fresh advice")
    _assert_equal(switched.advice_count, 1, "new match_session_id must not carry previous advice_count")
    _assert_equal(
        scheduler.stats(now)["match_session_id"],
        "accounting_match_b",
        "scheduler should track the current match session id",
    )

    scheduler.reset()
    _assert_equal(scheduler.stats(now)["advice_count"], 0, "session reset must set advice_count to 0")

    print("Overlay scheduler accounting check passed.")
    return 0


def _state(*, match_id: str, hp_percent: int) -> dict[str, Any]:
    return {
        "hero": "Juggernaut",
        "role": "carry",
        "minute": 3,
        "level": 4,
        "gold": 500,
        "items": ["Tango"],
        "hp_percent": hp_percent,
        "game_state": "laning",
        "team_status": "unknown",
        "extra_context": {
            "match_session_id": match_id,
            "match_id": match_id,
            "mana_percent": 52,
            "last_hits": 12,
        },
    }


def _assert_equal(actual: Any, expected: Any, message: str) -> None:
    if actual != expected:
        raise AssertionError(f"{message}: expected {expected!r}, got {actual!r}")


if __name__ == "__main__":
    raise SystemExit(main())
