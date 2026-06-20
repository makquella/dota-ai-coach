"""
laning_coach.py - context-specific lane advice for carry replay/GSI states.

This module combines already-available signals. It does not infer enemy
positions, exact team readiness, or cooldowns when those signals are missing.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


LANING_DECISION_POINTS = {
    "LANING_FARM_CHECK",
    "FARMING_PHASE_PRESSURE",
    "LOW_HP_WARNING",
    "LOW_HP",
}

REPEAT_WINDOW_SECONDS = 120


@dataclass(frozen=True)
class LaningAdvice:
    category: str
    action: str
    reason: str
    risk: str
    repeat_key: str
    farm_deficit: int | None
    pressure_state: str
    pressure_active: bool
    position_risk: str
    position_zone: str


def build_laning_advice(
    game_state: Mapping[str, Any] | Any,
    decision_point: str,
) -> LaningAdvice | None:
    state = _as_mapping(game_state)
    extra = _extra_context(state)
    minute = _to_int(state.get("minute"), 0)
    if minute > 10 and decision_point not in {"LOW_HP"}:
        return None

    hp_percent = _to_int(state.get("hp_percent"), 100)
    farm_quality = str(extra.get("farm_quality") or "").strip().lower()
    hp_pressure = str(extra.get("hp_pressure_state") or "").strip().lower()
    position_risk = str(extra.get("position_risk") or "").strip().lower()
    position_zone = str(extra.get("position_zone") or "").strip().lower()
    enemy_context_missing = _enemy_context_missing(extra)
    pressure_active = _pressure_active(state, extra, hp_pressure)
    farm_low = farm_quality in {"very_low", "low"}
    farm_deficit = _farm_deficit(extra)
    category = _category_for_state(
        decision_point=decision_point,
        minute=minute,
        hp_percent=hp_percent,
        farm_low=farm_low,
        pressure_active=pressure_active,
        hp_pressure=hp_pressure,
        position_risk=position_risk,
        position_zone=position_zone,
        enemy_context_missing=enemy_context_missing,
        farm_quality=farm_quality,
    )

    action, reason, risk = _copy_for_category(category, minute)
    repeat_key = f"{category}:{_deficit_bucket(farm_deficit)}:{hp_pressure or 'unknown'}:{position_risk or 'unknown'}"
    return LaningAdvice(
        category=category,
        action=action,
        reason=reason,
        risk=risk,
        repeat_key=repeat_key,
        farm_deficit=farm_deficit,
        pressure_state=hp_pressure or ("pressure" if pressure_active else "stable"),
        pressure_active=pressure_active,
        position_risk=position_risk or "unknown",
        position_zone=position_zone or "unknown",
    )


def laning_context_for_review(
    game_state: Mapping[str, Any] | Any,
    decision_point: str,
) -> dict[str, Any]:
    advice = build_laning_advice(game_state, decision_point)
    if advice is None:
        return {
            "laning_category": "",
            "laning_advice_reason": "",
            "laning_farm_deficit": "",
            "laning_pressure_state": "",
            "laning_repeat_key": "",
        }
    return {
        "laning_category": advice.category,
        "laning_advice_reason": advice.reason,
        "laning_farm_deficit": "" if advice.farm_deficit is None else advice.farm_deficit,
        "laning_pressure_state": advice.pressure_state,
        "laning_repeat_key": advice.repeat_key,
    }


def important_laning_context_changed(
    previous: dict[str, Any] | None,
    current: LaningAdvice,
) -> bool:
    if not previous:
        return True

    previous_pressure = str(previous.get("pressure_state") or "")
    if previous_pressure != current.pressure_state:
        return True

    previous_pressure_active = bool(previous.get("pressure_active"))
    if previous_pressure_active != current.pressure_active:
        return True

    previous_position_risk = str(previous.get("position_risk") or "")
    if previous_position_risk != "high" and current.position_risk == "high":
        return True

    previous_deficit = previous.get("farm_deficit")
    if isinstance(previous_deficit, int) and isinstance(current.farm_deficit, int):
        return current.farm_deficit - previous_deficit >= 5

    return False


def _category_for_state(
    *,
    decision_point: str,
    minute: int,
    hp_percent: int,
    farm_low: bool,
    pressure_active: bool,
    hp_pressure: str,
    position_risk: str,
    position_zone: str,
    enemy_context_missing: bool,
    farm_quality: str,
) -> str:
    if decision_point == "LOW_HP" or hp_percent < 35 or hp_pressure == "critical":
        return "critical_hp_reset"

    if position_zone == "river_or_mid" and enemy_context_missing:
        return "risky_position_with_unknown_enemies"

    missing_enemy_context = position_risk in {"high", "medium"}
    if missing_enemy_context and pressure_active and not farm_low:
        return "risky_position_with_unknown_enemies"

    if farm_low and pressure_active and (hp_pressure == "risky" or 50 <= hp_percent < 70):
        return "recovery_after_pressure"

    if farm_low and pressure_active and hp_percent >= 70:
        return "farm_deficit_under_pressure"

    if farm_low and not pressure_active:
        return "farm_deficit_no_pressure"

    if pressure_active and hp_percent >= 70:
        return "pressure_but_stable"

    if position_risk == "high":
        return "risky_position_with_unknown_enemies"

    if farm_quality in {"okay", "good"} and hp_pressure in {"healthy", "", "unknown"}:
        return "stable_farm_rhythm"

    return "pressure_but_stable" if pressure_active else "stable_farm_rhythm"


def _copy_for_category(category: str, minute: int) -> tuple[str, str, str]:
    if category == "farm_deficit_no_pressure":
        return (
            "Secure the next wave first and avoid trading unless it protects last hits.",
            (
                "Your carry farm pace is behind for this minute, but HP is stable, "
                "so the fastest recovery is clean last hitting."
            ),
            "Medium risk if you trade instead of recovering lane farm.",
        )
    if category == "farm_deficit_under_pressure":
        if minute >= 8:
            return (
                "Take safe creeps, then rotate to safer farm if pressure continues.",
                "You are still behind on farm, and staying in pressure can cost both HP and timing.",
                "High risk if you stay in a pressured lane without stabilizing.",
            )
        return (
            "Take only the safe creeps and avoid extending the trade.",
            (
                "You are behind on farm and under lane pressure; forcing a trade can "
                "cost both HP and last hits."
            ),
            "Medium risk if you trade while pressure is active.",
        )
    if category == "recovery_after_pressure":
        return (
            "Back up slightly, secure safe last hits, then reset your HP.",
            "Reduced HP plus lane pressure can turn one more trade into a death.",
            "High risk if you stay exposed and take another trade.",
        )
    if category == "critical_hp_reset":
        return (
            "Leave the wave now and reset HP before rejoining.",
            "At this HP, one more trade or spell can kill you.",
            "High risk of dying if you stay visible or keep fighting.",
        )
    if category == "risky_position_with_unknown_enemies":
        return (
            "Move closer to a safer lane area before contesting the next wave.",
            "Your position is exposed and enemy locations are not confirmed.",
            "Medium risk if you show in an exposed area without enemy location info.",
        )
    if category == "stable_farm_rhythm":
        return (
            "Keep your farm rhythm and avoid low-value trades.",
            "Your lane progress is stable, so do not break it by taking unnecessary damage.",
            "Low risk if you keep farming without taking avoidable damage.",
        )
    return (
        "Farm the safer part of the lane and avoid long trades.",
        "You are under pressure but still have enough HP to keep farming if you stay conservative.",
        "Medium risk if you take extended trades while pressure is active.",
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


def _enemy_context_missing(extra: Mapping[str, Any]) -> bool:
    missing = set(extra.get("missing_signals") or [])
    return "enemy_positions" in missing or "nearby_allies_enemies" in missing


def _farm_deficit(extra: Mapping[str, Any]) -> int | None:
    value = str(extra.get("lh_deficit_or_status") or "")
    digits = "".join(char for char in value if char.isdigit())
    if digits:
        return _to_int(digits, 0)
    return None


def _deficit_bucket(value: int | None) -> str:
    if value is None:
        return "unknown"
    if value < 5:
        return "0-4"
    if value < 10:
        return "5-9"
    if value < 15:
        return "10-14"
    return "15+"


def _as_mapping(value: Mapping[str, Any] | Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    if hasattr(value, "model_dump"):
        return value.model_dump()
    return {}


def _extra_context(state: Mapping[str, Any]) -> Mapping[str, Any]:
    extra = state.get("extra_context")
    return extra if isinstance(extra, Mapping) else {}


def _to_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
