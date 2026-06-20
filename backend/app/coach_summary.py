"""
coach_summary.py - lightweight post-session summary for shown advice cards.

The summary uses only advice already produced by the backend overlay path. It
does not infer enemy positions, team readiness, objective state, cooldowns, or
spendable gold when those signals are missing.
"""

from __future__ import annotations

from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any


MAX_HISTORY = 200


class CoachSessionHistory:
    def __init__(self) -> None:
        self._records: list[dict[str, Any]] = []
        self._last_record_key = ""

    def reset(self) -> None:
        self._records.clear()
        self._last_record_key = ""

    def record_overlay_advice(
        self,
        overlay_response: dict[str, Any],
        state: dict[str, Any] | None = None,
    ) -> None:
        recommendation = overlay_response.get("recommendation")
        if not isinstance(recommendation, dict):
            return
        if overlay_response.get("status") not in {"advice", "active_advice", "cooldown"}:
            return

        action = str(recommendation.get("action") or "").strip()
        reason = str(recommendation.get("reason") or "").strip()
        if not action:
            return

        extra_context = {}
        if isinstance(state, dict) and isinstance(state.get("extra_context"), dict):
            extra_context = state["extra_context"]

        game_time = str(
            overlay_response.get("simulated_time_label")
            or _minute_label(overlay_response.get("minute"))
            or ""
        )
        record_key = "|".join(
            [
                str(overlay_response.get("advice_count") or ""),
                str(overlay_response.get("decision_point") or ""),
                action,
                reason,
                str(overlay_response.get("source") or ""),
            ]
        )
        if record_key == self._last_record_key:
            return
        self._last_record_key = record_key

        record = {
            "timestamp": overlay_response.get("timestamp")
            or overlay_response.get("last_updated")
            or datetime.now(timezone.utc).isoformat(),
            "game_time": game_time,
            "timestamp_seconds": overlay_response.get("simulated_timestamp_seconds"),
            "hero": overlay_response.get("hero") or (state or {}).get("hero"),
            "stage": overlay_response.get("stage") or _stage_from_minute(overlay_response.get("minute")),
            "decision_point": overlay_response.get("decision_point"),
            "action": action,
            "reason": reason,
            "priority": recommendation.get("priority") or overlay_response.get("priority"),
            "source": overlay_response.get("source"),
            "confidence": overlay_response.get("context_confidence")
            or extra_context.get("context_confidence"),
            "advice_mode": overlay_response.get("advice_mode"),
            "laning_category": extra_context.get("laning_category", ""),
            "post_laning_category": extra_context.get("post_laning_category", ""),
            "farm_quality": overlay_response.get("farm_quality") or extra_context.get("farm_quality", ""),
            "hp_pressure_state": extra_context.get("hp_pressure_state", ""),
            "position_zone": extra_context.get("position_zone", ""),
            "position_risk": overlay_response.get("position_risk") or extra_context.get("position_risk", ""),
            "missing_signals": list(overlay_response.get("missing_signals") or extra_context.get("missing_signals") or []),
        }
        self._records.append(record)
        if len(self._records) > MAX_HISTORY:
            del self._records[: len(self._records) - MAX_HISTORY]

    def records(self) -> list[dict[str, Any]]:
        return deepcopy(self._records)

    def build_summary(self, scheduler_stats: dict[str, Any] | None = None) -> dict[str, Any]:
        records = self.records()
        scheduler_stats = scheduler_stats or {}
        hero = _most_common(record.get("hero") for record in records) or "unknown"
        game_times = [str(record.get("game_time") or "") for record in records if record.get("game_time")]
        urgent_count = sum(1 for record in records if record.get("advice_mode") == "urgent")
        coaching_count = max(0, len(records) - urgent_count)
        decision_counts = Counter(str(record.get("decision_point") or "UNKNOWN") for record in records)
        pattern_counts = _detect_patterns(records)

        overview = {
            "hero": hero,
            "window": _window_label(game_times),
            "total_advice_shown": len(records),
            "urgent_advice_count": urgent_count,
            "coaching_advice_count": coaching_count,
            "source_counts": dict(Counter(str(record.get("source") or "unknown") for record in records)),
            "decision_point_counts": dict(decision_counts),
            "suppression_metrics": _suppression_metrics(scheduler_stats),
        }

        patterns = _pattern_list(pattern_counts)
        return {
            "title": "Coach Session Summary",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "session_overview": overview,
            "patterns": patterns,
            "most_repeated_issue_types": decision_counts.most_common(5),
            "key_moments": _key_moments(records),
            "observations": _observations(records, pattern_counts, scheduler_stats),
            "focus_points": _focus_points(pattern_counts, records),
            "limitations": _limitations(records),
            "advice_history": records,
        }


