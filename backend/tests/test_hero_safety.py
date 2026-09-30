"""
Characterization tests for hero_safety.evaluate_hero_safety.

This module is the safety gate that the rule-based policy leans on. The tests
pin the CURRENT gating behavior so that any refactor that weakens or changes
safety detection is caught. Behavior is asserted AS-IS.

Coverage:
  - Medusa mana-shield resource depletion (survival_resource == "mana")
  - Anti-Mage / Slark escape-on-cooldown gating
  - Juggernaut / Lifestealer defensive-ability cooldown (gated by low HP)
  - Unknown hero falls back to a default low-risk result
  - Risk escalation: high > medium; max-risk wins
"""

from __future__ import annotations

from typing import Any

from app.hero_safety import DEFAULT_RESULT, evaluate_hero_safety


def _state(hero: str, **overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "hero": hero,
        "hp_percent": 100,
        "extra_context": {
            "mana_percent": 100,
            "abilities": [],
        },
    }
    extra = overrides.pop("extra_context", {})
    base["extra_context"].update(extra)
    base.update(overrides)
    return base


def _ability(
    name: str, *, can_cast: bool = False, cooldown: int = 10, level: int = 1
) -> dict[str, Any]:
    return {
        "name": name,
        "raw_name": name.lower().replace(" ", "_"),
        "level": level,
        "cooldown": cooldown,
        "can_cast": can_cast,
    }


# --- unknown hero ---------------------------------------------------------


def test_unknown_hero_returns_default_low_risk() -> None:
    result = evaluate_hero_safety(_state("Pudge"))
    assert result == DEFAULT_RESULT
    assert result["hero_risk_level"] == "low"
    assert result["hero_safety_flags"] == []


# --- Medusa mana shield ---------------------------------------------------


def test_medusa_low_mana_flags_mana_shield_resource_low_at_high_risk() -> None:
    result = evaluate_hero_safety(_state("Medusa", extra_context={"mana_percent": 15}))
    assert result["hero_risk_level"] == "high"
    assert "mana_shield_resource_low" in result["hero_safety_flags"]
    assert result["hero_safety_ability"] == "Mana Shield"
    assert result["hero_safety_kind"] == "resource"


def test_medusa_mana_above_threshold_is_safe() -> None:
    # mana_warning_threshold == 25; mana_percent == 26 should NOT trigger.
    result = evaluate_hero_safety(_state("Medusa", extra_context={"mana_percent": 26}))
    assert result["hero_risk_level"] == "low"
    assert result["hero_safety_flags"] == []


def test_medusa_mana_at_threshold_boundary_triggers() -> None:
    # mana_percent == 25 satisfies `<= mana_warning_threshold` -> triggers.
    result = evaluate_hero_safety(_state("Medusa", extra_context={"mana_percent": 25}))
    assert "mana_shield_resource_low" in result["hero_safety_flags"]


# --- escape on cooldown (Anti-Mage Blink, Slark Pounce) --------------------


def test_antimage_blink_on_cooldown_flags_escape_high_risk() -> None:
    state = _state(
        "Anti-Mage",
        extra_context={"abilities": [_ability("Blink", can_cast=False)]},
    )
    result = evaluate_hero_safety(state)
    assert result["hero_risk_level"] == "high"
    assert "escape_on_cooldown" in result["hero_safety_flags"]
    assert result["hero_safety_ability"] == "Blink"
    assert result["hero_safety_kind"] == "escape"


def test_antimage_blink_ready_is_safe() -> None:
    state = _state(
        "Anti-Mage",
        extra_context={"abilities": [_ability("Blink", can_cast=True, cooldown=0)]},
    )
    result = evaluate_hero_safety(state)
    assert result["hero_risk_level"] == "low"


def test_slark_pounce_on_cooldown_flags_escape() -> None:
    state = _state(
        "Slark",
        extra_context={"abilities": [_ability("Pounce", can_cast=False)]},
    )
    result = evaluate_hero_safety(state)
    assert "escape_on_cooldown" in result["hero_safety_flags"]
    assert result["hero_safety_ability"] == "Pounce"


# --- defensive ability on cooldown (gated by low HP) ----------------------


