"""
Simulate the GSI overlay advice loop over a prepared 40-minute carry game.

Run from backend/:
    python scripts/simulate_match_advice.py
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from collections import Counter
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.advice_scheduler import (  # noqa: E402
    DEATH_REVIEW_DECISIONS,
    AdviceScheduler,
    ScheduledAdvice,
    _compact_recommendation,
    _is_safe_recommendation,
)
from app.advice_policy import apply_advice_policy, build_advice_policy  # noqa: E402
from app.advice_text import clean_recommendation_text  # noqa: E402
from app.advice_ux_policy import apply_ux_policy  # noqa: E402
from app.config import LLM_TIMEOUT  # noqa: E402
from app.decision_points import detect_decision_point  # noqa: E402
from app.laning_coach import laning_context_for_review  # noqa: E402
from app.llm_provider import generate_llm_recommendation  # noqa: E402
from app.post_laning_coach import post_laning_context_for_review  # noqa: E402
from app.rag import retrieve_context  # noqa: E402
from app.schemas import GameSituationRequest  # noqa: E402
from app.signal_capabilities import capability_summary  # noqa: E402


DEFAULT_SIMULATION_PATH = REPO_ROOT / "data/match_simulations/carry_match_40min.jsonl"
RESULTS_DIR = BACKEND_DIR / "simulation_results"
EXPECTED_HINT_RANGE = (40, 50)
REVIEW_FIELDS = [
    "index",
    "timestamp_seconds",
    "minute",
    "hero",
    "role",
    "hp_percent",
    "level",
    "gold",
    "total_earned_gold",
    "items",
    "game_state",
    "team_status",
    "source_type",
    "context_confidence",
    "capability_source",
    "available_signals",
    "missing_signals",
    "partial_signals",
    "replay_exact_fields",
    "replay_defaulted_fields",
    "replay_meaningful_context",
    "replay_damage_pressure_window",
    "farm_quality",
    "expected_lh_range",
    "lh_deficit_or_status",
    "hp_pressure_state",
    "hp_pressure_reason",
    "position_zone",
    "position_risk",
    "position_reason",
    "laning_category",
    "laning_advice_reason",
    "repeated_laning_suppressed_count",
    "post_laning_category",
    "post_laning_reason",
    "repeated_post_laning_suppressed_count",
    "repeated_objective_suppressed_count",
    "low_hp_episode_id",
    "repeated_low_hp_suppressed_count",
    "selected_team",
    "teamfight_result",
    "allied_deaths_in_fight",
    "enemy_deaths_in_fight",
    "recent_allied_deaths",
    "recent_enemy_deaths",
    "objective_type",
    "objective_team",
    "objective_for_selected_team",
    "objective_context",
    "event_context",
    "near_player_death",
    "near_teamfight",
    "near_objective",
    "recent_item_purchase",
    "item_timing_category",
    "gold_delta",
    "lh_delta",
    "decision_point",
    "action_type",
    "advice_mode",
    "game_time_gap_since_previous_advice",
    "suppressed_by_game_time_spacing",
    "source",
    "llm_used",
    "fallback_used",
    "stale_response",
    "suppressed_reason",
    "action",
    "reason",
    "risk",
    "priority",
    "time_window",
    "player_rating",
    "player_comment",
]


def main() -> int:
    args = _parse_args()
    simulation_path = Path(args.simulation_file)
    if not simulation_path.exists():
        print(f"Simulation file not found: {simulation_path}")
        return 1

    use_llm = _env_bool("SIMULATION_USE_LLM", default=False)
    llm_blocking = bool(args.llm_blocking or _env_bool("SIMULATION_LLM_BLOCKING", default=False))
    export_review = _env_bool("SIMULATION_EXPORT_REVIEW", default=True)
    review_only_shown = _env_bool("SIMULATION_REVIEW_ONLY_SHOWN", default=True)
    scheduler = AdviceScheduler(enable_llm=False if llm_blocking else use_llm)
    blocking_llm_metrics = _new_blocking_llm_metrics()
    base_time = datetime(2026, 1, 1, tzinfo=timezone.utc)

    total_states = 0
    min_timestamp_seconds: int | None = None
    max_timestamp_seconds = 0
    advice_buckets: Counter[int] = Counter()
    advice_modes: Counter[str] = Counter()
    statuses: Counter[str] = Counter()
    suppressed: Counter[str] = Counter()
    decision_points: Counter[str] = Counter()
    source_types: Counter[str] = Counter()
    context_confidences: Counter[str] = Counter()
    pinned_advice_count = 0
    review_rows: list[dict[str, Any]] = []

    entries = _load_jsonl(simulation_path)
    for index, entry in enumerate(entries):
        total_states += 1
        timestamp_seconds = int(entry.get("timestamp_seconds", 0))
        if min_timestamp_seconds is None:
            min_timestamp_seconds = timestamp_seconds
        min_timestamp_seconds = min(min_timestamp_seconds, timestamp_seconds)
        max_timestamp_seconds = max(max_timestamp_seconds, timestamp_seconds)
        state_data = _state_from_entry(entry)
        state_data = _ensure_signal_capabilities(state_data, simulation_path)
        source_types[_source_type_from_state(state_data, simulation_path)] += 1
        context_confidences[_context_confidence_from_state(state_data)] += 1

        request = GameSituationRequest(**state_data)
        decision_point = detect_decision_point(request.model_dump())
        policy = build_advice_policy(request, decision_point)
        decision_points[decision_point] += 1
        rag_context = _retrieve_rag_context(request)
        now = base_time + timedelta(seconds=timestamp_seconds)
        stats_before = scheduler.stats(now)
        if decision_point in {"NO_ADVICE", "SOFT_STATUS"}:
            scheduler.observe_state(request.model_dump(), decision_point, now=now)
            active = scheduler.active_advice_for_state(request.model_dump(), decision_point, now=now)
            result = active or _status_result(
                status="monitoring" if decision_point == "SOFT_STATUS" else "no_advice",
                decision_point=decision_point,
                advice_count=scheduler.stats(now)["advice_count"],
                suppressed_reason="no_advice" if decision_point == "NO_ADVICE" else None,
            )
        else:
            result = scheduler.evaluate(request, decision_point, rag_context, now=now)

        statuses[result.status] += 1
        if result.is_pinned:
            pinned_advice_count += 1
        if result.suppressed_reason:
            suppressed[result.suppressed_reason] += 1
        if result.new_advice:
            relative_seconds = timestamp_seconds - (min_timestamp_seconds or 0)
            advice_buckets[_bucket_for_elapsed_seconds(relative_seconds)] += 1
            advice_modes[result.advice_mode] += 1
        blocking_snapshot = None
        blocking_llm_applied = False
        if use_llm and llm_blocking:
            result, blocking_llm_applied, blocking_snapshot = _apply_blocking_llm_refinement(
                result=result,
                request=request,
                decision_point=decision_point,
                rag_context=rag_context,
                policy=policy,
                metrics=blocking_llm_metrics,
            )
        elif use_llm and scheduler.stats(now)["llm_call_count"] > stats_before["llm_call_count"]:
            scheduler.wait_for_pending(timeout=_llm_wait_budget(entries, index, timestamp_seconds))
        stats_after = scheduler.stats(now)
        llm_applied = (
            blocking_llm_applied
            if llm_blocking
            else stats_after["llm_applied_count"] > stats_before["llm_applied_count"]
        )
        review_rows.append(
            _build_review_row(
                index=index + 1,
                timestamp_seconds=timestamp_seconds,
                request=request,
                decision_point=decision_point,
                action_type=policy["action_type"],
                result=result,
                stale_response=(
                    False
                    if llm_blocking
                    else stats_after["stale_llm_count"] > stats_before["stale_llm_count"]
                ),
                llm_applied=llm_applied,
                latest_snapshot=(
                    blocking_snapshot
                    if blocking_snapshot is not None
                    else scheduler.latest_advice_snapshot() if llm_applied else None
                ),
                repeated_laning_suppressed_count=stats_after["repeated_laning_suppressed_count"],
                repeated_post_laning_suppressed_count=stats_after["repeated_post_laning_suppressed_count"],
                repeated_objective_suppressed_count=stats_after["repeated_objective_suppressed_count"],
                repeated_low_hp_suppressed_count=stats_after["repeated_low_hp_suppressed_count"],
            )
        )

    if use_llm and not llm_blocking:
        scheduler.wait_for_pending(timeout=LLM_TIMEOUT + 2.0)

    stats = scheduler.stats(base_time + timedelta(seconds=max_timestamp_seconds))
    report = _build_report(
        simulation_path=simulation_path,
        total_states=total_states,
        min_timestamp_seconds=min_timestamp_seconds or 0,
        max_timestamp_seconds=max_timestamp_seconds,
        advice_buckets=advice_buckets,
        advice_modes=advice_modes,
        statuses=statuses,
        suppressed=suppressed,
        decision_points=decision_points,
        source_types=source_types,
        context_confidences=context_confidences,
        stats=stats,
        use_llm=use_llm,
        llm_blocking=llm_blocking,
        blocking_llm_metrics=blocking_llm_metrics,
        export_review=export_review,
        review_only_shown=review_only_shown,
        review_row_count=len(review_rows),
        pinned_advice_count=pinned_advice_count,
    )
    report_path = _write_report(report)
    review_csv_path = None
    review_md_path = None
    if export_review:
        exported_rows = [
            row for row in review_rows
            if not review_only_shown or row["shown_advice"]
        ]
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        review_csv_path = _write_review_csv(exported_rows, timestamp)
        review_md_path = _write_review_markdown(exported_rows, timestamp)

    _print_report(report, report_path, review_csv_path, review_md_path)
    return 0


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Simulate overlay advice over a prepared match JSONL file.",
    )
    parser.add_argument(
        "--simulation-file",
        default=os.getenv("MATCH_SIMULATION_PATH", str(DEFAULT_SIMULATION_PATH)),
        help="Path to a match simulation JSONL file.",
    )
    parser.add_argument(
        "--llm-blocking",
        action="store_true",
        help="Call the optional LLM synchronously for eligible full advice events.",
    )
    return parser.parse_args()


def _state_from_entry(entry: dict[str, Any]) -> dict[str, Any]:
    state = entry.get("state")
    if isinstance(state, dict):
        return state
    return {
        key: value
        for key, value in entry.items()
        if key != "timestamp_seconds"
    }


def _ensure_signal_capabilities(state: dict[str, Any], simulation_path: Path) -> dict[str, Any]:
    extra_context = state.get("extra_context") if isinstance(state.get("extra_context"), dict) else {}
    source_type = _source_type_from_state(state, simulation_path)
    if extra_context.get("available_signals") and extra_context.get("missing_signals"):
        return state

    enriched = dict(state)
    enriched_extra = dict(extra_context)
    enriched_extra.setdefault("source_type", source_type)
    enriched_extra.update(capability_summary(source_type))
    enriched.setdefault("extra_context", enriched_extra)
    enriched["extra_context"] = enriched_extra
    return enriched


def _status_result(
    *,
    status: str,
    decision_point: str,
    advice_count: int,
    suppressed_reason: str | None,
) -> ScheduledAdvice:
    return ScheduledAdvice(
        status=status,  # type: ignore[arg-type]
        decision_point=decision_point,
        recommendation=None,
        advice_count=advice_count,
        llm_used=False,
        source="none",
        last_updated=None,
        next_allowed_advice_in_seconds=0,
        new_advice=False,
        advice_mode="status",
        suppressed_reason=suppressed_reason,
    )


def _new_blocking_llm_metrics() -> dict[str, Any]:
    return {
        "llm_call_count": 0,
        "llm_applied_count": 0,
        "llm_timeout_count": 0,
        "llm_invalid_count": 0,
        "llm_valid_but_rejected_count": 0,
        "llm_skipped_by_policy_count": 0,
        "llm_wording_guard_applied_count": 0,
        "llm_wording_guard_fallback_count": 0,
        "llm_latencies": [],
    }


def _apply_blocking_llm_refinement(
    *,
    result: ScheduledAdvice,
    request: GameSituationRequest,
    decision_point: str,
    rag_context: list[str],
    policy: dict[str, Any],
    metrics: dict[str, Any],
) -> tuple[ScheduledAdvice, bool, dict[str, Any] | None]:
    if not result.new_advice or result.recommendation is None:
        return result, False, None

    if _llm_skipped_by_policy(decision_point, result.advice_mode):
        metrics["llm_skipped_by_policy_count"] += 1
        return result, False, None

    metrics["llm_call_count"] += 1
    started = time.perf_counter()
    llm_result = generate_llm_recommendation(request, decision_point, rag_context)
    latency = time.perf_counter() - started
    metrics["llm_latencies"].append(latency)
    metrics["llm_wording_guard_applied_count"] += llm_result.wording_guard_applied_count
    metrics["llm_wording_guard_fallback_count"] += llm_result.wording_guard_fallback_count

    if llm_result.recommendation is None:
        _record_blocking_llm_failure(metrics, llm_result.error)
        return result, False, None

    recommendation = apply_advice_policy(llm_result.recommendation, policy)
    recommendation = _compact_recommendation(recommendation, decision_point)
    ux_result = apply_ux_policy(
        recommendation,
        decision_point,
        [],
        action_type=policy["action_type"],
    )
    if ux_result["recommendation"] is None:
        metrics["llm_valid_but_rejected_count"] += 1
        return result, False, None

    recommendation = clean_recommendation_text(ux_result["recommendation"], decision_point)
    if not _is_safe_recommendation(recommendation, decision_point):
        metrics["llm_valid_but_rejected_count"] += 1
        return result, False, None

    metrics["llm_applied_count"] += 1
    updated_result = replace(
        result,
        recommendation=recommendation,
        llm_used=True,
        source="llm",
        last_visible_advice=recommendation.model_dump(),
    )
    return (
        updated_result,
        True,
        {
            "recommendation": recommendation.model_dump(),
            "source": "llm",
            "llm_used": True,
            "advice_mode": result.advice_mode,
            "last_updated": result.last_updated,
        },
    )


def _llm_skipped_by_policy(decision_point: str, advice_mode: str) -> bool:
    if advice_mode == "status":
        return True
    return decision_point in {"NO_ADVICE", "SOFT_STATUS", "LOW_HP", *DEATH_REVIEW_DECISIONS}


def _record_blocking_llm_failure(metrics: dict[str, Any], error: str | None) -> None:
    error_text = (error or "").lower()
    if "timed out" in error_text or "timeout" in error_text:
        metrics["llm_timeout_count"] += 1
        return
    metrics["llm_invalid_count"] += 1


def _source_type_from_state(state: dict[str, Any], simulation_path: Path) -> str:
    extra_context = state.get("extra_context") if isinstance(state.get("extra_context"), dict) else {}
    source_type = str(extra_context.get("source_type") or state.get("source_type") or "").strip()
    if source_type:
        return source_type

    name = simulation_path.name.lower()
    if "replay_gsi_like" in name:
        return "replay_gsi_like"
    if "opendota" in name:
        return "opendota"
    if "gsi" in name:
        return "gsi_live"
    return "synthetic"


def _context_confidence_from_state(state: dict[str, Any]) -> str:
    extra_context = state.get("extra_context") if isinstance(state.get("extra_context"), dict) else {}
    confidence = str(extra_context.get("context_confidence") or state.get("context_confidence") or "").strip().lower()
    return confidence if confidence in {"low", "medium", "high"} else "unknown"


def _llm_wait_budget(entries: list[dict[str, Any]], index: int, timestamp_seconds: int) -> float:
    if index + 1 >= len(entries):
        return LLM_TIMEOUT + 2.0

    next_timestamp = int(entries[index + 1].get("timestamp_seconds", timestamp_seconds))
    simulated_gap = max(0.0, float(next_timestamp - timestamp_seconds))
    return min(LLM_TIMEOUT + 2.0, simulated_gap)


def _build_review_row(
    *,
    index: int,
    timestamp_seconds: int,
    request: GameSituationRequest,
    decision_point: str,
    action_type: str,
    result: Any,
    stale_response: bool,
    llm_applied: bool,
    latest_snapshot: dict[str, Any] | None,
    repeated_laning_suppressed_count: int,
    repeated_post_laning_suppressed_count: int,
    repeated_objective_suppressed_count: int,
    repeated_low_hp_suppressed_count: int,
) -> dict[str, Any]:
    recommendation = result.recommendation
    refined = latest_snapshot.get("recommendation") if latest_snapshot else None
    if isinstance(refined, dict):
        action = refined.get("action", "")
        reason = refined.get("reason", "")
        risk = refined.get("risk", "")
        priority = refined.get("priority", "")
        time_window = refined.get("time_window", "")
    elif recommendation is None:
        action = ""
        reason = ""
        risk = ""
        priority = ""
        time_window = ""
    else:
        action = recommendation.action
        reason = recommendation.reason
        risk = recommendation.risk
        priority = recommendation.priority
        time_window = recommendation.time_window

    source = latest_snapshot.get("source") if latest_snapshot else result.source
    llm_used = bool(result.llm_used or llm_applied or (latest_snapshot and latest_snapshot.get("llm_used")))
    if llm_applied:
        source = "llm"
    extra_context = request.extra_context if isinstance(request.extra_context, dict) else {}
    laning_review = laning_context_for_review(request, decision_point)
    post_laning_review = post_laning_context_for_review(request, decision_point)
    review_gold = _review_gold_value(request.gold, extra_context)

    return {
        "index": index,
        "timestamp_seconds": timestamp_seconds,
        "minute": request.minute,
        "hero": request.hero,
        "role": request.role,
        "hp_percent": request.hp_percent,
        "level": request.level,
        "gold": review_gold,
        "total_earned_gold": extra_context.get("total_earned_gold", ""),
        "items": "; ".join(request.items),
        "game_state": request.game_state,
        "team_status": request.team_status,
        "source_type": extra_context.get("source_type", ""),
        "context_confidence": extra_context.get("context_confidence", ""),
        "capability_source": extra_context.get("capability_source", ""),
        "available_signals": "; ".join(extra_context.get("available_signals") or []),
        "missing_signals": "; ".join(extra_context.get("missing_signals") or []),
        "partial_signals": "; ".join(extra_context.get("partial_signals") or []),
        "replay_exact_fields": "; ".join(extra_context.get("replay_exact_fields") or []),
        "replay_defaulted_fields": "; ".join(extra_context.get("replay_defaulted_fields") or []),
        "replay_meaningful_context": extra_context.get("replay_meaningful_context", ""),
        "replay_damage_pressure_window": extra_context.get("replay_damage_pressure_window", ""),
        "farm_quality": extra_context.get("farm_quality", ""),
        "expected_lh_range": _format_range(extra_context.get("expected_lh_range")),
        "lh_deficit_or_status": extra_context.get("lh_deficit_or_status", ""),
        "hp_pressure_state": extra_context.get("hp_pressure_state", ""),
        "hp_pressure_reason": extra_context.get("hp_pressure_reason", ""),
        "position_zone": extra_context.get("position_zone", ""),
        "position_risk": extra_context.get("position_risk", ""),
        "position_reason": extra_context.get("position_reason", ""),
        "laning_category": laning_review["laning_category"],
        "laning_advice_reason": laning_review["laning_advice_reason"],
        "repeated_laning_suppressed_count": repeated_laning_suppressed_count,
        "post_laning_category": post_laning_review["post_laning_category"],
        "post_laning_reason": post_laning_review["post_laning_reason"],
        "repeated_post_laning_suppressed_count": repeated_post_laning_suppressed_count,
        "repeated_objective_suppressed_count": repeated_objective_suppressed_count,
        "low_hp_episode_id": result.low_hp_episode_id or "",
        "repeated_low_hp_suppressed_count": repeated_low_hp_suppressed_count,
        "selected_team": request.selected_team,
        "teamfight_result": request.teamfight_result,
        "allied_deaths_in_fight": request.allied_deaths_in_fight,
        "enemy_deaths_in_fight": request.enemy_deaths_in_fight,
        "recent_allied_deaths": request.recent_allied_deaths,
        "recent_enemy_deaths": request.recent_enemy_deaths,
        "objective_type": request.objective_type or "",
        "objective_team": request.objective_team or "",
        "objective_for_selected_team": (
            "" if request.objective_for_selected_team is None else request.objective_for_selected_team
        ),
        "objective_context": request.objective_context,
        "event_context": request.event_context,
        "near_player_death": request.near_player_death,
        "near_teamfight": request.near_teamfight,
        "near_objective": request.near_objective,
        "recent_item_purchase": request.recent_item_purchase or "",
        "item_timing_category": request.item_timing_category or "",
        "gold_delta": request.gold_delta,
        "lh_delta": request.lh_delta,
        "decision_point": decision_point,
        "action_type": action_type,
        "advice_mode": result.advice_mode,
        "game_time_gap_since_previous_advice": (
            "" if result.game_time_gap_since_previous_advice is None else result.game_time_gap_since_previous_advice
        ),
        "suppressed_by_game_time_spacing": result.suppressed_by_game_time_spacing,
        "source": source,
        "llm_used": llm_used,
        "fallback_used": recommendation is not None and (result.source == "fallback" or llm_applied),
        "stale_response": stale_response,
        "suppressed_reason": result.suppressed_reason or "",
        "action": action,
        "reason": reason,
        "risk": risk,
        "priority": priority,
        "time_window": time_window,
        "player_rating": "",
        "player_comment": "",
        "shown_advice": bool(result.new_advice),
    }


def _review_gold_value(gold: int, extra_context: dict[str, Any]) -> int | str:
    source_type = str(extra_context.get("source_type") or "").strip()
    defaulted_fields = set(extra_context.get("replay_defaulted_fields") or [])
    missing_signals = set(extra_context.get("missing_signals") or [])
    if source_type == "replay_gsi_like" and ("gold" in defaulted_fields or "gold" in missing_signals):
        return "unknown"
    return gold


def _format_range(value: Any) -> str:
    if isinstance(value, (list, tuple)) and len(value) == 2:
        return f"{value[0]}-{value[1]}"
    return "" if value is None else str(value)


def _build_report(
    *,
    simulation_path: Path,
    total_states: int,
    min_timestamp_seconds: int,
    max_timestamp_seconds: int,
    advice_buckets: Counter[int],
    advice_modes: Counter[str],
    statuses: Counter[str],
    suppressed: Counter[str],
    decision_points: Counter[str],
    source_types: Counter[str],
    context_confidences: Counter[str],
    stats: dict[str, Any],
    use_llm: bool,
    llm_blocking: bool,
    blocking_llm_metrics: dict[str, Any],
    export_review: bool,
    review_only_shown: bool,
    review_row_count: int,
    pinned_advice_count: int,
) -> dict[str, Any]:
    duration_seconds = max(1, max_timestamp_seconds - min_timestamp_seconds)
    bucket_count = max(1, _ceil_div(duration_seconds, 600))
    advice_per_10_minutes = {
        f"{bucket * 10:02d}-{bucket * 10 + 10:02d}": advice_buckets[bucket]
        for bucket in range(bucket_count)
    }
    total_advice = int(stats["advice_count"])
    fits_target = EXPECTED_HINT_RANGE[0] <= total_advice <= EXPECTED_HINT_RANGE[1]
    duration_minutes = max(duration_seconds / 60, 1 / 60)
    duration_expected_range = _duration_expected_range(duration_minutes)
    states_per_minute = total_states / duration_minutes
    advice_per_minute = total_advice / duration_minutes
    repeated_advice_suppressed_count = int(stats["duplicate_suppressed_count"])
    repeated_laning_suppressed_count = int(stats.get("repeated_laning_suppressed_count", 0))
    repeated_post_laning_suppressed_count = int(stats.get("repeated_post_laning_suppressed_count", 0))
    repeated_objective_suppressed_count = int(stats.get("repeated_objective_suppressed_count", 0))
    post_laning_safety_suppressed_count = int(stats.get("post_laning_safety_suppressed_count", 0))
    objective_suppressed_by_recent_safety_count = int(
        stats.get("objective_suppressed_by_recent_safety_count", 0)
    )
    item_timing_suppressed_by_safety_count = int(stats.get("item_timing_suppressed_by_safety_count", 0))
    death_route_suppressed_count = int(stats.get("death_route_suppressed_count", 0))
    repeated_low_hp_suppressed_count = int(stats.get("repeated_low_hp_suppressed_count", 0))
    suppressed_by_game_time_spacing_count = int(stats.get("suppressed_by_game_time_spacing_count", 0))
    heartbeat_nudge_count = int(stats.get("heartbeat_nudge_count", 0))
    suppressed_heartbeat_duplicate_count = int(stats.get("suppressed_heartbeat_duplicate_count", 0))
    source_type = _single_or_mixed(source_types)
    llm_count = int(blocking_llm_metrics["llm_call_count"] if llm_blocking else stats["llm_call_count"])
    llm_applied_count = int(
        blocking_llm_metrics["llm_applied_count"] if llm_blocking else stats["llm_applied_count"]
    )
    llm_latencies = blocking_llm_metrics["llm_latencies"] if llm_blocking else None
    return {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "simulation_file": str(simulation_path),
        "source_type": source_type,
        "source_type_counts": dict(source_types),
        "context_confidence_distribution": dict(context_confidences),
        "simulation_use_llm": use_llm,
        "simulation_llm_blocking": llm_blocking,
        "simulation_export_review": export_review,
        "simulation_review_only_shown": review_only_shown,
        "review_row_count": review_row_count,
        "total_states_processed": total_states,
        "min_timestamp_seconds": min_timestamp_seconds,
        "max_timestamp_seconds": max_timestamp_seconds,
        "duration_seconds": duration_seconds,
        "duration_minutes": round(duration_minutes, 1),
        "states_per_minute": round(states_per_minute, 2),
        "total_advice_shown": total_advice,
        "advice_per_minute": round(advice_per_minute, 2),
        "advice_per_10_minutes": advice_per_10_minutes,
        "active_advice_count": statuses["active_advice"],
        "monitoring_count": statuses["monitoring"],
        "pinned_advice_count": pinned_advice_count,
        "repeated_advice_suppressed_count": repeated_advice_suppressed_count,
        "repeated_laning_suppressed_count": repeated_laning_suppressed_count,
        "repeated_post_laning_suppressed_count": repeated_post_laning_suppressed_count,
        "repeated_objective_suppressed_count": repeated_objective_suppressed_count,
        "post_laning_safety_suppressed_count": post_laning_safety_suppressed_count,
        "objective_suppressed_by_recent_safety_count": objective_suppressed_by_recent_safety_count,
        "item_timing_suppressed_by_safety_count": item_timing_suppressed_by_safety_count,
        "death_route_suppressed_count": death_route_suppressed_count,
        "low_hp_episode_count": int(stats.get("low_hp_episode_count", 0)),
        "repeated_low_hp_suppressed_count": repeated_low_hp_suppressed_count,
        "suppressed_by_game_time_spacing_count": suppressed_by_game_time_spacing_count,
        "heartbeat_nudge_count": heartbeat_nudge_count,
        "suppressed_heartbeat_duplicate_count": suppressed_heartbeat_duplicate_count,
        "min_game_time_gap_seconds": stats.get("min_game_time_gap_seconds"),
        "max_game_time_silence_seconds": stats.get("max_game_time_silence_seconds"),
        "average_game_time_gap_seconds": stats.get("average_game_time_gap_seconds"),
        "advice_game_time_gaps_seconds": stats.get("advice_game_time_gaps_seconds", []),
        "low_hp_pattern_advice_count": int(stats.get("low_hp_pattern_advice_count", 0)),
        "urgent_advice_count": advice_modes["urgent"],
        "coaching_advice_count": advice_modes["coaching"],
        "no_advice_count": statuses["no_advice"],
        "suppressed_by_rate_limit": suppressed["rate_limit"],
        "suppressed_by_duplicate": suppressed["duplicate"],
        "suppressed_by_duplicate_death_review": suppressed["duplicate_death_review"],
        "suppressed_by_cooldown": suppressed["cooldown"],
        "suppressed_by_cooldown_keep_visible": suppressed["cooldown_keep_visible"],
        "fallback_count": stats["fallback_count"],
        "llm_count": llm_count,
        "llm_applied_count": llm_applied_count,
        "llm_applied_rate": _rate(llm_applied_count, llm_count),
        "llm_timeout_count": (
            int(blocking_llm_metrics["llm_timeout_count"]) if llm_blocking else 0
        ),
        "llm_invalid_count": (
            int(blocking_llm_metrics["llm_invalid_count"]) if llm_blocking else 0
        ),
        "llm_valid_but_rejected_count": (
            int(blocking_llm_metrics["llm_valid_but_rejected_count"]) if llm_blocking else 0
        ),
        "llm_skipped_by_policy_count": (
            int(blocking_llm_metrics["llm_skipped_by_policy_count"]) if llm_blocking else 0
        ),
        "llm_wording_guard_applied_count": (
            int(blocking_llm_metrics["llm_wording_guard_applied_count"]) if llm_blocking else 0
        ),
        "llm_wording_guard_fallback_count": (
            int(blocking_llm_metrics["llm_wording_guard_fallback_count"]) if llm_blocking else 0
        ),
        "stale_response_count": 0 if llm_blocking else stats["stale_llm_count"],
        "tactical_hash_changes": stats["tactical_hash_changes"],
        "duplicate_suppressed_count": stats["duplicate_suppressed_count"],
        "average_latency": _average(llm_latencies) if llm_blocking else stats["average_llm_latency"],
        "p95_latency": _p95(llm_latencies) if llm_blocking else stats["p95_llm_latency"],
        "expected_hints_per_match": f"{EXPECTED_HINT_RANGE[0]}-{EXPECTED_HINT_RANGE[1]}",
        "fits_target_40_50_hints": fits_target,
        "expected_hints_for_duration": (
            f"{duration_expected_range[0]}-{duration_expected_range[1]}"
            if duration_expected_range
            else None
        ),
        "fits_duration_target": (
            duration_expected_range[0] <= total_advice <= duration_expected_range[1]
            if duration_expected_range
            else None
        ),
        "decision_points": dict(decision_points),
    }


def _write_report(report: dict[str, Any]) -> Path:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    path = RESULTS_DIR / f"match_advice_simulation_{timestamp}.json"
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def _write_review_csv(rows: list[dict[str, Any]], timestamp: str) -> Path:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    path = RESULTS_DIR / f"advice_review_{timestamp}.csv"
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=REVIEW_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return path


def _write_review_markdown(rows: list[dict[str, Any]], timestamp: str) -> Path:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    path = RESULTS_DIR / f"advice_review_{timestamp}.md"
    lines = [
        "# Match Advice Review",
        "",
        "| # | Time | Hero | Decision point | Lane category | Post-laning category | Low HP episode | Gap since previous advice | Low HP repeats suppressed | Post-laning repeats suppressed | Objective repeats suppressed | Mode | Source | Confidence | Farm | HP pressure | Position | Missing signals | Team | Fight | Objective | Context | Action | Reason | Priority | Rating | Comment |",
        "|---|---|---|---|---|---|---:|---:|---:|---:|---:|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for row in rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    _md_cell(row["index"]),
                    _md_cell(_format_time(row["timestamp_seconds"])),
                    _md_cell(row["hero"]),
                    _md_cell(row["decision_point"]),
                    _md_cell(row["laning_category"]),
                    _md_cell(row["post_laning_category"]),
                    _md_cell(row["low_hp_episode_id"]),
                    _md_cell(row["game_time_gap_since_previous_advice"]),
                    _md_cell(row["repeated_low_hp_suppressed_count"]),
                    _md_cell(row["repeated_post_laning_suppressed_count"]),
                    _md_cell(row["repeated_objective_suppressed_count"]),
                    _md_cell(row["advice_mode"]),
                    _md_cell(row["source"]),
                    _md_cell(row["context_confidence"]),
                    _md_cell(_review_context_summary(row, "farm")),
                    _md_cell(_review_context_summary(row, "hp")),
                    _md_cell(_review_context_summary(row, "position")),
                    _md_cell(row["missing_signals"]),
                    _md_cell(row["team_status"]),
                    _md_cell(row["teamfight_result"]),
                    _md_cell(row["objective_context"]),
                    _md_cell(row["event_context"]),
                    _md_cell(row["action"]),
                    _md_cell(row["reason"]),
                    _md_cell(row["priority"]),
                    _md_cell(row["player_rating"]),
                    _md_cell(row["player_comment"]),
                ]
            )
            + " |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _print_report(
    report: dict[str, Any],
    report_path: Path,
    review_csv_path: Path | None,
    review_md_path: Path | None,
) -> None:
    print(f"total states processed: {report['total_states_processed']}")
    print(f"source type: {report['source_type']}")
    print(f"context confidence distribution: {report['context_confidence_distribution']}")
    print(f"simulation_llm_blocking: {report['simulation_llm_blocking']}")
    print(f"states per minute: {report['states_per_minute']}")
    print(f"total advice shown: {report['total_advice_shown']}")
    print(f"advice per minute: {report['advice_per_minute']}")
    print("advice per 10 minutes:")
    for bucket, count in report["advice_per_10_minutes"].items():
        print(f"  {bucket}: {count}")
    print(f"active advice count: {report['active_advice_count']}")
    print(f"monitoring count: {report['monitoring_count']}")
    print(f"pinned advice count: {report['pinned_advice_count']}")
    print(f"repeated advice suppressed count: {report['repeated_advice_suppressed_count']}")
    print(f"repeated laning suppressed count: {report['repeated_laning_suppressed_count']}")
    print(f"repeated post-laning suppressed count: {report['repeated_post_laning_suppressed_count']}")
    print(f"repeated objective suppressed count: {report['repeated_objective_suppressed_count']}")
    print(f"post-laning safety suppressed count: {report['post_laning_safety_suppressed_count']}")
    print(f"objective suppressed by recent safety count: {report['objective_suppressed_by_recent_safety_count']}")
    print(f"item timing suppressed by safety count: {report['item_timing_suppressed_by_safety_count']}")
    print(f"death route suppressed count: {report['death_route_suppressed_count']}")
    print(f"low_hp_episode_count: {report['low_hp_episode_count']}")
    print(f"repeated_low_hp_suppressed_count: {report['repeated_low_hp_suppressed_count']}")
    print(f"suppressed_by_game_time_spacing_count: {report['suppressed_by_game_time_spacing_count']}")
    print(f"heartbeat_nudge_count: {report['heartbeat_nudge_count']}")
    print(f"suppressed_heartbeat_duplicate_count: {report['suppressed_heartbeat_duplicate_count']}")
    print(f"min_game_time_gap_seconds: {report['min_game_time_gap_seconds']}")
    print(f"max_game_time_silence_seconds: {report['max_game_time_silence_seconds']}")
    print(f"average_game_time_gap_seconds: {report['average_game_time_gap_seconds']}")
    print(f"advice_game_time_gaps_seconds: {report['advice_game_time_gaps_seconds']}")
    print(f"low_hp_pattern_advice_count: {report['low_hp_pattern_advice_count']}")
    print(f"urgent advice count: {report['urgent_advice_count']}")
    print(f"coaching advice count: {report['coaching_advice_count']}")
    print(f"no_advice count: {report['no_advice_count']}")
    print(f"suppressed_by_rate_limit: {report['suppressed_by_rate_limit']}")
    print(f"suppressed_by_duplicate: {report['suppressed_by_duplicate']}")
    print(f"fallback_count: {report['fallback_count']}")
    print(f"llm_count: {report['llm_count']}")
    print(f"llm_applied_count: {report['llm_applied_count']}")
    print(f"llm_applied_rate: {_format_rate(report['llm_applied_rate'])}")
    print(f"llm_timeout_count: {report['llm_timeout_count']}")
    print(f"llm_invalid_count: {report['llm_invalid_count']}")
    print(f"llm_valid_but_rejected_count: {report['llm_valid_but_rejected_count']}")
    print(f"llm_skipped_by_policy_count: {report['llm_skipped_by_policy_count']}")
    print(f"llm_wording_guard_applied_count: {report['llm_wording_guard_applied_count']}")
    print(f"llm_wording_guard_fallback_count: {report['llm_wording_guard_fallback_count']}")
    print(f"expected hints per match: {report['expected_hints_per_match']}")
    print(f"fits target 40-50 hints/match: {'yes' if report['fits_target_40_50_hints'] else 'no'}")
    if report["expected_hints_for_duration"]:
        print(f"expected hints for {report['duration_minutes']}m replay: {report['expected_hints_for_duration']}")
        print(f"fits duration target: {'yes' if report['fits_duration_target'] else 'no'}")
    print(f"stale response count: {report['stale_response_count']}")
    print(f"tactical_hash_changes: {report['tactical_hash_changes']}")
    print(f"average latency: {_format_latency(report['average_latency'])}")
    print(f"p95 latency: {_format_latency(report['p95_latency'])}")
    print(f"report saved: {report_path}")
    if review_csv_path is not None:
        print(f"Review CSV saved: {review_csv_path}")
    if review_md_path is not None:
        print(f"Review Markdown saved: {review_md_path}")


def _review_context_summary(row: dict[str, Any], kind: str) -> str:
    if kind == "farm":
        parts = [
            str(row.get("farm_quality") or ""),
            f"expected {row.get('expected_lh_range')}" if row.get("expected_lh_range") else "",
            str(row.get("lh_deficit_or_status") or ""),
        ]
    elif kind == "hp":
        parts = [
            str(row.get("hp_pressure_state") or ""),
            str(row.get("hp_pressure_reason") or ""),
        ]
    else:
        parts = [
            str(row.get("position_zone") or ""),
            str(row.get("position_risk") or ""),
            str(row.get("position_reason") or ""),
        ]
    return "; ".join(part for part in parts if part)


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSONL at {path}:{line_number}: {exc}") from exc
    return rows


def _retrieve_rag_context(request: GameSituationRequest) -> list[str]:
    query = (
        f"{request.hero} {request.role} {request.game_state} {request.team_status} "
        f"{request.event_context} {request.item_timing_category or ''} "
        f"{request.selected_team} {request.teamfight_result} {request.objective_context} "
        f"{request.objective_type or ''} {request.objective_team or ''} "
        f"minute {request.minute} level {request.level} hp {request.hp_percent} "
        f"gold {request.gold} " + " ".join(request.items)
    )
    return retrieve_context(
        query,
        hero=request.hero,
        game_state=request.game_state,
        owned_items=request.items,
    )


def _format_latency(value: float | None) -> str:
    if value is None:
        return "0.000s"
    return f"{value:.3f}s"


def _format_rate(value: float | None) -> str:
    if value is None:
        return "0.0%"
    return f"{value * 100:.1f}%"


def _rate(part: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return part / total


def _average(values: list[float] | None) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def _p95(values: list[float] | None) -> float | None:
    if not values:
        return None
    sorted_values = sorted(values)
    index = max(0, int(round(0.95 * (len(sorted_values) - 1))))
    return sorted_values[index]


def _single_or_mixed(counter: Counter[str]) -> str:
    nonzero = [key for key, count in counter.items() if count > 0]
    if len(nonzero) == 1:
        return nonzero[0]
    if not nonzero:
        return "unknown"
    return "mixed"


def _duration_expected_range(duration_minutes: float) -> tuple[int, int] | None:
    if duration_minutes >= 35:
        return None
    lower = max(1, round(duration_minutes * 0.5))
    upper = max(lower, round(duration_minutes * 0.8))
    return lower, upper


def _bucket_for_elapsed_seconds(relative_seconds: int) -> int:
    if relative_seconds <= 0:
        return 0
    return (relative_seconds - 1) // 600


def _ceil_div(value: int, divisor: int) -> int:
    return (value + divisor - 1) // divisor


def _format_time(timestamp_seconds: Any) -> str:
    seconds = int(timestamp_seconds)
    minute = seconds // 60
    second = seconds % 60
    return f"{minute:02d}:{second:02d}"


def _md_cell(value: Any) -> str:
    text = str(value).replace("\n", " ").replace("|", "\\|").strip()
    return text


def _env_bool(name: str, *, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


if __name__ == "__main__":
    raise SystemExit(main())
