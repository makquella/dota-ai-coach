"""
Offline LLM model benchmark for Dota AI Coach.

Run manually from backend/:
    python scripts/benchmark_llm_models.py
"""

from __future__ import annotations

import csv
import json
import multiprocessing as mp
import os
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv


BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.decision_points import detect_decision_point  # noqa: E402
from app.gsi_state import normalize_gsi_payload  # noqa: E402
from app.llm_provider import OUTPUT_SCHEMA, OPENROUTER_CHAT_URL  # noqa: E402
from app.rag import retrieve_context  # noqa: E402
from app.schemas import GameSituationRequest  # noqa: E402


OPENROUTER_MODELS = (
    "openai/gpt-oss-120b:free",
    "deepseek/deepseek-v4-flash:free",
    "google/gemma-4-31b-it:free",
)
GROQ_MODELS = (
    "openai/gpt-oss-120b",
    "llama-3.3-70b-versatile",
    "openai/gpt-oss-20b",
)
GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_LLAMACPP_MODEL = "local-gpt-oss-20b"
DEFAULT_DELAY_SECONDS = 2.0
DEFAULT_MAX_TOKENS = 350
HARD_TIMEOUT_OVERHEAD_SECONDS = 1.0

REQUIRED_FIELDS = ["action", "reason", "risk", "priority", "time_window", "source"]
VALID_TIME_WINDOWS = {
    "immediate: next 10-15 seconds",
    "next 60-90 seconds",
    "reassess in 60 seconds",
}


@dataclass(frozen=True)
class ProviderConfig:
    name: str
    chat_url: str
    api_key_env: str | None
    default_models: tuple[str, ...]
    extra_headers: dict[str, str]


@dataclass
class Scenario:
    name: str
    state: GameSituationRequest
    expected_priority: str
    expected_time_window: str


def main() -> int:
    load_dotenv(BACKEND_DIR / ".env", override=False)
    load_dotenv(REPO_ROOT / ".env", override=False)

    provider = _get_provider_config()
    if provider is None:
        return 1

    api_key = os.getenv(provider.api_key_env, "").strip() if provider.api_key_env else ""
    if provider.api_key_env and not api_key:
        print(f"{provider.api_key_env} is missing. Add it to backend/.env or export it in your shell.")
        return 1

    timeout = _get_timeout()
    max_tokens = _get_max_tokens()
    delay_seconds = _get_delay_seconds()
    models = _get_models(provider.default_models)
    scenarios = _load_scenarios()
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    output_dir = BACKEND_DIR / "benchmark_results"
    output_dir.mkdir(parents=True, exist_ok=True)

    results: list[dict[str, Any]] = []
    for model_index, model in enumerate(models):
        for scenario in scenarios:
            result = _run_case(provider, api_key, model, scenario, timeout, max_tokens)
            results.append(result)
            _print_row(result)
            if not (model_index == len(models) - 1 and scenario == scenarios[-1]):
                time.sleep(delay_seconds)

    summary = _summarize(results, provider.name, models)
    ranking = _rank(summary)

    json_path = output_dir / f"llm_benchmark_{timestamp}.json"
    csv_path = output_dir / f"llm_benchmark_{timestamp}.csv"
    _write_json(
        json_path,
        provider.name,
        timeout,
        max_tokens,
        delay_seconds,
        models,
        scenarios,
        results,
        summary,
        ranking,
    )
    _write_csv(csv_path, summary)

    print()
    print(f"Detailed results: {json_path}")
    print(f"Summary CSV: {csv_path}")
    print()
    _print_ranking(ranking)
    return 0


