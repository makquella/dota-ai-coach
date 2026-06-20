"""
Generate a dense synthetic replay event JSONL for offline adapter testing.

This does not use Dota 2 files. It only creates combat-log-style events that
exercise the replay-to-GSI-like converter and live advice state machine.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parent
DEFAULT_OUTPUT = REPO_ROOT / "data" / "replay_events" / "synthetic_juggernaut_lane_events.jsonl"


def main() -> int:
    args = _parse_args()
    output_path = Path(args.output)
    events = _sample_events(hero=args.hero, player_slot=args.player_slot)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        "\n".join(json.dumps(event, ensure_ascii=False) for event in events) + "\n",
        encoding="utf-8",
    )
    print(f"Synthetic replay event sample saved: {output_path}")
    print(f"events: {len(events)}")
    return 0


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a synthetic replay event JSONL sample.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Output events JSONL path.")
    parser.add_argument("--hero", default="Juggernaut", help="Hero name to write into events.")
    parser.add_argument("--player-slot", type=int, default=1, help="Selected player_slot.")
    return parser.parse_args()


def _sample_events(*, hero: str, player_slot: int) -> list[dict[str, Any]]:
    base = {"player_slot": player_slot, "hero": hero}
    events: list[dict[str, Any]] = []

    for timestamp in range(0, 601, 20):
        events.append(_event(timestamp, "snapshot", base, _lane_snapshot(timestamp)))

    for timestamp in range(0, 601, 15):
        events.append(_event(timestamp, "ability", base, _blade_fury_snapshot(timestamp)))

    events.extend(
        [
            _event(90, "level", base, {"level": 2, "xp": 310, "context_confidence": "high"}),
            _event(205, "level", base, {"level": 3, "xp": 720, "context_confidence": "high"}),
            _event(360, "level", base, {"level": 4, "xp": 1280, "context_confidence": "high"}),
            _event(520, "level", base, {"level": 5, "xp": 1980, "context_confidence": "high"}),
            _event(75, "purchase", base, {"item": "quelling_blade", "context_confidence": "high"}),
            _event(215, "purchase", base, {"item": "boots", "context_confidence": "high"}),
            _event(110, "damage", base, {"damage_percent": 12, "hp_after_percent": 88, "context_confidence": "high"}),
            _event(125, "damage", base, {"damage_percent": 25, "hp_after_percent": 63, "context_confidence": "high"}),
            _event(132, "damage", base, {"damage_percent": 16, "hp_after_percent": 47, "context_confidence": "high"}),
            _event(148, "snapshot", base, _manual_snapshot(148, hp=47, mana=69, lh=5, gold=980)),
            _event(160, "snapshot", base, _manual_snapshot(160, hp=34, mana=67, lh=6, gold=1030)),
            _event(170, "death", base, {"deaths": 1, "respawn_seconds": 22, "context_confidence": "high"}),
            _event(195, "snapshot", base, _manual_snapshot(195, hp=100, mana=92, lh=6, gold=1040)),
            _event(260, "snapshot", base, _manual_snapshot(260, hp=92, mana=84, lh=10, gold=1290)),
            _event(300, "snapshot", base, _manual_snapshot(300, hp=90, mana=82, lh=13, gold=1450)),
            _event(330, "ability", base, _blade_fury_snapshot(330, cooldown=14)),
            _event(340, "snapshot", base, _manual_snapshot(340, hp=68, mana=78, lh=15, gold=1560)),
            _event(345, "ability", base, _blade_fury_snapshot(345, cooldown=7)),
            _event(360, "ability", base, _blade_fury_snapshot(360, cooldown=0)),
            _event(405, "damage", base, {"damage_percent": 18, "hp_after_percent": 76, "context_confidence": "high"}),
            _event(422, "damage", base, {"damage_percent": 24, "hp_after_percent": 52, "context_confidence": "high"}),
            _event(438, "snapshot", base, _manual_snapshot(438, hp=45, mana=55, lh=21, gold=1810)),
            _event(448, "damage", base, {"damage_percent": 18, "hp_after_percent": 27, "context_confidence": "high"}),
            _event(462, "death", base, {"deaths": 2, "respawn_seconds": 25, "context_confidence": "high"}),
            _event(492, "snapshot", base, _manual_snapshot(492, hp=100, mana=88, lh=22, gold=1840)),
            _event(540, "snapshot", base, _manual_snapshot(540, hp=96, mana=84, lh=28, gold=2120)),
            _event(580, "snapshot", base, _manual_snapshot(580, hp=98, mana=82, lh=34, gold=2400)),
        ]
    )

    return sorted(events, key=lambda event: (event["timestamp_seconds"], _event_order(event["type"])))


def _lane_snapshot(timestamp: int) -> dict[str, Any]:
    minute = timestamp / 60
    hp = 100
    mana = max(62, 100 - int(minute * 4))
    if 120 <= timestamp < 170:
        hp = 47 if timestamp < 160 else 34
        mana = 68
    elif 170 <= timestamp < 195:
        hp = 0
    elif 320 <= timestamp < 365:
        hp = 68
        mana = 78
    elif 405 <= timestamp < 462:
        hp = 52 if timestamp < 440 else 27
        mana = 55
    elif 462 <= timestamp < 492:
        hp = 0
    elif timestamp >= 492:
        hp = 96
        mana = 84

    last_hits = _last_hits_at(timestamp)
    return {
        "hp_percent": hp,
        "mana_percent": mana,
        "level": _level_at(timestamp),
        "xp": _xp_at(timestamp),
        "gold": _gold_at(timestamp, last_hits),
        "last_hits": last_hits,
        "gpm": _gpm_at(timestamp),
        "xpm": _xpm_at(timestamp),
        "xpos": -4800 + int(timestamp * 3.6),
        "ypos": 900 - int(timestamp * 0.8),
        "context_confidence": "high",
    }


def _manual_snapshot(timestamp: int, *, hp: int, mana: int, lh: int, gold: int) -> dict[str, Any]:
    return {
        "hp_percent": hp,
        "mana_percent": mana,
        "level": _level_at(timestamp),
        "xp": _xp_at(timestamp),
        "gold": gold,
        "last_hits": lh,
        "gpm": _gpm_at(timestamp),
        "xpm": _xpm_at(timestamp),
        "xpos": -4800 + int(timestamp * 3.6),
        "ypos": 900 - int(timestamp * 0.8),
        "context_confidence": "high",
    }


def _blade_fury_snapshot(timestamp: int, cooldown: int | None = None) -> dict[str, Any]:
    if cooldown is None:
        cooldown = 0
        if 330 <= timestamp < 360:
            cooldown = max(0, 14 - ((timestamp - 330) // 15) * 7)
    return {
        "ability": "Blade Fury",
        "ability_level": 1 if timestamp < 260 else 2,
        "cooldown": cooldown,
        "can_cast": cooldown <= 0,
        "mana_percent": _lane_snapshot(timestamp)["mana_percent"],
        "context_confidence": "high",
    }


def _last_hits_at(timestamp: int) -> int:
    points = [
        (0, 0),
        (60, 2),
        (120, 5),
        (180, 6),
        (240, 9),
        (300, 13),
        (360, 18),
        (420, 21),
        (480, 22),
        (540, 28),
        (600, 38),
    ]
    return _interpolate_points(points, timestamp)


def _level_at(timestamp: int) -> int:
    if timestamp >= 520:
        return 5
    if timestamp >= 360:
        return 4
    if timestamp >= 205:
        return 3
    if timestamp >= 90:
        return 2
    return 1


def _xp_at(timestamp: int) -> int:
    return min(2300, int(timestamp * 3.8))


def _gold_at(timestamp: int, last_hits: int) -> int:
    return max(600, 600 + last_hits * 42 + int(timestamp * 2.0))


def _gpm_at(timestamp: int) -> int:
    if timestamp < 300:
        return 275
    if timestamp < 480:
        return 245
    return 310


def _xpm_at(timestamp: int) -> int:
    return 260 if timestamp < 480 else 310


def _interpolate_points(points: list[tuple[int, int]], timestamp: int) -> int:
    previous_time, previous_value = points[0]
    for next_time, next_value in points[1:]:
        if timestamp <= next_time:
            span = max(1, next_time - previous_time)
            progress = (timestamp - previous_time) / span
            return round(previous_value + (next_value - previous_value) * progress)
        previous_time, previous_value = next_time, next_value
    return points[-1][1]


def _event_order(event_type: str) -> int:
    return {
        "snapshot": 0,
        "level": 1,
        "purchase": 2,
        "ability": 3,
        "damage": 4,
        "death": 5,
    }.get(event_type, 9)


def _event(timestamp: int, event_type: str, base: dict[str, Any], data: dict[str, Any]) -> dict[str, Any]:
    return {
        "timestamp_seconds": timestamp,
        "type": event_type,
        **base,
        "data": data,
    }


if __name__ == "__main__":
    raise SystemExit(main())
