"""
hero_profiles.py - data-driven carry profiles for lane and safety context.

Profiles describe broad archetypes and conservative safety resources. Decision
logic should ask this module for context instead of hardcoding hero clauses.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from functools import lru_cache
from pathlib import Path
from typing import Any


DEFAULT_PROFILE = {
    "hero": "Unknown",
    "aliases": [],
    "archetype": "generic_carry",
    "lane_profile": "generic_carry_lane",
    "survival_resource": None,
    "key_escape_abilities": [],
    "key_defensive_abilities": [],
    "key_fight_abilities": [],
    "low_hp_warning_threshold": 50,
    "critical_hp_threshold": 35,
    "mana_warning_threshold": 25,
    "laning_expected_lh": {"3": [8, 15], "5": [18, 30], "10": [45, 60]},
    "notes": "Use generic carry safety rules.",
}


def load_hero_profile(hero_name: str) -> dict[str, Any]:
    """Return a profile by hero name or alias, falling back to generic carry."""

    profile = _profiles_by_alias().get(_profile_key(hero_name))
    if not profile:
        return dict(DEFAULT_PROFILE)
    return dict(profile)


def get_hero_archetype(hero_name: str) -> str:
    return str(load_hero_profile(hero_name).get("archetype") or "generic_carry")


def get_laning_thresholds(hero_name: str, minute: int) -> dict[str, int]:
    profile = load_hero_profile(hero_name)
    thresholds = profile.get("laning_expected_lh")
    if not isinstance(thresholds, Mapping):
        thresholds = DEFAULT_PROFILE["laning_expected_lh"]

    selected_key: int | None = None
    for raw_key in thresholds:
        try:
            threshold_minute = int(raw_key)
        except (TypeError, ValueError):
            continue
        if threshold_minute <= minute and (selected_key is None or threshold_minute > selected_key):
            selected_key = threshold_minute

    if selected_key is None:
        return {}

    value = thresholds.get(str(selected_key), thresholds.get(selected_key))
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        return {}
    return {
        "minute": selected_key,
        "expected_min": _to_int(value[0], 0),
        "expected_max": _to_int(value[1], 999),
    }


def get_key_safety_abilities(hero_name: str) -> dict[str, list[str]]:
    profile = load_hero_profile(hero_name)
    return {
        "escape": _string_list(profile.get("key_escape_abilities")),
        "defensive": _string_list(profile.get("key_defensive_abilities")),
        "fight": _string_list(profile.get("key_fight_abilities")),
    }


def evaluate_laning_context(normalized_state: Mapping[str, Any] | Any) -> dict[str, Any]:
    state = _as_mapping(normalized_state)
    hero = str(state.get("hero") or "").strip()
    profile = load_hero_profile(hero)
    extra_context = _extra_context(state)
    minute = _to_int(state.get("minute"), 0)
    hp_percent = _to_int(state.get("hp_percent"), 100)
    last_hits = _to_int_or_none(_ctx_value(state, "last_hits"))
    demo_values = _to_bool(_ctx_value(state, "demo_values_detected"))

    low_hp_warning_threshold = _to_int(profile.get("low_hp_warning_threshold"), 50)
    critical_hp_threshold = _to_int(profile.get("critical_hp_threshold"), 35)
    farm_status = _farm_status(
        hero=hero,
        minute=minute,
        last_hits=last_hits,
        demo_values_detected=demo_values,
    )
    safety_status = _key_safety_status(profile, extra_context.get("abilities"))

    context_parts: list[str] = []
    if hp_percent <= critical_hp_threshold:
        context_parts.append("critical HP")
    elif minute <= 12 and hp_percent <= low_hp_warning_threshold:
        context_parts.append("low lane HP")
    if farm_status == "behind":
        context_parts.append("lane farm is behind profile threshold")
    if safety_status["available"] is False:
        context_parts.append(safety_status["missing_reason"])

    return {
        "archetype": str(profile.get("archetype") or "generic_carry"),
        "lane_profile": str(profile.get("lane_profile") or "generic_carry_lane"),
        "low_hp_warning_threshold": low_hp_warning_threshold,
        "critical_hp_threshold": critical_hp_threshold,
        "mana_warning_threshold": _to_int(profile.get("mana_warning_threshold"), 25),
        "farm_status": farm_status,
        "key_safety_available": safety_status["available"],
        "key_safety_missing_reason": safety_status["missing_reason"],
        "key_safety_ability": safety_status["ability"],
        "key_safety_kind": safety_status["kind"],
        "key_safety_cooldown": safety_status["cooldown"],
        "laning_advice_context": "; ".join(part for part in context_parts if part) or "stable lane context",
    }


def ability_is_unavailable(ability: Mapping[str, Any]) -> bool:
    level = _to_float(ability.get("level"))
    if level is not None and level <= 0:
        return True

    cooldown = _to_float(ability.get("cooldown"))
    if cooldown is not None and cooldown > 0:
        return True

    can_cast = ability.get("can_cast")
    return can_cast is False


def find_ability(abilities: Any, target_name: str) -> Mapping[str, Any] | None:
    target_key = _ability_key(target_name)
    if not target_key or not isinstance(abilities, list):
        return None

    for ability in abilities:
        if not isinstance(ability, Mapping):
            continue
        keys = {
            _ability_key(ability.get("name")),
            _ability_key(ability.get("raw_name")),
        }
        if target_key in keys:
            return ability
        if any(key and (target_key in key or key.endswith(target_key)) for key in keys):
            return ability
    return None


def _key_safety_status(profile: Mapping[str, Any], abilities: Any) -> dict[str, Any]:
    key_abilities = {
        "escape": _string_list(profile.get("key_escape_abilities")),
        "defensive": _string_list(profile.get("key_defensive_abilities")),
    }
    if not key_abilities["escape"] and not key_abilities["defensive"]:
        return _safety_status()

    if not isinstance(abilities, list) or not abilities:
        return _safety_status(available=None)

    any_found = False
    for kind in ("escape", "defensive"):
        for ability_name in key_abilities[kind]:
            ability = find_ability(abilities, ability_name)
            if not ability:
                continue
            any_found = True
            if ability_is_unavailable(ability):
                cooldown = _to_float(ability.get("cooldown"))
                reason = f"{ability_name} is unavailable"
                if cooldown is not None and cooldown > 0:
                    reason = f"{ability_name} is on cooldown"
                return _safety_status(
                    available=False,
                    ability=ability_name,
                    kind=kind,
                    cooldown=cooldown,
                    missing_reason=reason,
                )

    return _safety_status(available=True if any_found else None)


def _safety_status(
    *,
    available: bool | None = None,
    ability: str = "",
    kind: str = "",
    cooldown: float | None = None,
    missing_reason: str = "",
) -> dict[str, Any]:
    return {
        "available": available,
        "ability": ability,
        "kind": kind,
        "cooldown": cooldown,
        "missing_reason": missing_reason,
    }


def _farm_status(
    *,
    hero: str,
    minute: int,
    last_hits: int | None,
    demo_values_detected: bool,
) -> str:
    if demo_values_detected or last_hits is None or minute < 3 or minute > 12:
        return "unknown"

    threshold = get_laning_thresholds(hero, minute)
    if not threshold:
        return "unknown"
    if last_hits < threshold["expected_min"]:
        return "behind"
    if last_hits > threshold["expected_max"]:
        return "ahead"
    return "normal"


@lru_cache(maxsize=1)
def _profiles_by_alias() -> dict[str, dict[str, Any]]:
    profiles = _load_profiles()
    by_alias: dict[str, dict[str, Any]] = {}
    for profile in profiles:
        if not isinstance(profile, Mapping):
            continue
        canonical = str(profile.get("hero") or "").strip()
        if canonical:
            by_alias[_profile_key(canonical)] = dict(profile)
        for alias in _string_list(profile.get("aliases")):
            by_alias[_profile_key(alias)] = dict(profile)
    return by_alias


@lru_cache(maxsize=1)
def _load_profiles() -> list[dict[str, Any]]:
    path = Path(__file__).resolve().parents[2] / "data" / "heroes" / "hero_profiles.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    profiles = data.get("profiles") if isinstance(data, Mapping) else None
    return profiles if isinstance(profiles, list) else []


def _ctx_value(state: Mapping[str, Any], key: str, default: Any = None) -> Any:
    if key in state:
        return state.get(key)
    return _extra_context(state).get(key, default)


def _extra_context(state: Mapping[str, Any]) -> Mapping[str, Any]:
    extra_context = state.get("extra_context")
    return extra_context if isinstance(extra_context, Mapping) else {}


def _as_mapping(value: Mapping[str, Any] | Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    if hasattr(value, "model_dump"):
        return value.model_dump()
    return {}


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _profile_key(value: Any) -> str:
    return _ability_key(value)


def _ability_key(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = text.removeprefix("ability_").removeprefix("npc_dota_hero_")
    text = text.replace("_", " ").replace("-", " ")
    text = re.sub(r"[^a-z0-9 ]+", "", text)
    return " ".join(text.split())


def _to_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _to_int_or_none(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _to_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)