def _get_provider_config() -> ProviderConfig | None:
    provider = os.getenv("BENCHMARK_PROVIDER", "openrouter").strip().lower()
    if provider == "openrouter":
        return ProviderConfig(
            name="openrouter",
            chat_url=OPENROUTER_CHAT_URL,
            api_key_env="OPENROUTER_API_KEY",
            default_models=OPENROUTER_MODELS,
            extra_headers={
                "HTTP-Referer": "http://127.0.0.1:8000",
                "X-Title": "Dota AI Coach Benchmark",
            },
        )
    if provider == "groq":
        return ProviderConfig(
            name="groq",
            chat_url=GROQ_CHAT_URL,
            api_key_env="GROQ_API_KEY",
            default_models=GROQ_MODELS,
            extra_headers={},
        )
    if provider == "llamacpp":
        base_url = os.getenv("LLAMACPP_BASE_URL", "http://127.0.0.1:8080").strip().rstrip("/")
        model = os.getenv("LLAMACPP_MODEL", DEFAULT_LLAMACPP_MODEL).strip() or DEFAULT_LLAMACPP_MODEL
        return ProviderConfig(
            name="llamacpp",
            chat_url=f"{base_url}/v1/chat/completions",
            api_key_env=None,
            default_models=(model,),
            extra_headers={},
        )

    print("Unsupported BENCHMARK_PROVIDER. Use 'openrouter', 'groq', or 'llamacpp'.")
    return None


def _get_timeout() -> float:
    try:
        return max(1.0, float(os.getenv("BENCHMARK_TIMEOUT", "20")))
    except ValueError:
        return 20.0


def _get_max_tokens() -> int:
    try:
        return max(1, int(os.getenv("BENCHMARK_MAX_TOKENS", str(DEFAULT_MAX_TOKENS))))
    except ValueError:
        return DEFAULT_MAX_TOKENS


def _get_delay_seconds() -> float:
    try:
        return max(0.0, float(os.getenv("BENCHMARK_DELAY_SECONDS", str(DEFAULT_DELAY_SECONDS))))
    except ValueError:
        return DEFAULT_DELAY_SECONDS


def _get_models(default_models: tuple[str, ...]) -> list[str]:
    raw_models = os.getenv("BENCHMARK_MODELS", "").strip()
    if not raw_models:
        return list(default_models)

    models = [model.strip() for model in raw_models.split(",") if model.strip()]
    return models or list(default_models)


def _load_scenarios() -> list[Scenario]:
    return [
        Scenario(
            name="antimage_pressure",
            state=_load_direct_scenario(REPO_ROOT / "data/scenarios/antimage_14min_pressure.json"),
            expected_priority="high",
            expected_time_window="next 60-90 seconds",
        ),
        Scenario(
            name="juggernaut_low_hp",
            state=_load_direct_scenario(REPO_ROOT / "data/scenarios/juggernaut_low_hp.json"),
            expected_priority="high",
            expected_time_window="immediate: next 10-15 seconds",
        ),
        Scenario(
            name="luna_objective_fight",
            state=_load_direct_scenario(REPO_ROOT / "data/scenarios/luna_farm_or_fight.json"),
            expected_priority="medium",
            expected_time_window="next 60-90 seconds",
        ),
        Scenario(
            name="calm_farming",
            state=_load_calm_farming_scenario(),
            expected_priority="low",
            expected_time_window="reassess in 60 seconds",
        ),
    ]


def _load_direct_scenario(path: Path) -> GameSituationRequest:
    return GameSituationRequest(**json.loads(path.read_text(encoding="utf-8")))


def _load_calm_farming_scenario() -> GameSituationRequest:
    path = REPO_ROOT / "data/gsi_samples/calm_farming_antimage.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return GameSituationRequest(**normalize_gsi_payload(payload))
    except (OSError, ValueError, TypeError):
        return GameSituationRequest(
            hero="Anti-Mage",
            role="carry",
            minute=20,
            level=14,
            gold=1200,
            items=["Power Treads", "Battle Fury"],
            hp_percent=82,
            game_state="calm_farming",
            team_status="all_alive",
        )


