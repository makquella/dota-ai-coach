"""
Characterization tests for the evaluate() game-time spacing gate (segment S10).

Added in Phase 4B Wave 2 BEFORE extracting S10. Branch coverage showed the
``spacing_remaining > 0`` early-return (and both of its sub-returns) was never
entered by the existing suite. The pre-existing demo test
``test_game_time_spacing_blocks_normal_coaching_every_few_seconds`` asserts a
weak ``... or status in {active_advice, cooldown}`` disjunction and is in
practice satisfied by the duplicate/cooldown gates, never reaching spacing.

Reaching spacing requires the EARLIER cooldown gate to be bypassed: the regular
advice cooldown is measured in game-time, so a small game-time gap is normally
caught there first. The cooldown gate returns 0 for the warning decision points
({LOW_HP, DISABLED_STATUS, RECENT_DAMAGE_WARNING, OVERSTAY_WARNING, *DEATH_REVIEW})
when ``last_advice_type`` differs. So: a SAFE_FARMING advice followed by a
RECENT_DAMAGE_WARNING (a different type) skips cooldown, passes the duplicate /
laning / post-laning gates (distinct state hash + distinct post-laning category),
and is then suppressed purely by game-time spacing (coaching min-gap 45s).

Two sub-paths of the early-return are pinned:
- active card still visible (small wall gap) -> returns the active advice with
  suppressed_by_game_time_spacing=True and the game-time gap stamped on it;
- active card expired -> returns the cooldown _result_locked with
  suppressed_reason="game_time_spacing".

Determinism: explicit ``now`` per step; game_time advances with wall-clock.
USE_LLM false.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.advice_scheduler import AdviceScheduler
from app.schemas import GameSituationRequest


def _farm_req(game_time: int) -> GameSituationRequest:
    """Post-laning SAFE_FARMING state with low farm -> post_laning_farm_recovery."""
    return GameSituationRequest(
        hero="Phantom Lancer",
        role="carry",
        minute=20,
        level=15,
        gold=3000,
        items=["Power Treads", "Manta Style"],
        hp_percent=85,
        game_state="calm farming",
        team_status="unknown",
        extra_context={
            "source_type": "replay_gsi_like",
            "context_confidence": "high",
            "game_time": game_time,
            "timestamp_seconds": game_time,
            "alive": True,
            "mana_percent": 80,
            "last_hits": 150,
            "farm_quality": "low",
            "hp_pressure_state": "healthy",
            "position_zone": "lane_area",
            "position_risk": "low",
            "missing_signals": [],
        },
    )


def _damage_req(game_time: int) -> GameSituationRequest:
    """RECENT_DAMAGE_WARNING state (a different advice type -> cooldown bypass),
    post-laning, risky -> post_laning_risky_showing (distinct category)."""
    return GameSituationRequest(
        hero="Phantom Lancer",
        role="carry",
        minute=20,
        level=15,
        gold=3000,
        items=["Power Treads", "Manta Style"],
        hp_percent=55,
        game_state="took damage",
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
            "hp_pressure_state": "risky",
            "position_zone": "enemy_jungle",
            "position_risk": "high",
            "recent_damage": True,
            "missing_signals": [],
        },
    )


def test_spacing_suppresses_with_active_card_visible() -> None:
    """A second advice within the spacing min-gap, while the first advice card is
    still visible (small wall gap), returns the ACTIVE advice annotated with
    suppressed_by_game_time_spacing and the game-time gap, and bumps the spacing
    and duplicate counters."""
    scheduler = AdviceScheduler(enable_llm=False)
    t0 = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)

    first = scheduler.evaluate(_farm_req(1200), "SAFE_FARMING", [], now=t0)
    assert first.new_advice is True

    # +5s: game-time gap 5 < 45 (coaching min-gap); cooldown bypassed because the
    # second decision point (RECENT_DAMAGE_WARNING) differs from SAFE_FARMING.
    t1 = t0 + timedelta(seconds=5)
    second = scheduler.evaluate(_damage_req(1205), "RECENT_DAMAGE_WARNING", [], now=t1)
    assert second.new_advice is not True
    assert second.status == "active_advice"
    assert second.suppressed_by_game_time_spacing is True
    assert second.game_time_gap_since_previous_advice == 5.0
    assert scheduler.state.suppressed_by_game_time_spacing_count == 1
    assert scheduler.state.duplicate_suppressed_count == 1


def test_spacing_suppresses_as_cooldown_when_no_active_card() -> None:
    """A second advice within the spacing min-gap, after the first card's active
    visibility has lapsed (larger wall gap), returns a cooldown status with
    suppressed_reason 'game_time_spacing', and bumps the spacing and duplicate
    counters."""
    scheduler = AdviceScheduler(enable_llm=False)
    t0 = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)

    first = scheduler.evaluate(_farm_req(1200), "SAFE_FARMING", [], now=t0)
    assert first.new_advice is True

    # +10s: game-time gap 10 < 45 (still inside spacing), but the active card has
    # expired so the cooldown _result_locked branch is taken.
    t1 = t0 + timedelta(seconds=10)
    second = scheduler.evaluate(_damage_req(1210), "RECENT_DAMAGE_WARNING", [], now=t1)
    assert second.new_advice is False
    assert second.status == "cooldown"
    assert second.suppressed_reason == "game_time_spacing"
    assert second.suppressed_by_game_time_spacing is True
    assert second.game_time_gap_since_previous_advice == 10.0
    assert scheduler.state.suppressed_by_game_time_spacing_count == 1
    assert scheduler.state.duplicate_suppressed_count == 1