COACH_SESSION_HISTORY = CoachSessionHistory()


def summary_to_markdown(summary: dict[str, Any]) -> str:
    overview = summary.get("session_overview", {})
    lines = [
        "# Coach Session Summary",
        "",
        "## Session overview",
        f"Hero: {overview.get('hero', 'unknown')}",
        f"Window: {overview.get('window', 'unknown')}",
        f"Advice shown: {overview.get('total_advice_shown', 0)}",
        f"Urgent: {overview.get('urgent_advice_count', 0)}",
        f"Coaching: {overview.get('coaching_advice_count', 0)}",
        "",
        "## Main patterns detected",
    ]

    patterns = summary.get("patterns") or []
    lines.extend(f"- {pattern}" for pattern in patterns) if patterns else lines.append("- No strong repeated pattern detected.")

    lines.extend(["", "## Key advice moments"])
    moments = summary.get("key_moments") or []
    lines.extend(
        f"- {moment.get('time', '??:??')} - {moment.get('action', '')}"
        for moment in moments
    ) if moments else lines.append("- No advice cards were shown.")

    lines.extend(["", "## What to improve next"])
    lines.extend(f"- {point}" for point in summary.get("focus_points", []))

    lines.extend(["", "## Data limitations"])
    lines.extend(f"- {limitation}" for limitation in summary.get("limitations", []))
    lines.append("")
    return "\n".join(lines)


def _detect_patterns(records: list[dict[str, Any]]) -> Counter[str]:
    counts: Counter[str] = Counter()
    for record in records:
        decision = str(record.get("decision_point") or "")
        action = str(record.get("action") or "").lower()
        reason = str(record.get("reason") or "").lower()
        combined = f"{action} {reason}"
        if decision in {"LOW_HP", "LOW_HP_WARNING", "RECENT_DAMAGE_WARNING", "OVERSTAY_WARNING", "DEATH_LOW_RESOURCE"}:
            counts["HP/reset management"] += 1
        if decision in {"FARMING_PHASE_PRESSURE", "LANING_FARM_CHECK", "SAFE_FARMING"} or "farm" in combined:
            counts["safe farming route and recovery"] += 1
        if decision == "OBJECTIVE_FIGHT_CHECK" or "objective" in combined:
            counts["objective participation caution"] += 1
        if decision in {"REPEATED_DEATH_PATTERN"} or "repeating" in combined or "re-contesting" in combined:
            counts["repeated risky re-entry"] += 1
        if record.get("position_risk") in {"medium", "high"} or "enemy locations are not confirmed" in combined:
            counts["position risk with missing enemy information"] += 1
    return counts


def _pattern_list(pattern_counts: Counter[str]) -> list[str]:
    return [name for name, count in pattern_counts.most_common() if count > 0]


