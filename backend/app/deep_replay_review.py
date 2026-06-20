"""
deep_replay_review.py - deterministic offline replay review builder.

Deep Replay Review v0 summarizes a replay demo session using only local data:
processed GSI-like replay states, shown backend advice cards, and scheduler
suppression metrics. It avoids unsupported claims about enemy positions, team
readiness, Roshan/objective state, cooldowns, or spendable gold.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Any


def build_deep_replay_review(
    *,
    processed_entries: list[dict[str, Any]],
    advice_history: list[dict[str, Any]],
    scheduler_stats: dict[str, Any] | None = None,
) -> dict[str, Any]:
    states = _states_from_entries(processed_entries)
    scheduler_stats = scheduler_stats or {}
    timestamps = [_safe_int(entry.get("timestamp_seconds")) for entry in processed_entries]
    timestamps = [value for value in timestamps if value is not None]
    duration_minutes = _duration_minutes(timestamps, len(processed_entries))
    hero = _most_common(
        [state.get("hero") for state in states]
        + [record.get("hero") for record in advice_history]
    ) or "unknown"
    confidence_counts = Counter(_extra(state).get("context_confidence", "unknown") for state in states)
    urgent_count = sum(1 for record in advice_history if record.get("advice_mode") == "urgent")
    coaching_count = max(0, len(advice_history) - urgent_count)

    overview = {
        "hero": hero,
        "time_window": _time_window(timestamps, advice_history),
        "duration_minutes": duration_minutes,
        "states_processed": len(processed_entries),
        "advice_shown": len(advice_history),
        "urgent_advice_count": urgent_count,
        "coaching_advice_count": coaching_count,
        "confidence_distribution": dict(confidence_counts),
    }

    pattern_counts = _pattern_counts(advice_history, scheduler_stats)
    farm_review = _farm_review(states, advice_history)
    hp_review = _hp_and_death_review(states, advice_history, scheduler_stats)
    objective_review = _objective_review(advice_history, states)
    item_review = _item_timing_review(advice_history, states)

    return {
        "title": "Deep Replay Review",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "overview": overview,
        "main_patterns": _main_patterns(pattern_counts),
        "key_moments": _key_moments(advice_history),
        "farm_review": farm_review,
        "hp_and_death_review": hp_review,
        "objective_review": objective_review,
        "item_timing_review": item_review,
        "focus_points": _focus_points(pattern_counts, farm_review, hp_review, objective_review),
        "limitations": _limitations(states, advice_history),
    }


def deep_replay_review_to_markdown(review: dict[str, Any]) -> str:
    overview = review.get("overview", {})
    lines = [
        "# Deep Replay Review",
        "",
        "## Overview",
        f"Hero: {overview.get('hero', 'unknown')}",
        f"Window: {overview.get('time_window', 'unknown')}",
        f"Duration: {overview.get('duration_minutes', 0)} minutes",
        f"States processed: {overview.get('states_processed', 0)}",
        f"Advice shown: {overview.get('advice_shown', 0)}",
        f"Urgent advice: {overview.get('urgent_advice_count', 0)}",
        f"Coaching advice: {overview.get('coaching_advice_count', 0)}",
        "",
        "## Main patterns",
    ]
    _extend_bullets(lines, review.get("main_patterns"), fallback="No strong repeated pattern detected.")

    lines.extend(["", "## Key moments"])
    key_moments = review.get("key_moments") or []
    if key_moments:
        for moment in key_moments:
            lines.append(
                f"- {moment.get('game_time', '??:??')} - "
                f"{moment.get('decision_point', 'UNKNOWN')}: {moment.get('action', '')}"
            )
            lines.append(f"  - Why it matters: {moment.get('why_it_matters', '')}")
            if moment.get("missing_context_note"):
                lines.append(f"  - Context limit: {moment.get('missing_context_note')}")
    else:
        lines.append("- No advice moments were shown.")

    lines.extend(["", "## Farm review"])
    _extend_bullets(lines, _review_lines(review.get("farm_review")))

    lines.extend(["", "## HP and death review"])
    _extend_bullets(lines, _review_lines(review.get("hp_and_death_review")))

    lines.extend(["", "## Objective review"])
    _extend_bullets(lines, _review_lines(review.get("objective_review")))

    lines.extend(["", "## Item timing review"])
    _extend_bullets(lines, _review_lines(review.get("item_timing_review")))

    lines.extend(["", "## Focus points for next game"])
    _extend_bullets(lines, review.get("focus_points"))

    lines.extend(["", "## Data limitations"])
    _extend_bullets(lines, review.get("limitations"))
    lines.append("")
    return "\n".join(lines)


def _states_from_entries(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    states: list[dict[str, Any]] = []
    for entry in entries:
        state = entry.get("state")
        if isinstance(state, dict):
            states.append(state)
    return states


def _pattern_counts(advice_history: list[dict[str, Any]], stats: dict[str, Any]) -> Counter[str]:
    counts: Counter[str] = Counter()
    for record in advice_history:
        decision = str(record.get("decision_point") or "")
        text = f"{record.get('action', '')} {record.get('reason', '')}".lower()
        if decision in {"FARMING_PHASE_PRESSURE", "LANING_FARM_CHECK", "SAFE_FARMING"} or "farm" in text:
            counts["Safe farming route and recovery"] += 1
        if decision in {"LOW_HP", "LOW_HP_WARNING", "RECENT_DAMAGE_WARNING", "OVERSTAY_WARNING", "DEATH_LOW_RESOURCE"}:
            counts["HP and reset management"] += 1
        if decision == "REPEATED_DEATH_PATTERN" or "repeated" in text or "re-contesting" in text:
            counts["Repeated risky re-entry"] += 1
        if decision == "OBJECTIVE_FIGHT_CHECK" or "objective" in text:
            counts["Objective participation caution"] += 1
        if decision == "ITEM_TIMING" or "item pickup" in text:
            counts["Item timing reassessment"] += 1

    suppressions = sum(
        _safe_int(stats.get(key), 0) or 0
        for key in (
            "duplicate_suppressed_count",
            "repeated_laning_suppressed_count",
            "repeated_post_laning_suppressed_count",
            "repeated_objective_suppressed_count",
            "repeated_low_hp_suppressed_count",
        )
    )
    if suppressions:
        counts["Scheduler reduced repeated advice to avoid information noise"] = suppressions
    return counts


def _main_patterns(pattern_counts: Counter[str]) -> list[str]:
    return [name for name, count in pattern_counts.most_common() if count > 0]


def _key_moments(advice_history: list[dict[str, Any]]) -> list[dict[str, Any]]:
    priority_order = {
        "LOW_HP": 0,
        "REPEATED_DEATH_PATTERN": 1,
        "DEATH_LOW_RESOURCE": 2,
        "DEATH_REVIEW": 3,
        "OBJECTIVE_FIGHT_CHECK": 4,
        "ITEM_TIMING": 5,
        "FARMING_PHASE_PRESSURE": 6,
        "LANING_FARM_CHECK": 7,
        "RECENT_DAMAGE_WARNING": 8,
    }
    indexed = list(enumerate(advice_history))
    indexed.sort(
        key=lambda item: (
            priority_order.get(str(item[1].get("decision_point") or ""), 20),
            item[0],
        )
    )
    selected = sorted(indexed[:8], key=lambda item: item[0])
    return [_moment_from_record(record) for _, record in selected]


def _moment_from_record(record: dict[str, Any]) -> dict[str, Any]:
    decision = str(record.get("decision_point") or "UNKNOWN")
    missing = set(str(signal) for signal in record.get("missing_signals") or [])
    return {
        "game_time": record.get("game_time") or "",
        "decision_point": decision,
        "action": record.get("action") or "",
        "reason": record.get("reason") or "",
        "why_it_matters": _why_it_matters(decision),
        "data_confidence": record.get("confidence") or "unknown",
        "missing_context_note": _missing_context_note(missing),
    }


def _why_it_matters(decision_point: str) -> str:
    if decision_point == "LOW_HP":
        return "Critical HP moments can quickly turn into deaths if the player keeps showing."
    if decision_point in {"DEATH_REVIEW", "DEATH_LOW_RESOURCE", "REPEATED_DEATH_PATTERN"}:
        return "Death review helps prevent repeating the same route or resource mistake."
    if decision_point == "OBJECTIVE_FIGHT_CHECK":
        return "Objective participation can be valuable, but only with enough team context."
    if decision_point == "ITEM_TIMING":
        return "An item pickup can change options, but it still requires reassessing pressure."
    if decision_point in {"FARMING_PHASE_PRESSURE", "LANING_FARM_CHECK", "SAFE_FARMING"}:
        return "Safe farm routing is the most reliable way to recover without adding risk."
    if decision_point in {"RECENT_DAMAGE_WARNING", "OVERSTAY_WARNING", "LOW_HP_WARNING"}:
        return "Recent damage and low HP are early warnings before a preventable death."
    return "This advice was selected as a shown coaching moment in the replay session."


def _farm_review(states: list[dict[str, Any]], advice_history: list[dict[str, Any]]) -> dict[str, Any]:
    qualities = Counter(str(_extra(state).get("farm_quality") or "unknown") for state in states)
    deficits = [
        str(_extra(state).get("lh_deficit_or_status") or "")
        for state in states
        if _extra(state).get("lh_deficit_or_status")
    ]
    farm_advice = [
        record for record in advice_history
        if record.get("decision_point") in {"FARMING_PHASE_PRESSURE", "LANING_FARM_CHECK", "SAFE_FARMING"}
    ]
    observations = []
    if qualities.get("very_low") or qualities.get("low"):
        observations.append("The replay window contains periods where farm quality was below the expected local range.")
    if qualities.get("okay") or qualities.get("good"):
        observations.append("Some states show farm quality stabilizing later in the reviewed window.")
    if farm_advice:
        observations.append("Shown advice emphasized safer wave-and-camp routes before uncertain fights.")
    if deficits:
        observations.append(f"Representative farm context: {deficits[0]}.")
    if not observations:
        observations.append("Farm context was limited or not available in the reviewed states.")
    return {
        "farm_quality_distribution": dict(qualities),
        "farm_advice_count": len(farm_advice),
        "observations": observations,
        "recommendation": "Prioritize safer wave-and-camp routes before uncertain fights when farm recovery is needed.",
    }


def _hp_and_death_review(
    states: list[dict[str, Any]],
    advice_history: list[dict[str, Any]],
    stats: dict[str, Any],
) -> dict[str, Any]:
    hp_states = Counter(str(_extra(state).get("hp_pressure_state") or "unknown") for state in states)
    hp_advice = [
        record for record in advice_history
        if record.get("decision_point") in {
            "LOW_HP",
            "LOW_HP_WARNING",
            "RECENT_DAMAGE_WARNING",
            "OVERSTAY_WARNING",
            "DEATH_REVIEW",
            "DEATH_LOW_RESOURCE",
            "REPEATED_DEATH_PATTERN",
        }
    ]
    observations = []
    if hp_states.get("critical"):
        observations.append("Critical HP states appeared in the replay window.")
    if hp_states.get("risky") or hp_states.get("pressured_but_stable"):
        observations.append("Several states indicated pressure before critical HP.")
    if stats.get("low_hp_episode_count"):
        observations.append(f"Low HP episodes detected: {stats.get('low_hp_episode_count')}.")
    if stats.get("repeated_low_hp_suppressed_count"):
        observations.append("Repeated low-HP reminders were suppressed to avoid urgent spam.")
    if any(record.get("decision_point") == "REPEATED_DEATH_PATTERN" for record in advice_history):
        observations.append("A repeated risky re-entry or repeated death pattern was shown.")
    if not observations:
        observations.append("No strong HP/death pattern was detected in the shown advice.")
    return {
        "hp_pressure_distribution": dict(hp_states),
        "hp_or_death_advice_count": len(hp_advice),
        "observations": observations,
        "recommendation": "Reset HP before showing again when pressure or recent damage is present.",
    }


def _objective_review(advice_history: list[dict[str, Any]], states: list[dict[str, Any]]) -> dict[str, Any]:
    objective_advice = [
        record for record in advice_history
        if record.get("decision_point") == "OBJECTIVE_FIGHT_CHECK"
    ]
    near_objective_states = sum(1 for state in states if state.get("near_objective"))
    observations = []
    if objective_advice:
        observations.append("Objective advice appeared, but it stayed conditional because team readiness is unavailable.")
    if near_objective_states:
        observations.append(f"Replay states near objective context: {near_objective_states}.")
    if not objective_advice:
        observations.append("No shown objective caution card appeared in this reviewed session.")
    return {
        "objective_advice_count": len(objective_advice),
        "near_objective_states": near_objective_states,
        "observations": observations,
        "recommendation": "Objective participation should be conditional on team grouping and available information.",
    }


def _item_timing_review(advice_history: list[dict[str, Any]], states: list[dict[str, Any]]) -> dict[str, Any]:
    item_advice = [record for record in advice_history if record.get("decision_point") == "ITEM_TIMING"]
    item_pickups = [
        str(state.get("recent_item_purchase") or "")
        for state in states
        if state.get("recent_item_purchase") and state.get("item_timing_category")
    ]
    observations = []
    if item_advice:
        observations.append("A meaningful item timing was shown as a reassessment point, not as a forced fight call.")
    if item_pickups:
        observations.append(f"Meaningful item timing candidates seen: {', '.join(sorted(set(item_pickups))[:5])}.")
    if not item_advice and not item_pickups:
        observations.append("No meaningful item timing advice appeared in this session.")
    return {
        "item_timing_advice_count": len(item_advice),
        "meaningful_item_pickups": sorted(set(item_pickups)),
        "observations": observations,
        "recommendation": "After an item pickup, reassess whether to farm safely or pressure with team context.",
    }


def _focus_points(
    patterns: Counter[str],
    farm_review: dict[str, Any],
    hp_review: dict[str, Any],
    objective_review: dict[str, Any],
) -> list[str]:
    candidates = []
    if patterns.get("HP and reset management"):
        candidates.append("Reset HP before showing on another lane or taking another trade.")
    if patterns.get("Safe farming route and recovery"):
        candidates.append("Use safer wave-and-camp routes when farm is behind or pressure is active.")
    if patterns.get("Objective participation caution") or objective_review.get("objective_advice_count"):
        candidates.append("Do not join objective fights unless team context is favorable.")
    if patterns.get("Repeated risky re-entry"):
        candidates.append("Avoid returning to the same pressured route immediately after a bad trade or death.")
    if patterns.get("Item timing reassessment"):
        candidates.append("Treat item pickups as reassessment points, not automatic fight commands.")
    while len(candidates) < 3:
        fallback = [
            farm_review.get("recommendation"),
            hp_review.get("recommendation"),
            objective_review.get("recommendation"),
        ][len(candidates) % 3]
        if fallback and fallback not in candidates:
            candidates.append(str(fallback))
        else:
            candidates.append("Keep decisions conservative when replay context is incomplete.")
    return candidates[:3]


def _limitations(states: list[dict[str, Any]], advice_history: list[dict[str, Any]]) -> list[str]:
    missing = set()
    for state in states:
        missing.update(str(signal) for signal in _extra(state).get("missing_signals") or [])
    for record in advice_history:
        missing.update(str(signal) for signal in record.get("missing_signals") or [])

    limitations = [
        "Replay-derived GSI-like states are not full live GSI.",
        "Exact enemy positions are unavailable.",
        "Team readiness is unavailable.",
        "Exact objective/Roshan context is unavailable.",
    ]
    if "gold" in missing:
        limitations.append("Spendable gold may be missing and is not treated as exact.")
    else:
        limitations.append("Spendable gold may be missing in replay-derived states.")
    if "ability_cooldowns" in missing:
        limitations.append("Cooldown-specific conclusions are avoided when cooldown signals are missing.")
    else:
        limitations.append("Full cooldown state may be missing in replay-derived states.")
    return limitations


def _review_lines(section: Any) -> list[str]:
    if not isinstance(section, dict):
        return []
    lines = list(section.get("observations") or [])
    recommendation = section.get("recommendation")
    if recommendation:
        lines.append(f"Recommendation: {recommendation}")
    return [str(line) for line in lines if line]


def _extend_bullets(lines: list[str], values: Any, *, fallback: str | None = None) -> None:
    values = list(values or [])
    if not values and fallback:
        lines.append(f"- {fallback}")
        return
    for value in values:
        lines.append(f"- {value}")


def _missing_context_note(missing: set[str]) -> str:
    notes = []
    if "enemy_positions" in missing or "nearby_allies_enemies" in missing:
        notes.append("enemy positions / nearby units missing")
    if "exact_teamfight_context" in missing:
        notes.append("teamfight readiness missing")
    if "objective_context" in missing or "exact_roshan_context" in missing:
        notes.append("exact objective/Roshan context missing")
    if "ability_cooldowns" in missing:
        notes.append("cooldowns missing")
    if "gold" in missing:
        notes.append("spendable gold missing")
    return "; ".join(notes)


def _duration_minutes(timestamps: list[int], state_count: int) -> float:
    if len(timestamps) >= 2:
        return round((max(timestamps) - min(timestamps)) / 60, 2)
    if state_count > 1:
        return round(state_count / 60, 2)
    return 0.0


def _time_window(timestamps: list[int], advice_history: list[dict[str, Any]]) -> str:
    if timestamps:
        return f"{_format_time(min(timestamps))}-{_format_time(max(timestamps))}"
    advice_times = [str(record.get("game_time") or "") for record in advice_history if record.get("game_time")]
    if advice_times:
        return f"{advice_times[0]}-{advice_times[-1]}"
    return "unknown"


def _format_time(timestamp_seconds: int) -> str:
    return f"{max(0, timestamp_seconds) // 60:02d}:{max(0, timestamp_seconds) % 60:02d}"


def _extra(state: dict[str, Any]) -> dict[str, Any]:
    extra = state.get("extra_context")
    return extra if isinstance(extra, dict) else {}


def _safe_int(value: Any, default: int | None = None) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _most_common(values: list[Any]) -> str:
    counter = Counter(str(value) for value in values if value)
    return counter.most_common(1)[0][0] if counter else ""
