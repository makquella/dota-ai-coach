"""
Characterization tests for laning_coach and post_laning_coach.

These coaches produce category-specific advice text for the laning phase
(minute <= 10) and post-laning phase (minute >= 10). The tests pin the CURRENT
category-selection logic and minute-gating so refactors cannot silently
reshuffle which advice a given lane/post-lane state produces.

Behavior is asserted AS-IS.
"""

from __future__ import annotations

from typing import Any

from app.laning_coach import build_laning_advice
from app.post_laning_coach import build_post_laning_advice

# --- state builders -------------------------------------------------------


def _lane_state(minute: int = 5, hp: int = 80, **extra: Any) -> dict[str, Any]:
    base_extra: dict[str, Any] = {
        "farm_quality": "good",
        "last_hits": 30,
        "hp_pressure_state": "healthy",
        "position_zone": "lane_area",
        "position_risk": "low",
        "missing_signals": [],
    }
    base_extra.update(extra)
    return {
        "hero": "Juggernaut",
        "minute": minute,
        "hp_percent": hp,
        "game_state": "calm lane",
        "team_status": "unknown",
        "extra_context": base_extra,
    }


def _post_state(minute: int = 15, hp: int = 80, **extra: Any) -> dict[str, Any]:
    base_extra: dict[str, Any] = {
        "farm_quality": "good",
        "last_hits": 100,
        "hp_pressure_state": "healthy",
        "position_zone": "lane_area",
        "position_risk": "low",
        "missing_signals": [],
    }
    base_extra.update(extra)
    return {
        "hero": "Juggernaut",
        "minute": minute,
        "hp_percent": hp,
        "game_state": "calm farming",
        "team_status": "unknown",
        "extra_context": base_extra,
    }


# --- laning coach: minute gating ------------------------------------------


def test_laning_coach_returns_none_after_minute_10_for_non_low_hp() -> None:
    # Laning coach is scoped to minutes 0-10; only LOW_HP survives past that.
    assert build_laning_advice(_lane_state(minute=15), "LANING_FARM_CHECK") is None
    assert build_laning_advice(_lane_state(minute=15), "FARMING_PHASE_PRESSURE") is None


def test_laning_coach_low_hp_survives_past_minute_10() -> None:
    # LOW_HP is the exception: it is still coached after the laning window.
    advice = build_laning_advice(_lane_state(minute=15, hp=20), "LOW_HP")
    assert advice is not None
    assert advice.category == "critical_hp_reset"


# --- laning coach: category branches --------------------------------------


def test_laning_critical_hp_reset() -> None:
    advice = build_laning_advice(
        _lane_state(hp=25, hp_pressure_state="critical"), "LANING_FARM_CHECK"
    )
    assert advice is not None
    assert advice.category == "critical_hp_reset"
    assert advice.pressure_active is True


def test_laning_farm_deficit_no_pressure() -> None:
    advice = build_laning_advice(_lane_state(farm_quality="low"), "LANING_FARM_CHECK")
    assert advice is not None
    assert advice.category == "farm_deficit_no_pressure"
    assert advice.pressure_active is False


def test_laning_farm_deficit_under_pressure() -> None:
    advice = build_laning_advice(
        _lane_state(hp=80, farm_quality="low", hp_pressure_state="pressured_but_stable"),
        "LANING_FARM_CHECK",
    )
    assert advice is not None
    assert advice.category == "farm_deficit_under_pressure"
    assert advice.pressure_active is True


def test_laning_recovery_after_pressure() -> None:
    # farm_low + pressure + 50 <= hp < 70 -> recovery_after_pressure.
    advice = build_laning_advice(
        _lane_state(hp=55, farm_quality="low", hp_pressure_state="risky"),
        "LANING_FARM_CHECK",
    )
    assert advice is not None
    assert advice.category == "recovery_after_pressure"


def test_laning_risky_position_with_unknown_enemies() -> None:
    # position_risk high + pressure + missing enemy context -> risky position.
    advice = build_laning_advice(
        _lane_state(position_risk="high", recent_damage_taken=True),
        "LANING_FARM_CHECK",
    )
    assert advice is not None
    assert advice.category == "risky_position_with_unknown_enemies"


def test_laning_stable_farm_rhythm() -> None:
    advice = build_laning_advice(
        _lane_state(farm_quality="good", hp_pressure_state="healthy"),
        "LANING_FARM_CHECK",
    )
    assert advice is not None
    assert advice.category == "stable_farm_rhythm"


def test_laning_advice_always_has_action_reason_risk() -> None:
    # Every returned advice must carry non-empty text fields.
    advice = build_laning_advice(_lane_state(farm_quality="low"), "LANING_FARM_CHECK")
    assert advice is not None
    assert advice.action.strip()
    assert advice.reason.strip()
    assert advice.risk.strip()


# --- post-laning coach: minute gating -------------------------------------


def test_post_laning_coach_returns_none_before_minute_10() -> None:
    assert build_post_laning_advice(_post_state(minute=5), "SAFE_FARMING") is None


# --- post-laning coach: category branches ---------------------------------


def test_post_laning_low_hp_reset() -> None:
    advice = build_post_laning_advice(
        _post_state(hp=25, hp_pressure_state="critical"),
        "SAFE_FARMING",
    )
    assert advice is not None
    assert advice.category == "post_laning_low_hp_reset"