def _key_moments(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    moments: list[dict[str, Any]] = []
    seen_decisions: set[str] = set()
    for record in records:
        decision = str(record.get("decision_point") or "")
        if decision in seen_decisions and len(moments) >= 3:
            continue
        seen_decisions.add(decision)
        moments.append(
            {
                "time": record.get("game_time") or "",
                "decision_point": decision,
                "action": record.get("action") or "",
                "reason": record.get("reason") or "",
                "priority": record.get("priority") or "",
            }
        )
        if len(moments) >= 5:
            break
    return moments


def _observations(
    records: list[dict[str, Any]],
    pattern_counts: Counter[str],
    scheduler_stats: dict[str, Any],
) -> list[str]:
    observations: list[str] = []
    if pattern_counts["HP/reset management"]:
        observations.append("Several advice cards focused on HP/reset management.")
    if pattern_counts["safe farming route and recovery"]:
        observations.append("The session repeatedly emphasized safer farm routes and recovery.")
    if pattern_counts["objective participation caution"]:
        observations.append("Objective advice stayed cautious because full team context is not available.")
    if pattern_counts["repeated risky re-entry"]:
        observations.append("The player pattern suggests repeated risky re-entry after pressure or deaths.")

    suppressed = sum(int(scheduler_stats.get(key, 0) or 0) for key in (
        "duplicate_suppressed_count",
        "repeated_laning_suppressed_count",
        "repeated_post_laning_suppressed_count",
        "repeated_objective_suppressed_count",
        "repeated_low_hp_suppressed_count",
    ))
    if suppressed > 0:
        observations.append(f"The scheduler filtered {suppressed} repeated or low-value advice opportunities to avoid spam.")
    if not observations and records:
        observations.append("The session produced a small set of concise coaching moments.")
    return observations[:5]


def _focus_points(pattern_counts: Counter[str], records: list[dict[str, Any]]) -> list[str]:
    points: list[str] = []
    if pattern_counts["HP/reset management"]:
        points.append("Reset HP before showing on another lane or taking another trade.")
    if pattern_counts["safe farming route and recovery"]:
        points.append("Use the safest wave-and-camp route when farm recovery is the priority.")
    if pattern_counts["objective participation caution"]:
        points.append("Join objectives only when you can confirm team context is favorable.")
    if pattern_counts["repeated risky re-entry"]:
        points.append("Avoid returning to the same pressured route immediately after a bad trade or death.")
    if pattern_counts["position risk with missing enemy information"]:
        points.append("Avoid showing in exposed areas when enemy locations are not confirmed.")
    if len(points) < 3 and records:
        points.append("Keep advice simple: survive first, then recover farm, then reassess objectives.")
    return points[:3]


def _limitations(records: list[dict[str, Any]]) -> list[str]:
    missing = set()
    for record in records:
        missing.update(str(signal) for signal in record.get("missing_signals") or [])

    limitations = []
    if "enemy_positions" in missing or "nearby_allies_enemies" in missing:
        limitations.append("This session does not include exact enemy positions or nearby ally/enemy context.")
    if "exact_teamfight_context" in missing:
        limitations.append("Team readiness and exact fight context are not available.")
    if "objective_context" in missing or "exact_roshan_context" in missing:
        limitations.append("Exact objective/Roshan context is not reconstructed.")
    if "ability_cooldowns" in missing:
        limitations.append("Ability cooldown advice is avoided when cooldown signals are missing.")
    if "gold" in missing:
        limitations.append("Spendable gold is not treated as exact when the replay marks gold as missing.")
    if not limitations:
        limitations.append("The summary only uses advice already produced by the backend during this session.")
    return limitations


def _suppression_metrics(stats: dict[str, Any]) -> dict[str, int]:
    keys = [
        "duplicate_suppressed_count",
        "repeated_laning_suppressed_count",
        "repeated_post_laning_suppressed_count",
        "repeated_objective_suppressed_count",
        "repeated_low_hp_suppressed_count",
        "post_laning_safety_suppressed_count",
    ]
    return {key: int(stats.get(key, 0) or 0) for key in keys}


def _most_common(values: Any) -> str:
    counter = Counter(str(value) for value in values if value)
    return counter.most_common(1)[0][0] if counter else ""


def _window_label(game_times: list[str]) -> str:
    if not game_times:
        return "unknown"
    return f"{game_times[0]}-{game_times[-1]}"


def _minute_label(minute: Any) -> str:
    try:
        value = int(minute)
    except (TypeError, ValueError):
        return ""
    return f"{value:02d}:00"


def _stage_from_minute(minute: Any) -> str:
    try:
        value = int(minute)
    except (TypeError, ValueError):
        return "unknown"
    if value < 10:
        return "laning"
    if value < 20:
        return "post-laning"
    return "macro"
