"""
Characterization tests for the evaluate() laning gate (segment S8).

Added in Phase 4B Wave 2 BEFORE extracting S8. Coverage showed the laning-
suppress branch (suppress_laning) was not entered by existing tests. This drives
the reachable branch: a repeat laning advice within REPEAT_WINDOW (120s), after
the regular cooldown clears, with a distinct state hash (different game_state)
and the same laning category + action, is suppressed as duplicate_laning and
bumps repeated_laning / duplicate counters.

Sub-paths carried verbatim by the extract:
- ux_result['recommendation'] is None branch (cooldown via ux suppression):
  reachable in principle when apply_ux_policy returns None, but the reproducible
  path needs a specific stale duplicate; flagged, not fabricated.
- active-keep-visible sub-returns: same shape as S5/S6 (active TTL shorter than
  the regular cooldown), unreachable in practice.

Determinism: every step passes an explicit `now`; game_time in state advances
in lockstep with wall-clock so _elapsed_since computes correctly. USE_LLM false.
Different game_state per step so state_hash differs and the duplicate gate does
not fire.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.advice_scheduler import ADVICE_SCHEDULER
from app.schemas import GameSituationRequest


def _mk(game_state: str, game_time: int) -> GameSituationRequest:
    return GameSituationRequest(
        hero="Phantom Lancer",
        role="carry",
        minute=5,
        level=5,
        gold=500,
        items=["Power Treads"],
        hp_percent=55,
        game_state=game_state,
        team_status="unknown",
        extra_context={
            "source_type": "replay_gsi_like",
            "context_confidence": "high",
            "game_time": game_time,
            "timestamp_seconds": game_time,
            "alive": True,
            "mana_percent": 80,
            "last_hits": 20,
            "farm_quality": "low",
            "hp_pressure_state": "healthy",
            "position_zone": "lane_area",
            "position_risk": "low",
            "missing_signals": ["enemy_positions"],
        },
    )


def test_evaluate_repeat_laning_advice_within_repeat_window_is_suppressed() -> None:
    """A repeat laning advice (same category + action, within REPEAT_WINDOW=120s)
    is suppressed as duplicate_laning once the regular cooldown (45s) clears.
    game_state differs so state_hash differs and the duplicate gate does not fire;
    game_time advances with wall-clock so the cooldown actually elapses."""
    ADVICE_SCHEDULER.reset()
    t0 = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)
    first = ADVICE_SCHEDULER.evaluate(
        _mk(game_state="calm farming", game_time=300), "LANING_FARM_CHECK", [], now=t0
    )
    assert first.new_advice is True
    assert "farm_deficit_no_pressure" in ADVICE_SCHEDULER.state._last_laning_category

    # t+50s, game_time 300->350: regular cooldown (45s) cleared, REPEAT_WINDOW
    # (120s) still active, different game_state (different hash), same laning
    # category + action -> suppress_laning fires.
    t50 = t0 + timedelta(seconds=50)
    second = ADVICE_SCHEDULER.evaluate(
        _mk(game_state="passive lane", game_time=350), "LANING_FARM_CHECK", [], now=t50
    )
    assert second.new_advice is False
    assert second.status == "cooldown"
    assert second.suppressed_reason == "duplicate_laning"
    assert ADVICE_SCHEDULER.state.repeated_laning_suppressed_count == 1
    assert ADVICE_SCHEDULER.state.duplicate_suppressed_count == 1
