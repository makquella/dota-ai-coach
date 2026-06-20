#!/usr/bin/env python3
"""
Offline Dota replay parser adapter.

This script does not parse live game memory, screen pixels, or input. It wraps a
local offline parser command and normalizes its output into the replay_events
JSONL format consumed by convert_replay_events_to_gsi_like.py.

Without a configured external parser command, it exits with a clear error
instead of generating fake data.
"""

from __future__ import annotations

import argparse
import bz2
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests


BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parent
DEFAULT_REPLAY_DIR = REPO_ROOT / "data" / "replays"
DEFAULT_OPENDOTA_DIR = REPO_ROOT / "data" / "opendota"
DOWNLOAD_TIMEOUT_SECONDS = 30
SUPPORTED_TYPES = {
    "snapshot",
    "damage",
    "death",
    "heal",
    "farm",
    "purchase",
    "level",
    "position",
    "ability",
    "objective",
}


def main() -> int:
    args = _parse_args()
    try:
        demo_path = _resolve_demo_path(args)
        parser_command = _parser_command(args)
        if not parser_command:
            raise ValueError(
                "No usable .dem parser command is configured. "
                "Set DOTA_DEMO_PARSER_COMMAND or pass --parser-command. "
                "Current project can convert replay_events.jsonl to GSI-like states, "
                "but it cannot decode Dota .dem files without an external offline parser."
            )

        with tempfile.TemporaryDirectory(prefix="dota_demo_parse_") as temp_dir:
            temp_path = Path(temp_dir)
            parser_demo_path = _prepare_demo_for_parser(demo_path, temp_path)
            raw_events_path = temp_path / "parser_events.jsonl"
            _run_parser_command(
                parser_command=parser_command,
                demo_path=parser_demo_path,
                raw_events_path=raw_events_path,
                args=args,
            )
            events = _load_and_normalize_events(
                raw_events_path,
                hero=args.hero,
                player_slot=args.player_slot,
                start_minute=args.start_minute,
                end_minute=args.end_minute,
            )

        if not events:
            raise ValueError(
                "Parser produced no usable events for the selected player/time window. "
                "No fake replay data was generated."
            )

        output_path = Path(args.output)
        _write_jsonl(output_path, events)
        print(f"Replay events saved: {output_path}")
        print(f"events: {len(events)}")
        print(f"demo: {demo_path}")
        return 0
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Parse a Dota 2 .dem/.dem.bz2 replay into replay_events JSONL via an external offline parser.",
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--demo", help="Path to a local .dem or .dem.bz2 replay file.")
    source.add_argument("--match-id", help="Match id. Uses local/OpenDota match JSON replay_url when available.")
    parser.add_argument("--hero", required=True, help='Selected hero name, for example "Juggernaut".')
    parser.add_argument("--player-slot", type=int, required=True, help="Selected Dota player_slot.")
    parser.add_argument("--start-minute", type=int, default=0, help="First minute to keep.")
    parser.add_argument("--end-minute", type=int, default=10, help="Last minute to keep.")
    parser.add_argument("--output", required=True, help="Output replay_events JSONL path.")
    parser.add_argument(
        "--parser-command",
        default=os.getenv("DOTA_DEMO_PARSER_COMMAND", ""),
        help=(
            "External parser command template. Placeholders: {demo}, {output}, {hero}, "
            "{player_slot}, {start_minute}, {end_minute}, {start_seconds}, {end_seconds}."
        ),
    )
    parser.add_argument(
        "--replay-dir",
        default=str(DEFAULT_REPLAY_DIR),
        help="Directory for downloaded match_id replays.",
    )
    parser.add_argument(
        "--match-json",
        help="Optional local OpenDota match JSON path to use with --match-id.",
    )
    args = parser.parse_args()
    if args.start_minute < 0:
        parser.error("--start-minute must be >= 0")
    if args.end_minute <= args.start_minute:
        parser.error("--end-minute must be greater than --start-minute")
    return args


