"""
advice_scheduler.py - in-memory live advice scheduling for the GSI overlay.

Purpose:
- accept normalized live/demo state plus a decision point;
- return either a new visible advice card, the still-active previous card, or a
  compact status/cooldown response;
- keep realtime coaching useful without spamming the player.

The scheduler does not choose high-level game meaning by itself. Decision
selection comes from ``decision_points.py`` and wording comes from the
fallback recommender or optional LLM refinement. This module owns the display
contract: game-time spacing, duplicate suppression, active-card lifetime,
urgent interrupts, low-HP episode handling, death pinning, objective/card
suppression, and accounting metrics.

Timing distinction:
- decision frequency and duplicate suppression use Dota game_time / simulated
  replay time when available;
- wall-clock time is kept for UI visibility, async LLM staleness, and ordinary
  HTTP polling.

The overlay should get immediate rule-based advice. Optional LLM refinement runs
in the background and is discarded if the tactical state changes before it
arrives.
"""

from __future__ import annotations

import hashlib
import json
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from statistics import mean
from typing import Any, Literal

from app.advice_policy import apply_advice_policy, build_advice_policy
from app.advice_ux_policy import (
    REGULAR_ADVICE_INTERVAL_SECONDS,
    URGENT_ADVICE_INTERVAL_SECONDS,
    apply_ux_policy,
)
from app.advice_text import clean_recommendation_text
from app.config import USE_LLM
from app.laning_coach import (
    REPEAT_WINDOW_SECONDS,
    build_laning_advice,
    important_laning_context_changed,
)
from app.llm_provider import generate_llm_recommendation, is_llm_provider_enabled
from app.post_laning_coach import (
    POST_LANING_DEATH_ROUTE_WINDOW_SECONDS,
    OBJECTIVE_REPEAT_WINDOW_SECONDS,
    POST_LANING_REPEAT_WINDOW_SECONDS,
    POST_LANING_RECENT_SAFETY_WINDOW_SECONDS,
    POST_LANING_SAME_ACTION_WINDOW_SECONDS,
    build_post_laning_advice,
    important_post_laning_context_changed,
)
from app.recommender import generate_recommendation
from app.schemas import GameSituationRequest, RecommendationResponse


AdviceType = Literal[
    "LOW_HP",
    "LOW_HP_WARNING",
    "RECENT_DAMAGE_WARNING",
    "OVERSTAY_WARNING",
    "DEATH_REVIEW",
    "REPEATED_DEATH_PATTERN",
    "DEATH_WITH_ESCAPE_ON_COOLDOWN",
    "DEATH_LOW_RESOURCE",
    "LOW_MANA",
    "DISABLED_STATUS",
    "BUYBACK_AVAILABLE",
    "DEAD_WAIT",
    "SMOKED_STATUS",
    "HERO_SURVIVABILITY_RISK",
    "LANING_REGEN_CHECK",
    "LANING_FARM_CHECK",
    "ABILITY_SAFETY_COOLDOWN",
    "SOFT_STATUS",
    "FARMING_PHASE_PRESSURE",
    "OBJECTIVE_FIGHT_CHECK",
    "BAD_FIGHT_RISK",
    "ITEM_TIMING",
    "SAFE_FARMING",
    "NO_ADVICE",
]

OverlayStatus = Literal["advice", "active_advice", "no_advice", "cooldown"]
OverlaySource = Literal["llm", "fallback", "none"]

SOFT_INTERVAL_SECONDS = REGULAR_ADVICE_INTERVAL_SECONDS
REGULAR_ADVICE_COOLDOWN_SECONDS = REGULAR_ADVICE_INTERVAL_SECONDS
URGENT_LOW_HP_COOLDOWN_SECONDS = URGENT_ADVICE_INTERVAL_SECONDS
LLM_REFINEMENT_EVERY_N_ADVICES = 3

MAX_ACTION_LENGTH = 100
MAX_REASON_LENGTH = 180
DEATH_REVIEW_DECISIONS = {
    "DEATH_REVIEW",
    "REPEATED_DEATH_PATTERN",
    "DEATH_WITH_ESCAPE_ON_COOLDOWN",
    "DEATH_LOW_RESOURCE",
}
COACHING_GAME_TIME_GAP_SECONDS = 45
POST_LANING_GAME_TIME_GAP_SECONDS = 60
SAME_ACTION_GAME_TIME_GAP_SECONDS = 120
RECENT_SAFETY_GAME_TIME_GAP_SECONDS = 35
HEARTBEAT_NUDGE_SECONDS = 150
HEARTBEAT_DUPLICATE_WAIT_SECONDS = 180


@dataclass
class ScheduledAdvice:
    status: OverlayStatus
    decision_point: str
    recommendation: RecommendationResponse | None
    advice_count: int
    llm_used: bool
    source: OverlaySource
    last_updated: str | None
    next_allowed_advice_in_seconds: int
    new_advice: bool = False
    advice_mode: str = "status"
    suppressed_reason: str | None = None
    active_advice_until: str | None = None
    last_visible_advice: dict[str, Any] | None = None
    is_pinned: bool = False
    low_hp_episode_id: int | None = None
    game_time_gap_since_previous_advice: float | None = None
    suppressed_by_game_time_spacing: bool = False


