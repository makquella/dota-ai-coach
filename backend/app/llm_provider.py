"""
llm_provider.py — optional runtime LLM recommendation providers.

The rule-based recommender remains the safe default. Providers return structured
failure results instead of raising so API handlers can fall back quickly.
"""

from __future__ import annotations

import json
import multiprocessing as mp
import re
import time
from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError
import requests

from app.config import (
    GROQ_API_KEY,
    GROQ_MODEL,
    LLM_MAX_TOKENS,
    LLM_PROVIDER,
    LLM_TIMEOUT,
    LLAMACPP_BASE_URL,
    LLAMACPP_MODEL,
    OPENROUTER_API_KEY,
    OPENROUTER_MODEL,
)
from app.advice_policy import apply_advice_policy, build_advice_policy
from app.advice_text import clean_recommendation_text
from app.schemas import GameSituationRequest, RecommendationResponse


OPENROUTER_CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"
GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"
LLAMACPP_CHAT_URL = f"{LLAMACPP_BASE_URL}/v1/chat/completions"

VALID_TIME_WINDOWS = {
    "immediate: next 10-15 seconds",
    "next 60-90 seconds",
    "reassess in 60 seconds",
}

BANNED_LLM_ACTION_PHRASES = (
    "lane jungle camps",
    "consider farm last hits",
    "no nearby fights",
    "safe to fight",
    "team is ready",
    "enemy is not nearby",
)

OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "action": {"type": "string"},
        "reason": {"type": "string"},
        "risk": {"type": "string"},
        "priority": {"type": "string", "enum": ["low", "medium", "high"]},
        "time_window": {
            "type": "string",
            "enum": [
                "immediate: next 10-15 seconds",
                "next 60-90 seconds",
                "reassess in 60 seconds",
            ],
        },
        "source": {"type": "string", "enum": ["llm"]},
    },
    "required": ["action", "reason", "risk", "priority", "time_window", "source"],
    "additionalProperties": False,
}


@dataclass
class LLMResult:
    recommendation: RecommendationResponse | None
    provider: str
    model: str
    error: str | None = None
    wording_guard_applied_count: int = 0
    wording_guard_fallback_count: int = 0


class LLMWordingGuardError(ValueError):
    """Raised when visible LLM wording is unsafe or too weak to show."""


class BaseLLMProvider:
    name = "base"

    def __init__(
        self,
        *,
        api_key: str,
        api_key_name: str,
        model: str,
        chat_url: str,
        extra_headers: dict[str, str] | None = None,
        requires_api_key: bool = True,
    ) -> None:
        self.api_key = api_key
        self.api_key_name = api_key_name
        self.model = model
        self.chat_url = chat_url
        self.extra_headers = extra_headers or {}
        self.requires_api_key = requires_api_key

    def generate(
        self,
        request: GameSituationRequest,
        decision_point: str,
        rag_context: list[str],
    ) -> LLMResult:
        if self.requires_api_key and not self.api_key:
            return LLMResult(
                recommendation=None,
                provider=self.name,
                model=self.model,
                error=f"{self.api_key_name} is not set",
            )

        policy = build_advice_policy(request, decision_point)
        payload = _build_payload(self.model, request, decision_point, rag_context, policy)
        headers = {"Content-Type": "application/json", **self.extra_headers}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        started = time.perf_counter()
        call_result = _post_with_hard_timeout(
            provider_name=self.name,
            chat_url=self.chat_url,
            headers=headers,
            payload=payload,
            api_key=self.api_key,
        )
        elapsed = time.perf_counter() - started

        if elapsed > LLM_TIMEOUT:
            return LLMResult(
                recommendation=None,
                provider=self.name,
                model=self.model,
                error=f"{_display_provider(self.name)} request timed out after {LLM_TIMEOUT:g} seconds",
            )

        if call_result.get("error"):
            return LLMResult(
                recommendation=None,
                provider=self.name,
                model=self.model,
                error=call_result["error"],
            )

        wording_guard_applied_count = 0
        try:
            content = _extract_message_content(call_result["response_json"], self.name)
            raw_recommendation = _validate_llm_content(content)
            recommendation = raw_recommendation
            recommendation = _naturalize_recommendation(recommendation, decision_point)
            recommendation = apply_advice_policy(recommendation, policy)
            recommendation = clean_recommendation_text(recommendation, decision_point)
            recommendation = _clean_context_sensitive_recommendation(
                recommendation,
                request,
                decision_point,
            )
            wording_guard_applied_count = _wording_change_count(raw_recommendation, recommendation)
        except LLMWordingGuardError as exc:
            return LLMResult(
                recommendation=None,
                provider=self.name,
                model=self.model,
                error=_clean_validation_error(exc, self.name),
                wording_guard_fallback_count=1,
            )
        except (
            requests.exceptions.JSONDecodeError,
            json.JSONDecodeError,
            ValueError,
            ValidationError,
        ) as exc:
            return LLMResult(
                recommendation=None,
                provider=self.name,
                model=self.model,
                error=_clean_validation_error(exc, self.name),
            )

        return LLMResult(
            recommendation=recommendation,
            provider=self.name,
            model=self.model,
            wording_guard_applied_count=wording_guard_applied_count,
        )


