"""
Characterization tests for the evaluate() LOW_HP_WARNING gate (segment S5).

Added in Phase 4B Wave 2 BEFORE extracting S5. Coverage showed S5 was not
entered by any existing test. This drives the reachable branch: after a LOW_HP
advice starts a low-HP episode, a subsequent LOW_HP_WARNING (with HP still low
enough to keep the episode active) is suppressed as duplicate_low_hp_episode.

Note on the active-keep-visible sub-branch of S5 (lines that call
_active_result_locked inside S5): empirically unreachable in a realistic
single-scheduler scenario, because LOW_HP_WARNING carries the regular cooldown
(45s) while the active advice TTL is ~12s - the S4 cooldown gate ahead of S5
always returns first while the active advice is still visible, and by the time
the cooldown clears (t>=45s) the active advice has long expired. We flag that
sub-branch as possibly-dead rather than fabricate a test; the extract will
carry it verbatim.

Determinism: every step passes an explicit `now`; USE_LLM stays false.
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


def test_evaluate_low_hp_warning_after_low_hp_episode_is_suppressed() -> None:
    """A LOW_HP advice starts a low-HP episode. After the LOW_HP_WARNING regular
    cooldown clears (t>=45s), with HP still <= 60 (episode still active), a
    LOW_HP_WARNING is suppressed as duplicate_low_hp_episode and counters bump.
    """
    ADVICE_SCHEDULER.reset()
    t0 = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)
    first = ADVICE_SCHEDULER.evaluate(_mk(hp=28, game_time=900), "LOW_HP", [], now=t0)
    assert first.new_advice is True
    assert ADVICE_SCHEDULER.state._low_hp_episode_active is True

    # LOW_HP_WARNING regular cooldown is 45s; at t+50s it has cleared, the active
    # advice has expired, and the episode is still active (HP 35 <= 60). S5 fires.
    t50 = t0 + timedelta(seconds=50)
    second = ADVICE_SCHEDULER.evaluate(_mk(hp=35, game_time=950), "LOW_HP_WARNING", [], now=t50)
    assert second.new_advice is False
    assert second.status == "cooldown"
    assert second.suppressed_reason == "duplicate_low_hp_episode"
    assert ADVICE_SCHEDULER.state.repeated_low_hp_suppressed_count == 1
    assert ADVICE_SCHEDULER.state.duplicate_suppressed_count == 1
    assert ADVICE_SCHEDULER.state._low_hp_episode_active is True