def _resolve_demo_path(args: argparse.Namespace) -> Path:
    if args.demo:
        demo_path = Path(args.demo).expanduser()
        if not demo_path.exists():
            raise ValueError(f"Demo file not found: {demo_path}")
        if not _is_demo_file(demo_path):
            raise ValueError(f"Demo file must end with .dem or .dem.bz2: {demo_path}")
        return demo_path.resolve()

    match_id = str(args.match_id).strip()
    match_json = _load_match_json(match_id, explicit_path=args.match_json)
    replay_url = str(match_json.get("replay_url") or "").strip()
    if not replay_url:
        raise ValueError("Replay URL is not available from local/OpenDota match data. Provide --demo path.")
    return _download_replay(replay_url, Path(args.replay_dir).expanduser())


def _load_match_json(match_id: str, *, explicit_path: str | None) -> dict[str, Any]:
    if explicit_path:
        path = Path(explicit_path).expanduser()
        if not path.exists():
            raise ValueError(f"Match JSON not found: {path}")
        return _read_json(path)

    first_local_match: dict[str, Any] | None = None
    for path in _match_json_candidates(match_id):
        if path.exists():
            data = _read_json(path)
            if first_local_match is None:
                first_local_match = data
            if str(data.get("replay_url") or "").strip():
                return data

    if first_local_match is not None:
        return first_local_match

    fetched = _fetch_opendota_match_json(match_id)
    if fetched is not None:
        DEFAULT_OPENDOTA_DIR.mkdir(parents=True, exist_ok=True)
        path = DEFAULT_OPENDOTA_DIR / f"match_{match_id}.json"
        path.write_text(json.dumps(fetched, indent=2, ensure_ascii=False), encoding="utf-8")
        return fetched

    raise ValueError(
        f"OpenDota match JSON not found locally for match_id {match_id}, "
        "and fetching it from OpenDota failed. Provide --demo path."
    )


def _match_json_candidates(match_id: str) -> list[Path]:
    cwd = Path.cwd()
    return [
        REPO_ROOT / f"match_{match_id}.json",
        REPO_ROOT / "data" / "opendota" / f"match_{match_id}.json",
        BACKEND_DIR / "data" / "opendota" / f"match_{match_id}.json",
        BACKEND_DIR / "imported_matches" / f"opendota_match_{match_id}_raw.json",
        cwd / f"match_{match_id}.json",
        cwd / ".." / f"match_{match_id}.json",
        cwd / "data" / "opendota" / f"match_{match_id}.json",
        cwd / ".." / "data" / "opendota" / f"match_{match_id}.json",
    ]


def _fetch_opendota_match_json(match_id: str) -> dict[str, Any] | None:
    url = f"https://api.opendota.com/api/matches/{match_id}"
    try:
        response = requests.get(url, timeout=DOWNLOAD_TIMEOUT_SECONDS)
        response.raise_for_status()
        data = response.json()
    except (requests.RequestException, ValueError):
        return None
    return data if isinstance(data, dict) else None


def _download_replay(replay_url: str, replay_dir: Path) -> Path:
    replay_dir.mkdir(parents=True, exist_ok=True)
    filename = Path(urlparse(replay_url).path).name or "dota_replay.dem.bz2"
    output_path = replay_dir / filename
    if output_path.exists() and output_path.stat().st_size > 0:
        return output_path

    try:
        with requests.get(replay_url, timeout=DOWNLOAD_TIMEOUT_SECONDS, stream=True) as response:
            response.raise_for_status()
            with output_path.open("wb") as file:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        file.write(chunk)
    except requests.RequestException as exc:
        raise ValueError(f"Failed to download replay from replay_url: {exc}") from exc

    if output_path.stat().st_size <= 0:
        raise ValueError(f"Downloaded replay is empty: {output_path}")
    return output_path


def _parser_command(args: argparse.Namespace) -> str:
    command = str(args.parser_command or "").strip()
    if command:
        return command
    return ""


def _prepare_demo_for_parser(demo_path: Path, temp_path: Path) -> Path:
    if demo_path.name.lower().endswith(".dem"):
        return demo_path
    if not demo_path.name.lower().endswith(".dem.bz2"):
        raise ValueError(f"Unsupported replay extension: {demo_path}")

    output_path = temp_path / demo_path.name.removesuffix(".bz2")
    try:
        with bz2.open(demo_path, "rb") as source, output_path.open("wb") as target:
            shutil.copyfileobj(source, target)
    except OSError as exc:
        raise ValueError(f"Failed to decompress .dem.bz2 replay: {exc}") from exc
    if output_path.stat().st_size <= 0:
        raise ValueError(f"Decompressed .dem is empty: {output_path}")
    return output_path