class OpenRouterProvider(BaseLLMProvider):
    name = "openrouter"

    def __init__(self) -> None:
        super().__init__(
            api_key=OPENROUTER_API_KEY,
            api_key_name="OPENROUTER_API_KEY",
            model=OPENROUTER_MODEL,
            chat_url=OPENROUTER_CHAT_URL,
            extra_headers={
                "HTTP-Referer": "http://127.0.0.1:8000",
                "X-Title": "Dota AI Coach MVP",
            },
        )


class GroqProvider(BaseLLMProvider):
    name = "groq"

    def __init__(self) -> None:
        super().__init__(
            api_key=GROQ_API_KEY,
            api_key_name="GROQ_API_KEY",
            model=GROQ_MODEL,
            chat_url=GROQ_CHAT_URL,
        )


class LlamaCppProvider(BaseLLMProvider):
    name = "llamacpp"

    def __init__(self) -> None:
        super().__init__(
            api_key="",
            api_key_name="",
            model=LLAMACPP_MODEL,
            chat_url=LLAMACPP_CHAT_URL,
            requires_api_key=False,
        )


class DisabledProvider:
    name = "disabled"
    model = ""

    def generate(
        self,
        request: GameSituationRequest,
        decision_point: str,
        rag_context: list[str],
    ) -> LLMResult:
        return LLMResult(
            recommendation=None,
            provider=self.name,
            model=self.model,
            error="LLM provider is disabled",
        )


def is_llm_provider_enabled() -> bool:
    return LLM_PROVIDER != "disabled"


def get_llm_provider() -> BaseLLMProvider | DisabledProvider:
    if LLM_PROVIDER == "groq":
        return GroqProvider()
    if LLM_PROVIDER == "openrouter":
        return OpenRouterProvider()
    if LLM_PROVIDER == "llamacpp":
        return LlamaCppProvider()
    if LLM_PROVIDER == "disabled":
        return DisabledProvider()
    return DisabledProvider()


def generate_llm_recommendation(
    request: GameSituationRequest,
    decision_point: str,
    rag_context: list[str],
) -> LLMResult:
    provider = get_llm_provider()
    result = provider.generate(request, decision_point, rag_context)
    if LLM_PROVIDER not in {"groq", "openrouter", "llamacpp", "disabled"}:
        result.error = f"Unsupported LLM_PROVIDER '{LLM_PROVIDER}'"
    return result