def test_juggernaut_blade_fury_on_cooldown_at_low_hp_flags_defensive() -> None:
    # Defensive abilities only trigger when hp_percent <= warning_hp (50).
    state = _state(
        "Juggernaut",
        hp_percent=40,
        extra_context={"abilities": [_ability("Blade Fury", can_cast=False)]},
    )
    result = evaluate_hero_safety(state)
    assert "defensive_ability_on_cooldown" in result["hero_safety_flags"]
    assert result["hero_safety_ability"] == "Blade Fury"
    assert result["hero_safety_kind"] == "defensive"
    # hp 40 is above critical (35) -> medium risk.
    assert result["hero_risk_level"] == "medium"


def test_juggernaut_blade_fury_on_cooldown_at_full_hp_does_not_flag() -> None:
    # Characterize the conservative gate: at full HP a defensive cooldown is
    # not treated as a risk. (This is intentional; documented in the report.)
    state = _state(
        "Juggernaut",
        hp_percent=80,
        extra_context={"abilities": [_ability("Blade Fury", can_cast=False)]},
    )
    result = evaluate_hero_safety(state)
    assert result["hero_risk_level"] == "low"
    assert result["hero_safety_flags"] == []


def test_juggernaut_blade_fury_on_cooldown_at_critical_hp_is_high_risk() -> None:
    # hp <= critical_hp_threshold (35) -> risk escalates to high.
    state = _state(
        "Juggernaut",
        hp_percent=30,
        extra_context={"abilities": [_ability("Blade Fury", can_cast=False)]},
    )
    result = evaluate_hero_safety(state)
    assert result["hero_risk_level"] == "high"
    assert "defensive_ability_on_cooldown" in result["hero_safety_flags"]


def test_lifestealer_rage_on_cooldown_at_low_hp_flags_defensive() -> None:
    state = _state(
        "Lifestealer",
        hp_percent=45,
        extra_context={"abilities": [_ability("Rage", can_cast=False)]},
    )
    result = evaluate_hero_safety(state)
    assert "defensive_ability_on_cooldown" in result["hero_safety_flags"]
    assert result["hero_safety_ability"] == "Rage"


# --- risk aggregation: max risk wins --------------------------------------


def test_multiple_triggers_max_risk_wins() -> None:
    # Medusa with low mana (high) AND a defensive cooldown at medium hp:
    # both trigger; the highest risk (high from mana) should dominate.
    state = _state(
        "Slark",
        hp_percent=40,
        extra_context={
            "mana_percent": 100,
            "abilities": [
                _ability("Pounce", can_cast=False),  # escape -> high
                _ability("Dark Pact", can_cast=False),  # defensive -> medium
            ],
        },
    )
    result = evaluate_hero_safety(state)
    assert result["hero_risk_level"] == "high"
    # Both flags should be reported.
    assert "escape_on_cooldown" in result["hero_safety_flags"]
    assert "defensive_ability_on_cooldown" in result["hero_safety_flags"]


# --- pydantic / mapping passthrough ---------------------------------------


def test_evaluate_hero_safety_accepts_pydantic_like_object() -> None:
    # The function uses _as_mapping which supports objects with model_dump().
    class FakeReq:
        def model_dump(self) -> dict[str, Any]:
            return _state("Anti-Mage")

    result = evaluate_hero_safety(FakeReq())
    assert result["hero_risk_level"] == "low"


def test_an_unlearned_escape_is_nothing_to_wait_for() -> None:
    """A Queen of Pain at 0:29 was told «wait for Blink»: level 0, not learned."""
    state = _state(
        "Anti-Mage",
        extra_context={"abilities": [_ability("Blink", can_cast=False, cooldown=0, level=0)]},
    )
    assert "escape_on_cooldown" not in evaluate_hero_safety(state)["hero_safety_flags"]


def test_an_escape_on_cooldown_alone_needs_a_reason_to_speak() -> None:
    """«Wait for Blink» came eight times a match at full HP with nothing going on."""
    from app.decision_points import has_hero_survivability_risk

    blink = {"abilities": [_ability("Blink", can_cast=False)]}
    healthy = _state("Anti-Mage", extra_context=blink)
    assert not has_hero_survivability_risk(healthy, hp_percent=100, mana_percent=100)
    hurt = _state("Anti-Mage", hp_percent=55, extra_context=blink)
    assert has_hero_survivability_risk(hurt, hp_percent=55, mana_percent=100)
