"""
Characterization tests for the evaluate() post-laning suppression gate (segment S9).

Added in Phase 4B Wave 2 BEFORE extracting S9. The post-laning gate maps a
``post_laning_reason`` to a specific suppression counter in the ``heartbeat is
None`` else-block of ``evaluate``. Branch coverage showed two reason->counter
sub-branches were never entered by the existing suite:

- ``objective_after_recent_safety`` -> objective_suppressed_by_recent_safety_count
  AND repeated_objective_suppressed_count (both bumped);
- ``death_route_duplicate`` -> death_route_suppressed_count.

The remaining reason branches already had coverage and are pinned elsewhere:
- ``duplicate_objective`` / ``objective_context_missing`` -> repeated_objective_suppressed_count
- ``item_timing_after_recent_safety`` -> item_timing_suppressed_by_safety_count
- ``recent_safety`` -> post_laning_safety_suppressed_count + repeated_post_laning_suppressed_count
- else (any other reason, e.g. duplicate_post_laning) -> repeated_post_laning_suppressed_count

This file drives the two previously-uncovered reachable branches so the S9
extract (moving the gate into _evaluate_post_laning_locked via _SegmentResult)
is byte-for-byte protected, including the fallback rebind on the heartbeat path.

Determinism: every step passes an explicit ``now``; game_time advances in
lockstep with wall-clock so _elapsed_since_time computes correctly. USE_LLM false.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.advice_scheduler import ADVICE_SCHEDULER
from app.schemas import GameSituationRequest


def _death_req(game_time: int) -> GameSituationRequest:
    """Post-laning state with a fresh death (alive=False, respawn>0,
    death_count_changed) -> build_post_laning_advice selects
    post_laning_death_route_reset. Under DEATH_REVIEW it is shown (not a
    spurious duplicate) and records a recent post-laning safety marker."""
    return GameSituationRequest(
        hero="Juggernaut",
        role="carry",
        minute=15,
        level=12,
        gold=2000,
        items=["Power Treads"],
        hp_percent=40,
        game_state="just died",
        team_status="unknown",
        extra_context={
            "source_type": "replay_gsi_like",
            "context_confidence": "high",
            "game_time": game_time,
            "timestamp_seconds": game_time,
            "alive": False,
            "respawn_seconds": 20,
            "death_count_changed": True,
            "mana_percent": 50,
            "last_hits": 100,
            "farm_quality": "good",
            "hp_pressure_state": "healthy",
            "position_zone": "base",
            "position_risk": "low",
            "missing_signals": [],
        },
    )


def _objective_req(game_time: int) -> GameSituationRequest:
    """Alive post-laning state under OBJECTIVE_FIGHT_CHECK with full objective
    context (no missing_signals) -> post_laning_objective_caution category."""
    return GameSituationRequest(
        hero="Juggernaut",
        role="carry",
        minute=16,
        level=12,
        gold=2200,
        items=["Power Treads"],
        hp_percent=85,
        game_state="grouping mid",
        team_status="unknown",
        extra_context={
            "source_type": "replay_gsi_like",
            "context_confidence": "high",
            "game_time": game_time,
            "timestamp_seconds": game_time,
            "alive": True,
            "respawn_seconds": 0,
            "mana_percent": 80,
            "last_hits": 110,
            "farm_quality": "good",
            "hp_pressure_state": "healthy",
            "position_zone": "mid_area",
            "position_risk": "low",
            "missing_signals": [],
        },
    )


def _death_route_req(game_time: int) -> GameSituationRequest:
    """Alive post-laning state carrying death_count_changed -> death_context True
    -> post_laning_death_route_reset category, but under a NON death-review
    decision point with the hero alive. That is the spurious-death-route case:
    _should_suppress_post_laning_locked returns ``death_route_duplicate`` even on
    the first showing."""
    return GameSituationRequest(
        hero="Juggernaut",
        role="carry",
        minute=15,
        level=12,
        gold=2000,
        items=["Power Treads"],
        hp_percent=80,
        game_state="calm farming",
        team_status="unknown",
        extra_context={
            "source_type": "replay_gsi_like",
            "context_confidence": "high",
            "game_time": game_time,
            "timestamp_seconds": game_time,
            "alive": True,
            "respawn_seconds": 0,
            "death_count_changed": True,
            "mana_percent": 80,
            "last_hits": 100,
            "farm_quality": "good",
            "hp_pressure_state": "healthy",
            "position_zone": "lane_area",
            "position_risk": "low",
            "missing_signals": [],
        },
    )


def test_objective_after_recent_safety_bumps_both_objective_counters() -> None:
    """A post_laning_objective_caution advice issued within the recent-safety
    window (150s game-time) after a shown safety advice, with objective context
    unchanged, is suppressed as objective_after_recent_safety and bumps BOTH
    objective_suppressed_by_recent_safety_count and
    repeated_objective_suppressed_count."""
    ADVICE_SCHEDULER.reset()
    t0 = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)

    # Step 1: a death-review advice is shown and records a recent post-laning
    # safety marker (_last_post_laning_safety_at).
    first = ADVICE_SCHEDULER.evaluate(_death_req(900), "DEATH_REVIEW", [], now=t0)
    assert first.new_advice is True

    # Step 2 at t+50s (past the 45s regular cooldown, inside the 150s safety
    # window): objective caution is suppressed by the recent safety.
    t1 = t0 + timedelta(seconds=50)
    second = ADVICE_SCHEDULER.evaluate(_objective_req(950), "OBJECTIVE_FIGHT_CHECK", [], now=t1)
    assert second.new_advice is False
    assert second.status == "cooldown"
    assert second.suppressed_reason == "objective_after_recent_safety"
    assert ADVICE_SCHEDULER.state.objective_suppressed_by_recent_safety_count == 1
    assert ADVICE_SCHEDULER.state.repeated_objective_suppressed_count == 1
    assert ADVICE_SCHEDULER.state.duplicate_suppressed_count == 1


def test_spurious_death_route_is_suppressed_as_death_route_duplicate() -> None:
    """A post_laning_death_route_reset advice produced under a non death-review
    decision point while the hero is alive is suppressed as death_route_duplicate
    on its first occurrence and bumps death_route_suppressed_count."""
    ADVICE_SCHEDULER.reset()
    t0 = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)

    result = ADVICE_SCHEDULER.evaluate(_death_route_req(900), "SAFE_FARMING", [], now=t0)
    assert result.new_advice is False
    assert result.status == "cooldown"
    assert result.suppressed_reason == "death_route_duplicate"
    assert ADVICE_SCHEDULER.state.death_route_suppressed_count == 1
    assert ADVICE_SCHEDULER.state.duplicate_suppressed_count == 1