def _build_payload(
    model: str,
    request: GameSituationRequest,
    decision_point: str,
    rag_context: list[str],
    advice_policy: dict[str, Any],
) -> dict[str, Any]:
    return {
        "model": model,
        "temperature": 0.2,
        "max_tokens": LLM_MAX_TOKENS,
        "stream": False,
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a conservative Dota 2 carry coach. "
                    "Do not overload the player. Give only one main action and one short reason. "
                    "Do not suggest high-risk fights unless objective value is clear. "
                    "If uncertain, recommend farming, resetting, or waiting. "
                    "Do not recommend item builds or purchases. "
                    "For item timings, explain that the timing changes the next decision; never say to buy an item. "
                    "For objective checks, do not say 'safe to join' or 'objective value is clear' "
                    "unless fight_safe is explicitly true. "
                    "Do not assume team readiness if team_status is unknown. "
                    "Do not assume team readiness, nearby allies, enemy positions, exact HP, or cooldowns "
                    "when those signals are listed in missing_signals. "
                    "If gold is listed in missing_signals or replay_defaulted_fields, never mention exact gold, "
                    "lane gold, gold flow, or maintaining gold; say steady farm instead. "
                    "If exact_teamfight_context or nearby_allies_enemies is missing, avoid confident fight "
                    "language. Do not say safe to fight, team is ready, no nearby fights, or no nearby enemies. "
                    "Prefer conditional objective advice. "
                    "If hp is missing, do not create low-HP advice. If ability_cooldowns is missing, do not "
                    "give cooldown-specific survival advice. "
                    "If team_status is disadvantage, avoid recommending fights. "
                    "If team_status is advantage and an objective is nearby, objective advice may be more positive "
                    "but must still be cautious. "
                    "For live GSI status fields, treat low health, low mana, disables, death, and smoke as "
                    "player-safety signals. Never force aggression from smoke or item timing alone. "
                    "Use laning_context for farm status, HP thresholds, and key safety ability availability. "
                    "Do not contradict hero safety constraints. If a key escape or defensive ability is "
                    "unavailable, do not recommend aggressive fight entry. For Medusa, treat mana as "
                    "survivability, not only spell resource. "
                    "For death review states, advise what to change after respawn; do not suggest fighting "
                    "while dead or give buyback commands. "
                    "Preserve the local context-specific action and reason unless you can make them clearer. "
                    "Do not make advice more generic than local_advice_hint. "
                    "For LANING_FARM_CHECK and FARMING_PHASE_PRESSURE, prefer local_advice_hint because it uses "
                    "farm_quality, hp_pressure_state, and position_risk. "
                    "Do not use awkward phrases like 'Consider farm last hits', 'Consider farm safely', "
                    "'Focus last-hitting', or 'lane jungle camps'. "
                    "For objective checks, prefer: Consider joining only if the fight is near a valuable objective. "
                    "Do not provide mechanical execution commands. "
                    "Do not act as autopilot; use a coaching tone for non-urgent advice. "
                    "Keep action under 100 characters. Keep reason under 180 characters. "
                    "Use the provided advice policy for priority and time_window. "
                    "Return strict JSON only."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "validated_normalized_game_state": request.model_dump(),
                        "team_context": _team_context_for_prompt(request),
                        "live_gsi_context": request.extra_context,
                        "advice_context": _advice_context_for_prompt(request),
                        "laning_context": request.extra_context.get("laning_context", {}),
                        "hero_safety_context": _hero_safety_context_for_prompt(request),
                        "match_memory_context": _match_memory_context_for_prompt(request),
                        "decision_point": decision_point,
                        "advice_policy": advice_policy,
                        "local_advice_hint": _local_advice_hint_for_prompt(request),
                        "rag_context": rag_context,
                        "required_output_json_schema": OUTPUT_SCHEMA,
                    },
                    ensure_ascii=False,
                ),
            },
        ],
    }


def _team_context_for_prompt(request: GameSituationRequest) -> dict[str, Any]:
    return {
        "team_status": request.team_status,
        "selected_team": request.selected_team,
        "near_teamfight": request.near_teamfight,
        "teamfight_result": request.teamfight_result,
        "allied_deaths_in_fight": request.allied_deaths_in_fight,
        "enemy_deaths_in_fight": request.enemy_deaths_in_fight,
        "recent_allied_deaths": request.recent_allied_deaths,
        "recent_enemy_deaths": request.recent_enemy_deaths,
        "selected_player_in_teamfight": request.selected_player_in_teamfight,
        "selected_player_death_nearby": request.selected_player_death_nearby,
        "near_objective": request.near_objective,
        "objective_type": request.objective_type,
        "objective_team": request.objective_team,
        "objective_for_selected_team": request.objective_for_selected_team,
        "objective_context": request.objective_context,
    }


