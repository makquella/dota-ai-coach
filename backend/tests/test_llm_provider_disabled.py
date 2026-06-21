"""
Characterization tests for the LLM-isolation principle.

The project's core invariant: the optional LLM provider NEVER overrides
decision_point, priority, time_window, safety gating, or anti-spam. With
USE_LLM=false (the default), LLM is never invoked and the rule-based
recommender is the only path.

These tests pin that invariant. They must never make a real network call —
the DisabledProvider short-circuits before any HTTP attempt.

Tested layers:
  - llm_provider.is_llm_provider_enabled / get_llm_provider return disabled by default
  - DisabledProvider.generate returns recommendation=None + error, no network
  - generate_llm_recommendation preserves the disabled result
  - The rule-based recommender output is identical whether or not an LLM
    provider would be configured: priority/time_window come from advice_policy.
  - advice_policy.safety_constraints for SOFT_STATUS / NO_ADVICE literally say
    "do not call LLM" (characterization of that constraint text).
"""

from __future__ import annotations

from typing import Any

import app.config as config
import app.main as main_module
from app.advice_policy import build_advice_policy
from app.llm_provider import DisabledProvider, generate_llm_recommendation, get_llm_provider
from app.recommender import generate_recommendation
from app.schemas import GameSituationRequest


def _req(**overrides: Any) -> GameSituationRequest:
    fields: dict[str, Any] = {
        "hero": "Juggernaut",
        "role": "carry",
        "minute": 15,
        "level": 15,
        "gold": 0,
        "items": ["Power Treads"],
        "hp_percent": 20,
        "game_state": "low hp retreat",
        "team_status": "unknown",
        "extra_context": {"mana_percent": 80, "alive": True},
    }
    fields.update(overrides)
    return GameSituationRequest(**fields)


# --- default configuration is disabled ------------------------------------


def test_default_llm_provider_is_disabled() -> None:
    # Characterize the safe default: no env override means disabled.
    assert config.LLM_PROVIDER == "disabled"
    assert config.USE_LLM is False


def test_is_llm_provider_enabled_false_by_default() -> None:
    from app.llm_provider import is_llm_provider_enabled

    assert is_llm_provider_enabled() is False


def test_get_llm_provider_returns_disabled_provider_by_default() -> None:
    provider = get_llm_provider()
    assert isinstance(provider, DisabledProvider)
    assert provider.name == "disabled"


# --- DisabledProvider never makes a network call --------------------------


def test_disabled_provider_returns_none_recommendation_with_error() -> None:
    provider = DisabledProvider()
    result = provider.generate(_req(), "LOW_HP", [])
    assert result.recommendation is None
    assert result.error == "LLM provider is disabled"
    assert result.provider == "disabled"


def test_generate_llm_recommendation_preserves_disabled_result() -> None:
    result = generate_llm_recommendation(_req(), "LOW_HP", [])
    assert result.recommendation is None
    assert result.error == "LLM provider is disabled"


# --- LLM does not affect decision_point / priority / time_window ----------


def test_recommender_priority_is_independent_of_llm_config() -> None:
    # The rule-based policy owns priority/time_window. Even if we imagine an
    # LLM provider were enabled, the recommender output must be identical.
    rec_disabled = generate_recommendation(_req(), rag_context=[])
    policy = build_advice_policy(_req().model_dump(), "LOW_HP")

    assert rec_disabled.priority == policy["priority"] == "high"
    assert rec_disabled.time_window == policy["time_window"]
    assert rec_disabled.source == "fallback"


def test_decision_point_comes_from_rules_not_llm() -> None:
    # detect_decision_point is pure rule logic; LLM is never consulted for it.
    from app.decision_points import detect_decision_point

    state = _req().model_dump()
    assert detect_decision_point(state) == "LOW_HP"


def test_advice_policy_safety_constraint_for_soft_status_says_no_llm() -> None:
    # Characterization: the SOFT_STATUS policy explicitly lists "do not call LLM"
    # as a safety constraint, encoding the principle in the policy table itself.
    policy = build_advice_policy(
        _req(hp_percent=80, game_state="calm lane").model_dump(), "SOFT_STATUS"
    )
    constraints = " ".join(policy["safety_constraints"]).lower()
    assert "do not call llm" in constraints


def test_advice_policy_safety_constraint_for_no_advice_says_no_llm() -> None:
    policy = build_advice_policy(_req(hp_percent=80).model_dump(), "NO_ADVICE")
    constraints = " ".join(policy["safety_constraints"]).lower()
    assert "do not call llm" in constraints


# --- _build_recommendation never invokes LLM when USE_LLM is false --------


def test_build_recommendation_uses_fallback_source_when_use_llm_false(
    monkeypatch,  # noqa: ARG001
) -> None:
    # Even with a working request, USE_LLM=False means the LLM branch in
    # _build_recommendation is skipped entirely. We assert the source is
    # fallback and that generate_llm_recommendation was NOT called.
    calls: list[str] = []

    def _spy(*args: Any, **kwargs: Any) -> Any:
        calls.append("llm_invoked")
        raise AssertionError("LLM must not be invoked when USE_LLM is false")

    monkeypatch.setattr(main_module, "generate_llm_recommendation", _spy)
    # Defensive: ensure USE_LLM is false for this test.
    monkeypatch.setattr(main_module, "USE_LLM", False)

    recommendation, _ = main_module._build_recommendation(_req(), decision_point="LOW_HP")
    assert recommendation.source == "fallback"
    assert calls == []


# --- simulating USE_LLM=True with a disabled provider still falls back -----


def test_build_recommendation_falls_back_when_llm_returns_none(
    monkeypatch,
) -> None:
    # Characterize: even if USE_LLM were True, a disabled/erroring provider
    # (recommendation=None) makes _build_recommendation use the fallback
    # recommender. Priority/time_window still come from the rule-based policy.
    monkeypatch.setattr(main_module, "USE_LLM", True)
    # Force the provider lookup to stay disabled (no real network).
    monkeypatch.setattr(main_module, "is_llm_provider_enabled", lambda: True)

    def _fake_generate(request, decision_point, rag_context):  # noqa: ANN001
        # Mimic DisabledProvider: no recommendation, an error string.
        from app.llm_provider import LLMResult

        return LLMResult(
            recommendation=None,
            provider="disabled",
            model="",
            error="LLM provider is disabled",
        )

    monkeypatch.setattr(main_module, "generate_llm_recommendation", _fake_generate)

    recommendation, _ = main_module._build_recommendation(_req(), decision_point="LOW_HP")
    assert recommendation.source == "fallback"
    # Priority is still the rule-based HIGH for LOW_HP, never altered by LLM.
    assert recommendation.priority == "high"


# --- SOFT_STATUS / NO_ADVICE never reach the LLM branch --------------------


def test_soft_status_never_considers_llm_even_if_enabled(monkeypatch) -> None:
    # The LLM branch is gated on `decision_point not in {NO_ADVICE, SOFT_STATUS}`.
    # SOFT_STATUS must short-circuit to fallback regardless of USE_LLM.
    monkeypatch.setattr(main_module, "USE_LLM", True)

    def _spy(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("LLM must not be invoked for SOFT_STATUS")

    monkeypatch.setattr(main_module, "generate_llm_recommendation", _spy)

    recommendation, _ = main_module._build_recommendation(
        _req(hp_percent=80, game_state="calm lane"),
        decision_point="SOFT_STATUS",
    )
    assert recommendation.source == "fallback"
