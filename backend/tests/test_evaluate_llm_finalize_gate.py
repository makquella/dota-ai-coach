"""
Characterization tests for the evaluate() LLM-refinement + finalize tail (segment S12).

Added in Phase 4B Wave 2 BEFORE extracting S12. This tail runs AFTER the second
``with self._lock`` block: it conditionally kicks off async LLM refinement
(``if should_refine: self._start_llm_refinement(...)``) and then returns the
synchronous fallback-sourced ScheduledAdvice. Coverage showed the
``should_refine`` True branch (the _start_llm_refinement call) was never entered,
because the suite runs with LLM disabled.

These tests force should_refine True by constructing the scheduler with
``enable_llm=True`` (which bypasses USE_LLM / provider checks) and a decision
point in the always-refine set ({OBJECTIVE_FIGHT_CHECK, BAD_FIGHT_RISK,
ITEM_TIMING, HERO_SURVIVABILITY_RISK}). ``_start_llm_refinement`` is mocked so no
thread / network is started. They pin that:

(a) _start_llm_refinement is invoked exactly once with
    (tactical_hash, request, decision_point, rag_context); and
(b) the synchronous return is the rule-based fallback advice, byte-identical to
    the same scenario with LLM disabled — i.e. refinement is fire-and-forget and
    does NOT override decision_point / recommendation / source (per the project's
    main principle: the LLM never overrides the rule-based result).

USE_LLM false at the suite level; enable_llm is set per-instance.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import patch

from app.advice_scheduler import AdviceScheduler
from app.schemas import GameSituationRequest


def _objective_req(game_time: int) -> GameSituationRequest:
    """Post-laning OBJECTIVE_FIGHT_CHECK with full objective context (no missing
    signals) and no recent safety -> a fresh objective advice is shown (new)."""
    return GameSituationRequest(
        hero="Phantom Lancer",
        role="carry",
        minute=18,
        level=15,
        gold=4000,
        items=["Power Treads", "Manta Style"],
        hp_percent=85,
        game_state="grouping",
        team_status="unknown",
        extra_context={
            "source_type": "replay_gsi_like",
            "context_confidence": "high",
            "game_time": game_time,
            "timestamp_seconds": game_time,
            "alive": True,
            "mana_percent": 80,
            "last_hits": 150,
            "farm_quality": "good",
            "hp_pressure_state": "healthy",
            "position_zone": "mid_area",
            "position_risk": "low",
            "missing_signals": [],
        },
    )


def test_should_refine_starts_llm_refinement_once_with_expected_args() -> None:
    """With enable_llm=True and OBJECTIVE_FIGHT_CHECK, a new advice triggers
    should_refine, calling _start_llm_refinement exactly once with the tactical
    hash (the one registered as pending), the request, the decision point, and
    the rag_context."""
    scheduler = AdviceScheduler(enable_llm=True)
    t0 = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)
    request = _objective_req(1080)
    rag_context = ["objective context note"]

    with patch.object(scheduler, "_start_llm_refinement") as mock_refine:
        result = scheduler.evaluate(request, "OBJECTIVE_FIGHT_CHECK", rag_context, now=t0)

    assert mock_refine.call_count == 1
    called_args = mock_refine.call_args.args
    tactical_hash, called_request, called_dp, called_rag = called_args
    # The tactical hash passed to refinement is exactly the one registered as
    # pending by _should_start_llm_locked.
    assert tactical_hash in scheduler.state._pending_llm_tactical_hashes
    assert called_request is request
    assert called_dp == "OBJECTIVE_FIGHT_CHECK"
    assert called_rag is rag_context

    # The synchronous return is the rule-based advice (not yet refined).
    assert result.status == "advice"
    assert result.new_advice is True
    assert result.llm_used is False
    assert result.source == "fallback"
    assert result.recommendation is not None


def test_refinement_does_not_change_the_returned_advice() -> None:
    """The async refinement is fire-and-forget: the synchronously returned
    ScheduledAdvice is byte-identical to the same scenario with LLM disabled
    (same decision_point, recommendation, source, advice_mode)."""
    t0 = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)

    refined = AdviceScheduler(enable_llm=True)
    with patch.object(refined, "_start_llm_refinement") as mock_refine:
        with_llm = refined.evaluate(_objective_req(1080), "OBJECTIVE_FIGHT_CHECK", ["c"], now=t0)
    assert mock_refine.call_count == 1

    plain = AdviceScheduler(enable_llm=False)
    without_llm = plain.evaluate(_objective_req(1080), "OBJECTIVE_FIGHT_CHECK", ["c"], now=t0)

    assert with_llm.decision_point == without_llm.decision_point
    assert with_llm.source == without_llm.source == "fallback"
    assert with_llm.llm_used is without_llm.llm_used is False
    assert with_llm.advice_mode == without_llm.advice_mode
    assert with_llm.recommendation == without_llm.recommendation