def _advice_context_for_prompt(request: GameSituationRequest) -> dict[str, Any]:
    context = request.extra_context if isinstance(request.extra_context, dict) else {}
    keys = (
        "farm_quality",
        "expected_lh_range",
        "lh_deficit_or_status",
        "hp_pressure_state",
        "hp_pressure_reason",
        "position_zone",
        "position_risk",
        "position_reason",
        "missing_signals",
        "replay_defaulted_fields",
    )
    return {key: context.get(key) for key in keys if context.get(key) is not None}


def _local_advice_hint_for_prompt(request: GameSituationRequest) -> dict[str, str]:
    try:
        from app.recommender import generate_recommendation

        recommendation = generate_recommendation(request, [])
    except Exception:
        return {}
    return {
        "action": recommendation.action,
        "reason": recommendation.reason,
        "risk": recommendation.risk,
    }


def _hero_safety_context_for_prompt(request: GameSituationRequest) -> dict[str, Any]:
    return {
        "hero_safety_flags": request.extra_context.get("hero_safety_flags", []),
        "hero_risk_level": request.extra_context.get("hero_risk_level", "low"),
        "hero_safety_reason": request.extra_context.get("hero_safety_reason", ""),
        "recommended_constraint": request.extra_context.get("recommended_constraint", ""),
        "hero_safety_ability": request.extra_context.get("hero_safety_ability", ""),
        "hero_safety_kind": request.extra_context.get("hero_safety_kind", ""),
    }


def _match_memory_context_for_prompt(request: GameSituationRequest) -> dict[str, Any]:
    return {
        "match_session_id": request.extra_context.get("match_session_id"),
        "match_death_count": request.extra_context.get("match_death_count"),
        "recent_death_pattern": request.extra_context.get("recent_death_pattern"),
        "recent_death_patterns": request.extra_context.get("recent_death_patterns", []),
        "last_death_minute": request.extra_context.get("last_death_minute"),
        "last_death_context": request.extra_context.get("last_death_context", ""),
        "death_review_available": request.extra_context.get("death_review_available", False),
    }


def _post_with_hard_timeout(
    *,
    provider_name: str,
    chat_url: str,
    headers: dict[str, str],
    payload: dict[str, Any],
    api_key: str,
) -> dict[str, Any]:
    context = _multiprocessing_context()
    queue: mp.Queue = context.Queue(maxsize=1)
    process = context.Process(
        target=_post_worker,
        args=(queue, provider_name, chat_url, headers, payload, api_key),
        daemon=True,
    )
    process.start()
    process.join(LLM_TIMEOUT)

    if process.is_alive():
        process.terminate()
        process.join(0.5)
        return {
            "error": f"{_display_provider(provider_name)} request timed out after {LLM_TIMEOUT:g} seconds"
        }

    if queue.empty():
        return {"error": f"{_display_provider(provider_name)} request returned no result"}

    return queue.get()


def _multiprocessing_context() -> mp.context.BaseContext:
    if "fork" in mp.get_all_start_methods():
        return mp.get_context("fork")
    return mp.get_context()


def _post_worker(
    queue: mp.Queue,
    provider_name: str,
    chat_url: str,
    headers: dict[str, str],
    payload: dict[str, Any],
    api_key: str,
) -> None:
    provider = _display_provider(provider_name)
    connect_timeout = min(5.0, LLM_TIMEOUT)

    try:
        response = requests.post(
            chat_url,
            headers=headers,
            json=payload,
            timeout=(connect_timeout, LLM_TIMEOUT),
            stream=False,
        )
        if response.status_code >= 400:
            queue.put({"error": f"{provider} HTTP error: {response.status_code}"})
            return

        queue.put({"response_json": response.json()})
    except requests.Timeout:
        queue.put({"error": f"{provider} request timed out after {LLM_TIMEOUT:g} seconds"})
    except requests.exceptions.JSONDecodeError:
        queue.put({"error": f"{provider} returned invalid response JSON"})
    except requests.RequestException as exc:
        queue.put({"error": _sanitize_error(f"{provider} request failed: {exc}", api_key)})