class AdviceScheduler:
    def __init__(
        self,
        *,
        enable_llm: bool | None = None,
        regular_cooldown_seconds: int = REGULAR_ADVICE_COOLDOWN_SECONDS,
        urgent_cooldown_seconds: int = URGENT_LOW_HP_COOLDOWN_SECONDS,
    ) -> None:
        self.enable_llm = enable_llm
        self.regular_cooldown_seconds = regular_cooldown_seconds
        self.urgent_cooldown_seconds = urgent_cooldown_seconds
        self._lock = threading.Lock()
        self.reset()

    def reset(self) -> None:
        with self._lock:
            self._reset_locked()

    def _reset_locked(self) -> None:
        self.match_started_at: datetime | None = None
        self.match_session_id: str | None = None
        self.last_advice_at: datetime | None = None
        self.last_advice_type: str | None = None
        self.last_state_hash: str | None = None
        self.last_tactical_state_hash: str | None = None
        self.advice_count = 0
        self.llm_call_count = 0
        self.llm_applied_count = 0
        self.fallback_count = 0
        self.stale_llm_count = 0
        self.duplicate_suppressed_count = 0
        self.repeated_laning_suppressed_count = 0
        self.repeated_post_laning_suppressed_count = 0
        self.repeated_objective_suppressed_count = 0
        self.post_laning_safety_suppressed_count = 0
        self.objective_suppressed_by_recent_safety_count = 0
        self.item_timing_suppressed_by_safety_count = 0
        self.death_route_suppressed_count = 0
        self.low_hp_episode_count = 0
        self.repeated_low_hp_suppressed_count = 0
        self.low_hp_pattern_advice_count = 0
        self.tactical_hash_changes = 0
        self._last_advice_state_hash: str | None = None
        self._last_advice_tactical_state_hash: str | None = None
        self._last_recommendation: RecommendationResponse | None = None
        self._last_source: OverlaySource = "none"
        self._last_llm_used = False
        self._last_advice_mode = "status"
        self._last_updated: str | None = None
        self._active_advice_until: datetime | None = None
        self._is_pinned = False
        self._last_seen_minute: int | None = None
        self._pending_llm_tactical_hashes: set[str] = set()
        self._llm_latencies: list[float] = []
        self._advice_history: list[dict[str, Any]] = []
        self._last_laning_category: dict[str, dict[str, Any]] = {}
        self._last_post_laning_category: dict[str, dict[str, Any]] = {}
        self._last_objective_advice_at: datetime | None = None
        self._last_post_laning_safety_at: datetime | None = None
        self._last_post_laning_safety_game_time: float | None = None
        self._last_post_laning_death_route_at: datetime | None = None
        self._last_post_laning_death_route_game_time: float | None = None
        self._last_post_laning_death_route_event_id: str | None = None
        self._last_low_hp_urgent_at: datetime | None = None
        self._last_low_hp_urgent_game_time: float | None = None
        self._last_low_hp_pattern_at: datetime | None = None
        self._last_low_hp_pattern_game_time: float | None = None
        self._last_objective_advice_game_time: float | None = None
        self._post_laning_hp_recovered_since_safety = False
        self._last_shown_game_time_seconds: float | None = None
        self._last_shown_decision_point: str | None = None
        self._last_shown_category: str | None = None
        self._last_shown_action_hash: str | None = None
        self._advice_game_time_gaps_seconds: list[float] = []
        self.suppressed_by_game_time_spacing_count = 0
        self.heartbeat_nudge_count = 0
        self.suppressed_heartbeat_duplicate_count = 0
        self._low_hp_episode_active = False
        self._low_hp_episode_id = 0
        self._low_hp_episode_lowest_hp: int | None = None
        self._low_hp_episode_repeat_count = 0
        self._low_hp_episode_pattern_shown = False
        self._low_hp_pattern_advice_shown = False
        self._low_hp_pattern_last_at: datetime | None = None
        self._low_hp_episode_last_severe_signature: str | None = None

    # ------------------------------------------------------------------
    # Public API — observe_state and evaluate are the two entry points.
    # observe_state is a lightweight state tracker used by the demo path.
    # evaluate is the full scheduling decision, called per overlay tick.
    # ------------------------------------------------------------------

    def observe_state(
        self,
        state: dict[str, Any],
        decision_point: str,
        now: datetime | None = None,
    ) -> None:
        current_time = _utcnow(now)
        state_hash = build_state_hash(state, decision_point)
        policy = build_advice_policy(state, decision_point)
        tactical_hash = build_tactical_state_hash(
            state,
            decision_point,
            action_type=policy["action_type"],
        )
        minute = _to_int(state.get("minute"), 0)

        with self._lock:
            self._ensure_session_locked(current_time, minute, state)
            game_time_seconds = self._game_time_seconds_locked(state, current_time)
            self._update_hashes_locked(state_hash, tactical_hash)
            self._update_low_hp_recovery_locked(state)

    def evaluate(
        self,
        request: GameSituationRequest,
        decision_point: str,
        rag_context: list[str],
        now: datetime | None = None,
    ) -> ScheduledAdvice:
        current_time = _utcnow(now)
        state = request.model_dump()
        state_hash = build_state_hash(state, decision_point)
        policy = build_advice_policy(request, decision_point)
        tactical_hash = build_tactical_state_hash(
            state,
            decision_point,
            action_type=policy["action_type"],
        )

        with self._lock:
            self._ensure_session_locked(current_time, request.minute, state)
            game_time_seconds = self._game_time_seconds_locked(state, current_time)
            self._update_hashes_locked(state_hash, tactical_hash)
            if decision_point != "LOW_HP":
                self._update_low_hp_recovery_locked(state)

            if decision_point == "NO_ADVICE":
                active = self._active_result_locked(
                    decision_point=decision_point,
                    now=current_time,
                    next_allowed=0,
                    suppressed_reason="cooldown_keep_visible",
                )
                if active is not None:
                    return active
                return self._result_locked(
                    status="no_advice",
                    decision_point=decision_point,
                    recommendation=None,
                    source="none",
                    llm_used=False,
                    next_allowed=0,
                    new_advice=False,
                    advice_mode="status",
                    suppressed_reason="no_advice",
                )

            cooldown_remaining = self._cooldown_remaining_locked(
                decision_point,
                current_time,
                game_time_seconds,
            )
            duplicate = self._last_advice_state_hash == state_hash
            if duplicate:
                self.duplicate_suppressed_count += 1
                suppressed_reason = "duplicate_death_review" if decision_point in DEATH_REVIEW_DECISIONS else "duplicate"
                active = self._active_result_locked(
                    decision_point=decision_point,
                    now=current_time,
                    next_allowed=cooldown_remaining,
                    suppressed_reason="cooldown_keep_visible" if suppressed_reason == "duplicate" else suppressed_reason,
                )
                if active is not None:
                    return active
                recommendation, source, llm_used, advice_mode = self._last_matching_advice_locked(tactical_hash)
                return self._result_locked(
                    status="cooldown",
                    decision_point=decision_point,
                    recommendation=recommendation,
                    source=source,
                    llm_used=llm_used,
                    next_allowed=cooldown_remaining,
                    new_advice=False,
                    advice_mode=advice_mode,
                    suppressed_reason=suppressed_reason,
                )

            if cooldown_remaining > 0:
                active = self._active_result_locked(
                    decision_point=decision_point,
                    now=current_time,
                    next_allowed=cooldown_remaining,
                    suppressed_reason="cooldown_keep_visible",
                )
                if active is not None:
                    return active
                recommendation, source, llm_used, advice_mode = self._last_matching_advice_locked(tactical_hash)
                return self._result_locked(
                    status="cooldown",
                    decision_point=decision_point,
                    recommendation=recommendation,
                    source=source,
                    llm_used=llm_used,
                    next_allowed=cooldown_remaining,
                    new_advice=False,
                    advice_mode=advice_mode,
                    suppressed_reason="cooldown",
                )

            if decision_point == "LOW_HP_WARNING" and (
                self._low_hp_episode_active
                or self._recent_low_hp_pattern_locked(current_time, game_time_seconds)
            ):
                self.repeated_low_hp_suppressed_count += 1
                self.duplicate_suppressed_count += 1
                active = self._active_result_locked(
                    decision_point=decision_point,
                    now=current_time,
                    next_allowed=self._cooldown_for_type_locked(decision_point),
                    suppressed_reason="cooldown_keep_visible",
                )
                if active is not None:
                    return active
                return self._result_locked(
                    status="cooldown",
                    decision_point=decision_point,
                    recommendation=None,
                    source="none",
                    llm_used=False,
                    next_allowed=self._cooldown_for_type_locked(decision_point),
                    new_advice=False,
                    advice_mode="status",
                    suppressed_reason="duplicate_low_hp_episode",
                )

            if decision_point == "LOW_HP":
                low_hp_action = self._low_hp_episode_action_locked(state)
                if low_hp_action == "suppress":
                    self.repeated_low_hp_suppressed_count += 1
                    self.post_laning_safety_suppressed_count += _post_laning_int(state)
                    self.duplicate_suppressed_count += 1
                    active = self._active_result_locked(
                        decision_point=decision_point,
                        now=current_time,
                        next_allowed=self._cooldown_for_type_locked(decision_point),
                        suppressed_reason="cooldown_keep_visible",
                    )
                    if active is not None:
                        return active
                    return self._result_locked(
                        status="cooldown",
                        decision_point=decision_point,
                        recommendation=None,
                        source="none",
                        llm_used=False,
                        next_allowed=self._cooldown_for_type_locked(decision_point),
                        new_advice=False,
                        advice_mode="status",
                        suppressed_reason="duplicate_low_hp_episode",
                    )
                if low_hp_action == "show" and self._should_suppress_post_laning_low_hp_locked(
                    state=state,
                    now=current_time,
                    game_time_seconds=game_time_seconds,
                ):
                    self.repeated_low_hp_suppressed_count += 1
                    self.post_laning_safety_suppressed_count += 1
                    self.duplicate_suppressed_count += 1
                    active = self._active_result_locked(
                        decision_point=decision_point,
                        now=current_time,
                        next_allowed=self._cooldown_for_type_locked(decision_point),
                        suppressed_reason="cooldown_keep_visible",
                    )
                    if active is not None:
                        return active
                    return self._result_locked(
                        status="cooldown",
                        decision_point=decision_point,
                        recommendation=None,
                        source="none",
                        llm_used=False,
                        next_allowed=self._cooldown_for_type_locked(decision_point),
                        new_advice=False,
                        advice_mode="status",
                        suppressed_reason="duplicate_low_hp_episode",
                    )
                if low_hp_action == "pattern":
                    pattern = _low_hp_pattern_recommendation()
                    self.advice_count += 1
                    self.fallback_count += 1
                    self.low_hp_pattern_advice_count += 1
                    self._record_post_laning_safety_locked(
                        now=current_time,
                        state=state,
                        category="low_hp_pattern",
                        game_time_seconds=game_time_seconds,
                    )
                    self._last_low_hp_pattern_at = current_time
                    self._low_hp_pattern_last_at = current_time
                    gap = self._record_shown_advice_timing_locked(
                        decision_point=decision_point,
                        state=state,
                        recommendation=pattern,
                        category="low_hp_pattern",
                        game_time_seconds=game_time_seconds,
                    )
                    self.last_advice_at = current_time
                    self.last_advice_type = decision_point
                    self._last_advice_state_hash = state_hash
                    self._last_advice_tactical_state_hash = tactical_hash
                    self._last_recommendation = pattern
                    self._last_source = "fallback"
                    self._last_llm_used = False
                    self._last_advice_mode = "coaching"
                    self._last_updated = current_time.isoformat()
                    self._set_active_advice_locked(decision_point, state, current_time)
                    self._advice_history.append(
                        {
                            "timestamp": self._last_updated,
                            "decision_point": decision_point,
                            "source": "fallback",
                            "action": pattern.action,
                            "action_type": "low_hp_pattern",
                            "low_hp_episode_id": self._low_hp_episode_id,
                            "game_time_gap_since_previous_advice": gap,
                        }
                    )
                    return ScheduledAdvice(
                        status="advice",
                        decision_point=decision_point,
                        recommendation=pattern,
                        advice_count=self.advice_count,
                        llm_used=False,
                        source="fallback",
                        last_updated=self._last_updated,
                        next_allowed_advice_in_seconds=self._cooldown_for_type_locked(decision_point),
                        new_advice=True,
                        advice_mode="coaching",
                        suppressed_reason=None,
                        active_advice_until=(
                            self._active_advice_until.isoformat()
                            if self._active_advice_until
                            else None
                        ),
                        last_visible_advice=pattern.model_dump(),
                        is_pinned=self._is_pinned,
                        low_hp_episode_id=self._low_hp_episode_id,
                        game_time_gap_since_previous_advice=gap,
                    )

        fallback = apply_advice_policy(generate_recommendation(request, rag_context), policy)
        fallback = _compact_recommendation(fallback, decision_point)

        with self._lock:
            ux_result = apply_ux_policy(
                fallback,
                decision_point,
                list(self._advice_history),
                now=current_time,
                action_type=policy["action_type"],
            )
            if ux_result["recommendation"] is None:
                reason = ux_result["suppressed_reason"] or "cooldown"
                if reason == "duplicate":
                    self.duplicate_suppressed_count += 1
                active = self._active_result_locked(
                    decision_point=decision_point,
                    now=current_time,
                    next_allowed=self._cooldown_for_type_locked(decision_point),
                    suppressed_reason="cooldown_keep_visible",
                )
                if active is not None:
                    return active
                return self._result_locked(
                    status="cooldown",
                    decision_point=decision_point,
                    recommendation=None,
                    source="none",
                    llm_used=False,
                    next_allowed=self._cooldown_for_type_locked(decision_point),
                    new_advice=False,
                    advice_mode=ux_result["advice_mode"],
                    suppressed_reason=reason,
                )

            fallback = clean_recommendation_text(ux_result["recommendation"], decision_point)
            suppress_laning, laning_category = self._should_suppress_laning_locked(
                decision_point=decision_point,
                state=state,
                recommendation=fallback,
                now=current_time,
                game_time_seconds=game_time_seconds,
            )
            if suppress_laning:
                self.repeated_laning_suppressed_count += 1
                self.duplicate_suppressed_count += 1
                active = self._active_result_locked(
                    decision_point=decision_point,
                    now=current_time,
                    next_allowed=self._cooldown_for_type_locked(decision_point),
                    suppressed_reason="cooldown_keep_visible",
                )
                if active is not None:
                    return active
                return self._result_locked(
                    status="cooldown",
                    decision_point=decision_point,
                    recommendation=None,
                    source="none",
                    llm_used=False,
                    next_allowed=self._cooldown_for_type_locked(decision_point),
                    new_advice=False,
                    advice_mode=ux_result["advice_mode"],
                    suppressed_reason="duplicate_laning",
                )

            suppress_post_laning, post_laning_category, post_laning_reason = (
                self._should_suppress_post_laning_locked(
                    decision_point=decision_point,
                    state=state,
                    recommendation=fallback,
                    now=current_time,
                    game_time_seconds=game_time_seconds,
                )
            )
            if suppress_post_laning:
                heartbeat = self._heartbeat_nudge_locked(
                    decision_point=decision_point,
                    state=state,
                    recommendation=fallback,
                    category=post_laning_category,
                    reason=post_laning_reason,
                    game_time_seconds=game_time_seconds,
                )
                if heartbeat is not None:
                    fallback = heartbeat
                    post_laning_category = "post_laning_safe_farm_route"
                    post_laning_reason = None
                    suppress_post_laning = False
                else:
                    if post_laning_reason == "objective_after_recent_safety":
                        self.objective_suppressed_by_recent_safety_count += 1
                        self.repeated_objective_suppressed_count += 1
                    elif post_laning_reason in {"duplicate_objective", "objective_context_missing"}:
                        self.repeated_objective_suppressed_count += 1
                    elif post_laning_reason == "item_timing_after_recent_safety":
                        self.item_timing_suppressed_by_safety_count += 1
                    elif post_laning_reason == "death_route_duplicate":
                        self.death_route_suppressed_count += 1
                    elif post_laning_reason == "recent_safety":
                        self.post_laning_safety_suppressed_count += 1
                        self.repeated_post_laning_suppressed_count += 1
                    else:
                        self.repeated_post_laning_suppressed_count += 1
                    self.duplicate_suppressed_count += 1
                    active = self._active_result_locked(
                        decision_point=decision_point,
                        now=current_time,
                        next_allowed=self._cooldown_for_type_locked(decision_point),
                        suppressed_reason="cooldown_keep_visible",
                    )
                    if active is not None:
                        return active
                    return self._result_locked(
                        status="cooldown",
                        decision_point=decision_point,
                        recommendation=None,
                        source="none",
                        llm_used=False,
                        next_allowed=self._cooldown_for_type_locked(decision_point),
                        new_advice=False,
                        advice_mode=ux_result["advice_mode"],
                        suppressed_reason=post_laning_reason or "duplicate_post_laning",
                    )

            spacing_remaining, spacing_gap = self._game_time_spacing_remaining_locked(
                decision_point=decision_point,
                state=state,
                recommendation=fallback,
                advice_mode=ux_result["advice_mode"],
                category=post_laning_category or laning_category,
                game_time_seconds=game_time_seconds,
            )
            if spacing_remaining > 0:
                self.suppressed_by_game_time_spacing_count += 1
                self.duplicate_suppressed_count += 1
                active = self._active_result_locked(
                    decision_point=decision_point,
                    now=current_time,
                    next_allowed=spacing_remaining,
                    suppressed_reason="cooldown_keep_visible",
                )
                if active is not None:
                    active.suppressed_by_game_time_spacing = True
                    active.game_time_gap_since_previous_advice = spacing_gap
                    return active
                return self._result_locked(
                    status="cooldown",
                    decision_point=decision_point,
                    recommendation=None,
                    source="none",
                    llm_used=False,
                    next_allowed=spacing_remaining,
                    new_advice=False,
                    advice_mode=ux_result["advice_mode"],
                    suppressed_reason="game_time_spacing",
                    game_time_gap_since_previous_advice=spacing_gap,
                    suppressed_by_game_time_spacing=True,
                )

            self.advice_count += 1
            self.fallback_count += 1
            shown_category = post_laning_category or laning_category or decision_point
            if _is_heartbeat_recommendation(fallback):
                self.heartbeat_nudge_count += 1
            gap = self._record_shown_advice_timing_locked(
                decision_point=decision_point,
                state=state,
                recommendation=fallback,
                category=shown_category,
                game_time_seconds=game_time_seconds,
            )
            self.last_advice_at = current_time
            self.last_advice_type = decision_point
            self._last_advice_state_hash = state_hash
            self._last_advice_tactical_state_hash = tactical_hash
            self._last_recommendation = fallback
            self._last_source = "fallback"
            self._last_llm_used = False
            self._last_advice_mode = ux_result["advice_mode"]
            self._last_updated = current_time.isoformat()
            self._set_active_advice_locked(decision_point, state, current_time)
            self._advice_history.append(
                {
                    "timestamp": self._last_updated,
                    "decision_point": decision_point,
                    "source": "fallback",
                    "action": fallback.action,
                    "action_type": ux_result["action_type"],
                    "laning_category": laning_category or "",
                    "post_laning_category": post_laning_category or "",
                    "game_time_gap_since_previous_advice": gap,
                }
            )
            self._record_laning_advice_locked(
                decision_point=decision_point,
                state=state,
                recommendation=fallback,
                now=current_time,
                game_time_seconds=game_time_seconds,
            )
            self._record_post_laning_advice_locked(
                decision_point=decision_point,
                state=state,
                recommendation=fallback,
                now=current_time,
                game_time_seconds=game_time_seconds,
            )
            self._record_safety_advice_locked(
                decision_point=decision_point,
                state=state,
                post_laning_category=post_laning_category,
                now=current_time,
                game_time_seconds=game_time_seconds,
            )
            should_refine = self._should_start_llm_locked(decision_point, tactical_hash)
            next_allowed = self._cooldown_for_type_locked(decision_point)

        if should_refine:
            self._start_llm_refinement(tactical_hash, request, decision_point, rag_context)

        return ScheduledAdvice(
            status="advice",
            decision_point=decision_point,
            recommendation=fallback,
            advice_count=self.advice_count,
            llm_used=False,
            source="fallback",
            last_updated=self._last_updated,
            next_allowed_advice_in_seconds=next_allowed,
            new_advice=True,
            advice_mode=ux_result["advice_mode"],
            suppressed_reason=None,
            active_advice_until=self._active_advice_until.isoformat() if self._active_advice_until else None,
            last_visible_advice=fallback.model_dump(),
            is_pinned=self._is_pinned,
            game_time_gap_since_previous_advice=gap,
        )

    # ------------------------------------------------------------------
    # Public helpers — read-only or secondary entry points used by the
    # demo path, the launcher, and debug/stats endpoints.
    # ------------------------------------------------------------------

    def active_advice_for_state(
        self,
        state: dict[str, Any],
        decision_point: str,
        now: datetime | None = None,
    ) -> ScheduledAdvice | None:
        current_time = _utcnow(now)
        minute = _to_int(state.get("minute"), 0)
        state_hash = build_state_hash(state, decision_point)
        policy = build_advice_policy(state, decision_point)
        tactical_hash = build_tactical_state_hash(
            state,
            decision_point,
            action_type=policy["action_type"],
        )
        with self._lock:
            self._ensure_session_locked(current_time, minute, state)
            game_time_seconds = self._game_time_seconds_locked(state, current_time)
            self._update_hashes_locked(state_hash, tactical_hash)
            return self._active_result_locked(
                decision_point=decision_point,
                now=current_time,
                next_allowed=self._current_cooldown_remaining_locked(current_time, game_time_seconds),
                suppressed_reason="cooldown_keep_visible",
            )

    def stats(self, now: datetime | None = None) -> dict[str, Any]:
        current_time = _utcnow(now)
        with self._lock:
            game_time_seconds = None
            return {
                "match_started_at": self.match_started_at.isoformat() if self.match_started_at else None,
                "match_session_id": self.match_session_id,
                "advice_count": self.advice_count,
                "llm_call_count": self.llm_call_count,
                "llm_applied_count": self.llm_applied_count,
                "llm_applied_rate": _rate(self.llm_applied_count, self.llm_call_count),
                "fallback_count": self.fallback_count,
                "stale_llm_count": self.stale_llm_count,
                "duplicate_suppressed_count": self.duplicate_suppressed_count,
                "repeated_laning_suppressed_count": self.repeated_laning_suppressed_count,
                "repeated_post_laning_suppressed_count": self.repeated_post_laning_suppressed_count,
                "repeated_objective_suppressed_count": self.repeated_objective_suppressed_count,
                "post_laning_safety_suppressed_count": self.post_laning_safety_suppressed_count,
                "objective_suppressed_by_recent_safety_count": self.objective_suppressed_by_recent_safety_count,
                "item_timing_suppressed_by_safety_count": self.item_timing_suppressed_by_safety_count,
                "death_route_suppressed_count": self.death_route_suppressed_count,
                "low_hp_episode_count": self.low_hp_episode_count,
                "repeated_low_hp_suppressed_count": self.repeated_low_hp_suppressed_count,
                "low_hp_pattern_advice_count": self.low_hp_pattern_advice_count,
                "tactical_hash_changes": self.tactical_hash_changes,
                "last_advice_type": self.last_advice_type,
                "average_llm_latency": _average(self._llm_latencies),
                "p95_llm_latency": _p95(self._llm_latencies),
                "current_cooldown_remaining": self._current_cooldown_remaining_locked(current_time, game_time_seconds),
                "active_advice_until": self._active_advice_until.isoformat() if self._active_advice_until else None,
                "is_pinned": self._is_pinned,
                "suppressed_by_game_time_spacing_count": self.suppressed_by_game_time_spacing_count,
                "heartbeat_nudge_count": self.heartbeat_nudge_count,
                "suppressed_heartbeat_duplicate_count": self.suppressed_heartbeat_duplicate_count,
                "min_game_time_gap_seconds": _minimum(self._advice_game_time_gaps_seconds),
                "max_game_time_silence_seconds": _maximum(self._advice_game_time_gaps_seconds),
                "average_game_time_gap_seconds": _average(self._advice_game_time_gaps_seconds),
                "advice_game_time_gaps_seconds": list(self._advice_game_time_gaps_seconds),
            }

    def state_machine_debug(
        self,
        *,
        current_decision_point: str,
        state: dict[str, Any],
        now: datetime | None = None,
    ) -> dict[str, Any]:
        current_time = _utcnow(now)
        extra_context = state.get("extra_context") if isinstance(state.get("extra_context"), dict) else {}
        with self._lock:
            game_time_seconds = self._game_time_seconds_locked(state, current_time)
            return {
                "current_decision_point": current_decision_point,
                "last_full_advice": self._last_recommendation.model_dump() if self._last_recommendation else None,
                "last_full_advice_at": self._last_updated,
                "active_advice_until": self._active_advice_until.isoformat() if self._active_advice_until else None,
                "is_pinned": self._is_pinned,
                "cooldown_reason": self._cooldown_reason_locked(current_decision_point, current_time, game_time_seconds),
                "last_shown_game_time_seconds": self._last_shown_game_time_seconds,
                "hp_delta_5s": extra_context.get("hp_delta_5s", 0),
                "hp_delta_10s": extra_context.get("hp_delta_10s", 0),
                "recent_damage_taken": extra_context.get("recent_damage_taken", False),
                "alive": extra_context.get("alive"),
                "deaths": extra_context.get("deaths"),
                "match_death_count": extra_context.get("match_death_count", 0),
            }

    def llm_latencies(self) -> list[float]:
        with self._lock:
            return list(self._llm_latencies)

    def latest_advice_snapshot(self) -> dict[str, Any]:
        with self._lock:
            recommendation = (
                self._last_recommendation.model_dump()
                if self._last_recommendation is not None
                else None
            )
            return {
                "recommendation": recommendation,
                "source": self._last_source,
                "llm_used": self._last_llm_used,
                "advice_mode": self._last_advice_mode,
                "last_updated": self._last_updated,
            }

    def wait_for_pending(self, timeout: float = 0.0) -> None:
        deadline = time.perf_counter() + timeout
        while time.perf_counter() < deadline:
            with self._lock:
                if not self._pending_llm_tactical_hashes:
                    return
            time.sleep(0.01)

    # ------------------------------------------------------------------
    # Private locked helpers — all called under self._lock.
    # Groups: hash tracking, suppression logic, low-HP episodes,
    # session management, cooldown, timing, LLM refinement.
    # ------------------------------------------------------------------

    def _update_hashes_locked(self, state_hash: str, tactical_hash: str) -> None:
        self.last_state_hash = state_hash
        if (
            self.last_tactical_state_hash is not None
            and self.last_tactical_state_hash != tactical_hash
        ):
            self.tactical_hash_changes += 1
        self.last_tactical_state_hash = tactical_hash

    def _last_matching_advice_locked(
        self,
        tactical_hash: str,
    ) -> tuple[RecommendationResponse | None, OverlaySource, bool, str]:
        if (
            self._last_recommendation is None
            or self._last_advice_tactical_state_hash != tactical_hash
        ):
            return None, "none", False, "status"
        return (
            self._last_recommendation,
            self._last_source,
            self._last_llm_used,
            self._last_advice_mode,
        )

    def _should_suppress_laning_locked(
        self,
        *,
        decision_point: str,
        state: dict[str, Any],
        recommendation: RecommendationResponse,
        now: datetime,
        game_time_seconds: float | None,
    ) -> tuple[bool, str | None]:
        laning_advice = build_laning_advice(state, decision_point)
        if laning_advice is None:
            return False, None
        if laning_advice.category == "critical_hp_reset" or decision_point == "LOW_HP":
            return False, laning_advice.category

        previous = self._last_laning_category.get(laning_advice.category)
        if previous is None:
            return False, laning_advice.category

        elapsed = self._elapsed_since_locked(previous, now, game_time_seconds)
        changed = important_laning_context_changed(previous, laning_advice)
        same_action = str(previous.get("action") or "") == recommendation.action
        same_category = str(previous.get("category") or "") == laning_advice.category

        if (
            elapsed < REPEAT_WINDOW_SECONDS
            and same_category
            and same_action
            and not _strong_laning_interrupt(previous, laning_advice)
        ):
            return True, laning_advice.category
        if elapsed < REPEAT_WINDOW_SECONDS and not changed:
            return True, laning_advice.category
        if same_action and not changed:
            return True, laning_advice.category
        return False, laning_advice.category

    def _record_laning_advice_locked(
        self,
        *,
        decision_point: str,
        state: dict[str, Any],
        recommendation: RecommendationResponse,
        now: datetime,
        game_time_seconds: float | None,
    ) -> None:
        laning_advice = build_laning_advice(state, decision_point)
        if laning_advice is None:
            return
        self._last_laning_category[laning_advice.category] = {
            "at": now,
            "game_time_seconds": game_time_seconds,
            "category": laning_advice.category,
            "action": recommendation.action,
            "farm_deficit": laning_advice.farm_deficit,
            "pressure_state": laning_advice.pressure_state,
            "pressure_active": laning_advice.pressure_active,
            "position_risk": laning_advice.position_risk,
        }

    def _should_suppress_post_laning_locked(
        self,
        *,
        decision_point: str,
        state: dict[str, Any],
        recommendation: RecommendationResponse,
        now: datetime,
        game_time_seconds: float | None,
    ) -> tuple[bool, str | None, str | None]:
        post_laning_advice = build_post_laning_advice(state, decision_point)
        if post_laning_advice is None:
            return False, None, None

        if decision_point == "ITEM_TIMING" and _post_laning_item_timing_is_unsafe(state):
            return True, post_laning_advice.category, "item_timing_after_recent_safety"

        if decision_point == "ITEM_TIMING" and self._recent_post_laning_safety_locked(
            now,
            seconds=POST_LANING_DEATH_ROUTE_WINDOW_SECONDS,
            game_time_seconds=game_time_seconds,
        ):
            return True, post_laning_advice.category, "item_timing_after_recent_safety"

        if post_laning_advice.category == "post_laning_death_route_reset":
            if decision_point not in DEATH_REVIEW_DECISIONS and not _is_dead_or_respawning(state):
                return True, post_laning_advice.category, "death_route_duplicate"
            if self._should_suppress_death_route_locked(state, now, game_time_seconds):
                return True, post_laning_advice.category, "death_route_duplicate"

        if post_laning_advice.category == "post_laning_low_hp_reset" or decision_point == "LOW_HP":
            return False, post_laning_advice.category, None

        if post_laning_advice.category == "post_laning_objective_caution":
            if self._recent_post_laning_safety_locked(
                now,
                seconds=POST_LANING_RECENT_SAFETY_WINDOW_SECONDS,
                game_time_seconds=game_time_seconds,
            ):
                if not _objective_context_changed_clearly(state):
                    return True, post_laning_advice.category, "objective_after_recent_safety"
            if (
                post_laning_advice.objective_context_missing
                and not post_laning_advice.clear_pressure_context
            ):
                return True, post_laning_advice.category, "objective_context_missing"
            if self._last_objective_advice_at is not None:
                elapsed = self._elapsed_since_time_locked(
                    at=self._last_objective_advice_at,
                    game_time_at=getattr(self, "_last_objective_advice_game_time", None),
                    now=now,
                    game_time_seconds=game_time_seconds,
                )
                if elapsed < OBJECTIVE_REPEAT_WINDOW_SECONDS:
                    return True, post_laning_advice.category, "duplicate_objective"

        if self._recent_post_laning_safety_locked(
            now,
            seconds=POST_LANING_RECENT_SAFETY_WINDOW_SECONDS,
            game_time_seconds=game_time_seconds,
        ) and _is_lower_value_post_laning_advice(decision_point, post_laning_advice.category):
            if not _post_laning_safety_suppression_exception(state, decision_point, post_laning_advice):
                return True, post_laning_advice.category, "recent_safety"

        previous = self._last_post_laning_category.get(post_laning_advice.category)
        if previous is None:
            return False, post_laning_advice.category, None

        elapsed = self._elapsed_since_locked(previous, now, game_time_seconds)
        changed = important_post_laning_context_changed(previous, post_laning_advice)
        same_action = str(previous.get("action") or "") == recommendation.action
        same_category = str(previous.get("category") or "") == post_laning_advice.category
        strong_interrupt = _strong_post_laning_interrupt(previous, post_laning_advice)

        if elapsed <= POST_LANING_SAME_ACTION_WINDOW_SECONDS and same_category and same_action and not strong_interrupt:
            return True, post_laning_advice.category, "duplicate_post_laning"
        if elapsed < POST_LANING_REPEAT_WINDOW_SECONDS and same_category and same_action and not strong_interrupt:
            return True, post_laning_advice.category, "duplicate_post_laning"
        if elapsed < POST_LANING_REPEAT_WINDOW_SECONDS and not changed:
            return True, post_laning_advice.category, "duplicate_post_laning"
        if same_action and not changed and not strong_interrupt:
            return True, post_laning_advice.category, "duplicate_post_laning"
        return False, post_laning_advice.category, None

    def _record_post_laning_advice_locked(
        self,
        *,
        decision_point: str,
        state: dict[str, Any],
        recommendation: RecommendationResponse,
        now: datetime,
        game_time_seconds: float | None,
    ) -> None:
        post_laning_advice = build_post_laning_advice(state, decision_point)
        if post_laning_advice is None:
            return
        self._last_post_laning_category[post_laning_advice.category] = {
            "at": now,
            "game_time_seconds": game_time_seconds,
            "category": post_laning_advice.category,
            "action": recommendation.action,
            "farm_quality": post_laning_advice.farm_quality,
            "hp_pressure_state": post_laning_advice.hp_pressure_state,
            "pressure_active": post_laning_advice.pressure_active,
            "position_risk": post_laning_advice.position_risk,
            "position_zone": post_laning_advice.position_zone,
        }
        if post_laning_advice.category == "post_laning_objective_caution":
            self._last_objective_advice_at = now
            self._last_objective_advice_game_time = game_time_seconds

    def _should_suppress_post_laning_low_hp_locked(
        self,
        *,
        state: dict[str, Any],
        now: datetime,
        game_time_seconds: float | None,
    ) -> bool:
        if _to_int(state.get("minute"), 0) < 10:
            return False
        if self._last_low_hp_urgent_at is None:
            return False
        if self._last_low_hp_pattern_at is not None:
            elapsed_pattern = self._elapsed_since_time_locked(
                at=self._last_low_hp_pattern_at,
                game_time_at=getattr(self, "_last_low_hp_pattern_game_time", None),
                now=now,
                game_time_seconds=game_time_seconds,
            )
            if (
                elapsed_pattern < POST_LANING_RECENT_SAFETY_WINDOW_SECONDS
                and not _post_laning_new_death_or_severe_pressure(state)
            ):
                return True
        elapsed = self._elapsed_since_time_locked(
            at=self._last_low_hp_urgent_at,
            game_time_at=getattr(self, "_last_low_hp_urgent_game_time", None),
            now=now,
            game_time_seconds=game_time_seconds,
        )
        if elapsed >= POST_LANING_RECENT_SAFETY_WINDOW_SECONDS:
            return False
        if self._post_laning_hp_recovered_since_safety:
            return False
        if _post_laning_new_death_or_severe_pressure(state):
            return False
        return True

    def _should_suppress_death_route_locked(
        self,
        state: dict[str, Any],
        now: datetime,
        game_time_seconds: float | None,
    ) -> bool:
        if (
            self._recent_post_laning_safety_locked(
                now,
                seconds=POST_LANING_DEATH_ROUTE_WINDOW_SECONDS,
                game_time_seconds=game_time_seconds,
            )
            and not _is_dead_or_respawning(state)
        ):
            return True

        if self._last_low_hp_pattern_at is not None:
            elapsed_pattern = self._elapsed_since_time_locked(
                at=self._last_low_hp_pattern_at,
                game_time_at=getattr(self, "_last_low_hp_pattern_game_time", None),
                now=now,
                game_time_seconds=game_time_seconds,
            )
            if elapsed_pattern < POST_LANING_DEATH_ROUTE_WINDOW_SECONDS:
                return True

        if self._last_post_laning_death_route_at is None:
            return False

        elapsed = self._elapsed_since_time_locked(
            at=self._last_post_laning_death_route_at,
            game_time_at=getattr(self, "_last_post_laning_death_route_game_time", None),
            now=now,
            game_time_seconds=game_time_seconds,
        )
        if elapsed >= POST_LANING_DEATH_ROUTE_WINDOW_SECONDS:
            return False

        current_event_id = _death_event_id(state)
        if current_event_id and current_event_id != self._last_post_laning_death_route_event_id:
            return False
        return True

    def _record_safety_advice_locked(
        self,
        *,
        decision_point: str,
        state: dict[str, Any],
        post_laning_category: str | None,
        now: datetime,
        game_time_seconds: float | None,
    ) -> None:
        if _to_int(state.get("minute"), 0) < 10:
            return
        if decision_point == "LOW_HP":
            self._last_low_hp_urgent_at = now
            self._last_low_hp_urgent_game_time = game_time_seconds
            self._record_post_laning_safety_locked(
                now=now,
                state=state,
                category=post_laning_category or "post_laning_low_hp_reset",
                game_time_seconds=game_time_seconds,
            )
            return
        if decision_point in DEATH_REVIEW_DECISIONS or post_laning_category == "post_laning_death_route_reset":
            self._record_post_laning_safety_locked(
                now=now,
                state=state,
                category=post_laning_category or decision_point,
                game_time_seconds=game_time_seconds,
            )

    def _record_post_laning_safety_locked(
        self,
        *,
        now: datetime,
        state: dict[str, Any],
        category: str,
        game_time_seconds: float | None,
    ) -> None:
        if _to_int(state.get("minute"), 0) < 10:
            return
        self._last_post_laning_safety_at = now
        self._last_post_laning_safety_game_time = game_time_seconds
        self._post_laning_hp_recovered_since_safety = False
        if category == "post_laning_death_route_reset":
            self._last_post_laning_death_route_at = now
            self._last_post_laning_death_route_game_time = game_time_seconds
            self._last_post_laning_death_route_event_id = _death_event_id(state)
        if category == "low_hp_pattern":
            self._last_low_hp_pattern_at = now
            self._last_low_hp_pattern_game_time = game_time_seconds

    def _recent_post_laning_safety_locked(
        self,
        now: datetime,
        *,
        seconds: int,
        game_time_seconds: float | None,
    ) -> bool:
        if self._last_post_laning_safety_at is None:
            return False
        return self._elapsed_since_time_locked(
            at=self._last_post_laning_safety_at,
            game_time_at=getattr(self, "_last_post_laning_safety_game_time", None),
            now=now,
            game_time_seconds=game_time_seconds,
        ) <= seconds

    def _update_low_hp_recovery_locked(self, state: dict[str, Any]) -> None:
        hp_percent = _ctx_int(state, "hp_percent", _to_int(state.get("hp_percent"), 100))
        if _is_dead_or_respawning(state):
            self._low_hp_episode_active = False
            self._low_hp_episode_lowest_hp = None
            self._low_hp_episode_repeat_count = 0
            self._low_hp_episode_pattern_shown = False
            self._low_hp_episode_last_severe_signature = None
            return
        if hp_percent > 60:
            self._low_hp_episode_active = False
            self._low_hp_episode_lowest_hp = None
            self._low_hp_episode_repeat_count = 0
            self._low_hp_episode_pattern_shown = False
            self._low_hp_episode_last_severe_signature = None
            if _to_int(state.get("minute"), 0) >= 10:
                self._post_laning_hp_recovered_since_safety = True

    def _low_hp_episode_action_locked(self, state: dict[str, Any]) -> str:
        hp_percent = _ctx_int(state, "hp_percent", _to_int(state.get("hp_percent"), 100))
        severe_signature = _low_hp_severe_signature(state)

        if not self._low_hp_episode_active:
            self._start_low_hp_episode_locked(hp_percent, severe_signature)
            return "show"

        lowest_hp = self._low_hp_episode_lowest_hp
        significant_drop = lowest_hp is not None and hp_percent <= lowest_hp - 15
        new_severe_event = bool(
            severe_signature
            and severe_signature != self._low_hp_episode_last_severe_signature
        )
        if significant_drop or new_severe_event:
            self._low_hp_episode_lowest_hp = (
                hp_percent if lowest_hp is None else min(lowest_hp, hp_percent)
            )
            self._low_hp_episode_last_severe_signature = severe_signature
            self._low_hp_episode_repeat_count = 0
            return "show"

        self._low_hp_episode_repeat_count += 1
        if self._low_hp_episode_repeat_count >= 2 and not self._low_hp_episode_pattern_shown:
            self._low_hp_episode_pattern_shown = True
            if not self._low_hp_pattern_advice_shown:
                self._low_hp_pattern_advice_shown = True
                return "pattern"
        return "suppress"

    def _start_low_hp_episode_locked(
        self,
        hp_percent: int,
        severe_signature: str | None,
    ) -> None:
        self.low_hp_episode_count += 1
        self._low_hp_episode_id += 1
        self._low_hp_episode_active = True
        self._low_hp_episode_lowest_hp = hp_percent
        self._low_hp_episode_repeat_count = 0
        self._low_hp_episode_pattern_shown = False
        self._low_hp_episode_last_severe_signature = severe_signature

    def _recent_low_hp_pattern_locked(
        self,
        now: datetime,
        game_time_seconds: float | None,
    ) -> bool:
        if self._low_hp_pattern_last_at is None:
            return False
        return self._elapsed_since_time_locked(
            at=self._low_hp_pattern_last_at,
            game_time_at=getattr(self, "_last_low_hp_pattern_game_time", None),
            now=now,
            game_time_seconds=game_time_seconds,
        ) < REPEAT_WINDOW_SECONDS

    def _active_result_locked(
        self,
        *,
        decision_point: str,
        now: datetime,
        next_allowed: int,
        suppressed_reason: str,
    ) -> ScheduledAdvice | None:
        if (
            self._last_recommendation is None
            or self._active_advice_until is None
            or now >= self._active_advice_until
        ):
            return None

        return self._result_locked(
            status="active_advice",
            decision_point=self.last_advice_type or decision_point,
            recommendation=self._last_recommendation,
            source=self._last_source,
            llm_used=self._last_llm_used,
            next_allowed=next_allowed,
            new_advice=False,
            advice_mode=self._last_advice_mode,
            suppressed_reason=suppressed_reason,
        )

    def _set_active_advice_locked(
        self,
        decision_point: str,
        state: dict[str, Any],
        now: datetime,
    ) -> None:
        duration = _active_advice_duration(decision_point, state)
        self._active_advice_until = now + duration
        self._is_pinned = decision_point in DEATH_REVIEW_DECISIONS or _is_dead_or_respawning(state)

    def _ensure_session_locked(self, now: datetime, minute: int, state: dict[str, Any]) -> None:
        session_id = _session_id_from_state(state)
        if self.match_started_at is None:
            self.match_started_at = now
            self.match_session_id = session_id
            self._last_seen_minute = minute
            return

        if session_id and self.match_session_id and session_id != self.match_session_id:
            self._reset_locked()
            self.match_started_at = now
            self.match_session_id = session_id
            self._last_seen_minute = minute
            return

        if session_id and self.match_session_id is None:
            self.match_session_id = session_id

        if self._last_seen_minute is not None and minute < self._last_seen_minute - 5:
            self._reset_locked()
            self.match_started_at = now
            self.match_session_id = session_id

        self._last_seen_minute = minute

    def _game_time_seconds_locked(self, state: dict[str, Any], now: datetime) -> float | None:
        explicit = _state_game_time_seconds(state)
        if explicit is not None:
            return explicit
        if self.match_started_at is None:
            return None
        return max(0.0, (now - self.match_started_at).total_seconds())

    def _elapsed_since_locked(
        self,
        previous: dict[str, Any],
        now: datetime,
        game_time_seconds: float | None,
    ) -> float:
        return self._elapsed_since_time_locked(
            at=previous.get("at"),
            game_time_at=previous.get("game_time_seconds"),
            now=now,
            game_time_seconds=game_time_seconds,
        )

    def _elapsed_since_time_locked(
        self,
        *,
        at: Any,
        game_time_at: Any,
        now: datetime,
        game_time_seconds: float | None,
    ) -> float:
        previous_game_time = _optional_float(game_time_at)
        if previous_game_time is not None and game_time_seconds is not None:
            return max(0.0, game_time_seconds - previous_game_time)
        if isinstance(at, datetime):
            return max(0.0, (now - at).total_seconds())
        return 999999.0

    def _game_time_spacing_remaining_locked(
        self,
        *,
        decision_point: str,
        state: dict[str, Any],
        recommendation: RecommendationResponse,
        advice_mode: str,
        category: str | None,
        game_time_seconds: float | None,
    ) -> tuple[int, float | None]:
        if self._last_shown_game_time_seconds is None or game_time_seconds is None:
            return 0, None

        gap = max(0.0, game_time_seconds - self._last_shown_game_time_seconds)
        if decision_point in {"LOW_HP", *DEATH_REVIEW_DECISIONS}:
            return 0, gap

        min_gap = 0
        normalized_category = str(category or decision_point or "").strip()
        action_hash = _action_hash(recommendation.action)
        same_action = action_hash == self._last_shown_action_hash
        same_category = normalized_category and normalized_category == self._last_shown_category
        post_laning = _to_int(state.get("minute"), 0) >= 10

        if decision_point in {"RECENT_DAMAGE_WARNING", "OVERSTAY_WARNING"}:
            if self._last_shown_decision_point in {
                "LOW_HP",
                "RECENT_DAMAGE_WARNING",
                "OVERSTAY_WARNING",
                *DEATH_REVIEW_DECISIONS,
            }:
                min_gap = max(min_gap, RECENT_SAFETY_GAME_TIME_GAP_SECONDS)

        if same_action and same_category:
            min_gap = max(min_gap, SAME_ACTION_GAME_TIME_GAP_SECONDS)
        elif advice_mode == "coaching":
            min_gap = max(min_gap, COACHING_GAME_TIME_GAP_SECONDS)

        if (
            post_laning
            and advice_mode == "coaching"
            and str(recommendation.priority or "").lower() in {"medium", "high"}
            and same_category
        ):
            min_gap = max(min_gap, POST_LANING_GAME_TIME_GAP_SECONDS)

        if min_gap <= 0 or gap >= min_gap:
            return 0, gap
        return int(max(1, round(min_gap - gap))), gap

    def _heartbeat_nudge_locked(
        self,
        *,
        decision_point: str,
        state: dict[str, Any],
        recommendation: RecommendationResponse,
        category: str | None,
        reason: str | None,
        game_time_seconds: float | None,
    ) -> RecommendationResponse | None:
        if not self._heartbeat_allowed_locked(
            decision_point=decision_point,
            state=state,
            game_time_seconds=game_time_seconds,
        ):
            return None

        gap = max(0.0, game_time_seconds - (self._last_shown_game_time_seconds or 0.0))
        if (
            category
            and category == self._last_shown_category
            and _action_hash(recommendation.action) == self._last_shown_action_hash
            and gap < HEARTBEAT_DUPLICATE_WAIT_SECONDS
        ):
            self.suppressed_heartbeat_duplicate_count += 1
            return None

        if reason in {
            "objective_after_recent_safety",
            "objective_context_missing",
            "duplicate_objective",
            "item_timing_after_recent_safety",
            "death_route_duplicate",
        }:
            return None

        action, reason_text, risk = _heartbeat_copy(state)
        return RecommendationResponse(
            action=action,
            reason=reason_text,
            risk=risk,
            priority="low",
            time_window="reassess in 60-90 seconds",
            source="fallback",
        )

    def _heartbeat_allowed_locked(
        self,
        *,
        decision_point: str,
        state: dict[str, Any],
        game_time_seconds: float | None,
    ) -> bool:
        if game_time_seconds is None or self._last_shown_game_time_seconds is None:
            return False
        if game_time_seconds - self._last_shown_game_time_seconds < HEARTBEAT_NUDGE_SECONDS:
            return False
        if _to_int(state.get("minute"), 0) < 10:
            return False
        if decision_point in {
            "LOW_HP",
            "RECENT_DAMAGE_WARNING",
            "OVERSTAY_WARNING",
            "BUYBACK_AVAILABLE",
            "DISABLED_STATUS",
            *DEATH_REVIEW_DECISIONS,
        }:
            return False
        if _is_dead_or_respawning(state) or self._is_pinned:
            return False
        if self._last_shown_decision_point in {"LOW_HP", *DEATH_REVIEW_DECISIONS}:
            recent_safety_gap = game_time_seconds - self._last_shown_game_time_seconds
            if recent_safety_gap < POST_LANING_RECENT_SAFETY_WINDOW_SECONDS:
                return False
        if not _heartbeat_context_is_confident(state):
            return False
        return _heartbeat_safe_category_available(state)

    def _record_shown_advice_timing_locked(
        self,
        *,
        decision_point: str,
        state: dict[str, Any],
        recommendation: RecommendationResponse,
        category: str | None,
        game_time_seconds: float | None,
    ) -> float | None:
        gap = None
        if self._last_shown_game_time_seconds is not None and game_time_seconds is not None:
            gap = max(0.0, game_time_seconds - self._last_shown_game_time_seconds)
            self._advice_game_time_gaps_seconds.append(round(gap, 1))

        self._last_shown_game_time_seconds = game_time_seconds
        self._last_shown_decision_point = decision_point
        self._last_shown_category = str(category or decision_point or "").strip()
        self._last_shown_action_hash = _action_hash(recommendation.action)
        return None if gap is None else round(gap, 1)

    def _result_locked(
        self,
        *,
        status: OverlayStatus,
        decision_point: str,
        recommendation: RecommendationResponse | None,
        source: OverlaySource,
        llm_used: bool,
        next_allowed: int,
        new_advice: bool,
        advice_mode: str,
        suppressed_reason: str | None,
        game_time_gap_since_previous_advice: float | None = None,
        suppressed_by_game_time_spacing: bool = False,
    ) -> ScheduledAdvice:
        return ScheduledAdvice(
            status=status,
            decision_point=decision_point,
            recommendation=recommendation,
            advice_count=self.advice_count,
            llm_used=llm_used,
            source=source,
            last_updated=self._last_updated,
            next_allowed_advice_in_seconds=max(0, next_allowed),
            new_advice=new_advice,
            advice_mode=advice_mode,
            suppressed_reason=suppressed_reason,
            active_advice_until=self._active_advice_until.isoformat() if self._active_advice_until else None,
            last_visible_advice=self._last_recommendation.model_dump() if self._last_recommendation else None,
            is_pinned=self._is_pinned,
            low_hp_episode_id=self._low_hp_episode_id if decision_point == "LOW_HP" else None,
            game_time_gap_since_previous_advice=game_time_gap_since_previous_advice,
            suppressed_by_game_time_spacing=suppressed_by_game_time_spacing,
        )

    def _cooldown_remaining_locked(
        self,
        decision_point: str,
        now: datetime,
        game_time_seconds: float | None,
    ) -> int:
        if self.last_advice_at is None:
            return 0

        if (
            decision_point in {
                "LOW_HP",
                "DISABLED_STATUS",
                "RECENT_DAMAGE_WARNING",
                "OVERSTAY_WARNING",
                *DEATH_REVIEW_DECISIONS,
            }
            and self.last_advice_type != decision_point
        ):
            return 0

        cooldown = self._cooldown_for_type_locked(decision_point)
        elapsed = self._elapsed_since_time_locked(
            at=self.last_advice_at,
            game_time_at=self._last_shown_game_time_seconds,
            now=now,
            game_time_seconds=game_time_seconds,
        )
        return max(0, int(cooldown - elapsed))

    def _current_cooldown_remaining_locked(
        self,
        now: datetime,
        game_time_seconds: float | None,
    ) -> int:
        if self.last_advice_at is None or self.last_advice_type is None:
            return 0
        cooldown = self._cooldown_for_type_locked(self.last_advice_type)
        elapsed = self._elapsed_since_time_locked(
            at=self.last_advice_at,
            game_time_at=self._last_shown_game_time_seconds,
            now=now,
            game_time_seconds=game_time_seconds,
        )
        return max(0, int(cooldown - elapsed))

    def _cooldown_for_type_locked(self, decision_point: str) -> int:
        if decision_point in {"LOW_HP", "DISABLED_STATUS", *DEATH_REVIEW_DECISIONS}:
            return self.urgent_cooldown_seconds
        return self.regular_cooldown_seconds

    def _cooldown_reason_locked(
        self,
        decision_point: str,
        now: datetime,
        game_time_seconds: float | None,
    ) -> str | None:
        if self._last_recommendation is not None and self._active_advice_until and now < self._active_advice_until:
            return "cooldown_keep_visible"
        remaining = self._cooldown_remaining_locked(decision_point, now, game_time_seconds)
        return "cooldown" if remaining > 0 else None

    def _should_start_llm_locked(self, decision_point: str, tactical_hash: str) -> bool:
        if decision_point in {"NO_ADVICE", "SOFT_STATUS", "LOW_HP", *DEATH_REVIEW_DECISIONS}:
            return False
        if not self._llm_enabled():
            return False
        if tactical_hash in self._pending_llm_tactical_hashes:
            return False
        if decision_point in {"OBJECTIVE_FIGHT_CHECK", "BAD_FIGHT_RISK", "ITEM_TIMING", "HERO_SURVIVABILITY_RISK"}:
            self._pending_llm_tactical_hashes.add(tactical_hash)
            self.llm_call_count += 1
            return True
        if self.advice_count % LLM_REFINEMENT_EVERY_N_ADVICES == 0:
            self._pending_llm_tactical_hashes.add(tactical_hash)
            self.llm_call_count += 1
            return True
        return False

    def _llm_enabled(self) -> bool:
        if self.enable_llm is not None:
            return self.enable_llm
        return USE_LLM and is_llm_provider_enabled()

    def _start_llm_refinement(
        self,
        tactical_hash: str,
        request: GameSituationRequest,
        decision_point: str,
        rag_context: list[str],
    ) -> None:
        thread = threading.Thread(
            target=self._run_llm_refinement,
            args=(tactical_hash, request, decision_point, rag_context),
            daemon=True,
        )
        thread.start()

    def _run_llm_refinement(
        self,
        tactical_hash: str,
        request: GameSituationRequest,
        decision_point: str,
        rag_context: list[str],
    ) -> None:
        started = time.perf_counter()
        result = generate_llm_recommendation(request, decision_point, rag_context)
        latency = time.perf_counter() - started

        with self._lock:
            self._pending_llm_tactical_hashes.discard(tactical_hash)
            self._llm_latencies.append(latency)

            if self.last_tactical_state_hash != tactical_hash:
                self.stale_llm_count += 1
                return

            if result.recommendation is None:
                return

            policy = build_advice_policy(request, decision_point)
            recommendation = apply_advice_policy(result.recommendation, policy)
            recommendation = _compact_recommendation(recommendation, decision_point)
            ux_result = apply_ux_policy(
                recommendation,
                decision_point,
                [],
                action_type=policy["action_type"],
            )
            if ux_result["recommendation"] is None:
                if ux_result["suppressed_reason"] == "duplicate":
                    self.duplicate_suppressed_count += 1
                return
            recommendation = clean_recommendation_text(ux_result["recommendation"], decision_point)
            if not _is_safe_recommendation(recommendation, decision_point):
                return

            self._last_recommendation = recommendation
            self._last_source = "llm"
            self._last_llm_used = True
            self.llm_applied_count += 1
            self._last_updated = datetime.now(timezone.utc).isoformat()
            if self._advice_history:
                self._advice_history[-1]["source"] = "llm"
                self._advice_history[-1]["action"] = recommendation.action


