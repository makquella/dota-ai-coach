"""
Characterization tests for the core advice-selection path.

Goal: pin the CURRENT behavior of decision_points.detect_decision_point and
recommender.generate_recommendation so future refactors must not silently
change which decision_point / priority / action_type is emitted for a given
input state. These tests assert behavior AS-IS — if something looks wrong,
it is documented in the phase report, not "fixed" here.

Two layers are exercised:
  - detect_decision_point() called directly on hand-built normalized states
    (priority ordering, threshold boundaries, signal keyword detection);
  - generate_recommendation() for action_type / priority / time_window
    mapping per decision_point (the advice_policy table).
"""

from __future__ import annotations

from typing import Any

from app.advice_policy import build_advice_policy
from app.decision_points import detect_decision_point
from app.recommender import generate_recommendation
from app.schemas import GameSituationRequest

# --- helpers ---------------------------------------------------------------


def _state(**overrides: Any) -> dict[str, Any]:
    """A normalized-style state with safe defaults (alive, healthy, mid-game)."""
    base: dict[str, Any] = {
        "hero": "Juggernaut",
        "minute": 15,
        "hp_percent": 100,
        "alive": True,
        "game_state": "calm farming",
        "team_status": "unknown",
        "extra_context": {
            "mana_percent": 100,
            "alive": True,
            "farm_quality": "good",
            "last_hits": 200,
            "hp_pressure_state": "healthy",
            "position_zone": "lane_area",
            "position_risk": "low",
        },
    }
    _deep_update(base, overrides)
    return base


def _deep_update(target: dict[str, Any], overrides: dict[str, Any]) -> None:
    for key, value in overrides.items():
        if key == "extra_context" and isinstance(value, dict):
            merged = dict(target.get("extra_context") or {})
            merged.update(value)
            target["extra_context"] = merged
        else:
            target[key] = value


def _req(**overrides: Any) -> GameSituationRequest:
    """Build a GameSituationRequest mirroring _state() defaults plus required schema fields."""
    state = _state()
    # GameSituationRequest requires role/level/gold/items/game_state/team_status.
    req_fields: dict[str, Any] = {
        "role": "carry",
        "level": 15,
        "gold": 0,
        "items": ["Power Treads"],
        "hero": state["hero"],
        "minute": state["minute"],
        "hp_percent": state["hp_percent"],
        "game_state": state["game_state"],
        "team_status": state["team_status"],
        "extra_context": state["extra_context"],
    }
    _deep_update(req_fields, overrides)
    return GameSituationRequest(**req_fields)


# --- priority ordering: more urgent conditions win first --------------------


def test_empty_state_returns_no_advice() -> None:
    assert detect_decision_point(None) == "NO_ADVICE"
    assert detect_decision_point({}) == "NO_ADVICE"


def test_no_advice_keywords_short_circuit_before_hp() -> None:
    # "paused" / "disconnected" force NO_ADVICE even at critical HP.
    paused = _state(hp_percent=10, game_state="paused")
    assert detect_decision_point(paused) == "NO_ADVICE"

    disconnected = _state(hp_percent=10, game_state="disconnected")
    assert detect_decision_point(disconnected) == "NO_ADVICE"


def test_death_branch_takes_priority_over_low_hp() -> None:
    # Dead + no buyback context -> DEATH_REVIEW even though hp is also critical.
    dead = _state(hp_percent=0, alive=False, extra_context={"respawn_seconds": 30})
    assert detect_decision_point(dead) == "DEATH_REVIEW"


def test_low_hp_takes_priority_over_disabled_and_mana() -> None:
    # Critical HP + stunned + low mana -> LOW_HP wins (first non-death check).
    state = _state(
        hp_percent=20,
        extra_context={"stunned": True, "mana_percent": 5},
    )
    assert detect_decision_point(state) == "LOW_HP"


def test_disabled_status_beats_survivability_and_mana() -> None:
    state = _state(
        hp_percent=50,
        extra_context={"stunned": True, "mana_percent": 5},
    )
    assert detect_decision_point(state) == "DISABLED_STATUS"


def test_low_mana_alone_does_not_trigger_bad_fight_without_pressure() -> None:
    # low_mana ORed with death/score change needs fight_pressure to become BAD_FIGHT_RISK.
    state = _state(extra_context={"mana_percent": 10})
    assert detect_decision_point(state) == "LOW_MANA"


def test_low_mana_with_fight_pressure_becomes_bad_fight_risk() -> None:
    state = _state(
        extra_context={"mana_percent": 10},
        near_teamfight=True,
    )
    assert detect_decision_point(state) == "BAD_FIGHT_RISK"


# --- threshold boundaries (characterize exact cutoffs) ----------------------


def test_low_hp_boundary_inclusive_at_critical_threshold() -> None:
    # Default critical_hp_threshold = 35 (Juggernaut profile). HP == 35 -> LOW_HP.
    assert detect_decision_point(_state(hp_percent=35)) == "LOW_HP"


def test_low_hp_boundary_one_above_critical_falls_through() -> None:
    # HP == 36 is above critical; nothing else triggers -> falls to SAFE_FARMING.
    # NOTE: this characterizes the catch-all `minute >= 0` SAFE_FARMING branch.
    assert detect_decision_point(_state(hp_percent=36)) == "SAFE_FARMING"


def test_low_mana_boundary_inclusive_at_20_percent() -> None:
    # mana_percent == 20 satisfies `<= 20` -> LOW_MANA.
    assert detect_decision_point(_state(extra_context={"mana_percent": 20})) == "LOW_MANA"