def _display_provider(provider_name: str) -> str:
    if provider_name == "groq":
        return "Groq"
    if provider_name == "openrouter":
        return "OpenRouter"
    if provider_name == "llamacpp":
        return "llama.cpp"
    return "LLM provider"


def _sanitize_error(message: str, api_key: str) -> str:
    cleaned = message.replace(api_key, "[redacted_api_key]") if api_key else message
    for marker in ("Authorization", "authorization", "Bearer", "bearer"):
        cleaned = cleaned.replace(marker, "[redacted_auth]")
    return cleaned[:500]


def _clean_validation_error(exc: Exception, provider_name: str) -> str:
    provider = _display_provider(provider_name)
    if isinstance(exc, (requests.exceptions.JSONDecodeError, json.JSONDecodeError)):
        return f"{provider} returned invalid recommendation JSON"
    if isinstance(exc, ValidationError):
        return f"{provider} recommendation failed schema validation"
    return _sanitize_error(f"{provider} recommendation invalid: {exc}", "")


def _extract_message_content(response: dict[str, Any], provider_name: str) -> str:
    provider = _display_provider(provider_name)
    choices = response.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ValueError(f"{provider} response did not include choices")

    message = choices[0].get("message")
    if not isinstance(message, dict):
        raise ValueError(f"{provider} response did not include a message")

    content = message.get("content")
    if isinstance(content, str):
        return content.strip()

    raise ValueError(f"{provider} response content was not a string")


def _validate_llm_content(content: str) -> RecommendationResponse:
    data = json.loads(content)
    if not isinstance(data, dict):
        raise ValueError("LLM output was not a JSON object")

    if data.get("source") != "llm":
        raise ValueError("LLM output source must be 'llm'")

    if data.get("time_window") not in VALID_TIME_WINDOWS:
        raise ValueError("LLM output time_window is not allowed")

    return RecommendationResponse(**data)


def _naturalize_recommendation(
    recommendation: RecommendationResponse,
    decision_point: str | None = None,
) -> RecommendationResponse:
    recommendation = clean_recommendation_text(recommendation, decision_point)
    replacements = {
        "keep_farming": "Keep farming safely and reassess in 60 seconds.",
        "switch_to_safe_farm": "Avoid contesting pressure and move to safer farm.",
        "play_back_and_regen": "Use regen or play back until your HP is safer.",
        "stabilize_after_recent_damage": "Back up and stabilize before trading again.",
        "stop_overstay_low_hp": "Do not overstay on low HP; reset or play behind creeps.",
        "stabilize_lane_farm": "Focus on safe last hits before forcing trades.",
        "respect_defensive_ability_cooldown": "Avoid risky trades until your defensive tool is ready.",
        "retreat_reset": "Retreat and reset before rejoining.",
        "avoid_bad_fight": "Avoid this fight and reset to safer farm.",
        "join_only_if_objective_value": "Consider joining only if your team is ready and the fight is near the objective.",
        "play_around_timing": "You reached a timing; reassess whether to pressure or keep farming safely.",
        "respect_hero_safety_window": "Respect your hero's safety window before forcing a fight.",
        "plan_safer_respawn_route": "Use the respawn time to plan a safer next route.",
        "break_repeated_death_pattern": "After respawn, reset your route and avoid repeating the same risky path.",
        "respect_escape_cooldown_after_respawn": "After respawn, avoid committing forward until your escape is ready.",
        "reset_before_resources_collapse": "After respawn, reset earlier when HP or key resources get low.",
        "soft_status": "Monitoring lane - no urgent advice.",
    }
    action = recommendation.action.strip()
    key = action.lower()
    canonical_key = key.replace(" ", "_").replace("-", "_")
    if canonical_key in replacements:
        action = replacements[canonical_key]
    elif "_" in key and len(action.split()) == 1:
        action = key.replace("_", " ").capitalize() + "."

    return clean_recommendation_text(
        RecommendationResponse(
            action=action,
            reason=recommendation.reason,
            risk=recommendation.risk,
            priority=recommendation.priority,
            time_window=recommendation.time_window,
            source=recommendation.source,
        ),
        decision_point,
    )


