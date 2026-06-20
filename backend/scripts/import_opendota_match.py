"""
Import a public OpenDota match into the local simulation JSONL format.

This is offline tooling only. It does not affect live GSI or overlay behavior.

Run from backend/:
    python scripts/import_opendota_match.py --match-id 1234567890 --interval-seconds 60
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests


BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.item_timing import (  # noqa: E402
    classify_item_timing,
    is_meaningful_item_timing,
    normalize_item_name,
)
from app.schemas import SUPPORTED_HEROES  # noqa: E402
from app.signal_capabilities import capability_summary  # noqa: E402


OPENDOTA_MATCH_URL = "https://api.opendota.com/api/matches/{match_id}"
RAW_MATCH_DIR = BACKEND_DIR / "imported_matches"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "data" / "match_simulations"
REQUEST_TIMEOUT_SECONDS = 20

SUPPORTED_HERO_SET = {hero.lower() for hero in SUPPORTED_HEROES}

HERO_ID_TO_NAME = {
    1: "Anti-Mage",
    2: "Axe",
    3: "Bane",
    4: "Bloodseeker",
    5: "Crystal Maiden",
    6: "Drow Ranger",
    7: "Earthshaker",
    8: "Juggernaut",
    9: "Mirana",
    10: "Morphling",
    11: "Shadow Fiend",
    12: "Phantom Lancer",
    13: "Puck",
    14: "Pudge",
    15: "Razor",
    16: "Sand King",
    17: "Storm Spirit",
    18: "Sven",
    19: "Tiny",
    20: "Vengeful Spirit",
    21: "Windranger",
    22: "Zeus",
    23: "Kunkka",
    25: "Lina",
    26: "Lion",
    27: "Shadow Shaman",
    28: "Slardar",
    29: "Tidehunter",
    30: "Witch Doctor",
    31: "Lich",
    32: "Riki",
    33: "Enigma",
    34: "Tinker",
    35: "Sniper",
    36: "Necrophos",
    37: "Warlock",
    38: "Beastmaster",
    39: "Queen of Pain",
    40: "Venomancer",
    41: "Faceless Void",
    42: "Wraith King",
    43: "Death Prophet",
    44: "Phantom Assassin",
    45: "Pugna",
    46: "Templar Assassin",
    47: "Viper",
    48: "Luna",
    49: "Dragon Knight",
    50: "Dazzle",
    51: "Clockwerk",
    52: "Leshrac",
    53: "Nature's Prophet",
    54: "Lifestealer",
    55: "Dark Seer",
    56: "Clinkz",
    57: "Omniknight",
    58: "Enchantress",
    59: "Huskar",
    60: "Night Stalker",
    61: "Broodmother",
    62: "Bounty Hunter",
    63: "Weaver",
    64: "Jakiro",
    65: "Batrider",
    66: "Chen",
    67: "Spectre",
    68: "Ancient Apparition",
    69: "Doom",
    70: "Ursa",
    71: "Spirit Breaker",
    72: "Gyrocopter",
    73: "Alchemist",
    74: "Invoker",
    75: "Silencer",
    76: "Outworld Destroyer",
    77: "Lycan",
    78: "Brewmaster",
    79: "Shadow Demon",
    80: "Lone Druid",
    81: "Chaos Knight",
    82: "Meepo",
    83: "Treant Protector",
    84: "Ogre Magi",
    85: "Undying",
    86: "Rubick",
    87: "Disruptor",
    88: "Nyx Assassin",
    89: "Naga Siren",
    90: "Keeper of the Light",
    91: "Io",
    92: "Visage",
    93: "Slark",
    94: "Medusa",
    95: "Troll Warlord",
    96: "Centaur Warrunner",
    97: "Magnus",
    98: "Timbersaw",
    99: "Bristleback",
    100: "Tusk",
    101: "Skywrath Mage",
    102: "Abaddon",
    103: "Elder Titan",
    104: "Legion Commander",
    105: "Techies",
    106: "Ember Spirit",
    107: "Earth Spirit",
    108: "Underlord",
    109: "Terrorblade",
    110: "Phoenix",
    111: "Oracle",
    112: "Winter Wyvern",
    113: "Arc Warden",
    114: "Monkey King",
    119: "Dark Willow",
    120: "Pangolier",
    121: "Grimstroke",
    123: "Hoodwink",
    126: "Void Spirit",
    128: "Snapfire",
    129: "Mars",
    131: "Ringmaster",
    135: "Dawnbreaker",
    136: "Marci",
    137: "Primal Beast",
    138: "Muerta",
    145: "Kez",
}

XP_BY_LEVEL = [
    0,
    240,
    640,
    1160,
    1760,
    2440,
    3200,
    4000,
    4900,
    5900,
    7000,
    8200,
    9500,
    10900,
    12400,
    14000,
    15700,
    17500,
    19400,
    21400,
    23600,
    26000,
    28600,
    31400,
    34400,
    38400,
    43400,
    49400,
    56400,
    63900,
]


@dataclass
class PlayerCandidate:
    player: dict[str, Any]
    player_slot: int
    account_id: int | None
    hero: str
    last_hits: int
    gold_per_min: int
    carry_item_count: int
    score: float
    supported: bool


@dataclass(frozen=True)
class PurchaseEvent:
    time: int
    item: str
    timing_category: str | None = None
    inferred: bool = False


@dataclass(frozen=True)
class ObjectiveEvent:
    time: int
    objective_type: str
    objective_team: str | None


@dataclass(frozen=True)
class TeamfightEvent:
    start: int
    end: int
    allied_deaths: int
    enemy_deaths: int
    selected_player_in_teamfight: bool
    selected_player_deaths: int
    result: str


@dataclass(frozen=True)
class TeamContextSnapshot:
    selected_team: str
    near_teamfight: bool
    teamfight_start: int | None
    teamfight_end: int | None
    allied_deaths_in_fight: int
    enemy_deaths_in_fight: int
    selected_player_in_teamfight: bool
    teamfight_result: str
    recent_allied_deaths: int
    recent_enemy_deaths: int
    selected_player_death_nearby: bool
    team_status: str
    near_objective: bool
    objective_type: str | None
    objective_team: str | None
    objective_for_selected_team: bool | None
    objective_context: str


@dataclass(frozen=True)
class MatchEvents:
    objective_times: list[int]
    teamfight_windows: list[tuple[int, int]]
    death_times: list[int]
    death_times_inferred: bool
    kill_times: list[int]
    kill_times_inferred: bool
    purchase_events: list[PurchaseEvent]
    selected_team: str
    objective_events: list[ObjectiveEvent]
    teamfight_events: list[TeamfightEvent]
    allied_death_times: list[int]
    enemy_death_times: list[int]


def main() -> int:
    args = _parse_args()
    try:
        match = _fetch_match(args.match_id)
    except (requests.RequestException, ValueError) as exc:
        print(f"Failed to fetch OpenDota match {args.match_id}: {exc}")
        return 1
    raw_path = _write_raw_match(args.match_id, match)

    players = match.get("players")
    if not isinstance(players, list) or not players:
        print("OpenDota response does not contain a usable players list.")
        return 1

    selected = _select_player(
        players,
        account_id=args.account_id,
        player_slot=args.player_slot,
    )
    if selected is None:
        _print_candidates(_rank_candidates(players))
        print("Could not confidently auto-select a supported carry. Rerun with --player-slot or --account-id.")
        return 1

    if not selected.supported:
        _print_candidates(_rank_candidates(players))
        print(
            f"Selected hero '{selected.hero}' is not supported by the current simulation schema. "
            "Rerun with a supported carry player slot."
        )
        return 1

    output_path = (
        Path(args.output)
        if args.output
        else DEFAULT_OUTPUT_DIR / f"opendota_match_{args.match_id}.jsonl"
    )
    rows = _build_simulation_rows(
        match=match,
        player=selected.player,
        hero=selected.hero,
        interval_seconds=args.interval_seconds,
        start_minute=args.start_minute,
        end_minute=args.end_minute,
    )
    _write_jsonl(output_path, rows)

    print(f"Raw OpenDota match saved: {raw_path}")
    print(f"Simulation JSONL saved: {output_path}")
    print(
        "Selected player: "
        f"slot={selected.player_slot}, hero={selected.hero}, "
        f"last_hits={selected.last_hits}, gpm={selected.gold_per_min}"
    )
    print(
        "Timeline: "
        f"interval={args.interval_seconds}s, "
        f"start={args.start_minute}m, "
        f"end={args.end_minute if args.end_minute is not None else 'match_end'}m, "
        f"states={len(rows)}"
    )
    print(
        "Next: "
        f"python scripts/simulate_match_advice.py --simulation-file {output_path}"
    )
    return 0


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import a public OpenDota match into match simulation JSONL.",
    )
    parser.add_argument("--match-id", required=True, help="OpenDota match id.")
    parser.add_argument(
        "--interval-seconds",
        type=int,
        default=60,
        help="Spacing between generated simulation states.",
    )
    parser.add_argument(
        "--start-minute",
        type=int,
        default=0,
        help="First game minute to export. Defaults to 0.",
    )
    parser.add_argument(
        "--end-minute",
        type=int,
        help="Last game minute to export. Defaults to match end.",
    )
    parser.add_argument("--player-slot", type=int, help="Exact OpenDota player_slot to import.")
    parser.add_argument("--account-id", type=int, help="OpenDota account_id to import.")
    parser.add_argument("--output", help="Output JSONL path. Defaults to data/match_simulations/opendota_match_<match_id>.jsonl.")
    args = parser.parse_args()
    if args.interval_seconds < 1:
        parser.error("--interval-seconds must be at least 1")
    if args.start_minute < 0:
        parser.error("--start-minute must be >= 0")
    if args.end_minute is not None and args.end_minute <= args.start_minute:
        parser.error("--end-minute must be greater than --start-minute")
    return args


def _fetch_match(match_id: str) -> dict[str, Any]:
    url = OPENDOTA_MATCH_URL.format(match_id=match_id)
    response = requests.get(url, timeout=REQUEST_TIMEOUT_SECONDS)
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise ValueError("OpenDota response must be a JSON object.")
    if payload.get("error"):
        raise ValueError(f"OpenDota error: {payload['error']}")
    return payload


def _write_raw_match(match_id: str, match: dict[str, Any]) -> Path:
    RAW_MATCH_DIR.mkdir(parents=True, exist_ok=True)
    path = RAW_MATCH_DIR / f"opendota_match_{match_id}_raw.json"
    path.write_text(json.dumps(match, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = "\n".join(json.dumps(row, ensure_ascii=False) for row in rows)
    path.write_text(content + "\n", encoding="utf-8")


def _select_player(
    players: list[dict[str, Any]],
    *,
    account_id: int | None,
    player_slot: int | None,
) -> PlayerCandidate | None:
    candidates = _rank_candidates(players)

    if account_id is not None:
        return next((candidate for candidate in candidates if candidate.account_id == account_id), None)

    if player_slot is not None:
        return next((candidate for candidate in candidates if candidate.player_slot == player_slot), None)

    supported = [candidate for candidate in candidates if candidate.supported]
    if not supported:
        return None

    best = supported[0]
    second = supported[1] if len(supported) > 1 else None
    if second and best.score - second.score < 60:
        return None
    return best


def _rank_candidates(players: list[dict[str, Any]]) -> list[PlayerCandidate]:
    candidates = [_build_candidate(player) for player in players]
    return sorted(candidates, key=lambda candidate: candidate.score, reverse=True)


def _build_candidate(player: dict[str, Any]) -> PlayerCandidate:
    hero = _hero_name(player.get("hero_id"))
    last_hits = _to_int(player.get("last_hits"), _last_t_value(player.get("lh_t"), 0))
    gold_per_min = _to_int(player.get("gold_per_min"), 0)
    carry_item_count = _carry_item_count(player)
    supported = hero.lower() in SUPPORTED_HERO_SET
    score = (
        gold_per_min
        + last_hits * 2
        + carry_item_count * 75
        + (40 if supported else -80)
    )
    return PlayerCandidate(
        player=player,
        player_slot=_to_int(player.get("player_slot"), -1),
        account_id=_optional_int(player.get("account_id")),
        hero=hero,
        last_hits=last_hits,
        gold_per_min=gold_per_min,
        carry_item_count=carry_item_count,
        score=score,
        supported=supported,
    )


def _print_candidates(candidates: list[PlayerCandidate]) -> None:
    print("Candidate carries:")
    print("slot | account_id | hero | lh | gpm | carry_items | supported | score")
    for candidate in candidates[:10]:
        print(
            f"{candidate.player_slot} | "
            f"{candidate.account_id or '-'} | "
            f"{candidate.hero} | "
            f"{candidate.last_hits} | "
            f"{candidate.gold_per_min} | "
            f"{candidate.carry_item_count} | "
            f"{'yes' if candidate.supported else 'no'} | "
            f"{candidate.score:.0f}"
        )


def _build_simulation_rows(
    *,
    match: dict[str, Any],
    player: dict[str, Any],
    hero: str,
    interval_seconds: int,
    start_minute: int,
    end_minute: int | None,
) -> list[dict[str, Any]]:
    duration = max(_to_int(match.get("duration"), 0), interval_seconds)
    start_seconds = min(duration, max(0, start_minute * 60))
    requested_end_seconds = duration if end_minute is None else end_minute * 60
    end_seconds = max(start_seconds, min(duration, requested_end_seconds))
    events = _extract_match_events(match, player, duration)
    farm_window_seconds = max(60, interval_seconds)
    timeline_context = _timeline_inference_context(player, interval_seconds)
    rows: list[dict[str, Any]] = []

    for timestamp in range(start_seconds, end_seconds + 1, interval_seconds):
        minute = min(90, timestamp // 60)
        team_context = _team_context_at(timestamp, events)
        near_player_death = team_context.selected_player_death_nearby or _near_player_death(timestamp, events.death_times)
        near_teamfight = team_context.near_teamfight or _near_teamfight(timestamp, events)
        near_objective = team_context.near_objective or _near_any(timestamp, events.objective_times, max(60, interval_seconds))
        recent_item_timing = _recent_item_timing(events.purchase_events, timestamp, interval_seconds)
        recent_item_purchase = recent_item_timing.item if recent_item_timing else None
        item_timing_category = recent_item_timing.timing_category if recent_item_timing else None
        gold_delta = _gold_delta_at_timestamp(player, timestamp, farm_window_seconds)
        lh_delta = _lh_delta_at_timestamp(player, timestamp, farm_window_seconds)
        farm_rate_state = _farm_rate_state(gold_delta, lh_delta)
        previous_farm_timestamp = max(0, timestamp - farm_window_seconds)
        low_farm_pressure = (
            farm_rate_state == "slow"
            and _farm_rate_state(
                _gold_delta_at_timestamp(player, previous_farm_timestamp, farm_window_seconds),
                _lh_delta_at_timestamp(player, previous_farm_timestamp, farm_window_seconds),
            ) == "slow"
            and (near_player_death or near_teamfight or near_objective or minute < 18)
        )
        game_state, event_context = _state_context_at(
            timestamp=timestamp,
            minute=minute,
            events=events,
            near_player_death=near_player_death,
            near_teamfight=near_teamfight,
            near_objective=near_objective,
            team_context=team_context,
            recent_item_purchase=recent_item_purchase,
            item_timing_category=item_timing_category,
            low_farm_pressure=low_farm_pressure,
            farm_rate_state=farm_rate_state,
        )
        event_context = _join_context([event_context, timeline_context])
        context_confidence = _opendota_context_confidence(
            near_player_death=near_player_death,
            near_teamfight=near_teamfight,
            near_objective=near_objective,
            recent_item_purchase=recent_item_purchase,
        )
        capabilities = capability_summary("opendota_import")
        state = {
            "hero": hero,
            "role": "carry",
            "minute": minute,
            "level": _level_at_timestamp(player, timestamp),
            "gold": _gold_at_timestamp(player, timestamp),
            "items": _items_at(events.purchase_events, timestamp),
            "hp_percent": _hp_at(timestamp, events.death_times),
            "game_state": game_state,
            "team_status": team_context.team_status,
            "event_context": event_context,
            "near_player_death": near_player_death,
            "near_teamfight": near_teamfight,
            "near_objective": near_objective,
            "selected_team": team_context.selected_team,
            "teamfight_start": team_context.teamfight_start,
            "teamfight_end": team_context.teamfight_end,
            "teamfight_result": team_context.teamfight_result,
            "allied_deaths_in_fight": team_context.allied_deaths_in_fight,
            "enemy_deaths_in_fight": team_context.enemy_deaths_in_fight,
            "selected_player_in_teamfight": team_context.selected_player_in_teamfight,
            "recent_allied_deaths": team_context.recent_allied_deaths,
            "recent_enemy_deaths": team_context.recent_enemy_deaths,
            "selected_player_death_nearby": team_context.selected_player_death_nearby,
            "objective_type": team_context.objective_type,
            "objective_team": team_context.objective_team,
            "objective_for_selected_team": team_context.objective_for_selected_team,
            "objective_context": team_context.objective_context,
            "recent_item_purchase": recent_item_purchase,
            "item_timing_category": item_timing_category,
            "gold_delta": gold_delta,
            "lh_delta": lh_delta,
            "farm_rate_state": farm_rate_state,
            "extra_context": {
                "source_type": "opendota_import",
                "context_confidence": context_confidence,
                **capabilities,
                "sample_interval_seconds": interval_seconds,
                "farm_window_seconds": farm_window_seconds,
                "timeline_inference": timeline_context,
            },
        }
        rows.append({"timestamp_seconds": timestamp, "state": state})

    return rows


def _opendota_context_confidence(
    *,
    near_player_death: bool,
    near_teamfight: bool,
    near_objective: bool,
    recent_item_purchase: str | None,
) -> str:
    if near_player_death or near_teamfight or near_objective:
        return "medium"
    if recent_item_purchase:
        return "medium"
    return "low"


def _extract_match_events(match: dict[str, Any], player: dict[str, Any], duration: int) -> MatchEvents:
    players = match.get("players") if isinstance(match.get("players"), list) else []
    selected_slot = _to_int(player.get("player_slot"), -1)
    selected_team = _team_from_slot(selected_slot)
    objective_events = _objective_events(match, selected_team, players)
    teamfight_events = _teamfight_events(match, players, selected_team, selected_slot)
    selected_teamfight_death_times = _selected_teamfight_death_times(teamfight_events)
    death_times, death_times_inferred = _death_times(player, duration)
    if selected_teamfight_death_times:
        remaining_deaths = max(0, _to_int(player.get("deaths"), 0) - len(selected_teamfight_death_times))
        death_times = sorted(
            set(selected_teamfight_death_times)
            | set(_spread_inferred_events(remaining_deaths, duration, start_ratio=0.18, end_ratio=0.9))
        )
        death_times_inferred = remaining_deaths > 0
    kill_times, kill_times_inferred = _kill_times(player, duration)
    teamfight_windows = [(event.start, event.end) for event in teamfight_events]
    if not teamfight_windows:
        inferred_fight_times = sorted(set(death_times + kill_times))
        teamfight_windows = [
            (max(0, event_time - 20), min(duration, event_time + 20))
            for event_time in inferred_fight_times
        ]

    allied_death_times, enemy_death_times = _team_death_times(
        players=players,
        selected_team=selected_team,
        duration=duration,
        teamfight_events=teamfight_events,
    )
    allied_death_times = _append_unique_times(allied_death_times, death_times)
    enemy_death_times = _append_unique_times(enemy_death_times, kill_times)

    return MatchEvents(
        objective_times=[event.time for event in objective_events],
        teamfight_windows=teamfight_windows,
        death_times=death_times,
        death_times_inferred=death_times_inferred,
        kill_times=kill_times,
        kill_times_inferred=kill_times_inferred,
        purchase_events=_purchase_events(player, duration),
        selected_team=selected_team,
        objective_events=objective_events,
        teamfight_events=teamfight_events,
        allied_death_times=allied_death_times,
        enemy_death_times=enemy_death_times,
    )


def _team_context_at(timestamp: int, events: MatchEvents) -> TeamContextSnapshot:
    teamfights = [
        fight for fight in events.teamfight_events
        if fight.start - 45 <= timestamp <= fight.end + 45
    ]
    nearest_fight = min(teamfights, key=lambda fight: _distance_to_window(timestamp, fight.start, fight.end), default=None)
    allied_deaths_in_fight = sum(fight.allied_deaths for fight in teamfights)
    enemy_deaths_in_fight = sum(fight.enemy_deaths for fight in teamfights)
    selected_player_in_teamfight = any(fight.selected_player_in_teamfight for fight in teamfights)
    teamfight_result = _fight_result(allied_deaths_in_fight, enemy_deaths_in_fight) if teamfights else "unknown"

    objective = min(
        [event for event in events.objective_events if abs(timestamp - event.time) <= 60],
        key=lambda event: abs(timestamp - event.time),
        default=None,
    )
    objective_for_selected_team = (
        None
        if objective is None or objective.objective_team is None or events.selected_team == "unknown"
        else objective.objective_team == events.selected_team
    )
    near_objective = objective is not None

    recent_allied_deaths = sum(1 for time in events.allied_death_times if abs(timestamp - time) <= 60)
    recent_enemy_deaths = sum(1 for time in events.enemy_death_times if abs(timestamp - time) <= 60)
    selected_player_death_nearby = _near_player_death(timestamp, events.death_times)

    team_status = _team_status(
        recent_allied_deaths=recent_allied_deaths,
        recent_enemy_deaths=recent_enemy_deaths,
        allied_deaths_in_fight=allied_deaths_in_fight,
        enemy_deaths_in_fight=enemy_deaths_in_fight,
        has_team_context=bool(teamfights or objective),
    )
    objective_context = _objective_context(
        near_objective=near_objective,
        objective_for_selected_team=objective_for_selected_team,
        teamfight_result=teamfight_result,
        recent_allied_deaths=recent_allied_deaths,
        recent_enemy_deaths=recent_enemy_deaths,
    )

    return TeamContextSnapshot(
        selected_team=events.selected_team,
        near_teamfight=bool(teamfights),
        teamfight_start=nearest_fight.start if nearest_fight else None,
        teamfight_end=nearest_fight.end if nearest_fight else None,
        allied_deaths_in_fight=allied_deaths_in_fight,
        enemy_deaths_in_fight=enemy_deaths_in_fight,
        selected_player_in_teamfight=selected_player_in_teamfight,
        teamfight_result=teamfight_result,
        recent_allied_deaths=recent_allied_deaths,
        recent_enemy_deaths=recent_enemy_deaths,
        selected_player_death_nearby=selected_player_death_nearby,
        team_status=team_status,
        near_objective=near_objective,
        objective_type=objective.objective_type if objective else None,
        objective_team=objective.objective_team if objective else None,
        objective_for_selected_team=objective_for_selected_team,
        objective_context=objective_context,
    )


def _distance_to_window(timestamp: int, start: int, end: int) -> int:
    if start <= timestamp <= end:
        return 0
    return min(abs(timestamp - start), abs(timestamp - end))


def _team_status(
    *,
    recent_allied_deaths: int,
    recent_enemy_deaths: int,
    allied_deaths_in_fight: int,
    enemy_deaths_in_fight: int,
    has_team_context: bool,
) -> str:
    if recent_enemy_deaths > recent_allied_deaths:
        return "advantage"
    if recent_allied_deaths > recent_enemy_deaths:
        return "disadvantage"
    if enemy_deaths_in_fight > allied_deaths_in_fight:
        return "advantage"
    if allied_deaths_in_fight > enemy_deaths_in_fight:
        return "disadvantage"
    if has_team_context:
        return "even"
    return "unknown"


def _objective_context(
    *,
    near_objective: bool,
    objective_for_selected_team: bool | None,
    teamfight_result: str,
    recent_allied_deaths: int,
    recent_enemy_deaths: int,
) -> str:
    if not near_objective:
        return "unknown"
    if teamfight_result == "even" or (recent_allied_deaths > 0 and recent_enemy_deaths > 0):
        return "contested_objective"
    if objective_for_selected_team is True:
        return "friendly_objective"
    if objective_for_selected_team is False:
        return "enemy_objective"
    return "unknown"


def _state_context_at(
    *,
    timestamp: int,
    minute: int,
    events: MatchEvents,
    near_player_death: bool,
    near_teamfight: bool,
    near_objective: bool,
    team_context: TeamContextSnapshot,
    recent_item_purchase: str | None,
    item_timing_category: str | None,
    low_farm_pressure: bool,
    farm_rate_state: str,
) -> tuple[str, str]:
    context: list[str] = []
    if near_player_death:
        if events.death_times_inferred:
            context.append("player death count nearby; danger window inferred from match summary")
        else:
            context.append("player death nearby; danger window inferred from match events")
    if near_objective:
        if team_context.objective_context == "friendly_objective":
            context.append(f"friendly objective nearby: {team_context.objective_type}")
        elif team_context.objective_context == "enemy_objective":
            context.append(f"enemy objective nearby: {team_context.objective_type}")
        elif team_context.objective_context == "contested_objective":
            context.append(f"contested objective nearby: {team_context.objective_type}")
        else:
            context.append("objective event nearby")
    if near_teamfight:
        if events.kill_times_inferred or events.death_times_inferred:
            context.append("fight pressure inferred from kill/death counts")
        else:
            context.append("teamfight nearby")
        if team_context.teamfight_result != "unknown":
            context.append(f"teamfight result: {team_context.teamfight_result}")
    if team_context.team_status != "unknown":
        context.append(f"team status: {team_context.team_status}")
    elif near_teamfight or near_objective:
        context.append("team_status_unknown")
    if recent_item_purchase:
        context.append(f"meaningful item timing: {recent_item_purchase}")
    if farm_rate_state == "slow":
        context.append("slow farm gain in recent interval")

    if near_player_death and not near_objective:
        return "bad_fight_risk", _join_context(context)
    if near_objective:
        if near_player_death:
            context.append("objective fight has elevated death risk")
        return "objective_fight", _join_context(context)
    if near_teamfight:
        return "bad_fight_risk", _join_context(context)
    if recent_item_purchase:
        return "item_timing", _join_context(context)
    if low_farm_pressure:
        context.append("low farm for multiple intervals while pressure is nearby")
        return "farming_pressure", _join_context(context)
    if minute < 10:
        return "laning", _join_context(context) or "laning phase from match time"
    if farm_rate_state == "good":
        return "safe_farming", _join_context(context) or "steady farm gain; no major event nearby"
    return "calm_farming", _join_context(context) or "no major event nearby"


def _join_context(parts: list[str]) -> str:
    return "; ".join(dict.fromkeys(part for part in parts if part))


def _hp_at(timestamp: int, death_times: list[int]) -> int:
    if any(0 <= death_time - timestamp <= 60 for death_time in death_times):
        return 30
    return 100


def _gold_at(player: dict[str, Any], minute: int) -> int:
    return _gold_at_timestamp(player, minute * 60)


def _gold_at_timestamp(player: dict[str, Any], timestamp: int) -> int:
    gold_t = player.get("gold_t")
    if isinstance(gold_t, list) and gold_t:
        return max(0, _timeline_value_at(gold_t, timestamp, 600, interpolate=True))
    gpm = _to_int(player.get("gold_per_min"), 0)
    return max(0, 600 + round((gpm / 60) * timestamp))


def _level_at(player: dict[str, Any], minute: int) -> int:
    return _level_at_timestamp(player, minute * 60)


def _level_at_timestamp(player: dict[str, Any], timestamp: int) -> int:
    xp_t = player.get("xp_t")
    if isinstance(xp_t, list) and xp_t:
        xp = _timeline_value_at(xp_t, timestamp, 0, interpolate=False)
        return _level_from_xp(xp)
    return max(1, min(30, 1 + (timestamp // 60) // 2))


def _level_from_xp(xp: int) -> int:
    level = 1
    for index, threshold in enumerate(XP_BY_LEVEL, start=1):
        if xp >= threshold:
            level = index
    return max(1, min(30, level))


def _gold_delta_at(player: dict[str, Any], minute: int, interval_minutes: int) -> int:
    return _gold_delta_at_timestamp(player, minute * 60, interval_minutes * 60)


def _gold_delta_at_timestamp(player: dict[str, Any], timestamp: int, window_seconds: int) -> int:
    current = _gold_at_timestamp(player, timestamp)
    previous = _gold_at_timestamp(player, max(0, timestamp - window_seconds))
    return max(0, current - previous)


def _lh_delta_at(player: dict[str, Any], minute: int, interval_minutes: int) -> int:
    return _lh_delta_at_timestamp(player, minute * 60, interval_minutes * 60)


def _lh_delta_at_timestamp(player: dict[str, Any], timestamp: int, window_seconds: int) -> int:
    current = _lh_at_timestamp(player, timestamp)
    previous = _lh_at_timestamp(player, max(0, timestamp - window_seconds))
    return max(0, current - previous)


def _lh_at(player: dict[str, Any], minute: int) -> int:
    return _lh_at_timestamp(player, minute * 60)


def _lh_at_timestamp(player: dict[str, Any], timestamp: int) -> int:
    lh_t = player.get("lh_t")
    if isinstance(lh_t, list) and lh_t:
        return _timeline_value_at(lh_t, timestamp, 0, interpolate=False)

    duration_minutes = max(1, round(_to_int(player.get("duration"), 0) / 60))
    last_hits = _to_int(player.get("last_hits"), 0)
    return max(0, round((last_hits / (duration_minutes * 60)) * timestamp))


def _farm_rate_state(gold_delta: int, lh_delta: int) -> str:
    if gold_delta <= 0 and lh_delta <= 0:
        return "unknown"
    if lh_delta >= 4 or gold_delta >= 300:
        return "good"
    if lh_delta <= 1 and gold_delta < 220:
        return "slow"
    return "unknown"


def _near_player_death(timestamp: int, death_times: list[int]) -> bool:
    return any(-15 <= timestamp - death_time <= 60 or 0 <= death_time - timestamp <= 60 for death_time in death_times)


def _near_teamfight(timestamp: int, events: MatchEvents) -> bool:
    if any(start - 30 <= timestamp <= end + 30 for start, end in events.teamfight_windows):
        return True
    return _near_any(timestamp, events.kill_times, 45)


def _recent_item_timing(events: list[PurchaseEvent], timestamp: int, interval_seconds: int) -> PurchaseEvent | None:
    recent = [
        event for event in events
        if _nearest_interval_timestamp(event.time, interval_seconds) == timestamp
    ]
    if not recent:
        return None
    return min(
        recent,
        key=lambda event: (
            _timing_priority(event.timing_category),
            abs(timestamp - event.time),
        ),
    )


def _nearest_interval_timestamp(event_time: int, interval_seconds: int) -> int:
    interval = max(1, interval_seconds)
    return round(event_time / interval) * interval


def _timing_priority(category: str | None) -> int:
    priorities = {
        "defensive_timings": 0,
        "farming_timings": 1,
        "mobility_timings": 2,
        "damage_timings": 3,
        "late_game_timings": 4,
        "fight_timings": 5,
        "situational_timings": 6,
    }
    return priorities.get(category or "", 9)


def _items_at(events: list[PurchaseEvent], timestamp: int) -> list[str]:
    items: list[str] = []
    seen: set[str] = set()
    for event in sorted(events, key=lambda item: item.time):
        if event.time > timestamp:
            continue
        if event.item not in seen:
            items.append(event.item)
            seen.add(event.item)
    return items


def _purchase_events(player: dict[str, Any], duration: int) -> list[PurchaseEvent]:
    purchase_log = player.get("purchase_log")
    if isinstance(purchase_log, list) and purchase_log:
        events: list[PurchaseEvent] = []
        seen_meaningful_items: set[str] = set()
        for purchase in purchase_log:
            key = str(purchase.get("key", "")).strip().lower()
            timing = classify_item_timing(key)
            if not timing["is_meaningful"]:
                continue
            item = str(timing["item"])
            item_key = item.lower()
            if item_key in seen_meaningful_items:
                continue
            seen_meaningful_items.add(item_key)
            events.append(
                PurchaseEvent(
                    time=max(0, _to_int(purchase.get("time"), 0)),
                    item=item,
                    timing_category=str(timing["category"] or ""),
                    inferred=False,
                )
            )
        return _dedupe_purchase_events(events)

    final_items = _final_inventory_items(player)
    meaningful = [item for item in final_items if is_meaningful_item_timing(item)]
    if not meaningful:
        return []

    start = max(8 * 60, duration // 4)
    end = max(start + 60, min(duration - 60, int(duration * 0.85)))
    step = max(60, (end - start) // max(1, len(meaningful)))
    return [
        PurchaseEvent(
            time=min(duration, start + index * step),
            item=item,
            timing_category=str(classify_item_timing(item)["category"] or ""),
            inferred=True,
        )
        for index, item in enumerate(meaningful)
    ]


def _dedupe_purchase_events(events: list[PurchaseEvent]) -> list[PurchaseEvent]:
    seen: set[str] = set()
    deduped: list[PurchaseEvent] = []
    for event in sorted(events, key=lambda item: item.time):
        if event.item in seen:
            continue
        deduped.append(event)
        seen.add(event.item)
    return deduped


def _final_inventory_items(player: dict[str, Any]) -> list[str]:
    items: list[str] = []
    seen: set[str] = set()
    for slot in ("item_0", "item_1", "item_2", "item_3", "item_4", "item_5"):
        item_id = _to_int(player.get(slot), 0)
        if item_id <= 0:
            continue
        item = _display_item_id(item_id)
        if item not in seen:
            items.append(item)
            seen.add(item)
    return items


def _objective_events(
    match: dict[str, Any],
    selected_team: str,
    players: list[dict[str, Any]],
) -> list[ObjectiveEvent]:
    objectives = match.get("objectives")
    if not isinstance(objectives, list):
        return []

    events: list[ObjectiveEvent] = []
    for objective in objectives:
        if not isinstance(objective, dict):
            continue
        objective_type = _objective_type(objective)
        if objective_type is None:
            continue
        time = _to_int(objective.get("time"), -1)
        if time < 0:
            continue
        events.append(
            ObjectiveEvent(
                time=time,
                objective_type=objective_type,
                objective_team=_objective_team(objective, selected_team, players),
            )
        )
    return sorted(events, key=lambda event: event.time)


def _objective_type(objective: dict[str, Any]) -> str | None:
    raw_type = str(objective.get("type", "")).lower()
    key = str(objective.get("key", "")).lower()
    text = f"{raw_type} {key}"
    if "roshan" in text:
        return "roshan"
    if "aegis" in text:
        return "aegis"
    if "barracks" in text or "rax" in text:
        return "barracks"
    if "tower" in text:
        return "tower"
    if "fort" in text or "ancient" in text:
        return "ancient"
    if "building" in text:
        return "building"
    return None


def _objective_team(
    objective: dict[str, Any],
    selected_team: str,
    players: list[dict[str, Any]],
) -> str | None:
    if "player_slot" in objective:
        team = _team_from_slot(_to_int(objective.get("player_slot"), -1))
        if team != "unknown":
            return team

    if "slot" in objective:
        slot = _to_int(objective.get("slot"), -1)
        player = players[slot] if 0 <= slot < len(players) else {}
        team = _team_from_slot(_to_int(player.get("player_slot"), -1))
        if team != "unknown":
            return team

    team = _team_from_opendota_team(objective.get("team"))
    if team is not None:
        return team

    key = str(objective.get("key", "")).lower()
    if "badguys" in key:
        return "radiant"
    if "goodguys" in key:
        return "dire"
    return selected_team if selected_team != "unknown" else None


def _teamfight_events(
    match: dict[str, Any],
    players: list[dict[str, Any]],
    selected_team: str,
    selected_slot: int,
) -> list[TeamfightEvent]:
    teamfights = match.get("teamfights")
    if not isinstance(teamfights, list):
        return []

    events: list[TeamfightEvent] = []
    for fight in teamfights:
        if not isinstance(fight, dict):
            continue
        start = _to_int(fight.get("start"), -1)
        end = max(start, _to_int(fight.get("end"), start))
        if start < 0:
            continue

        allied_deaths = 0
        enemy_deaths = 0
        selected_player_in_teamfight = False
        selected_player_deaths = 0
        fight_players = fight.get("players")
        if not isinstance(fight_players, list):
            fight_players = []

        for index, fight_player in enumerate(fight_players):
            if not isinstance(fight_player, dict):
                continue
            player = players[index] if index < len(players) else {}
            player_slot = _to_int(player.get("player_slot"), index)
            player_team = _team_from_slot(player_slot)
            deaths = max(0, _to_int(fight_player.get("deaths"), 0))

            if player_team == selected_team:
                allied_deaths += deaths
            elif player_team != "unknown":
                enemy_deaths += deaths

            if player_slot == selected_slot:
                selected_player_deaths = deaths
                selected_player_in_teamfight = _player_participated_in_fight(fight_player)

        events.append(
            TeamfightEvent(
                start=start,
                end=end,
                allied_deaths=allied_deaths,
                enemy_deaths=enemy_deaths,
                selected_player_in_teamfight=selected_player_in_teamfight,
                selected_player_deaths=selected_player_deaths,
                result=_fight_result(allied_deaths, enemy_deaths),
            )
        )
    return sorted(events, key=lambda event: event.start)


def _team_death_times(
    *,
    players: list[dict[str, Any]],
    selected_team: str,
    duration: int,
    teamfight_events: list[TeamfightEvent],
) -> tuple[list[int], list[int]]:
    allied_deaths: list[int] = []
    enemy_deaths: list[int] = []
    for event in teamfight_events:
        death_time = event.end
        allied_deaths.extend([death_time] * event.allied_deaths)
        enemy_deaths.extend([death_time] * event.enemy_deaths)

    if allied_deaths or enemy_deaths:
        return sorted(allied_deaths), sorted(enemy_deaths)

    for player in players:
        team = _team_from_slot(_to_int(player.get("player_slot"), -1))
        deaths = _to_int(player.get("deaths"), 0)
        inferred = _spread_inferred_events(deaths, duration, start_ratio=0.18, end_ratio=0.9)
        if team == selected_team:
            allied_deaths.extend(inferred)
        elif team != "unknown":
            enemy_deaths.extend(inferred)
    return sorted(allied_deaths), sorted(enemy_deaths)


def _selected_teamfight_death_times(teamfight_events: list[TeamfightEvent]) -> list[int]:
    times: list[int] = []
    for event in teamfight_events:
        times.extend([event.end] * event.selected_player_deaths)
    return sorted(times)


def _append_unique_times(existing: list[int], additional: list[int], *, tolerance_seconds: int = 10) -> list[int]:
    merged = list(existing)
    for time in additional:
        if not any(abs(time - current) <= tolerance_seconds for current in merged):
            merged.append(time)
    return sorted(merged)


def _player_participated_in_fight(fight_player: dict[str, Any]) -> bool:
    numeric_fields = ("deaths", "damage", "healing", "gold_delta", "xp_delta")
    if any(_to_int(fight_player.get(field), 0) > 0 for field in numeric_fields):
        return True
    for field in ("killed", "ability_uses", "item_uses"):
        value = fight_player.get(field)
        if isinstance(value, dict) and value:
            return True
    return False


def _fight_result(allied_deaths: int, enemy_deaths: int) -> str:
    if enemy_deaths > allied_deaths:
        return "favorable"
    if allied_deaths > enemy_deaths:
        return "bad"
    return "even"


def _team_from_slot(player_slot: int) -> str:
    if player_slot < 0:
        return "unknown"
    return "radiant" if player_slot < 128 else "dire"


def _team_from_opendota_team(value: Any) -> str | None:
    team = _to_int(value, -1)
    if team == 2:
        return "radiant"
    if team == 3:
        return "dire"
    return None


def _objective_times(match: dict[str, Any]) -> list[int]:
    objectives = match.get("objectives")
    if not isinstance(objectives, list):
        return []
    objective_keywords = ("tower", "roshan", "barracks", "aegis", "fort", "building")
    times: list[int] = []
    for objective in objectives:
        text = " ".join(str(objective.get(key, "")) for key in ("type", "key"))
        if any(keyword in text.lower() for keyword in objective_keywords):
            times.append(_to_int(objective.get("time"), 0))
    return [time for time in times if time >= 0]


def _teamfight_windows(match: dict[str, Any]) -> list[tuple[int, int]]:
    teamfights = match.get("teamfights")
    if not isinstance(teamfights, list):
        return []
    windows: list[tuple[int, int]] = []
    for fight in teamfights:
        start = _to_int(fight.get("start"), -1)
        end = _to_int(fight.get("end"), start)
        if start >= 0:
            windows.append((start, max(start, end)))
    return windows


def _death_times(player: dict[str, Any], duration: int) -> tuple[list[int], bool]:
    death_log = player.get("death_log")
    if isinstance(death_log, list) and death_log:
        return (
            sorted(
                _to_int(entry.get("time"), -1)
                for entry in death_log
                if isinstance(entry, dict) and _to_int(entry.get("time"), -1) >= 0
            ),
            False,
        )

    death_count = _to_int(player.get("deaths"), 0)
    return _spread_inferred_events(death_count, duration, start_ratio=0.18, end_ratio=0.9), death_count > 0


def _kill_times(player: dict[str, Any], duration: int) -> tuple[list[int], bool]:
    kills_log = player.get("kills_log")
    if isinstance(kills_log, list) and kills_log:
        return (
            sorted(
                _to_int(entry.get("time"), -1)
                for entry in kills_log
                if isinstance(entry, dict) and _to_int(entry.get("time"), -1) >= 0
            ),
            False,
        )

    kill_count = _to_int(player.get("kills"), 0)
    return _spread_inferred_events(kill_count, duration, start_ratio=0.22, end_ratio=0.86), kill_count > 0


def _spread_inferred_events(count: int, duration: int, *, start_ratio: float, end_ratio: float) -> list[int]:
    if count <= 0 or duration <= 0:
        return []
    start = int(duration * start_ratio)
    end = int(duration * end_ratio)
    if count == 1:
        return [max(0, min(duration, (start + end) // 2))]
    step = (end - start) / (count - 1)
    return [max(0, min(duration, round(start + index * step))) for index in range(count)]


def _lh_gain(player: dict[str, Any], minute: int) -> int:
    lh_t = player.get("lh_t")
    if not isinstance(lh_t, list) or len(lh_t) < 2:
        return 0
    current = _timeline_value(lh_t, minute, 0)
    previous = _timeline_value(lh_t, max(0, minute - 1), 0)
    return max(0, current - previous)


def _carry_item_count(player: dict[str, Any]) -> int:
    purchase_log = player.get("purchase_log")
    if isinstance(purchase_log, list):
        return sum(
            1
            for purchase in purchase_log
            if is_meaningful_item_timing(str(purchase.get("key", "")).strip().lower())
        )
    return sum(1 for item in _final_inventory_items(player) if is_meaningful_item_timing(item))


def _hero_name(hero_id: Any) -> str:
    return HERO_ID_TO_NAME.get(_to_int(hero_id, -1), f"Hero {hero_id}")


def _display_item_id(item_id: int) -> str:
    return normalize_item_name(item_id)


def _timeline_value(values: list[Any], minute: int, default: int) -> int:
    if not values:
        return default
    index = max(0, min(len(values) - 1, minute))
    return _to_int(values[index], default)


def _timeline_value_at(
    values: list[Any],
    timestamp: int,
    default: int,
    *,
    interpolate: bool,
) -> int:
    if not values:
        return default

    lower_minute = max(0, timestamp // 60)
    lower_index = min(len(values) - 1, lower_minute)
    lower_value = _to_int(values[lower_index], default)
    if not interpolate or timestamp % 60 == 0 or lower_index >= len(values) - 1:
        return lower_value

    upper_value = _to_int(values[lower_index + 1], lower_value)
    fraction = (timestamp % 60) / 60
    return round(lower_value + (upper_value - lower_value) * fraction)


def _timeline_inference_context(player: dict[str, Any], interval_seconds: int) -> str:
    if interval_seconds >= 60:
        return ""

    inferred_fields: list[str] = []
    if isinstance(player.get("gold_t"), list) and player.get("gold_t"):
        inferred_fields.append("gold interpolated")
    if isinstance(player.get("xp_t"), list) and player.get("xp_t"):
        inferred_fields.append("XP carried forward")
    if isinstance(player.get("lh_t"), list) and player.get("lh_t"):
        inferred_fields.append("last hits carried forward")
    if not inferred_fields:
        return "high-frequency replay uses match totals where per-second OpenDota data is unavailable"
    return "high-frequency replay uses per-minute OpenDota data: " + ", ".join(inferred_fields)


def _last_t_value(values: Any, default: int) -> int:
    if isinstance(values, list) and values:
        return _to_int(values[-1], default)
    return default


def _near_any(timestamp: int, times: list[int], window_seconds: int) -> bool:
    return any(abs(timestamp - time) <= window_seconds for time in times)


def _to_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _optional_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


if __name__ == "__main__":
    raise SystemExit(main())