def _run_case(
    provider: ProviderConfig,
    api_key: str,
    model: str,
    scenario: Scenario,
    timeout: float,
    max_tokens: int,
) -> dict[str, Any]:
    state = scenario.state
    decision_point = detect_decision_point(state.model_dump())
    rag_context = _retrieve_rag_context(state)
    started = time.perf_counter()

    raw_content = ""
    raw_error_body = ""
    parsed: dict[str, Any] | None = None
    error = ""
    http_status: int | None = None

    payload = _build_payload(model, state, decision_point, rag_context, max_tokens)
    call_result = _call_provider_with_hard_timeout(provider, api_key, payload, timeout)
    response_time = time.perf_counter() - started

    if response_time > timeout:
        error = "timeout_error"
        raw_error_body = call_result.get(
            "raw_error_body",
            f"elapsed {response_time:.3f}s exceeded BENCHMARK_TIMEOUT {timeout:g}s",
        )
        http_status = call_result.get("status_code")
    elif call_result.get("error"):
        error = call_result["error"]
        raw_error_body = call_result.get("raw_error_body", "")
        http_status = call_result.get("status_code")
    else:
        try:
            response_json = call_result["response_json"]
            raw_content = _extract_content(response_json)
            parsed = _parse_strict_json(raw_content)
        except json.JSONDecodeError as exc:
            error = "invalid_json"
            raw_error_body = str(exc)
        except ValueError as exc:
            error = str(exc)
            raw_error_body = raw_content or str(call_result.get("response_json", ""))

    score, checks, penalties = _score_result(parsed, raw_content, scenario, response_time)
    valid_json = checks["valid_json"]
    required_fields = checks["required_fields"]
    if parsed is not None and not required_fields and not error:
        error = "missing_fields"

    return {
        "provider": provider.name,
        "model": model,
        "scenario": scenario.name,
        "decision_point": decision_point,
        "response_time": round(response_time, 3),
        "valid_json": valid_json,
        "required_fields_present": required_fields,
        "score": score,
        "priority": parsed.get("priority") if parsed else None,
        "source": parsed.get("source") if parsed else None,
        "error": error,
        "availability": _availability_label(error),
        "http_status": http_status,
        "raw_error_body": raw_error_body,
        "output": parsed,
        "raw_content": raw_content,
        "checks": checks,
        "penalties": penalties,
        "expected_priority": scenario.expected_priority,
        "expected_time_window": scenario.expected_time_window,
    }


def _call_provider_with_hard_timeout(
    provider: ProviderConfig,
    api_key: str,
    payload: dict[str, Any],
    timeout: float,
) -> dict[str, Any]:
    queue: mp.Queue = mp.Queue(maxsize=1)
    process = mp.Process(
        target=_provider_worker,
        args=(queue, provider, api_key, payload, timeout),
        daemon=True,
    )
    process.start()
    process.join(timeout + HARD_TIMEOUT_OVERHEAD_SECONDS)

    if process.is_alive():
        process.terminate()
        process.join(0.5)
        return {"error": "timeout_error", "raw_error_body": f"hard timeout after {timeout:g}s"}

    if queue.empty():
        return {"error": "request_error", "raw_error_body": "worker returned no result"}
    return queue.get()


def _provider_worker(
    queue: mp.Queue,
    provider: ProviderConfig,
    api_key: str,
    payload: dict[str, Any],
    timeout: float,
) -> None:
    def clean_error(value: object) -> str:
        text = str(value)
        if api_key:
            text = text.replace(api_key, "[redacted_api_key]")
        for marker in ("Authorization", "authorization", "Bearer", "bearer"):
            text = text.replace(marker, "[redacted_auth]")
        return text[:4000]

    try:
        headers = {"Content-Type": "application/json", **provider.extra_headers}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        response = requests.post(
            provider.chat_url,
            headers=headers,
            json=payload,
            timeout=(5, timeout),
            stream=False,
        )
        if response.status_code >= 400:
            queue.put(
                {
                    "error": _http_error_label(response.status_code, provider.name),
                    "status_code": response.status_code,
                    "raw_error_body": clean_error(response.text),
                }
            )
            return

        queue.put({"response_json": response.json()})
    except requests.Timeout:
        queue.put({"error": "timeout_error", "raw_error_body": f"requests timeout after {timeout:g}s"})
    except requests.exceptions.JSONDecodeError as exc:
        queue.put({"error": "invalid_json", "raw_error_body": clean_error(exc)})
    except requests.HTTPError as exc:
        response = exc.response
        status_code = response.status_code if response is not None else None
        queue.put(
            {
                "error": _http_error_label(status_code, provider.name),
                "status_code": status_code,
                "raw_error_body": clean_error(response.text if response is not None else exc),
            }
        )
    except requests.RequestException as exc:
        queue.put({"error": "request_error", "raw_error_body": clean_error(exc)})