def _clean_context_sensitive_recommendation(
    recommendation: RecommendationResponse,
    request: GameSituationRequest,
    decision_point: str,
) -> RecommendationResponse:
    extra_context = request.extra_context if isinstance(request.extra_context, dict) else {}
    missing_signals = set(extra_context.get("missing_signals") or [])
    defaulted_fields = set(extra_context.get("replay_defaulted_fields") or [])

    action = recommendation.action
    reason = recommendation.reason
    risk = recommendation.risk

    if "gold" in missing_signals or "gold" in defaulted_fields:
        action = _remove_missing_gold_language(action)
        reason = _remove_missing_gold_language(reason)
        risk = _remove_missing_gold_language(risk)

    missing_team_context = (
        "nearby_allies_enemies" in missing_signals
        or "exact_teamfight_context" in missing_signals
    )
    if missing_team_context:
        action = _remove_overconfident_team_language(action, decision_point)
        reason = _remove_overconfident_team_language(reason, decision_point)
        risk = _remove_overconfident_team_language(risk, decision_point)

    if decision_point in {"LANING_FARM_CHECK", "FARMING_PHASE_PRESSURE", "LOW_HP"}:
        local_hint = _local_advice_hint_for_prompt(request)
        if local_hint:
            action = local_hint.get("action") or action
            reason = local_hint.get("reason") or reason

    cleaned = clean_recommendation_text(
        RecommendationResponse(
            action=action,
            reason=reason,
            risk=risk,
            priority=recommendation.priority,
            time_window=recommendation.time_window,
            source=recommendation.source,
        ),
        decision_point,
    )
    _validate_context_sensitive_text(cleaned, missing_signals, defaulted_fields)
    return cleaned


def _remove_missing_gold_language(text: str) -> str:
    cleaned = text
    replacements = {
        "Maintain lane gold": "Maintain farm pace",
        "maintain lane gold": "maintain farm pace",
        "lane gold": "farm pace",
        "Lane gold": "Farm pace",
        "gold flow": "farm pace",
        "Gold flow": "Farm pace",
        "gold income": "farm pace",
        "Gold income": "Farm pace",
    }
    for raw, replacement in replacements.items():
        cleaned = cleaned.replace(raw, replacement)
    cleaned = re.sub(r"\b\d+\s*gold\b", "farm", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bgold\b", "farm pace", cleaned, flags=re.IGNORECASE)
    return cleaned


def _remove_overconfident_team_language(text: str, decision_point: str) -> str:
    lowered = text.lower()
    banned = (
        "safe to fight",
        "safe to join",
        "team is ready",
        "no nearby fights",
        "no nearby enemies",
        "no enemies nearby",
    )
    if not any(phrase in lowered for phrase in banned):
        return text
    if decision_point == "OBJECTIVE_FIGHT_CHECK":
        return "Consider joining only if the fight is near a valuable objective."
    return text


def _validate_context_sensitive_text(
    recommendation: RecommendationResponse,
    missing_signals: set[str],
    defaulted_fields: set[str],
) -> None:
    combined = " ".join([recommendation.action, recommendation.reason, recommendation.risk]).lower()
    if ("gold" in missing_signals or "gold" in defaulted_fields) and re.search(r"\bgold\b", combined):
        raise LLMWordingGuardError("LLM output mentioned gold while gold signal is missing")

    if "nearby_allies_enemies" in missing_signals or "exact_teamfight_context" in missing_signals:
        banned = (
            "safe to fight",
            "safe to join",
            "team is ready",
            "no nearby fights",
            "no nearby enemies",
            "enemy is not nearby",
            "no enemies nearby",
        )
        if any(phrase in combined for phrase in banned):
            raise LLMWordingGuardError(
                "LLM output assumed unavailable teamfight or nearby-unit context"
            )

    action = recommendation.action.lower().strip()
    if any(phrase in action for phrase in BANNED_LLM_ACTION_PHRASES):
        raise LLMWordingGuardError("LLM output used banned coaching wording")


def _wording_change_count(
    before: RecommendationResponse,
    after: RecommendationResponse,
) -> int:
    return sum(
        1
        for field in ("action", "reason", "risk")
        if getattr(before, field).strip() != getattr(after, field).strip()
    )
