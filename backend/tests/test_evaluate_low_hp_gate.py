"""
Characterization tests for the evaluate() LOW_HP episode gate (segment S6).

Added in Phase 4B Wave 2 BEFORE extracting S6. Coverage showed none of S6's
three internal branches (suppress / show-suppress / pattern) were entered by
existing tests. These tests drive the two reachable branches:

- suppress: a repeat LOW_HP within an active episode (no significant drop, no
  new severe event) is suppressed as duplicate_low_hp_episode and bumps
  repeated_low_hp/post_laning_safety/duplicate counters.
- pattern: the third LOW_HP in an episode (repeat_count >= 2, pattern not yet
  shown) emits the low_hp_pattern fallback advice, bumps advice_count/
  fallback_count/low_hp_pattern_advice_count, and records the pattern timestamp.

Note on the show-suppress sub-branch (low_hp_action == "show" AND
_should_suppress_post_laning_low_hp_locked): empirically hard to reach - it
needs a significant HP drop that simultaneously keeps the recent-safety
suppression active, but the action predicate tends to return "suppress" on
such repeats, and a new-severe event flips the suppression off. Flagged as
possibly-dead/hard-to-reach; the extract carries it verbatim. This is the
segment that triggers the Wave-2 S6-pattern STOP (the heaviest branch:
state mutation + history append + ScheduledAdvice construction).

Determinism: every step passes an explicit `now`; USE_LLM stays false.
Different hp values are used per step so state_hash differs (hp is bucketed
by hp_percent // 10 in build_state_hash) and the duplicate gate does not fire.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.advice_scheduler import ADVICE_SCHEDULER
from app.schemas import GameSituationRequest


def _mk(hp: int, game_time: int) -> GameSituationRequest:
    return GameSituationRequest(
        hero="Phantom Lancer",
        role="carry",
        minute=15,
        level=15,
        gold=2000,
        items=["Power Treads", "Manta Style"],
        hp_percent=hp,
        game_state="pressure",
        team_status="unknown",
        extra_context={
            "source_type": "replay_gsi_like",
            "context_confidence": "high",
            "game_time": game_time,
            "timestamp_seconds": game_time,
            "alive": True,
            "mana_percent": 80,
            "last_hits": 120,
            "farm_quality": "low",
            "hp_pressure_state": "critical",
            "position_zone": "lane_area",
            "position_risk": "medium",
            "missing_signals": ["enemy_positions"],
        },
    )


def test_evaluate_low_hp_repeat_in_episode_is_suppressed() -> None:
    """A repeat LOW_HP within an active episode (no significant drop) hits the
    suppress branch: status cooldown, duplicate_low_hp_episode reason, and the
    repeated_low_hp / post_laning_safety / duplicate counters all bump."""
    ADVICE_SCHEDULER.reset()
    t0 = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)
    first = ADVICE_SCHEDULER.evaluate(_mk(hp=28, game_time=900), "LOW_HP", [], now=t0)
    assert first.new_advice is True
    assert ADVICE_SCHEDULER.state._low_hp_episode_active is True

    # Different hp bucket (45 -> bucket 4) so state_hash differs and duplicate
    # gate does not fire; hp 45 <= 60 so episode stays active; 45 > 28-15 so no
    # significant drop -> "suppress" action.
    t1 = t0 + timedelta(seconds=20)
    second = ADVICE_SCHEDULER.evaluate(_mk(hp=45, game_time=920), "LOW_HP", [], now=t1)
    assert second.new_advice is False
    assert second.status == "cooldown"
    assert second.suppressed_reason == "duplicate_low_hp_episode"
    assert ADVICE_SCHEDULER.state.repeated_low_hp_suppressed_count == 1
    assert ADVICE_SCHEDULER.state.post_laning_safety_suppressed_count == 1
    assert ADVICE_SCHEDULER.state.duplicate_suppressed_count == 1


def test_evaluate_low_hp_third_repeat_emits_pattern_advice() -> None:
    """The third LOW_HP in an episode (repeat_count >= 2, pattern not yet shown)
    emits the low_hp_pattern fallback advice: new advice, coaching mode,
    low_hp_pattern_advice_count bumps, _low_hp_episode_pattern_shown flips."""
    ADVICE_SCHEDULER.reset()
    t0 = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)
    ADVICE_SCHEDULER.evaluate(_mk(hp=28, game_time=900), "LOW_HP", [], now=t0)
    # second LOW_HP: suppress (hp bucket 4, no drop)
    t1 = t0 + timedelta(seconds=20)
    ADVICE_SCHEDULER.evaluate(_mk(hp=45, game_time=920), "LOW_HP", [], now=t1)
    assert ADVICE_SCHEDULER.state._low_hp_episode_repeat_count == 1

    # third LOW_HP: repeat_count -> 2, pattern not yet shown -> "pattern" action
    t2 = t0 + timedelta(seconds=40)
    third = ADVICE_SCHEDULER.evaluate(_mk(hp=52, game_time=940), "LOW_HP", [], now=t2)
    assert third.new_advice is True
    assert third.status == "advice"
    assert third.advice_mode == "coaching"
    assert ADVICE_SCHEDULER.state.low_hp_pattern_advice_count == 1
    assert ADVICE_SCHEDULER.state._low_hp_episode_pattern_shown is True
    # pattern advice counts as a shown advice
    assert ADVICE_SCHEDULER.state.advice_count == 2
    assert ADVICE_SCHEDULER.state.fallback_count == 2
    # pattern timestamp recorded (drives the S5 recent-pattern OR-trigger)
    assert ADVICE_SCHEDULER.state._low_hp_pattern_last_at == t2