def _http_error_label(status_code: int | None, provider_name: str) -> str:
    if provider_name == "openrouter" and status_code == 402:
        return "http_error_402_insufficient_credits"
    if provider_name == "openrouter" and status_code == 429:
        return "http_error_429_rate_limited"
    return f"http_error_{status_code or 'unknown'}"


def _availability_label(error: str) -> str:
    if error.startswith("http_error_402"):
        return "unavailable"
    if error.startswith("http_error_429"):
        return "rate_limited"
    return ""


def _retrieve_rag_context(state: GameSituationRequest) -> list[str]:
    query = (
        f"{state.hero} {state.role} {state.game_state} {state.team_status} "
        f"minute {state.minute} level {state.level} hp {state.hp_percent} "
        f"gold {state.gold} " + " ".join(state.items)
    )
    return retrieve_context(
        query,
        hero=state.hero,
        game_state=state.game_state,
        owned_items=state.items,
    )


def _build_payload(
    model: str,
    state: GameSituationRequest,
    decision_point: str,
    rag_context: list[str],
    max_tokens: int,
) -> dict[str, Any]:
    return {
        "model": model,
        "temperature": 0.2,
        "max_tokens": max_tokens,
        "stream": False,
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a conservative Dota 2 carry coach. "
                    "Do not overload the player. Do not act as autopilot. "
                    "Do not use chain-of-thought. Return strict JSON only."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "rules": [
                            "Be conservative.",
                            "Do not overload the player.",
                            "Give only one main action.",
                            "Give one short reason.",
                            "Do not suggest high-risk fights unless objective value is clear.",
                            "If uncertain, recommend farming, resetting, or waiting.",
                            "Do not recommend item builds or purchases.",
                            "Never give mechanical execution commands.",
                            "Do not act as autopilot.",
                            "Use coaching tone.",
                            "Keep action and reason short.",
                            "Return only JSON.",
                        ],
                        "examples": [
                            {
                                "input": {"hp_percent": 25, "decision_point": "LOW_HP"},
                                "output": {
                                    "action": "Retreat and reset immediately.",
                                    "reason": "Low HP makes any continued fight too risky.",
                                    "risk": "High risk of dying if you stay.",
                                    "priority": "high",
                                    "time_window": "immediate: next 10-15 seconds",
                                    "source": "llm",
                                },
                            },
                            {
                                "input": {"minute": 14, "game_state": "enemy_pressure_mid"},
                                "output": {
                                    "action": "Avoid the fight and farm safe camps.",
                                    "reason": "Early pressure is not worth risking your item timing.",
                                    "risk": "Medium risk if you contest pressure.",
                                    "priority": "high",
                                    "time_window": "next 60-90 seconds",
                                    "source": "llm",
                                },
                            },
                            {
                                "input": {"game_state": "calm_farming"},
                                "output": {
                                    "action": "Keep farming efficiently.",
                                    "reason": "No urgent fight or objective requires you now.",
                                    "risk": "Low if you avoid unnecessary fights.",
                                    "priority": "low",
                                    "time_window": "reassess in 60 seconds",
                                    "source": "llm",
                                },
                            },
                        ],
                        "validated_normalized_game_state": state.model_dump(),
                        "decision_point": decision_point,
                        "rag_context": rag_context,
                        "required_output_json_schema": OUTPUT_SCHEMA,
                    },
                    ensure_ascii=False,
                ),
            },
        ],
    }