def test_low_mana_boundary_one_above_20_is_not_low_mana() -> None:
    state = _state(extra_context={"mana_percent": 21})
    assert detect_decision_point(state) != "LOW_MANA"


# --- signal keyword detection via game_state text ---------------------------


def test_pressure_keyword_in_game_state_triggers_farming_phase_pressure_in_early_game() -> None:
    # minute < 18 + pressure keyword (without objective keyword) -> FARMING_PHASE_PRESSURE.
    state = _state(minute=14, hp_percent=80, game_state="enemy gank incoming")
    assert detect_decision_point(state) == "FARMING_PHASE_PRESSURE"


def test_objective_keyword_takes_priority_over_pressure_keyword() -> None:
    # Characterize: "tower" is an OBJECTIVE_FIGHT keyword and outranks pressure.
    # So "pressure on tower" yields OBJECTIVE_FIGHT_CHECK, not FARMING_PHASE_PRESSURE.
    state = _state(minute=14, hp_percent=80, game_state="enemy pressure on tower")
    assert detect_decision_point(state) == "OBJECTIVE_FIGHT_CHECK"


def test_fight_keyword_without_objective_is_bad_fight_risk() -> None:
    state = _state(minute=20, hp_percent=80, game_state="enemy teamfight starting")
    assert detect_decision_point(state) == "BAD_FIGHT_RISK"


def test_safe_farming_keyword_falls_to_safe_farming_when_no_threat() -> None:
    state = _state(minute=20, hp_percent=80, game_state="calm farming in jungle")
    assert detect_decision_point(state) == "SAFE_FARMING"


# --- ability safety cooldown branch ----------------------------------------


def test_laning_with_key_safety_unavailable_and_low_hp_triggers_ability_cooldown() -> None:
    # Characterize via the real blade-fury-cooldown lane sample: when the hero's
    # key safety ability (Blade Fury) cannot be cast and HP is moderate, the
    # detector emits ABILITY_SAFETY_COOLDOWN. The abilities payload must use the
    # normalized shape ({can_cast: False, cooldown: n}) that gsi_state produces.
    state = _state(
        hero="Juggernaut",
        minute=8,
        hp_percent=55,
        extra_context={
            "abilities": [
                {
                    "name": "Blade Fury",
                    "raw_name": "juggernaut_blade_fury",
                    "level": 2,
                    "cooldown": 10,
                    "can_cast": False,
                },
            ],
        },
    )
    assert detect_decision_point(state) == "ABILITY_SAFETY_COOLDOWN"


# --- early-game fallback: SOFT_STATUS --------------------------------------


def test_laning_early_game_with_no_signal_is_soft_status() -> None:
    state = _state(minute=5, hp_percent=80, game_state="calm lane")
    assert detect_decision_point(state) == "SOFT_STATUS"


# --- buyback conservative gating -------------------------------------------


def test_dead_with_buyback_in_critical_late_game_context_is_buyback_available() -> None:
    # minute >= 35, respawn >= 35 -> BUYBACK_AVAILABLE (conservative gate).
    state = _state(
        minute=40,
        alive=False,
        extra_context={
            "respawn_seconds": 40,
            "buyback_available": True,
        },
        game_state="defending ancient",
    )
    assert detect_decision_point(state) == "BUYBACK_AVAILABLE"


# --- recommender: action_type / priority / time_window mapping --------------


def test_recommender_low_hp_maps_to_retreat_reset_high_immediate() -> None:
    req = _req(hp_percent=20)
    rec = generate_recommendation(req, rag_context=[])
    policy = build_advice_policy(req.model_dump(), "LOW_HP")

    assert rec.priority == "high"
    assert rec.time_window == "immediate: next 10-15 seconds"
    assert policy["action_type"] == "retreat_reset"
    assert rec.source == "fallback"


def test_recommender_farming_phase_pressure_maps_to_high_priority() -> None:
    req = _req(minute=14, hp_percent=70, game_state="enemy pressure")
    rec = generate_recommendation(req, rag_context=[])
    assert rec.priority == "high"
    assert rec.time_window == "next 60-90 seconds"


def test_recommender_low_mana_maps_to_medium_priority() -> None:
    req = _req(extra_context={"mana_percent": 15})
    rec = generate_recommendation(req, rag_context=[])
    assert rec.priority == "medium"
    assert rec.time_window == "next 60-90 seconds"


def test_recommender_emits_fallback_source_never_llm_when_disabled() -> None:
    # With USE_LLM=false (the test default), the recommender is the fallback
    # path and source must be "fallback", never "llm".
    req = _req(hp_percent=20)
    rec = generate_recommendation(req, rag_context=[])
    assert rec.source == "fallback"


def test_recommender_action_text_is_non_empty_for_actionable_points() -> None:
    for hp, expected_dp in [(20, "LOW_HP"), (70, None)]:
        req = _req(hp_percent=hp)
        rec = generate_recommendation(req, rag_context=[])
        if expected_dp == "LOW_HP":
            assert rec.action.strip()
            assert rec.reason.strip()
            assert rec.risk.strip()


def test_recommender_priority_never_exceeds_policy_priority() -> None:
    # The recommender must not invent a higher priority than the policy table.
    req = _req(hp_percent=20)
    rec = generate_recommendation(req, rag_context=[])
    policy = build_advice_policy(req.model_dump(), "LOW_HP")
    assert rec.priority == policy["priority"]
    assert rec.time_window == policy["time_window"]
