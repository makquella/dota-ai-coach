"""
advice_context.py - derived coaching context from available local signals.

This module does not infer enemy positions, nearby allies, or hidden intent. It
only summarizes signals already present in live GSI or GSI-like replay states.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


LH_RANGE_POINTS = (
    (3, 8, 15),
    (5, 18, 30),
    (10, 45, 60),
    (15, 75, 95),
    (20, 120, 150),
    (25, 170, 205),
    (30, 220, 260),
)
MAP_CENTER = 16384.0


def build_advice_context(state: Mapping[str, Any] | Any) -> dict[str, Any]:
    data = _as_mapping(state)
    extra = _extra_context(data)
    minute = _to_int(data.get("minute"), 0)
    hp_percent = _to_int(data.get("hp_percent"), 100)
    last_hits = _optional_int(extra.get("last_hits", data.get("last_hits")))
    game_state = str(data.get("game_state") or "").strip().lower()
    team = _selected_team(data, extra)

    context: dict[str, Any] = {}
    context.update(_farm_quality_context(minute, last_hits))
    context.update(_hp_pressure_context(hp_percent, game_state, extra))
    context.update(_position_context(extra.get("xpos"), extra.get("ypos"), team))
    return context


def enrich_state_with_advice_context(state: dict[str, Any]) -> dict[str, Any]:
    enriched = dict(state)
    extra = dict(enriched.get("extra_context") if isinstance(enriched.get("extra_context"), dict) else {})
    extra.update(build_advice_context(enriched))
    enriched["extra_context"] = extra
    return enriched


def _farm_quality_context(minute: int, last_hits: int | None) -> dict[str, Any]:
    expected = _expected_lh_range(minute)
    if expected is None or last_hits is None:
        return {
            "farm_quality": "unknown",
            "expected_lh_range": None,
            "lh_deficit_or_status": "last hits unavailable",
        }

    low, high = expected
    if last_hits < max(1, round(low * 0.65)):
        quality = "very_low"
        status = f"behind by about {max(0, low - last_hits)}+ last hits"
    elif last_hits < low:
        quality = "low"
        status = f"behind by about {low - last_hits} last hits"
    elif last_hits <= high:
        quality = "okay"
        status = "within expected range"
    else:
        quality = "good"
        status = "ahead of expected range"

    return {
        "farm_quality": quality,
        "expected_lh_range": [low, high],
        "lh_deficit_or_status": status,
    }


def _expected_lh_range(minute: int) -> list[int] | None:
    if minute < 3:
        return None
    previous = LH_RANGE_POINTS[0]
    for point in LH_RANGE_POINTS:
        if minute == point[0]:
            return [point[1], point[2]]
        if minute < point[0]:
            return _interpolate_range(previous, point, minute)
        previous = point
    return [LH_RANGE_POINTS[-1][1], LH_RANGE_POINTS[-1][2]]


def _interpolate_range(previous: tuple[int, int, int], current: tuple[int, int, int], minute: int) -> list[int]:
    prev_minute, prev_low, prev_high = previous
    current_minute, current_low, current_high = current
    span = max(1, current_minute - prev_minute)
    ratio = (minute - prev_minute) / span
    low = round(prev_low + (current_low - prev_low) * ratio)
    high = round(prev_high + (current_high - prev_high) * ratio)
    return [low, high]


def _hp_pressure_context(hp_percent: int, game_state: str, extra: Mapping[str, Any]) -> dict[str, Any]:
    pressure = _pressure_active(game_state, extra)
    if hp_percent < 35:
        state = "critical"
        reason = "HP is critical; one more trade or spell can kill you."
    elif pressure and hp_percent >= 75:
        state = "pressured_but_stable"
        reason = "Pressure is active, but HP is still high enough for conservative farming."
    elif pressure and 50 <= hp_percent <= 74:
        state = "risky"
        reason = "Pressure plus reduced HP can turn the next trade into a death."
    elif pressure:
        state = "risky"
        reason = "Pressure is active while HP is not comfortable."
    elif hp_percent < 50:
        state = "risky"
        reason = "HP is low enough that another trade can become dangerous."
    else:
        state = "healthy"
        reason = "HP is stable and no pressure signal is active."

    return {
        "hp_pressure_state": state,
        "hp_pressure_reason": reason,
    }


def _pressure_active(game_state: str, extra: Mapping[str, Any]) -> bool:
    if bool(extra.get("replay_damage_pressure_window")) or bool(extra.get("recent_damage_taken")):
        return True
    pressure_words = ("pressure", "fight", "bad_fight", "danger", "objective")
    return any(word in game_state for word in pressure_words)


def _position_context(raw_x: Any, raw_y: Any, team: str) -> dict[str, Any]:
    x = _optional_float(raw_x)
    y = _optional_float(raw_y)
    if x is None or y is None:
        return {
            "position_zone": "unknown",
            "position_risk": "unknown",
            "position_reason": "Position is unavailable.",
        }

    if team == "unknown":
        return {
            "position_zone": "lane_area",
            "position_risk": "medium",
            "position_reason": "Position is known, but team side is unknown; avoid assuming the area is safe.",
        }

    if _is_safe_side(x, y, team):
        return {
            "position_zone": "safe_side",
            "position_risk": "low",
            "position_reason": "Position is on your side of the map; still avoid assuming enemies are absent.",
        }
    if _is_deep_enemy_side(x, y, team):
        return {
            "position_zone": "deep_enemy_side",
            "position_risk": "high",
            "position_reason": "Position is far from your safe side, and enemy locations are not confirmed.",
        }
    if abs(x - MAP_CENTER) <= 2600 or abs(y - MAP_CENTER) <= 2600:
        return {
            "position_zone": "river_or_mid",
            "position_risk": "medium",
            "position_reason": "Position is near central map areas; avoid assuming the area is safe.",
        }
    return {
        "position_zone": "lane_area",
        "position_risk": "medium",
        "position_reason": "Position is lane-side, but enemy locations are not confirmed.",
    }


def _is_safe_side(x: float, y: float, team: str) -> bool:
    if team == "radiant":
        return x <= 12500 and y <= 12500
    if team == "dire":
        return x >= 20500 and y >= 20500
    return False


def _is_deep_enemy_side(x: float, y: float, team: str) -> bool:
    if team == "radiant":
        return x >= 21500 and y >= 21500
    if team == "dire":
        return x <= 11500 and y <= 11500
    return False


def _selected_team(state: Mapping[str, Any], extra: Mapping[str, Any]) -> str:
    for value in (state.get("selected_team"), extra.get("selected_team"), extra.get("team_name")):
        text = str(value or "").strip().lower()
        if "radiant" in text:
            return "radiant"
        if "dire" in text:
            return "dire"
    player_slot = _optional_int(extra.get("player_slot", state.get("player_slot")))
    if player_slot is not None:
        return "dire" if player_slot >= 128 else "radiant"
    return "unknown"


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


def _optional_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _optional_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