def _extract_content(response_json: dict[str, Any]) -> str:
    choices = response_json.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ValueError("missing choices")
    message = choices[0].get("message")
    if not isinstance(message, dict):
        raise ValueError("missing message")
    content = message.get("content")
    if not isinstance(content, str):
        raise ValueError("missing string content")
    return content.strip()


def _parse_strict_json(content: str) -> dict[str, Any]:
    parsed = json.loads(content)
    if not isinstance(parsed, dict):
        raise ValueError("model output is not a JSON object")
    return parsed


def _score_result(
    parsed: dict[str, Any] | None,
    raw_content: str,
    scenario: Scenario,
    response_time: float,
) -> tuple[int, dict[str, bool], list[str]]:
    score = 0
    penalties: list[str] = []
    valid_json = parsed is not None
    required_fields = valid_json and all(field in parsed for field in REQUIRED_FIELDS)
    action = str(parsed.get("action", "")) if parsed else ""
    reason = str(parsed.get("reason", "")) if parsed else ""
    combined = f"{action} {reason}".lower()

    if valid_json:
        score += 2
    if required_fields:
        score += 2
    if valid_json and parsed.get("priority") == scenario.expected_priority:
        score += 2
    if valid_json and parsed.get("time_window") == scenario.expected_time_window:
        score += 1
    if action and len(action) < 160:
        score += 1
    if reason and len(reason) < 280:
        score += 1
    if _is_conservative(action, reason, scenario):
        score += 1

    if not valid_json:
        score -= 2
        penalties.append("invalid_json")
    if scenario.state.hp_percent <= 35 and _suggests_fighting(combined):
        score -= 3
        penalties.append("fight_suggestion_low_hp")
    if _is_pressure_scenario(scenario) and _ignores_pressure(combined):
        score -= 2
        penalties.append("ignores_early_pressure")
    if _contains_chain_of_thought(raw_content):
        score -= 2
        penalties.append("chain_of_thought")
    if response_time > 20:
        score -= 3
        penalties.append("slow_over_20s")
    elif response_time > 10:
        score -= 1
        penalties.append("slow_over_10s")

    checks = {
        "valid_json": valid_json,
        "required_fields": required_fields,
        "priority_match": valid_json and parsed.get("priority") == scenario.expected_priority,
        "time_window_match": valid_json and parsed.get("time_window") == scenario.expected_time_window,
        "action_concise": bool(action) and len(action) < 160,
        "reason_concise": bool(reason) and len(reason) < 280,
        "conservative_action": _is_conservative(action, reason, scenario),
    }
    return max(0, min(10, score)), checks, penalties


def _is_pressure_scenario(scenario: Scenario) -> bool:
    state = scenario.state
    return state.minute < 18 and "pressure" in state.game_state.lower()


def _suggests_fighting(text: str) -> bool:
    fight_terms = ["fight", "engage", "commit", "contest", "join", "attack", "initiate"]
    safety_terms = ["avoid", "only if", "do not", "don't", "retreat", "reset", "farm"]
    return any(term in text for term in fight_terms) and not any(term in text for term in safety_terms)


def _ignores_pressure(text: str) -> bool:
    pressure_terms = ["avoid", "retreat", "reset", "safe", "farm", "jungle", "pull", "back"]
    return not any(term in text for term in pressure_terms)


def _is_conservative(action: str, reason: str, scenario: Scenario) -> bool:
    text = f"{action} {reason}".lower()
    conservative_terms = [
        "avoid",
        "retreat",
        "reset",
        "farm",
        "safe",
        "wait",
        "objective",
        "only if",
        "reassess",
    ]
    if scenario.state.hp_percent <= 35 or _is_pressure_scenario(scenario):
        return not _suggests_fighting(text) and any(term in text for term in conservative_terms)
    return any(term in text for term in conservative_terms)


def _contains_chain_of_thought(content: str) -> bool:
    lowered = content.lower()
    markers = [
        "chain of thought",
        "step-by-step",
        "step 1",
        "first,",
        "second,",
        "let's think",
        "my reasoning",
    ]
    return any(marker in lowered for marker in markers)


