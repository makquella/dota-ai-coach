"""
Characterization tests for the evaluate() duplicate gate (segment S3).

Added in Phase 4B Wave 2 BEFORE extracting S3, so the extract can be verified
against frozen behavior. Coverage showed S3 was not entered by any test (only
its active-keep-visible sub-path was incidentally hit); these tests drive both
the plain duplicate and the DEATH_REVIEW (duplicate_death_review) branches,
asserting the visible suppressed_reason and the duplicate_suppressed_count.

Determinism: every step passes an explicit `now` so wall-clock fields are
frozen. USE_LLM stays false.
"""

from __future__ import annotations

from datetime import UTC, datetime

from app.advice_scheduler import ADVICE_SCHEDULER
from app.schemas import GameSituationRequest


def _farm_request() -> GameSituationRequest:
    return GameSituationRequest(
        hero="Phantom Lancer",
        role="carry",
        minute=15,
        level=15,
        gold=2000,
        items=["Power Treads", "Manta Style"],
        hp_percent=80,
        game_state="calm farming",
        team_status="unknown",
        extra_context={
            "source_type": "replay_gsi_like",
            "context_confidence": "high",
            "game_time": 900,
            "timestamp_seconds": 900,
            "alive": True,
            "mana_percent": 80,
            "last_hits": 120,
            "farm_quality": "low",
            "hp_pressure_state": "healthy",
            "position_zone": "lane_area",
            "position_risk": "medium",
            "missing_signals": ["enemy_positions"],
        },
    )


def _death_review_request() -> GameSituationRequest:
    req = _farm_request()
    data = req.model_dump()
    data["hp_percent"] = 0
    data["extra_context"]["alive"] = False
    data["extra_context"]["respawn_seconds"] = 20
    data["extra_context"]["hp_pressure_state"] = "critical"
    return GameSituationRequest(**data)


def test_evaluate_plain_duplicate_increments_counter_and_keeps_visible() -> None:
    """A repeated identical request is a duplicate: counter increments and the
    still-active advice is kept visible (cooldown_keep_visible reason)."""
    ADVICE_SCHEDULER.reset()
    t0 = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)
    first = ADVICE_SCHEDULER.evaluate(_farm_request(), "FARMING_PHASE_PRESSURE", [], now=t0)
    assert first.new_advice is True
    assert first.suppressed_reason is None

    t1 = datetime(2026, 1, 1, 0, 0, 2, tzinfo=UTC)
    second = ADVICE_SCHEDULER.evaluate(_farm_request(), "FARMING_PHASE_PRESSURE", [], now=t1)
    assert second.new_advice is False
    # Same state_hash -> duplicate path; advice still visible -> active_advice
    assert second.status == "active_advice"
    assert second.suppressed_reason == "cooldown_keep_visible"
    assert ADVICE_SCHEDULER.state.duplicate_suppressed_count == 1


def test_evaluate_plain_duplicate_returns_cooldown_when_active_expired() -> None:
    """The duplicate fall-through: when the same request repeats AFTER the active
    advice TTL has expired, the active-keep-visible path returns None and S3
    falls through to a cooldown result with the 'duplicate' reason. Covers the
    non-active sub-path of the duplicate gate."""
    ADVICE_SCHEDULER.reset()
    t0 = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)
    first = ADVICE_SCHEDULER.evaluate(_farm_request(), "FARMING_PHASE_PRESSURE", [], now=t0)
    assert first.new_advice is True

    # FARMING_PHASE_PRESSURE active TTL is 8s; at t+10 the active advice expired,
    # so the duplicate gate takes its fall-through (cooldown) return path.
    t10 = datetime(2026, 1, 1, 0, 0, 10, tzinfo=UTC)
    second = ADVICE_SCHEDULER.evaluate(_farm_request(), "FARMING_PHASE_PRESSURE", [], now=t10)
    assert second.new_advice is False
    assert second.status == "cooldown"
    assert second.suppressed_reason == "duplicate"
    assert ADVICE_SCHEDULER.state.duplicate_suppressed_count == 1


def test_evaluate_death_review_duplicate_uses_duplicate_death_review_reason() -> None:
    """A repeated DEATH_REVIEW request keeps the advice visible but surfaces the
    duplicate_death_review reason (DEATH_REVIEW is not masked into
    cooldown_keep_visible)."""
    ADVICE_SCHEDULER.reset()
    t0 = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)
    first = ADVICE_SCHEDULER.evaluate(_death_review_request(), "DEATH_REVIEW", [], now=t0)
    assert first.new_advice is True

    t1 = datetime(2026, 1, 1, 0, 0, 2, tzinfo=UTC)
    second = ADVICE_SCHEDULER.evaluate(_death_review_request(), "DEATH_REVIEW", [], now=t1)
    assert second.new_advice is False
    assert second.status == "active_advice"
    assert second.suppressed_reason == "duplicate_death_review"
    assert ADVICE_SCHEDULER.state.duplicate_suppressed_count == 1