def _run_parser_command(
    *,
    parser_command: str,
    demo_path: Path,
    raw_events_path: Path,
    args: argparse.Namespace,
) -> None:
    start_seconds = args.start_minute * 60
    end_seconds = args.end_minute * 60
    values = {
        "demo": shlex.quote(str(demo_path)),
        "output": shlex.quote(str(raw_events_path)),
        "hero": shlex.quote(args.hero),
        "player_slot": shlex.quote(str(args.player_slot)),
        "start_minute": shlex.quote(str(args.start_minute)),
        "end_minute": shlex.quote(str(args.end_minute)),
        "start_seconds": shlex.quote(str(start_seconds)),
        "end_seconds": shlex.quote(str(end_seconds)),
    }
    try:
        command = parser_command.format(**values)
    except KeyError as exc:
        raise ValueError(f"Unknown placeholder in --parser-command: {exc}") from exc

    argv = shlex.split(command)
    if not argv:
        raise ValueError("--parser-command resolved to an empty command")

    try:
        completed = subprocess.run(
            argv,
            cwd=str(REPO_ROOT),
            text=True,
            capture_output=True,
            check=False,
        )
    except OSError as exc:
        raise ValueError(f"External replay parser could not be started: {exc}") from exc
    if completed.returncode != 0:
        stderr = completed.stderr.strip()[:1000]
        stdout = completed.stdout.strip()[:1000]
        details = stderr or stdout or f"exit code {completed.returncode}"
        raise ValueError(f"External replay parser failed: {details}")

    if not raw_events_path.exists() and completed.stdout.strip():
        raw_events_path.write_text(completed.stdout, encoding="utf-8")

    if not raw_events_path.exists() or raw_events_path.stat().st_size <= 0:
        raise ValueError(
            "External replay parser did not create events output. "
            "It must write JSONL/JSON to {output} or stdout."
        )


def _load_and_normalize_events(
    path: Path,
    *,
    hero: str,
    player_slot: int,
    start_minute: int,
    end_minute: int,
) -> list[dict[str, Any]]:
    raw_events = _load_raw_events(path)
    start_seconds = start_minute * 60
    end_seconds = end_minute * 60
    events: list[dict[str, Any]] = []
    for raw_event in raw_events:
        event = _normalize_event(raw_event, default_hero=hero, default_player_slot=player_slot)
        if event is None:
            continue
        timestamp = int(event["timestamp_seconds"])
        if not (start_seconds <= timestamp <= end_seconds):
            continue
        if int(event["player_slot"]) != player_slot and event["type"] != "objective":
            continue
        if str(event["hero"]).lower() != hero.lower() and event["type"] != "objective":
            continue
        events.append(event)
    return sorted(events, key=lambda event: (event["timestamp_seconds"], event["type"]))


