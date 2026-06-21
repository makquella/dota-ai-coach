"""
scheduler.safety_predicates - stateless safety/suppression predicates.

Pure functions, no scheduler state, no ``self``. Extracted verbatim from
advice_scheduler.py as part of the Phase 2 split (no behavior change).

Two safety helpers that reference DEATH_REVIEW_DECISIONS
(_is_safe_recommendation, _is_lower_value_post_laning_advice) are
intentionally LEFT in advice_scheduler.py until step 7 moves
DEATH_REVIEW_DECISIONS into scheduler.constants — moving them now would
create a circular import (safety_predicates -> advice_scheduler).
"""

from __future__ import annotations

from typing import Any

from app.scheduler.state_utils import (
    _ctx_int,
    _ctx_value,
    _is_dead_or_respawning,
    _to_int,
)


def _suggests_fighting_without_safety(text: str) -> bool:
    fight_terms = ("fight", "engage", "commit", "contest", "join", "attack", "initiate")
    safety_terms = ("avoid", "retreat", "reset", "farm", "safe", "wait", "back", "skip", "only if")
    suggests_fight = any(term in text for term in fight_terms)
    has_safety = any(term in text for term in safety_terms)
    return suggests_fight and not has_safety


def _strong_laning_interrupt(previous: dict[str, Any], current: Any) -> bool:
    previous_pressure = str(previous.get("pressure_state") or "")
    if previous_pressure != current.pressure_state:
        return True

    previous_pressure_active = bool(previous.get("pressure_active"))
    if previous_pressure_active != current.pressure_active:
        return True

    previous_position_risk = str(previous.get("position_risk") or "")
    return previous_position_risk != "high" and current.position_risk == "high"


def _strong_post_laning_interrupt(previous: dict[str, Any], current: Any) -> bool:
    if current.category == "post_laning_low_hp_reset" or current.death_context:
        return True

    previous_position_risk = str(previous.get("position_risk") or "")
    if previous_position_risk != "high" and current.position_risk == "high":
        return True

    return current.hp_pressure_state == "critical"


def _post_laning_item_timing_is_unsafe(state: dict[str, Any]) -> bool:
    if _to_int(state.get("minute"), 0) < 10:
        return False
    hp_percent = _ctx_int(state, "hp_percent", _to_int(state.get("hp_percent"), 100))
    return hp_percent < 35 or _hp_pressure_state(state) == "critical"


def _post_laning_new_death_or_severe_pressure(state: dict[str, Any]) -> bool:
    if _is_dead_or_respawning(state):
        return True
    if _ctx_value(state, "death_count_changed", False):
        return True
    if _ctx_value(state, "selected_player_death_nearby", False):
        return True
    if _ctx_value(state, "near_player_death", False):
        return True
    event_context = str(
        state.get("event_context") or _ctx_value(state, "event_context", "") or ""
    ).lower()
    return "death" in event_context


def _objective_context_changed_clearly(state: dict[str, Any]) -> bool:
    objective_context = str(_ctx_value(state, "objective_context", "") or "").strip().lower()
    objective_for_selected = _ctx_value(state, "objective_for_selected_team", None)
    team_status = (
        str(_ctx_value(state, "team_status", state.get("team_status", "")) or "").strip().lower()
    )
    selected_objective = (
        objective_for_selected is True or str(objective_for_selected).lower() == "true"
    )
    friendly_objective = objective_context == "friendly_objective"
    return (selected_objective or friendly_objective) and team_status in {"advantage", "even"}


def _hp_pressure_state(state: dict[str, Any]) -> str:
    return str(_ctx_value(state, "hp_pressure_state", "") or "").strip().lower()


def _death_event_id(state: dict[str, Any]) -> str | None:
    value = _ctx_value(state, "last_death_event_id", None)
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _post_laning_int(state: dict[str, Any]) -> int:
    return 1 if _to_int(state.get("minute"), 0) >= 10 else 0


def _low_hp_severe_signature(state: dict[str, Any]) -> str | None:
    extra_context = (
        state.get("extra_context") if isinstance(state.get("extra_context"), dict) else {}
    )
    keys = (
        "death_count_changed",
        "near_player_death",
        "selected_player_death_nearby",
        "recent_damage_taken",
        "overstay_warning",
    )
    active = [key for key in keys if _ctx_value(state, key, False)]
    event_context = str(state.get("event_context") or extra_context.get("event_context") or "")
    if "death" in event_context.lower():
        active.append("death_context")
    if not active:
        return None
    minute = _to_int(state.get("minute"), 0)
    return f"{minute}:{'+'.join(sorted(set(active)))}"


def _post_laning_safety_suppression_exception(
    state: dict[str, Any],
    decision_point: str,
    post_laning_advice: Any,
) -> bool:
    if _post_laning_new_death_or_severe_pressure(state):
        return True
    if post_laning_advice.position_risk == "high":
        return True
    if decision_point == "OBJECTIVE_FIGHT_CHECK" and _objective_context_changed_clearly(state):
        return True
    return False


# NOTE: _is_safe_recommendation and _is_lower_value_post_laning_advice remain in
# advice_scheduler.py because they reference DEATH_REVIEW_DECISIONS. They will
# move here once DEATH_REVIEW_DECISIONS relocates to scheduler.constants (step 7).

__all__ = [
    "_suggests_fighting_without_safety",
    "_strong_laning_interrupt",
    "_strong_post_laning_interrupt",
    "_post_laning_item_timing_is_unsafe",
    "_post_laning_new_death_or_severe_pressure",
    "_objective_context_changed_clearly",
    "_hp_pressure_state",
    "_death_event_id",
    "_post_laning_int",
    "_low_hp_severe_signature",
    "_post_laning_safety_suppression_exception",
]