def _summarize(results: list[dict[str, Any]], provider_name: str, models: list[str]) -> list[dict[str, Any]]:
    summary = []
    for model in models:
        model_results = [
            result for result in results
            if result["provider"] == provider_name and result["model"] == model
        ]
        count = len(model_results)
        valid_count = sum(1 for result in model_results if result["valid_json"])
        error_count = sum(1 for result in model_results if result["error"])
        avg_score = sum(result["score"] for result in model_results) / count
        avg_time = sum(result["response_time"] for result in model_results) / count
        summary.append(
            {
                "provider": provider_name,
                "model": model,
                "average_score": round(avg_score, 2),
                "average_response_time": round(avg_time, 3),
                "valid_json_rate": round(valid_count / count, 3),
                "fallback_error_count": error_count,
            }
        )
    return summary


def _rank(summary: list[dict[str, Any]]) -> dict[str, Any]:
    best_score = max(summary, key=lambda item: item["average_score"])
    fastest = min(summary, key=lambda item: item["average_response_time"])
    best_json = max(summary, key=lambda item: item["valid_json_rate"])
    eligible = [
        item for item in summary
        if item["valid_json_rate"] >= 0.8 and item["average_response_time"] <= 10
    ]
    recommended = max(eligible, key=lambda item: item["average_score"]) if eligible else None
    return {
        "best_average_score": best_score,
        "fastest_average_response": fastest,
        "best_valid_json_rate": best_json,
        "recommended_model_for_live_overlay": (
            _summary_label(recommended) if recommended else "Keep rule-based fallback for live mode"
        ),
    }


def _summary_label(item: dict[str, Any]) -> str:
    return f"{item['provider']}:{item['model']}"


def _print_row(result: dict[str, Any]) -> None:
    if not hasattr(_print_row, "printed_header"):
        print("provider | model | scenario | valid_json | response_time | score | priority | source/error")
        print("-" * 125)
        _print_row.printed_header = True

    source_or_error = result["error"] or result["source"] or "unknown"
    print(
        f"{result['provider']} | {result['model']} | {result['scenario']} | {result['valid_json']} | "
        f"{result['response_time']:.3f}s | {result['score']} | "
        f"{result['priority'] or '-'} | {source_or_error}"
    )


def _write_json(
    path: Path,
    provider_name: str,
    timeout: float,
    max_tokens: int,
    delay_seconds: float,
    models: list[str],
    scenarios: list[Scenario],
    results: list[dict[str, Any]],
    summary: list[dict[str, Any]],
    ranking: dict[str, Any],
) -> None:
    payload = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "benchmark_provider": provider_name,
        "benchmark_timeout": timeout,
        "benchmark_max_tokens": max_tokens,
        "benchmark_delay_seconds": delay_seconds,
        "models": models,
        "scenarios": [
            {
                "name": scenario.name,
                "expected_priority": scenario.expected_priority,
                "expected_time_window": scenario.expected_time_window,
                "state": scenario.state.model_dump(),
            }
            for scenario in scenarios
        ],
        "results": results,
        "summary": summary,
        "ranking": ranking,
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def _write_csv(path: Path, summary: list[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=[
                "provider",
                "model",
                "average_score",
                "average_response_time",
                "valid_json_rate",
                "fallback_error_count",
            ],
        )
        writer.writeheader()
        writer.writerows(summary)


def _print_ranking(ranking: dict[str, Any]) -> None:
    print("Final ranking")
    print(f"Best average score: {_summary_label(ranking['best_average_score'])}")
    print(f"Fastest average response: {_summary_label(ranking['fastest_average_response'])}")
    print(f"Best valid JSON rate: {_summary_label(ranking['best_valid_json_rate'])}")
    print(f"Recommended model for live overlay: {ranking['recommended_model_for_live_overlay']}")


if __name__ == "__main__":
    raise SystemExit(main())