def _load_raw_events(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return []
    if text[0] in "[{":
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            data = None
        if isinstance(data, list):
            return [item for item in data if isinstance(item, dict)]
        if isinstance(data, dict) and isinstance(data.get("events"), list):
            return [item for item in data["events"] if isinstance(item, dict)]
        if isinstance(data, dict):
            return [data]

    events: list[dict[str, Any]] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid parser JSONL at {path}:{line_number}: {exc}") from exc
        if isinstance(item, dict):
            events.append(item)
    return events


def _normalize_event(
    raw_event: dict[str, Any],
    *,
    default_hero: str,
    default_player_slot: int,
) -> dict[str, Any] | None:
    timestamp = _timestamp_seconds(raw_event)
    if timestamp is None:
        return None

    event_type = _normalize_event_type(raw_event)
    if event_type not in SUPPORTED_TYPES:
        return None

    data = raw_event.get("data") if isinstance(raw_event.get("data"), dict) else {}
    flat_data = _flat_event_data(raw_event)
    merged_data = {**flat_data, **data}
    if "context_confidence" not in merged_data:
        merged_data["context_confidence"] = _default_confidence(event_type)
    if "event_context" not in merged_data:
        merged_data["event_context"] = _default_context(event_type)

    hero = str(raw_event.get("hero") or merged_data.get("hero") or default_hero).strip() or default_hero
    player_slot = _optional_int(raw_event.get("player_slot"))
    if player_slot is None:
        player_slot = _optional_int(merged_data.get("player_slot"))
    if player_slot is None:
        player_slot = default_player_slot

    canonical = {
        "timestamp_seconds": timestamp,
        "minute": timestamp // 60,
        "type": event_type,
        "event_type": event_type,
        "hero": hero,
        "player_slot": player_slot,
        "data": _drop_none(merged_data),
    }
    canonical.update(_top_level_mirrors(canonical["data"]))
    return canonical


def _timestamp_seconds(event: dict[str, Any]) -> int | None:
    for key in ("timestamp_seconds", "game_time", "time_seconds", "time"):
        value = _optional_int(event.get(key))
        if value is not None:
            return max(0, value)
    minute = _optional_int(event.get("minute"))
    if minute is not None:
        return max(0, minute * 60)
    return None


def _normalize_event_type(event: dict[str, Any]) -> str:
    raw_type = str(event.get("type") or event.get("event_type") or "").strip().lower()
    if not raw_type:
        if event.get("death") is True:
            raw_type = "death"
        elif event.get("damage_percent") is not None or event.get("damage") is not None:
            raw_type = "damage"
        elif event.get("item") is not None:
            raw_type = "item"
        elif event.get("ability") is not None:
            raw_type = "ability"
        else:
            raw_type = "snapshot"
    aliases = {
        "item": "purchase",
        "buy": "purchase",
        "purchase_log": "purchase",
        "last_hit": "farm",
        "lh": "farm",
        "combat_damage": "damage",
        "player_death": "death",
        "teamfight": "objective",
        "building": "objective",
    }
    return aliases.get(raw_type, raw_type)


def _flat_event_data(event: dict[str, Any]) -> dict[str, Any]:
    keys = [
        "hp_percent",
        "hp_after_percent",
        "hp",
        "health",
        "max_hp",
        "max_health",
        "mana_percent",
        "mana_after_percent",
        "mana",
        "max_mana",
        "level",
        "gold",
        "total_earned_gold",
        "networth",
        "last_hits",
        "lh",
        "denies",
        "gpm",
        "xpm",
        "xp",
        "item",
        "ability",
        "ability_level",
        "ability_cooldown",
        "cooldown",
        "can_cast",
        "damage_percent",
        "damage_taken_percent",
        "hp_delta",
        "death",
        "deaths",
        "alive",
        "respawn_seconds",
        "xpos",
        "ypos",
        "x",
        "y",
        "game_state",
        "team_status",
        "objective_type",
        "objective_team",
        "team",
        "event_context",
        "context_confidence",
        "entity_class",
    ]
    data = {key: event.get(key) for key in keys if key in event}
    if "ability_cooldown" in data and "cooldown" not in data:
        data["cooldown"] = data["ability_cooldown"]
    return data


def _top_level_mirrors(data: dict[str, Any]) -> dict[str, Any]:
    keys = [
        "hp_percent",
        "hp",
        "max_hp",
        "mana_percent",
        "mana",
        "max_mana",
        "level",
        "gold",
        "total_earned_gold",
        "networth",
        "last_hits",
        "denies",
        "item",
        "ability",
        "cooldown",
        "damage_percent",
        "death",
        "alive",
        "game_state",
        "event_context",
        "context_confidence",
        "entity_class",
    ]
    return {key: data[key] for key in keys if key in data}


def _default_confidence(event_type: str) -> str:
    if event_type in {"death", "purchase", "level", "ability", "objective"}:
        return "high"
    if event_type in {"damage", "farm", "position"}:
        return "medium"
    return "low"


def _default_context(event_type: str) -> str:
    if event_type == "death":
        return "parsed from Dota replay death event"
    if event_type == "damage":
        return "parsed from Dota replay combat log damage event"
    return f"parsed from Dota replay {event_type} event"


def _write_jsonl(path: Path, events: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(event, ensure_ascii=False) for event in events) + "\n",
        encoding="utf-8",
    )


def _read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid match JSON {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"Match JSON is not an object: {path}")
    return data


def _drop_none(data: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in data.items() if value is not None}


def _optional_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _is_demo_file(path: Path) -> bool:
    name = path.name.lower()
    return name.endswith(".dem") or name.endswith(".dem.bz2")


if __name__ == "__main__":
    raise SystemExit(main())
