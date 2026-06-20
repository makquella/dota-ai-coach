"""
post_laning_coach.py - conservative farming advice after the lane phase.

This helper only combines signals already present in GSI-like state. It does
not infer enemy positions, team readiness, Roshan state, or exact fight context.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


POST_LANING_REPEAT_WINDOW_SECONDS = 120
POST_LANING_SAME_ACTION_WINDOW_SECONDS = 330
POST_LANING_RECENT_SAFETY_WINDOW_SECONDS = 150
POST_LANING_DEATH_ROUTE_WINDOW_SECONDS = 180
OBJECTIVE_REPEAT_WINDOW_SECONDS = 180


@dataclass(frozen=True)
class PostLaningAdvice:
    category: str
    action: str
    reason: str
    risk: str
    repeat_key: str
    farm_quality: str
    hp_pressure_state: str
    pressure_active: bool
    position_risk: str
    position_zone: str
    objective_context_missing: bool
    clear_pressure_context: bool
    death_context: bool


def build_post_laning_advice(
    game_state: Mapping[str, Any] | Any,
    decision_point: str,
) -> PostLaningAdvice | None:
    state = _as_mapping(game_state)
    extra = _extra_context(state)
    minute = _to_int(state.get("minute"), 0)
    if minute < 10:
        return None

    hp_percent = _to_int(state.get("hp_percent"), 100)
    farm_quality = str(extra.get("farm_quality") or "").strip().lower()
    hp_pressure = str(extra.get("hp_pressure_state") or "").strip().lower()
    position_risk = str(extra.get("position_risk") or "").strip().lower()
    position_zone = str(extra.get("position_zone") or "").strip().lower()
    pressure_active = _pressure_active(state, extra, hp_pressure)
    death_context = _death_context(state, extra)
    objective_missing = objective_context_is_missing(extra)
    clear_context = _clear_pressure_context(state, extra)

    category = _category_for_state(
        decision_point=decision_point,
        hp_percent=hp_percent,
        farm_quality=farm_quality,
        hp_pressure=hp_pressure,
        pressure_active=pressure_active,
        position_risk=position_risk,
        position_zone=position_zone,
        death_context=death_context,
    )
    if category is None:
        return None

    action, reason, risk = _copy_for_category(category, objective_missing)
    repeat_key = ":".join(
        [
            category,
            farm_quality or "unknown",
            hp_pressure or "unknown",
            position_risk or "unknown",
            "pressure" if pressure_active else "stable",
        ]
    )
    return PostLaningAdvice(
        category=category,
        action=action,
        reason=reason,
        risk=risk,
        repeat_key=repeat_key,
        farm_quality=farm_quality or "unknown",
        hp_pressure_state=hp_pressure or ("pressure" if pressure_active else "healthy"),
        pressure_active=pressure_active,
        position_risk=position_risk or "unknown",
        position_zone=position_zone or "unknown",
        objective_context_missing=objective_missing,
        clear_pressure_context=clear_context,
        death_context=death_context,
    )


def post_laning_context_for_review(
    game_state: Mapping[str, Any] | Any,
    decision_point: str,
) -> dict[str, Any]:
    advice = build_post_laning_advice(game_state, decision_point)
    if advice is None:
        return {
            "post_laning_category": "",
            "post_laning_reason": "",
            "post_laning_repeat_key": "",
        }
    return {
        "post_laning_category": advice.category,
        "post_laning_reason": advice.reason,
        "post_laning_repeat_key": advice.repeat_key,
    }


def important_post_laning_context_changed(
    previous: dict[str, Any] | None,
    current: PostLaningAdvice,
) -> bool:
    if not previous:
        return True

    if current.category == "post_laning_low_hp_reset":
        return True
    if current.death_context:
        return True

    previous_pressure = str(previous.get("hp_pressure_state") or "")
    if previous_pressure != current.hp_pressure_state:
        return True

    previous_pressure_active = bool(previous.get("pressure_active"))
    if previous_pressure_active != current.pressure_active:
        return True

    previous_position_risk = str(previous.get("position_risk") or "")
    if previous_position_risk != "high" and current.position_risk == "high":
        return True

    return False


def objective_context_is_missing(extra: Mapping[str, Any]) -> bool:
    missing = set(extra.get("missing_signals") or [])
    return bool(
        {
            "nearby_allies_enemies",
            "enemy_positions",
            "exact_teamfight_context",
            "objective_context",
            "exact_roshan_context",
        }
        & missing
    )


def _category_for_state(
    *,
    decision_point: str,
    hp_percent: int,
    farm_quality: str,
    hp_pressure: str,
    pressure_active: bool,
    position_risk: str,
    position_zone: str,
    death_context: bool,
) -> str | None:
    if death_context or decision_point in {
        "DEATH_REVIEW",
        "DEATH_LOW_RESOURCE",
        "DEATH_WITH_ESCAPE_ON_COOLDOWN",
        "REPEATED_DEATH_PATTERN",
        "DEAD_WAIT",
    }:
        return "post_laning_death_route_reset"

    if decision_point == "LOW_HP" or hp_percent < 35 or hp_pressure == "critical":
        return "post_laning_low_hp_reset"

    if decision_point == "OBJECTIVE_FIGHT_CHECK":
        return "post_laning_objective_caution"

    if position_risk == "high" or position_zone == "deep_enemy_side":
        return "post_laning_risky_showing"

    farm_low = farm_quality in {"very_low", "low"}
    if farm_low and pressure_active:
        return "post_laning_pressure_avoidance"
    if farm_low:
        return "post_laning_farm_recovery"
    if pressure_active:
        return "post_laning_pressure_avoidance"
    if decision_point in {"SAFE_FARMING", "LANING_FARM_CHECK", "FARMING_PHASE_PRESSURE"}:
        return "post_laning_safe_farm_route"
    return None


def _copy_for_category(category: str, objective_missing: bool) -> tuple[str, str, str]:
    if category == "post_laning_low_hp_reset":
        return (
            "Reset HP before showing on another lane.",
            "At this HP, one more spell or rotation can turn into a death.",
            "High risk if you show again before resetting HP.",
        )
    if category == "post_laning_death_route_reset":
        return (
            "Use the respawn time to choose a safer farming route.",
            "Returning to the same pressured area can repeat the same death pattern.",
            "Medium risk if you respawn and run back into the same area.",
        )
    if category == "post_laning_farm_recovery":
        return (
            "Recover farm through the safest wave-and-camp route.",
            "You are behind on farm, so forcing fights before stabilizing can delay your next timing.",
            "Medium risk if you chase fights before rebuilding farm pace.",
        )
    if category == "post_laning_pressure_avoidance":
        return (
            "Avoid the pressured lane and farm a safer wave or nearby camp.",
            "Staying in pressure can cost HP and slow your recovery.",
            "High risk if you stay in pressure without confirmed support.",
        )
    if category == "post_laning_risky_showing":
        return (
            "Do not show deep until enemy positions are clearer.",
            "Your position is exposed and the replay does not confirm where enemies are.",
            "High risk if you show in a deep area with missing enemy context.",
        )
    if category == "post_laning_objective_caution":
        reason = (
            "Objective fights can be valuable, but the replay does not confirm team readiness."
            if objective_missing
            else "Objective fights can be valuable, but avoid forcing them without team support."
        )
        return (
            "Only consider the objective if your team is already grouped nearby.",
            reason,
            "Medium risk if the objective fight starts without confirmed support.",
        )
    return (
        "Keep farming the safest wave-and-camp route and reassess soon.",
        "Your farm pace is stable now, so keep using safe routes instead of forcing uncertain fights.",
        "Low risk if you keep farming without showing in exposed areas.",
    )


def _pressure_active(state: Mapping[str, Any], extra: Mapping[str, Any], hp_pressure: str) -> bool:
    if hp_pressure in {"pressured_but_stable", "risky", "critical"}:
        return True
    game_state = str(state.get("game_state") or "").strip().lower()
    if any(token in game_state for token in ("pressure", "fight", "risk", "damage")):
        return True
    return bool(
        extra.get("replay_damage_pressure_window")
        or extra.get("lane_pressure_from_damage_windows")
        or extra.get("recent_damage_taken")
    )


def _clear_pressure_context(state: Mapping[str, Any], extra: Mapping[str, Any]) -> bool:
    if _death_context(state, extra):
        return True
    if bool(state.get("near_teamfight") or extra.get("near_teamfight")):
        return True
    if bool(extra.get("replay_damage_pressure_window") or extra.get("recent_damage_taken")):
        return True
    game_state = str(state.get("game_state") or "").strip().lower()
    return any(token in game_state for token in ("pressure", "fight", "risk", "damage"))


def _death_context(state: Mapping[str, Any], extra: Mapping[str, Any]) -> bool:
    alive = extra.get("alive", state.get("alive", True))
    if alive is False or str(alive).strip().lower() in {"false", "0", "no"}:
        return True
    if _to_int(extra.get("respawn_seconds", state.get("respawn_seconds")), 0) > 0:
        return True
    return bool(
        state.get("near_player_death")
        or state.get("selected_player_death_nearby")
        or extra.get("near_player_death")
        or extra.get("selected_player_death_nearby")
        or extra.get("death_count_changed")
    )


def _extra_context(state: Mapping[str, Any]) -> Mapping[str, Any]:
    extra = state.get("extra_context")
    return extra if isinstance(extra, Mapping) else {}


def _as_mapping(value: Mapping[str, Any] | Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    if hasattr(value, "model_dump"):
        return value.model_dump()
    return {}


def _to_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
