"""The offline .dem wrapper contract, with a fake parser instead of Java/Clarity."""

from __future__ import annotations

import bz2
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

WRAPPER = Path(__file__).resolve().parents[1] / "scripts" / "parse_dota_demo_to_replay_events.py"

FAKE_PARSER = """
import json, sys
events = [
    {"timestamp_seconds": 30, "event_type": "damage", "player_slot": 1, "hero": "Juggernaut",
     "damage_percent": 25, "hp_percent": 55},
    {"timestamp_seconds": 45, "type": "purchase", "player_slot": 1, "hero": "Juggernaut",
     "data": {"item": "quelling_blade"}},
    {"timestamp_seconds": 50, "event_type": "damage", "player_slot": 2, "hero": "Luna",
     "damage_percent": 10},
    {"timestamp_seconds": 900, "event_type": "death", "player_slot": 1, "hero": "Juggernaut"},
    {"timestamp_seconds": 60, "event_type": "objective", "player_slot": 0, "hero": "",
     "objective": "tower"},
]
with open(sys.argv[1], "w", encoding="utf-8") as out:
    out.write("\\n".join(json.dumps(event) for event in events))
"""


def _run(tmp_path: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    demo = tmp_path / "match.dem.bz2"
    demo.write_bytes(bz2.compress(b"PBDEMS2 fake replay"))
    return subprocess.run(
        [sys.executable, str(WRAPPER), "--demo", str(demo), "--hero", "Juggernaut"]
        + ["--player-slot", "1", "--start-minute", "0", "--end-minute", "10"]
        + ["--output", str(tmp_path / "events.jsonl"), *extra],
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "DOTA_DEMO_PARSER_COMMAND": ""},
    )


def test_wrapper_normalizes_and_filters_parser_events(tmp_path: Path) -> None:
    parser = tmp_path / "fake_parser.py"
    parser.write_text(FAKE_PARSER, encoding="utf-8")
    command = f"{shlex.quote(sys.executable)} {shlex.quote(str(parser))} {{output}}"

    result = _run(tmp_path, "--parser-command", command)

    assert result.returncode == 0, result.stderr
    lines = (tmp_path / "events.jsonl").read_text(encoding="utf-8").splitlines()
    events = [json.loads(line) for line in lines]
    assert [(event["timestamp_seconds"], event["type"]) for event in events] == [
        (30, "damage"),
        (45, "purchase"),
        (60, "objective"),
    ]
    damage = events[0]["data"]
    assert damage["damage_percent"] == 25 and damage["context_confidence"]
    assert events[1]["data"]["item"] == "quelling_blade"


def test_wrapper_refuses_without_a_parser_instead_of_faking_data(tmp_path: Path) -> None:
    result = _run(tmp_path)

    assert result.returncode == 1
    assert "No usable .dem parser command" in result.stderr
    assert not (tmp_path / "events.jsonl").exists()


def test_wrapper_reports_a_failing_parser(tmp_path: Path) -> None:
    command = f"{shlex.quote(sys.executable)} -c 'import sys; sys.exit(\"no hero entity\")'"

    result = _run(tmp_path, "--parser-command", command)

    assert result.returncode == 1 and "no hero entity" in result.stderr
    assert not (tmp_path / "events.jsonl").exists()
