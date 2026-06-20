"""
Convert offline replay-derived events into GSI-like simulation states.

This is an offline adapter only. It does not parse live game memory and does not
run during live matches.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.advice_context import build_advice_context  # noqa: E402
from app.item_timing import classify_item_timing, is_ignored_item, normalize_item_name  # noqa: E402
from app.schemas import is_supported_hero  # noqa: E402
from app.signal_capabilities import capability_summary  # noqa: E402


DEFAULT_RESPAWN_SECONDS = 20
UTILITY_ABILITY_KEYS = {
    "quelling_blade",
    "tango",
    "courier_take_stash_and_transfer_items",
    "courier_transfer_items",
    "courier_take_stash_items",
    "courier_return_to_base",
    "courier_go_to_secretshop",
    "courier_shield",
}
UTILITY_ABILITY_KEYWORDS = {
    "courier",
    "stash",
    "transfer",
}
DANGEROUS_DAMAGE_ABILITY_KEYWORDS = {
    "bash",
    "bushwhack",
    "charge_of_darkness",
    "disable",
    "fissure",
    "hex",
    "impale",
    "magic_missile",
    "root",
    "shackle",
    "stun",
}
DENSE_DAMAGE_WINDOW_SECONDS = 10
DENSE_DAMAGE_EVENT_COUNT = 5


@dataclass
class ReplayAccumulator:
    hero: str
    player_slot: int
    level: int = 1
    gold: int = 600
    xp: int = 0
    last_hits: int = 0
    gpm: int = 0
    xpm: int = 0
    total_earned_gold: int | None = None
    items: list[str] = field(default_factory=list)
    health: int | None = None
    max_health: int | None = None
    hp_percent: int = 100
    mana: int | None = None
    max_mana: int | None = None
    mana_percent: int = 100
    alive: bool = True
    deaths: int = 0
    respawn_until: int = 0
    xpos: float | int | None = None
    ypos: float | int | None = None
    team_status: str = "unknown"
    hp_confidence: str = "low"
    mana_confidence: str = "low"
    has_exact_hp: bool = False
    has_exact_mana: bool = False
    has_exact_level: bool = False
    has_exact_gold: bool = False
    has_exact_last_hits: bool = False
    has_exact_alive: bool = False
    last_hp_known_at: int | None = None
    last_relevant_event_at: int | None = None
    last_meaningful_event_at: int | None = None
    last_meaningful_context_kind: str = ""
    last_context: str = "replay-derived"
    last_utility_context: str = ""
    last_utility_event_at: int | None = None
    last_death_decision: str | None = None
    last_death_time: int | None = None
    abilities: dict[str, dict[str, Any]] = field(default_factory=dict)
    damage_events: list[tuple[int, int]] = field(default_factory=list)
    raw_damage_event_times: list[int] = field(default_factory=list)
    dangerous_damage_event_times: list[int] = field(default_factory=list)
    objective_events: list[tuple[int, str, str | None]] = field(default_factory=list)


def main() -> int:
    args = _parse_args()
    events_path = Path(args.events_jsonl)
    if not events_path.exists():
        print(f"Events JSONL not found: {events_path}")
        return 1

    events = _load_events(events_path)
    rows = convert_events_to_rows(
        events=events,
        hero=args.hero,
        player_slot=args.player_slot,
        start_minute=args.start_minute,
        end_minute=args.end_minute,
        interval_seconds=args.interval_seconds,
    )
    output_path = Path(args.output)
    _write_jsonl(output_path, rows)
    print(f"GSI-like replay states saved: {output_path}")
    print(f"states: {len(rows)}")
    print("source_type: replay_gsi_like")
    return 0


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert replay event JSONL into GSI-like simulation JSONL.",
    )
    parser.add_argument("--events-jsonl", required=True, help="Replay-derived events JSONL path.")
    parser.add_argument("--hero", required=True, help='Hero name, for example "Kez".')
    parser.add_argument("--player-slot", type=int, required=True, help="Selected player_slot.")
    parser.add_argument("--start-minute", type=int, default=0, help="First minute to emit.")
    parser.add_argument("--end-minute", type=int, default=10, help="Last minute to emit.")
    parser.add_argument("--interval-seconds", type=int, default=1, help="Output interval in seconds.")
    parser.add_argument("--output", required=True, help="Output simulation JSONL path.")
    args = parser.parse_args()
    if args.interval_seconds < 1:
        parser.error("--interval-seconds must be at least 1")
    if args.start_minute < 0:
        parser.error("--start-minute must be >= 0")
    if args.end_minute <= args.start_minute:
        parser.error("--end-minute must be greater than --start-minute")
    if not is_supported_hero(args.hero):
        parser.error(f"--hero '{args.hero}' is not supported by the current carry advisor")
    return args


def convert_events_to_rows(
    *,
    events: list[dict[str, Any]],
    hero: str,
    player_slot: int,
    start_minute: int,
    end_minute: int,
    interval_seconds: int,
) -> list[dict[str, Any]]:
    grouped_events: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        timestamp = _to_int(event.get("timestamp_seconds"), -1)
        if timestamp < 0:
            continue
        grouped_events[timestamp].append(event)

    accumulator = ReplayAccumulator(hero=hero, player_slot=player_slot)
    rows: list[dict[str, Any]] = []
    start_seconds = start_minute * 60
    end_seconds = end_minute * 60
    previous_timestamp = 0

    for timestamp in range(start_seconds, end_seconds + 1, interval_seconds):
        current_events: list[dict[str, Any]] = []
        for event_time in sorted(time for time in grouped_events if previous_timestamp <= time <= timestamp):
            current_events.extend(grouped_events[event_time])
        previous_timestamp = timestamp + 1

        current_purchase: str | None = None
        current_purchase_category: str | None = None
        for event in current_events:
            purchase, category = _apply_event(accumulator, event, timestamp)
            if purchase:
                current_purchase = purchase
                current_purchase_category = category

        _update_respawn(accumulator, timestamp)
        rows.append(
            {
                "timestamp_seconds": timestamp,
                "state": _build_state(
                    accumulator,
                    timestamp,
                    interval_seconds=interval_seconds,
                    recent_item_purchase=current_purchase,
                    item_timing_category=current_purchase_category,
                ),
            }
        )

    return rows


def _apply_event(
    accumulator: ReplayAccumulator,
    event: dict[str, Any],
    timestamp: int,
) -> tuple[str | None, str | None]:
    event_type = str(event.get("type") or "").strip().lower()
    data = event.get("data") if isinstance(event.get("data"), dict) else {}
    player_slot = _optional_int(event.get("player_slot"))
    event_hero = str(event.get("hero") or "").strip()
    selected_event = (
        player_slot == accumulator.player_slot
        or (event_hero and event_hero.lower() == accumulator.hero.lower())
        or event_type == "objective"
    )
    if not selected_event:
        return None, None

    if event_type in {"snapshot", "farm"}:
        _apply_common_snapshot(accumulator, data, timestamp)
        accumulator.last_relevant_event_at = timestamp
        if event_type == "snapshot" or _snapshot_has_exact_farm_data(data):
            accumulator.last_meaningful_event_at = timestamp
            accumulator.last_meaningful_context_kind = "snapshot"
        accumulator.last_context = f"replay-derived {event_type} event"
        return None, None

    if event_type == "damage":
        damage_percent = _damage_percent(data)
        if damage_percent > 0:
            accumulator.damage_events.append((timestamp, damage_percent))
        accumulator.raw_damage_event_times.append(timestamp)
        if _is_dangerous_damage_event(data):
            accumulator.dangerous_damage_event_times.append(timestamp)
        previous_hp = accumulator.hp_percent
        hp_value = _first_int(data, "hp_percent", "hp_after_percent", "target_hp_percent")
        hp_transition = ""
        if hp_value is not None:
            accumulator.hp_percent = _clamp(hp_value, 0, 100)
            accumulator.hp_confidence = "high"
            accumulator.has_exact_hp = True
            accumulator.last_hp_known_at = timestamp
            if previous_hp > accumulator.hp_percent:
                hp_transition = f"hp {previous_hp}->{accumulator.hp_percent}"
        elif damage_percent > 0 and accumulator.hp_confidence != "low":
            accumulator.hp_percent = _clamp(accumulator.hp_percent - damage_percent, 0, 100)
            accumulator.hp_confidence = "medium"
            if previous_hp > accumulator.hp_percent:
                hp_transition = f"hp {previous_hp}->{accumulator.hp_percent}"
        elif damage_percent > 0:
            accumulator.hp_confidence = "medium"
        if accumulator.hp_percent <= 0:
            accumulator.alive = False
        raw_damage_count = _event_count_in_window(
            accumulator.raw_damage_event_times,
            timestamp,
            DENSE_DAMAGE_WINDOW_SECONDS,
        )
        has_dangerous_damage = _event_count_in_window(
            accumulator.dangerous_damage_event_times,
            timestamp,
            DENSE_DAMAGE_WINDOW_SECONDS,
        ) > 0
        is_pressure_window = raw_damage_count >= DENSE_DAMAGE_EVENT_COUNT or has_dangerous_damage
        accumulator.last_relevant_event_at = timestamp
        if is_pressure_window:
            accumulator.last_meaningful_event_at = timestamp
            accumulator.last_meaningful_context_kind = "damage_pressure"
        accumulator.last_context = _join_context(
            [
                (
                    "replay damage pressure window"
                    if is_pressure_window and not accumulator.has_exact_hp
                    else "replay-derived damage event"
                ),
                f"damage_percent={damage_percent}" if damage_percent > 0 else "",
                hp_transition,
            ]
        )
        return None, None

    if event_type == "heal":
        hp_value = _first_int(data, "hp_percent", "hp_after_percent")
        heal_percent = _first_int(data, "heal_percent", "amount_percent")
        if hp_value is not None:
            accumulator.hp_percent = _clamp(hp_value, 0, 100)
            accumulator.hp_confidence = "high"
            accumulator.has_exact_hp = True
            accumulator.last_hp_known_at = timestamp
        elif heal_percent is not None and accumulator.hp_confidence != "low":
            accumulator.hp_percent = _clamp(accumulator.hp_percent + heal_percent, 0, 100)
            accumulator.hp_confidence = "medium"
        mana_value = _first_int(data, "mana_percent", "mana_after_percent")
        if mana_value is not None:
            accumulator.mana_percent = _clamp(mana_value, 0, 100)
            accumulator.mana_confidence = "high"
            accumulator.has_exact_mana = True
        accumulator.last_relevant_event_at = timestamp
        accumulator.last_context = "replay-derived heal/resource event"
        return None, None

    if event_type == "death":
        previous_hp = accumulator.hp_percent
        accumulator.alive = False
        accumulator.hp_percent = 0
        accumulator.hp_confidence = "high"
        accumulator.has_exact_hp = True
        accumulator.last_hp_known_at = timestamp
        accumulator.deaths = max(accumulator.deaths + 1, _first_int(data, "deaths") or 0)
        respawn_seconds = _first_int(data, "respawn_seconds") or DEFAULT_RESPAWN_SECONDS
        accumulator.respawn_until = timestamp + max(1, respawn_seconds)
        accumulator.last_death_time = timestamp
        accumulator.last_death_decision = _death_decision(accumulator, previous_hp)
        accumulator.last_relevant_event_at = timestamp
        accumulator.last_meaningful_event_at = timestamp
        accumulator.last_meaningful_context_kind = "death"
        accumulator.last_context = "replay-derived death event"
        return None, None

    if event_type == "purchase":
        _apply_common_snapshot(accumulator, data, timestamp)
        raw_item = str(data.get("item") or data.get("key") or data.get("name") or "").strip()
        item = normalize_item_name(raw_item)
        if item and item not in accumulator.items:
            accumulator.items.append(item)
        timing = classify_item_timing(item)
        if timing["is_meaningful"]:
            accumulator.last_relevant_event_at = timestamp
            accumulator.last_meaningful_event_at = timestamp
            accumulator.last_meaningful_context_kind = "item_timing"
            accumulator.last_context = f"meaningful replay item timing: {item}"
            return str(timing["item"]), str(timing["category"] or "")
        if item and (is_ignored_item(item) or is_minor_replay_item(item)):
            accumulator.last_utility_event_at = timestamp
            accumulator.last_utility_context = f"replay minor item event: {item}"
            return None, None
        accumulator.last_relevant_event_at = timestamp
        accumulator.last_context = f"replay item event: {item}" if item else "replay item event"
        return None, None

    if event_type == "level":
        level = _first_int(data, "level")
        if level is not None:
            accumulator.level = _clamp(level, 1, 30)
            accumulator.has_exact_level = True
            accumulator.last_meaningful_event_at = timestamp
            accumulator.last_meaningful_context_kind = "level"
        _apply_common_snapshot(accumulator, data, timestamp)
        accumulator.last_relevant_event_at = timestamp
        accumulator.last_context = "replay-derived level event"
        return None, None

    if event_type == "position":
        _apply_common_snapshot(accumulator, data, timestamp)
        accumulator.xpos = _first_number(data, "xpos", "x")
        accumulator.ypos = _first_number(data, "ypos", "y")
        accumulator.last_relevant_event_at = timestamp
        accumulator.last_context = "replay-derived position event"
        return None, None

    if event_type == "ability":
        _apply_common_snapshot(accumulator, data, timestamp)
        ability = _ability_snapshot(data)
        if ability and _is_utility_ability(ability["name"]):
            accumulator.last_utility_event_at = timestamp
            accumulator.last_utility_context = f"replay utility event: {ability['name']}"
            return None, None
        if ability:
            accumulator.abilities[_ability_key(ability["name"])] = ability
            accumulator.last_relevant_event_at = timestamp
            if _is_meaningful_replay_ability(ability["name"]):
                accumulator.last_meaningful_event_at = timestamp
                accumulator.last_meaningful_context_kind = "ability"
        mana_value = _first_int(data, "mana_percent", "mana_after_percent")
        if mana_value is not None:
            accumulator.mana_percent = _clamp(mana_value, 0, 100)
            accumulator.mana_confidence = "high"
            accumulator.has_exact_mana = True
        accumulator.last_context = (
            f"replay ability event: {ability['name']}" if ability else "replay ability event"
        )
        return None, None

    if event_type == "objective":
        _apply_common_snapshot(accumulator, data, timestamp)
        objective_type = str(data.get("objective_type") or data.get("type") or "objective").strip()
        objective_team = _optional_str(data.get("team") or data.get("objective_team"))
        accumulator.objective_events.append((timestamp, objective_type, objective_team))
        accumulator.team_status = str(data.get("team_status") or accumulator.team_status or "unknown")
        accumulator.last_relevant_event_at = timestamp
        accumulator.last_meaningful_event_at = timestamp
        accumulator.last_meaningful_context_kind = "objective"
        accumulator.last_context = f"replay-derived objective event: {objective_type}"
        return None, None

    return None, None


def _build_state(
    accumulator: ReplayAccumulator,
    timestamp: int,
    *,
    interval_seconds: int,
    recent_item_purchase: str | None,
    item_timing_category: str | None,
) -> dict[str, Any]:
    damage_5s = _damage_in_window(accumulator.damage_events, timestamp, 5)
    damage_10s = _damage_in_window(accumulator.damage_events, timestamp, 10)
    raw_damage_count_10s = _event_count_in_window(
        accumulator.raw_damage_event_times,
        timestamp,
        DENSE_DAMAGE_WINDOW_SECONDS,
    )
    dangerous_damage_count_10s = _event_count_in_window(
        accumulator.dangerous_damage_event_times,
        timestamp,
        DENSE_DAMAGE_WINDOW_SECONDS,
    )
    replay_damage_pressure = (
        raw_damage_count_10s >= DENSE_DAMAGE_EVENT_COUNT
        or dangerous_damage_count_10s > 0
        or damage_10s >= 20
    )
    recent_damage_taken = damage_10s >= 20
    near_death = (
        not accumulator.alive
        or (
            accumulator.last_death_time is not None
            and 0 <= timestamp - accumulator.last_death_time <= 5
        )
    )
    objective = _nearest_objective(accumulator.objective_events, timestamp)
    near_objective = objective is not None
    context_confidence = _context_confidence(accumulator, timestamp)
    game_state = _game_state(
        accumulator=accumulator,
        timestamp=timestamp,
        damage_10s=damage_10s,
        replay_damage_pressure=replay_damage_pressure,
        near_death=near_death,
        near_objective=near_objective,
        recent_item_purchase=recent_item_purchase,
    )
    meaningful_context = _has_recent_meaningful_context(accumulator, timestamp)
    exact_fields = _exact_fields(accumulator)
    defaulted_fields = _defaulted_fields(accumulator)
    capabilities = capability_summary(
        "replay_gsi_like",
        observed={
            "hp": accumulator.has_exact_hp,
            "mana": accumulator.has_exact_mana,
            "gold": accumulator.has_exact_gold,
            "last_hits": accumulator.has_exact_last_hits,
            "level": accumulator.has_exact_level,
            "position": accumulator.xpos is not None and accumulator.ypos is not None,
            "alive_respawn": accumulator.has_exact_alive or accumulator.last_death_time is not None,
            "ability_cooldowns": _has_exact_ability_cooldown(accumulator),
            "objective_context": near_objective,
        },
    )
    event_context = _join_context(
        [
            "GSI-like replay state",
            accumulator.last_context if meaningful_context else "",
            (
                f"replay parser missing/defaulted fields: {', '.join(defaulted_fields)}"
                if defaulted_fields
                else ""
            ),
            (
                "exact HP unavailable; default HP placeholder is not live state"
                if not accumulator.has_exact_hp and accumulator.alive
                else ""
            ),
        ]
    )

    respawn_seconds = max(0, accumulator.respawn_until - timestamp) if not accumulator.alive else 0
    extra_context = {
        "source_type": "replay_gsi_like",
        "context_confidence": context_confidence,
        **capabilities,
        "player_slot": accumulator.player_slot,
        "selected_team": "dire" if accumulator.player_slot >= 128 else "radiant",
        "replay_exact_fields": exact_fields,
        "replay_defaulted_fields": defaulted_fields,
        "replay_meaningful_context": meaningful_context,
        "replay_damage_pressure_window": replay_damage_pressure,
        "replay_damage_event_count_10s": raw_damage_count_10s,
        "replay_dangerous_damage_event_count_10s": dangerous_damage_count_10s,
        "last_replay_utility_event": (
            accumulator.last_utility_context
            if accumulator.last_utility_event_at is not None and 0 <= timestamp - accumulator.last_utility_event_at <= 10
            else ""
        ),
        "alive": accumulator.alive,
        "health": accumulator.health,
        "max_health": accumulator.max_health,
        "hp_percent": accumulator.hp_percent if accumulator.has_exact_hp else None,
        "mana": accumulator.mana,
        "max_mana": accumulator.max_mana,
        "mana_percent": accumulator.mana_percent if accumulator.has_exact_mana else None,
        "xpos": accumulator.xpos,
        "ypos": accumulator.ypos,
        "xp": accumulator.xp,
        "total_earned_gold": accumulator.total_earned_gold,
        "last_hits": accumulator.last_hits if accumulator.has_exact_last_hits else None,
        "gpm": accumulator.gpm if accumulator.has_exact_last_hits else None,
        "xpm": accumulator.xpm if accumulator.has_exact_level else None,
        "abilities": list(accumulator.abilities.values()),
        "damage_taken_last_5s": damage_5s,
        "damage_taken_last_10s": damage_10s,
        "recent_damage_taken": recent_damage_taken,
        "recent_pressure_context": "took heavy replay-derived damage recently" if recent_damage_taken else "",
        "deaths": accumulator.deaths,
        "respawn_seconds": respawn_seconds,
        "event_context": "replay-derived",
        "match_session_id": f"replay_{accumulator.player_slot}_{accumulator.hero.lower().replace(' ', '_')}",
        "death_review_available": not accumulator.alive and accumulator.last_death_decision is not None,
        "death_review_decision": accumulator.last_death_decision,
        "match_death_count": accumulator.deaths,
        "sample_interval_seconds": interval_seconds,
    }
    if accumulator.last_death_time is not None:
        extra_context["last_death_minute"] = accumulator.last_death_time // 60
        extra_context["last_death_event_id"] = accumulator.deaths

    state = {
        "hero": accumulator.hero,
        "role": "carry",
        "minute": min(90, timestamp // 60),
        "level": accumulator.level,
        "gold": accumulator.gold,
        "items": list(accumulator.items),
        "hp_percent": accumulator.hp_percent,
        "game_state": game_state,
        "team_status": accumulator.team_status,
        "event_context": event_context,
        "near_player_death": near_death,
        "near_teamfight": False,
        "near_objective": near_objective,
        "objective_type": objective[1] if objective else None,
        "objective_team": objective[2] if objective else None,
        "objective_context": "contested_objective" if near_objective else "unknown",
        "recent_item_purchase": recent_item_purchase,
        "item_timing_category": item_timing_category,
        "gold_delta": 0,
        "lh_delta": 0,
        "farm_rate_state": "unknown",
        "extra_context": extra_context,
    }
    state["selected_team"] = extra_context["selected_team"]
    state["extra_context"].update(build_advice_context(state))
    return state


def _update_respawn(accumulator: ReplayAccumulator, timestamp: int) -> None:
    if not accumulator.alive and accumulator.respawn_until and timestamp >= accumulator.respawn_until:
        accumulator.alive = True
        accumulator.hp_percent = 100
        accumulator.mana_percent = max(accumulator.mana_percent, 80)
        accumulator.hp_confidence = "medium"
        accumulator.mana_confidence = "medium"
        accumulator.has_exact_hp = False
        accumulator.has_exact_mana = False
        accumulator.last_hp_known_at = timestamp
        accumulator.last_relevant_event_at = timestamp
        accumulator.last_meaningful_event_at = timestamp
        accumulator.last_meaningful_context_kind = "respawn"
        accumulator.last_context = "replay-derived respawn inferred from death timer"
        accumulator.last_death_decision = None


def _game_state(
    *,
    accumulator: ReplayAccumulator,
    timestamp: int,
    damage_10s: int,
    replay_damage_pressure: bool,
    near_death: bool,
    near_objective: bool,
    recent_item_purchase: str | None,
) -> str:
    if not accumulator.alive:
        return "dead"
    if damage_10s >= 20 or replay_damage_pressure:
        return "laning_pressure"
    if near_death:
        return "dead"
    if near_objective:
        return "objective_fight"
    if recent_item_purchase:
        return "item_timing"
    if timestamp < 10 * 60:
        return "laning"
    return "calm_farming"


def _death_decision(accumulator: ReplayAccumulator, previous_hp: int) -> str:
    if accumulator.deaths >= 2:
        return "REPEATED_DEATH_PATTERN"
    if previous_hp <= 40 or accumulator.mana_percent <= 25:
        return "DEATH_LOW_RESOURCE"
    return "DEATH_REVIEW"


def _apply_common_snapshot(accumulator: ReplayAccumulator, data: dict[str, Any], timestamp: int) -> None:
    raw_health = _first_int(data, "hp", "health")
    raw_max_health = _first_int(data, "max_hp", "max_health")
    if raw_health is not None:
        accumulator.health = max(0, raw_health)
    if raw_max_health is not None:
        accumulator.max_health = max(0, raw_max_health)

    hp_percent = _first_int(data, "hp_percent", "health_percent", "hp_after_percent")
    if hp_percent is None and raw_health is not None and raw_max_health and raw_max_health > 0:
        hp_percent = round((raw_health / raw_max_health) * 100)
    if hp_percent is not None:
        accumulator.hp_percent = _clamp(hp_percent, 0, 100)
        accumulator.hp_confidence = "high"
        accumulator.has_exact_hp = True
        accumulator.last_hp_known_at = timestamp

    raw_mana = _first_int(data, "mana")
    raw_max_mana = _first_int(data, "max_mana")
    if raw_mana is not None:
        accumulator.mana = max(0, raw_mana)
    if raw_max_mana is not None:
        accumulator.max_mana = max(0, raw_max_mana)

    mana_percent = _first_int(data, "mana_percent", "mana_after_percent")
    if mana_percent is None and raw_mana is not None and raw_max_mana and raw_max_mana > 0:
        mana_percent = round((raw_mana / raw_max_mana) * 100)
    if mana_percent is not None:
        accumulator.mana_percent = _clamp(mana_percent, 0, 100)
        accumulator.mana_confidence = "high"
        accumulator.has_exact_mana = True

    level = _first_int(data, "level")
    if level is not None:
        accumulator.level = _clamp(level, 1, 30)
        accumulator.has_exact_level = True

    xp = _first_int(data, "xp")
    if xp is not None:
        accumulator.xp = max(0, xp)

    gold = _first_int(data, "gold")
    if gold is not None:
        accumulator.gold = max(0, gold)
        accumulator.has_exact_gold = True

    total_earned_gold = _first_int(data, "total_earned_gold")
    if total_earned_gold is not None:
        accumulator.total_earned_gold = max(0, total_earned_gold)

    last_hits = _first_int(data, "last_hits", "lh")
    if last_hits is not None:
        accumulator.last_hits = max(0, last_hits)
        accumulator.has_exact_last_hits = True

    gpm = _first_int(data, "gpm")
    if gpm is not None:
        accumulator.gpm = max(0, gpm)
        accumulator.has_exact_last_hits = True

    xpm = _first_int(data, "xpm")
    if xpm is not None:
        accumulator.xpm = max(0, xpm)
        accumulator.has_exact_level = True

    xpos = _first_number(data, "xpos", "x")
    ypos = _first_number(data, "ypos", "y")
    if xpos is not None:
        accumulator.xpos = xpos
    if ypos is not None:
        accumulator.ypos = ypos

    alive = _optional_bool(data.get("alive"))
    if alive is not None:
        accumulator.alive = alive
        accumulator.has_exact_alive = True


def is_minor_replay_item(item: Any) -> bool:
    key = _item_key(item)
    return key in {
        "branches",
        "iron_branch",
        "tango",
        "faerie_fire",
        "healing_salve",
        "clarity",
        "blood_grenade",
        "quelling_blade",
        "magic_stick",
        "magic_wand",
        "boots",
        "boots_of_speed",
        "gloves",
        "gloves_of_haste",
        "boots_of_elves",
        "band_of_elvenskin",
        "belt_of_strength",
        "robe_of_the_magi",
        "circlet",
        "slippers_of_agility",
        "gauntlets_of_strength",
        "mantle_of_intelligence",
        "orb_of_venom",
        "blight_stone",
    }


def _item_key(value: Any) -> str:
    return str(value or "").strip().lower().replace("'", "").replace("-", " ").replace("_", " ").replace(" ", "_")


def _ability_snapshot(data: dict[str, Any]) -> dict[str, Any] | None:
    raw_name = str(data.get("ability") or data.get("name") or data.get("raw_name") or "").strip()
    if not raw_name:
        return None
    cooldown = _first_number(data, "cooldown", "cooldown_remaining", "cooldown_time")
    can_cast = data.get("can_cast")
    if can_cast is None and cooldown is not None:
        can_cast = cooldown <= 0
    return {
        "name": _display_ability_name(raw_name),
        "raw_name": raw_name,
        "level": _first_int(data, "ability_level", "level"),
        "cooldown": cooldown,
        "can_cast": can_cast,
    }


def _is_utility_ability(ability_name: Any) -> bool:
    key = _ability_key(ability_name)
    return key in UTILITY_ABILITY_KEYS or any(keyword in key for keyword in UTILITY_ABILITY_KEYWORDS)


def _is_meaningful_replay_ability(ability_name: Any) -> bool:
    return bool(_ability_key(ability_name)) and not _is_utility_ability(ability_name)


def _is_dangerous_damage_event(data: dict[str, Any]) -> bool:
    text = " ".join(
        str(data.get(key) or "")
        for key in ("ability", "inflictor", "attacker", "event_context")
    )
    key = _ability_key(text)
    return any(keyword in key for keyword in DANGEROUS_DAMAGE_ABILITY_KEYWORDS)


def _display_ability_name(raw_name: str) -> str:
    aliases = {
        "juggernaut_blade_fury": "Blade Fury",
        "blade_fury": "Blade Fury",
        "blade fury": "Blade Fury",
    }
    key = _ability_key(raw_name)
    return aliases.get(key, raw_name.replace("_", " ").title())


def _ability_key(value: Any) -> str:
    text = str(value or "").strip().lower().replace("-", "_")
    text = text.removeprefix("ability_").removeprefix("npc_dota_hero_")
    return text.replace(" ", "_")


def _context_confidence(accumulator: ReplayAccumulator, timestamp: int) -> str:
    if not accumulator.alive:
        return "high"
    if accumulator.last_meaningful_event_at is None:
        return "low"
    event_age = timestamp - accumulator.last_meaningful_event_at
    if event_age <= 5:
        if accumulator.last_meaningful_context_kind == "damage_pressure" and not accumulator.has_exact_hp:
            return "medium"
        return "high"
    if event_age <= 30:
        return "medium"
    return "low"


def _damage_percent(data: dict[str, Any]) -> int:
    direct = _first_int(data, "damage_percent", "damage_taken_percent", "amount_percent")
    if direct is not None:
        return max(0, direct)
    hp_delta = _first_int(data, "hp_delta")
    if hp_delta is not None and hp_delta < 0:
        return abs(hp_delta)
    amount = _first_int(data, "amount", "damage")
    max_health = _first_int(data, "max_health")
    if amount is not None and max_health and max_health > 0:
        return max(0, round((amount / max_health) * 100))
    return 0


def _damage_in_window(events: list[tuple[int, int]], timestamp: int, seconds: int) -> int:
    return sum(amount for event_time, amount in events if 0 <= timestamp - event_time <= seconds)


def _event_count_in_window(events: list[int], timestamp: int, seconds: int) -> int:
    return sum(1 for event_time in events if 0 <= timestamp - event_time <= seconds)


def _has_recent_meaningful_context(accumulator: ReplayAccumulator, timestamp: int) -> bool:
    return (
        accumulator.last_meaningful_event_at is not None
        and 0 <= timestamp - accumulator.last_meaningful_event_at <= 30
    )


def _snapshot_has_exact_farm_data(data: dict[str, Any]) -> bool:
    return any(
        data.get(key) is not None
        for key in (
            "hp_percent",
            "hp",
            "health",
            "mana_percent",
            "mana",
            "alive",
            "last_hits",
            "lh",
            "gpm",
            "gold",
            "level",
            "xpos",
            "ypos",
        )
    )


def _exact_fields(accumulator: ReplayAccumulator) -> list[str]:
    fields: list[str] = []
    if accumulator.has_exact_hp:
        fields.append("hp_percent")
    if accumulator.has_exact_mana:
        fields.append("mana_percent")
    if accumulator.has_exact_gold:
        fields.append("gold")
    if accumulator.has_exact_level:
        fields.append("level")
    if accumulator.has_exact_last_hits:
        fields.append("last_hits")
    if accumulator.has_exact_alive:
        fields.append("alive")
    if accumulator.health is not None:
        fields.append("health")
    if accumulator.max_health is not None:
        fields.append("max_health")
    if accumulator.mana is not None:
        fields.append("mana")
    if accumulator.max_mana is not None:
        fields.append("max_mana")
    if accumulator.xpos is not None and accumulator.ypos is not None:
        fields.append("position")
    return fields


def _defaulted_fields(accumulator: ReplayAccumulator) -> list[str]:
    fields: list[str] = []
    if not accumulator.has_exact_hp:
        fields.append("hp_percent")
    if not accumulator.has_exact_mana:
        fields.append("mana_percent")
    if not accumulator.has_exact_gold:
        fields.append("gold")
    if not accumulator.has_exact_level:
        fields.append("level")
    if not accumulator.has_exact_last_hits:
        fields.append("last_hits")
    if not accumulator.has_exact_alive:
        fields.append("alive")
    return fields


def _has_exact_ability_cooldown(accumulator: ReplayAccumulator) -> bool:
    return any(ability.get("cooldown") is not None for ability in accumulator.abilities.values())


def _nearest_objective(events: list[tuple[int, str, str | None]], timestamp: int) -> tuple[int, str, str | None] | None:
    nearby = [event for event in events if abs(timestamp - event[0]) <= 60]
    if not nearby:
        return None
    return min(nearby, key=lambda event: abs(timestamp - event[0]))


def _load_events(path: Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSONL at {path}:{line_number}: {exc}") from exc
        if isinstance(event, dict):
            events.append(event)
    return sorted(events, key=lambda event: _to_int(event.get("timestamp_seconds"), 0))


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n", encoding="utf-8")


def _join_context(parts: list[str]) -> str:
    return "; ".join(dict.fromkeys(part for part in parts if part))


def _first_int(data: dict[str, Any], *keys: str) -> int | None:
    for key in keys:
        value = _optional_int(data.get(key))
        if value is not None:
            return value
    return None


def _first_number(data: dict[str, Any], *keys: str) -> float | int | None:
    for key in keys:
        value = data.get(key)
        if value is None:
            continue
        try:
            number = float(value)
        except (TypeError, ValueError):
            continue
        return int(number) if number.is_integer() else number
    return None


def _optional_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _optional_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if value is None:
        return None
    text = str(value).strip().lower()
    if text in {"true", "1", "yes", "alive"}:
        return True
    if text in {"false", "0", "no", "dead"}:
        return False
    return None


def _to_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _clamp(value: int, minimum: int, maximum: int) -> int:
    return max(minimum, min(maximum, value))


if __name__ == "__main__":
    raise SystemExit(main())
