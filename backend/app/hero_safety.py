"""
hero_safety.py - conservative hero-specific survival context for live GSI.

The rules are intentionally small and data-driven. They should only constrain
advice around survival resources, never create aggressive hero-specific calls.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from app.hero_profiles import (
    ability_is_unavailable,
    find_ability,
    get_key_safety_abilities,
    load_hero_profile,
)


RISK_ORDER = {"low": 0, "medium": 1, "high": 2}
DEFAULT_RESULT = {
    "hero_safety_flags": [],
    "hero_risk_level": "low",
    "hero_safety_reason": "",
    "recommended_constraint": "",
    "hero_safety_ability": "",
    "hero_safety_kind": "",
}


def evaluate_hero_safety(normalized_state: Mapping[str, Any] | Any) -> dict[str, Any]:
    state = _as_mapping(normalized_state)
    hero = str(state.get("hero") or "").strip()
    profile = load_hero_profile(hero)
    if profile.get("hero") == "Unknown":
        return dict(DEFAULT_RESULT)

    extra_context = _extra_context(state)
    abilities = extra_context.get("abilities")
    hp_percent = _to_int(state.get("hp_percent"), 100)
    mana_percent = _to_int(extra_context.get("mana_percent"), 100)
    warning_hp = _to_int(profile.get("low_hp_warning_threshold"), 50)
    critical_hp = _to_int(profile.get("critical_hp_threshold"), 35)
    mana_warning = _to_int(profile.get("mana_warning_threshold"), 25)
    triggered: list[dict[str, Any]] = []

    survival_resource = str(profile.get("survival_resource") or "").strip().lower()
    if survival_resource == "mana" and mana_percent <= mana_warning:
        key_abilities = get_key_safety_abilities(hero)
        flag = (
            "mana_shield_resource_low"
            if any(_ability_key(ability) == "mana shield" for ability in key_abilities["defensive"])
            else "mana_survival_resource_low"
        )
        triggered.append(
            {
                "flag": flag,
                "risk": "high",
                "reason": f"{hero} is low on mana, so effective survivability is reduced.",
                "constraint": "avoid extended fights and reset mana",
                "ability": "Mana Shield" if flag == "mana_shield_resource_low" else "",
                "kind": "resource",
            }
        )

    key_abilities = get_key_safety_abilities(hero)
    for ability_name in key_abilities["escape"]:
        ability = find_ability(abilities, ability_name)
        if ability and ability_is_unavailable(ability):
            triggered.append(
                {
                    "flag": "escape_on_cooldown",
                    "risk": "high",
                    "reason": f"{ability_name} is unavailable, so committing forward is risky.",
                    "constraint": f"avoid aggressive moves until {ability_name} is ready",
                    "ability": ability_name,
                    "kind": "escape",
                }
            )

    for ability_name in key_abilities["defensive"]:
        ability = find_ability(abilities, ability_name)
        if ability and ability_is_unavailable(ability) and hp_percent <= warning_hp:
            risk = "high" if hp_percent <= critical_hp else "medium"
            triggered.append(
                {
                    "flag": "defensive_ability_on_cooldown",
                    "risk": risk,
                    "reason": f"{ability_name} is unavailable, so your hero is easier to punish.",
                    "constraint": f"avoid forcing fights until {ability_name} is ready",
                    "ability": ability_name,
                    "kind": "defensive",
                }
            )

    if not triggered:
        return dict(DEFAULT_RESULT)

    highest = max(
        triggered,
        key=lambda rule: RISK_ORDER.get(str(rule.get("risk") or "low"), 0),
    )
    return {
        "hero_safety_flags": [
            str(rule.get("flag") or rule.get("type") or "hero_safety_risk")
            for rule in triggered
        ],
        "hero_risk_level": _safe_risk(str(highest.get("risk") or "low")),
        "hero_safety_reason": str(highest.get("reason") or "").strip(),
        "recommended_constraint": str(highest.get("constraint") or "").strip(),
        "hero_safety_ability": str(highest.get("ability") or "").strip(),
        "hero_safety_kind": str(highest.get("kind") or "").strip(),
    }


def _extra_context(state: Mapping[str, Any]) -> Mapping[str, Any]:
    extra_context = state.get("extra_context")
    return extra_context if isinstance(extra_context, Mapping) else {}


def _as_mapping(value: Mapping[str, Any] | Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    if hasattr(value, "model_dump"):
        return value.model_dump()
    return {}


def _ability_key(value: Any) -> str:
    return str(value or "").strip().lower().replace("_", " ").replace("-", " ")


def _safe_risk(value: str) -> str:
    risk = value.strip().lower()
    return risk if risk in RISK_ORDER else "low"


def _to_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