def build_state_hash(state: dict[str, Any], decision_point: str) -> str:
    minute = _to_int(state.get("minute"), 0)
    hp_percent = _to_int(state.get("hp_percent"), 100)
    extra_context = state.get("extra_context") if isinstance(state.get("extra_context"), dict) else {}
    payload = {
        "hero": str(state.get("hero", "")).strip().lower(),
        "minute_bucket": minute,
        "hp_bucket": hp_percent // 10,
        "items": sorted(str(item).strip().lower() for item in state.get("items", [])),
        "game_state": str(state.get("game_state", "")).strip().lower(),
        "team_status": str(state.get("team_status", "")).strip().lower(),
        "decision_point": decision_point,
        "death_event_id": extra_context.get("last_death_event_id") if decision_point in DEATH_REVIEW_DECISIONS else None,
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def build_tactical_state_hash(
    state: dict[str, Any],
    decision_point: str,
    *,
    action_type: str | None = None,
) -> str:
    if not action_type:
        action_type = str(build_advice_policy(state, decision_point)["action_type"])
    extra_context = state.get("extra_context") if isinstance(state.get("extra_context"), dict) else {}
    payload = {
        "hero": str(state.get("hero", "")).strip().lower(),
        "decision_point": decision_point,
        "action_type": action_type,
        "game_phase": _game_phase(_to_int(state.get("minute"), 0)),
        "hp_bucket": _hp_bucket(_to_int(state.get("hp_percent"), 100)),
        "minute_bucket": _minute_bucket(_to_int(state.get("minute"), 0)),
        "team_status": _simplify_team_status(state.get("team_status", "")),
        "key_items": _key_item_signature(state.get("items", [])),
        "death_event_id": extra_context.get("last_death_event_id") if decision_point in DEATH_REVIEW_DECISIONS else None,
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def _compact_recommendation(
    recommendation: RecommendationResponse,
    decision_point: str | None = None,
) -> RecommendationResponse:
    recommendation = clean_recommendation_text(recommendation, decision_point)
    return RecommendationResponse(
        action=_truncate(_naturalize_action(recommendation.action, decision_point), MAX_ACTION_LENGTH),
        reason=_truncate(recommendation.reason, MAX_REASON_LENGTH),
        risk=recommendation.risk,
        priority=recommendation.priority,
        time_window=recommendation.time_window,
        source=recommendation.source,
    )


def _naturalize_action(action: str, decision_point: str | None = None) -> str:
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
        "conserve_mana_or_reset": "Conserve mana or reset before taking a fight.",
        "wait_out_disable": "Wait out the disable and avoid forcing actions.",
        "check_buyback_value": "Check buyback value only for base defense or a major objective.",
        "prepare_next_move": "Use the respawn time to plan your next safe farming route.",
        "stay_hidden_until_team_ready": "Stay hidden until your team is ready to make a move.",
        "respect_hero_safety_window": "Respect your hero's safety window before forcing a fight.",
        "plan_safer_respawn_route": "Use the respawn time to plan a safer next route.",
        "break_repeated_death_pattern": "After respawn, reset your route and avoid repeating the same risky path.",
        "respect_escape_cooldown_after_respawn": "After respawn, avoid committing forward until your escape is ready.",
        "reset_before_resources_collapse": "After respawn, reset earlier when HP or key resources get low.",
        "soft_status": "Monitoring lane - no urgent advice.",
    }
    key = action.strip().lower()
    canonical_key = key.replace(" ", "_").replace("-", "_")
    if canonical_key in replacements:
        return replacements[canonical_key]
    if "_" in key and len(action.strip().split()) == 1:
        return key.replace("_", " ").capitalize() + "."
    return clean_recommendation_text(
        RecommendationResponse(
            action=action,
            reason="ok",
            risk="ok",
            priority="low",
            time_window="reassess in 60 seconds",
        ),
        decision_point,
    ).action


def _is_safe_recommendation(recommendation: RecommendationResponse, decision_point: str) -> bool:
    if len(recommendation.action) > MAX_ACTION_LENGTH or len(recommendation.reason) > MAX_REASON_LENGTH:
        return False
    text = f"{recommendation.action} {recommendation.reason}".lower()
    mechanical_terms = (
        "press ",
        "click ",
        "hotkey",
        "animation cancel",
        "manta dodge",
        "blink dodge",
    )
    if any(term in text for term in mechanical_terms):
        return False
    if decision_point in {
        "BAD_FIGHT_RISK",
        "LOW_MANA",
        "LOW_HP_WARNING",
        "RECENT_DAMAGE_WARNING",
        "OVERSTAY_WARNING",
        "DISABLED_STATUS",
        "BUYBACK_AVAILABLE",
        "DEAD_WAIT",
        "SMOKED_STATUS",
        "HERO_SURVIVABILITY_RISK",
        "ABILITY_SAFETY_COOLDOWN",
        "LANING_REGEN_CHECK",
        *DEATH_REVIEW_DECISIONS,
    } and _suggests_fighting_without_safety(text):
        return False
    if decision_point != "LOW_HP":
        return True

    return not _suggests_fighting_without_safety(text)


def _strong_laning_interrupt(previous: dict[str, Any], current: Any) -> bool:
    previous_pressure = str(previous.get("pressure_state") or "")
    if previous_pressure != current.pressure_state:
        return True

    previous_pressure_active = bool(previous.get("pressure_active"))
    if previous_pressure_active != current.pressure_active:
        return True

    previous_position_risk = str(previous.get("position_risk") or "")
    return previous_position_risk != "high" and current.position_risk == "high"


def _strong_post_laning_interrupt(previous: dict[str, Any], current: Any) -> bool:
    if current.category == "post_laning_low_hp_reset" or current.death_context:
        return True

    previous_position_risk = str(previous.get("position_risk") or "")
    if previous_position_risk != "high" and current.position_risk == "high":
        return True

    return current.hp_pressure_state == "critical"


def _is_lower_value_post_laning_advice(decision_point: str, category: str) -> bool:
    if decision_point in {"LOW_HP", *DEATH_REVIEW_DECISIONS}:
        return False
    return category in {
        "post_laning_farm_recovery",
        "post_laning_pressure_avoidance",
        "post_laning_safe_farm_route",
        "post_laning_objective_caution",
    }


def _post_laning_safety_suppression_exception(
    state: dict[str, Any],
    decision_point: str,
    post_laning_advice: Any,
) -> bool:
    if _post_laning_new_death_or_severe_pressure(state):
        return True
    if post_laning_advice.position_risk == "high":
        return True
    if decision_point == "OBJECTIVE_FIGHT_CHECK" and _objective_context_changed_clearly(state):
        return True
    return False


def _post_laning_item_timing_is_unsafe(state: dict[str, Any]) -> bool:
    if _to_int(state.get("minute"), 0) < 10:
        return False
    hp_percent = _ctx_int(state, "hp_percent", _to_int(state.get("hp_percent"), 100))
    return hp_percent < 35 or _hp_pressure_state(state) == "critical"


def _post_laning_new_death_or_severe_pressure(state: dict[str, Any]) -> bool:
    if _is_dead_or_respawning(state):
        return True
    if _ctx_value(state, "death_count_changed", False):
        return True
    if _ctx_value(state, "selected_player_death_nearby", False):
        return True
    if _ctx_value(state, "near_player_death", False):
        return True
    event_context = str(state.get("event_context") or _ctx_value(state, "event_context", "") or "").lower()
    return "death" in event_context


def _objective_context_changed_clearly(state: dict[str, Any]) -> bool:
    objective_context = str(_ctx_value(state, "objective_context", "") or "").strip().lower()
    objective_for_selected = _ctx_value(state, "objective_for_selected_team", None)
    team_status = str(_ctx_value(state, "team_status", state.get("team_status", "")) or "").strip().lower()
    selected_objective = objective_for_selected is True or str(objective_for_selected).lower() == "true"
    friendly_objective = objective_context == "friendly_objective"
    return (selected_objective or friendly_objective) and team_status in {"advantage", "even"}


def _hp_pressure_state(state: dict[str, Any]) -> str:
    return str(_ctx_value(state, "hp_pressure_state", "") or "").strip().lower()


def _death_event_id(state: dict[str, Any]) -> str | None:
    value = _ctx_value(state, "last_death_event_id", None)
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _post_laning_int(state: dict[str, Any]) -> int:
    return 1 if _to_int(state.get("minute"), 0) >= 10 else 0


def _low_hp_severe_signature(state: dict[str, Any]) -> str | None:
    extra_context = state.get("extra_context") if isinstance(state.get("extra_context"), dict) else {}
    keys = (
        "death_count_changed",
        "near_player_death",
        "selected_player_death_nearby",
        "recent_damage_taken",
        "overstay_warning",
    )
    active = [key for key in keys if _ctx_value(state, key, False)]
    event_context = str(state.get("event_context") or extra_context.get("event_context") or "")
    if "death" in event_context.lower():
        active.append("death_context")
    if not active:
        return None
    minute = _to_int(state.get("minute"), 0)
    return f"{minute}:{'+'.join(sorted(set(active)))}"


def _low_hp_pattern_recommendation() -> RecommendationResponse:
    return RecommendationResponse(
        action="Stop re-contesting the pressured lane until you reset HP.",
        reason="Repeated low-HP returns can cost more than missing one wave.",
        risk="High risk if you keep returning to pressure without resetting.",
        priority="high",
        time_window="next 60-90 seconds",
        source="fallback",
    )


def _heartbeat_context_is_confident(state: dict[str, Any]) -> bool:
    confidence = str(_ctx_value(state, "context_confidence", "high") or "high").strip().lower()
    return confidence in {"high", "medium"}


def _heartbeat_safe_category_available(state: dict[str, Any]) -> bool:
    if _ctx_int(state, "hp_percent", _to_int(state.get("hp_percent"), 100)) < 35:
        return False
    if _hp_pressure_state(state) == "critical":
        return False
    if _is_dead_or_respawning(state):
        return False
    return True


def _heartbeat_copy(state: dict[str, Any]) -> tuple[str, str, str]:
    hp_percent = _ctx_int(state, "hp_percent", _to_int(state.get("hp_percent"), 100))
    mana_percent = _ctx_int(state, "mana_percent", 100)
    hp_pressure = _hp_pressure_state(state)
    position_risk = str(_ctx_value(state, "position_risk", "") or "").strip().lower()
    position_zone = str(_ctx_value(state, "position_zone", "") or "").strip().lower()
    pressure_active = hp_pressure in {"pressured_but_stable", "risky"}
    pressure_active = pressure_active or any(
        token in str(state.get("game_state") or "").lower()
        for token in ("pressure", "risk", "damage")
    )

    if hp_percent <= 55 or mana_percent <= 25:
        return (
            "Reset resources before showing on another lane.",
            "A short reset keeps the next farming route safer without forcing a fight.",
            "Medium risk if you keep showing while resources are low.",
        )
    if position_risk == "high" or position_zone == "deep_enemy_side":
        return (
            "Farm closer to a safer zone until enemy positions are clearer.",
            "Enemy locations are not confirmed, so exposed farming is unnecessary risk.",
            "Medium risk if you stay visible in an exposed area.",
        )
    if pressure_active:
        return (
            "Avoid the pressured lane and farm a safer wave or nearby camp.",
            "Staying in pressure can cost HP and slow your recovery.",
            "Medium risk if you keep farming the pressured area.",
        )
    return (
        "Keep farming the safest wave-and-camp route and reassess soon.",
        "Your farm route is the safest low-risk choice while enemy locations are uncertain.",
        "Low risk if you keep farming without forcing uncertain fights.",
    )


def _is_heartbeat_recommendation(recommendation: RecommendationResponse) -> bool:
    return recommendation.priority == "low" and recommendation.time_window == "reassess in 60-90 seconds"


def _suggests_fighting_without_safety(text: str) -> bool:
    fight_terms = ("fight", "engage", "commit", "contest", "join", "attack", "initiate")
    safety_terms = ("avoid", "retreat", "reset", "farm", "safe", "wait", "back", "skip", "only if")
    suggests_fight = any(term in text for term in fight_terms)
    has_safety = any(term in text for term in safety_terms)
    return suggests_fight and not has_safety


def _truncate(value: str, max_length: int) -> str:
    if len(value) <= max_length:
        return value
    return value[: max_length - 3].rstrip() + "..."


def _utcnow(value: datetime | None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _active_advice_duration(decision_point: str, state: dict[str, Any]) -> timedelta:
    if decision_point in DEATH_REVIEW_DECISIONS or _is_dead_or_respawning(state):
        respawn_seconds = _ctx_int(state, "respawn_seconds", 0)
        return timedelta(seconds=max(15, respawn_seconds))
    if decision_point in {"LOW_HP", "DISABLED_STATUS"}:
        return timedelta(seconds=12)
    if decision_point in {
        "RECENT_DAMAGE_WARNING",
        "OVERSTAY_WARNING",
        "LOW_HP_WARNING",
        "ABILITY_SAFETY_COOLDOWN",
        "HERO_SURVIVABILITY_RISK",
    }:
        return timedelta(seconds=10)
    return timedelta(seconds=8)


def _is_dead_or_respawning(state: dict[str, Any]) -> bool:
    alive = _ctx_value(state, "alive", True)
    respawn_seconds = _ctx_int(state, "respawn_seconds", 0)
    return alive is False or str(alive).strip().lower() in {"false", "0", "no"} or respawn_seconds > 0


def _ctx_value(state: dict[str, Any], key: str, default: Any = None) -> Any:
    if key in state:
        return state.get(key)
    extra_context = state.get("extra_context") if isinstance(state.get("extra_context"), dict) else {}
    return extra_context.get(key, default)


def _ctx_int(state: dict[str, Any], key: str, default: int) -> int:
    return _to_int(_ctx_value(state, key), default)


def _to_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _optional_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _state_game_time_seconds(state: dict[str, Any]) -> float | None:
    extra_context = state.get("extra_context") if isinstance(state.get("extra_context"), dict) else {}
    for key in (
        "game_time",
        "clock_time",
        "timestamp_seconds",
        "simulated_timestamp_seconds",
        "demo_timestamp_seconds",
    ):
        value = extra_context.get(key) if key in extra_context else state.get(key)
        parsed = _optional_float(value)
        if parsed is not None:
            return max(0.0, parsed)
    return None


def _action_hash(action: str) -> str:
    normalized = " ".join(str(action or "").strip().lower().split())
    if not normalized:
        return ""
    return hashlib.sha1(normalized.encode("utf-8")).hexdigest()[:12]


def _game_phase(minute: int) -> str:
    if minute < 10:
        return "laning"
    if minute < 20:
        return "early_mid"
    if minute < 35:
        return "mid_game"
    return "late_game"


def _minute_bucket(minute: int) -> str:
    if minute < 10:
        return "0-10"
    if minute < 20:
        return "10-20"
    if minute < 35:
        return "20-35"
    return "35+"


def _hp_bucket(hp_percent: int) -> str:
    if hp_percent <= 20:
        return "0-20"
    if hp_percent <= 35:
        return "21-35"
    if hp_percent <= 60:
        return "36-60"
    return "61-100"


def _simplify_team_status(value: Any) -> str:
    text = str(value or "").strip().lower().replace("_", " ")
    if not text:
        return "unknown"

    categories = [
        ("objective", ("objective", "roshan", "tower", "barracks", "push", "highground")),
        ("pressure", ("pressure", "gank", "danger", "smoke", "under attack")),
        ("bad_fight", ("bad fight", "dive", "chase", "skirmish", "brawl")),
        ("fight", ("fight", "teamfight", "contest", "engage")),
        ("safe_farm", ("farm", "farming", "calm", "safe", "jungle", "lane")),
        ("dead_or_paused", ("dead", "paused", "disconnected")),
    ]
    matches = [
        label
        for label, keywords in categories
        if any(keyword in text for keyword in keywords)
    ]
    return "+".join(matches) if matches else "generic"


KEY_ITEMS = {
    "battle fury",
    "manta style",
    "black king bar",
    "bkb",
    "butterfly",
    "satanic",
    "abyssal blade",
    "eye of skadi",
    "dragon lance",
    "hurricane pike",
    "silver edge",
    "desolator",
    "diffusal blade",
}


def _key_item_signature(items: Any) -> str:
    if not isinstance(items, list):
        return "none"
    normalized = {
        str(item).strip().lower().replace("_", " ").replace("-", " ")
        for item in items
        if str(item).strip()
    }
    key_items = sorted(item for item in normalized if item in KEY_ITEMS)
    return "|".join(key_items) if key_items else "none"


def _session_id_from_state(state: dict[str, Any]) -> str | None:
    extra_context = state.get("extra_context") if isinstance(state.get("extra_context"), dict) else {}
    value = extra_context.get("match_session_id") or extra_context.get("match_id")
    if value in {None, ""}:
        return None
    return str(value)


def _average(values: list[float]) -> float | None:
    if not values:
        return None
    return round(mean(values), 3)


def _minimum(values: list[float]) -> float | None:
    if not values:
        return None
    return round(min(values), 3)


def _maximum(values: list[float]) -> float | None:
    if not values:
        return None
    return round(max(values), 3)


def _p95(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, int(round((len(ordered) - 1) * 0.95))))
    return round(ordered[index], 3)


def _rate(part: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round(part / total, 3)


ADVICE_SCHEDULER = AdviceScheduler()