def test_post_laning_death_route_reset() -> None:
    # Phase 3 fix: death_route_reset is selected by the factual death_context
    # (alive=False / respawn_seconds>0 / death_count_changed / near_player_death),
    # NOT by the decision_point. Here alive=False makes death_context=True, which
    # is what actually drives the category. See the regression tests below.
    advice = build_post_laning_advice(
        _post_state(alive=False, respawn_seconds=20),
        "DEATH_REVIEW",
    )
    assert advice is not None
    assert advice.category == "post_laning_death_route_reset"
    assert advice.death_context is True


def test_post_laning_death_route_reset_requires_death_context() -> None:
    # Phase 3 regression fix: a DEATH_REVIEW decision_point alone must NOT select
    # post_laning_death_route_reset when state carries no sign of death. Category
    # and the public death_context field must stay in sync. This is an intentional
    # behavior change, not a regression.
    advice = build_post_laning_advice(
        _post_state(alive=True, respawn_seconds=0),
        "DEATH_REVIEW",
    )
    if advice is not None:
        assert advice.category != "post_laning_death_route_reset"
        assert advice.death_context is False


def test_post_laning_death_route_reset_post_respawn_series() -> None:
    # Phase 3 guard: variant A must not over-dry. Post-respawn death series
    # (REPEATED_DEATH_PATTERN / DEATH_WITH_ESCAPE_ON_COOLDOWN can fire when
    # alive=True but death_count_changed=True) must still select the death-route
    # reset, because death_context becomes True via death_count_changed.
    advice = build_post_laning_advice(
        _post_state(alive=True, respawn_seconds=0, death_count_changed=True),
        "REPEATED_DEATH_PATTERN",
    )
    assert advice is not None
    assert advice.death_context is True
    assert advice.category == "post_laning_death_route_reset"


def test_post_laning_risky_showing() -> None:
    advice = build_post_laning_advice(
        _post_state(position_risk="high"),
        "SAFE_FARMING",
    )
    assert advice is not None
    assert advice.category == "post_laning_risky_showing"


def test_post_laning_farm_recovery() -> None:
    # farm_low, no pressure -> farm recovery.
    advice = build_post_laning_advice(
        _post_state(farm_quality="low", hp_pressure_state="healthy"),
        "SAFE_FARMING",
    )
    assert advice is not None
    assert advice.category == "post_laning_farm_recovery"


def test_post_laning_pressure_avoidance() -> None:
    # farm_low + pressure -> pressure avoidance.
    advice = build_post_laning_advice(
        _post_state(farm_quality="low", hp_pressure_state="risky"),
        "SAFE_FARMING",
    )
    assert advice is not None
    assert advice.category == "post_laning_pressure_avoidance"


def test_post_laning_objective_caution() -> None:
    advice = build_post_laning_advice(_post_state(), "OBJECTIVE_FIGHT_CHECK")
    assert advice is not None
    assert advice.category == "post_laning_objective_caution"


def test_post_laning_safe_farm_route() -> None:
    advice = build_post_laning_advice(
        _post_state(farm_quality="good", hp_pressure_state="healthy"),
        "SAFE_FARMING",
    )
    assert advice is not None
    assert advice.category == "post_laning_safe_farm_route"


def test_post_laning_advice_always_has_action_reason_risk() -> None:
    advice = build_post_laning_advice(_post_state(), "OBJECTIVE_FIGHT_CHECK")
    assert advice is not None
    assert advice.action.strip()
    assert advice.reason.strip()
    assert advice.risk.strip()


# --- objective context missing flag ---------------------------------------


def test_post_laning_objective_caution_reflects_missing_context() -> None:
    # When objective context is missing, the advice still produces a category
    # but the reason text should mention missing team readiness.
    advice = build_post_laning_advice(
        _post_state(missing_signals=["nearby_allies_enemies", "exact_teamfight_context"]),
        "OBJECTIVE_FIGHT_CHECK",
    )
    assert advice is not None
    assert advice.objective_context_missing is True


def test_a_lane_under_the_pace_gets_the_numbers_not_the_river():
    """Live GSI never shows the enemies and a lane crosses the river: the farm
    card said «move to a safer part of the lane» instead of the farm it fired for."""
    from app.advice_i18n import translate_uk

    state = _lane_state(
        minute=5,
        farm_quality="okay",
        last_hits=12,
        expected_lh_range=[18, 30],
        position_zone="river_or_mid",
        position_risk="medium",
        missing_signals=["enemy_positions"],
    )
    advice = build_laning_advice(state, "LANING_FARM_CHECK")
    assert advice is not None and advice.category == "farm_deficit_no_pressure"
    assert advice.action == "Recover farm: 12 last hits at minute 5, a good pace is 18+."
    assert translate_uk(advice.action) == (
        "Надолужуйте фарм: добивань до 5-ї хвилини — 12, добрий темп — 18+."
    )
    assert translate_uk(advice.reason).startswith("Здоров'я вистачає")
    # On the pace: the river card stays as it was.
    on_pace = {**state, "extra_context": {**state["extra_context"], "last_hits": 20}}
    advice = build_laning_advice(on_pace, "LANING_FARM_CHECK")
    assert advice is not None and advice.category == "risky_position_with_unknown_enemies"
