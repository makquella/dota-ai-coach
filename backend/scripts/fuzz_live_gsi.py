"""
Fuzz the live path: mutated GSI through POST /gsi -> /overlay/recommendation.

Starts from a realistic whole-match GSI stream (tests/match_fixtures.py) and
the recorded samples in data/gsi_samples/, then breaks them at random: drops
fields and whole blocks, swaps types (strings, lists, None, booleans), puts in
huge, negative and fractional numbers, jumps the clock back and forth, switches
heroes, teams and matches mid-stream, adds spectator blocks. Every payload is
followed by the requests the launcher makes (overlay in ru and en, /gsi/status,
/player). Any 5xx answer fails the run and prints the payload that caused it.

    python scripts/fuzz_live_gsi.py --payloads 10000 --seed 1
    python scripts/fuzz_live_gsi.py --payloads 300            # quick (tests use this)

Exit code 0 when every answer was below 500.
"""

from __future__ import annotations

import argparse
import copy
import json
import random
import sys
import tempfile
from pathlib import Path
from typing import Any

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))
sys.path.insert(0, str(BACKEND_DIR / "tests"))

WEIRD_VALUES: list[Any] = [
    None,
    "",
    "abc",
    "123",
    -1,
    0,
    2**31,
    -(2**40),
    1e308,
    -0.5,
    3.7,
    True,
    False,
    [],
    [1, 2],
    {},
    {"nested": {"x": 1}},
    "npc_dota_hero_" + "x" * 300,
    "ñ😀",
]
HEROES = [
    "npc_dota_hero_juggernaut",
    "npc_dota_hero_lion",
    "npc_dota_hero_pudge",
    "npc_dota_hero_antimage",
    "npc_dota_hero_crystal_maiden",
    "npc_dota_hero_unknown_thing",
    "",
]
GAME_STATES = [
    "DOTA_GAMERULES_STATE_GAME_IN_PROGRESS",
    "DOTA_GAMERULES_STATE_PRE_GAME",
    "DOTA_GAMERULES_STATE_POST_GAME",
    "DOTA_GAMERULES_STATE_HERO_SELECTION",
    "DOTA_GAMERULES_STATE_STRATEGY_TIME",
    "SOMETHING_NEW",
]


def base_streams() -> list[list[dict[str, Any]]]:
    from match_fixtures import gsi_match_stream

    streams = [
        gsi_match_stream(minutes=12, positions=True, step_seconds=15),
        gsi_match_stream(minutes=8, lh_per_minute=1.0, death_minutes=(3, 4), positions=True),
    ]
    samples_dir = BACKEND_DIR.parent / "data" / "gsi_samples"
    samples = []
    for path in sorted(samples_dir.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(data, dict):
            samples.append(data)
    if samples:
        streams.append(samples)
    return streams


def _paths(node: Any, prefix: tuple = ()) -> list[tuple]:
    found = []
    if isinstance(node, dict):
        for key, value in node.items():
            found.append((*prefix, key))
            found.extend(_paths(value, (*prefix, key)))
    return found


def _set(node: dict, path: tuple, value: Any) -> None:
    for key in path[:-1]:
        node = node.get(key) if isinstance(node.get(key), dict) else {}
    if isinstance(node, dict):
        node[path[-1]] = value


def _drop(node: dict, path: tuple) -> None:
    for key in path[:-1]:
        node = node.get(key) if isinstance(node.get(key), dict) else {}
    if isinstance(node, dict):
        node.pop(path[-1], None)


def mutate(payload: dict[str, Any], rng: random.Random) -> dict[str, Any]:
    result = copy.deepcopy(payload)
    for _ in range(rng.randint(1, 6)):
        paths = _paths(result)
        kind = rng.random()
        if not paths or kind < 0.1:
            result[rng.choice(["hero", "map", "player", "items", "abilities", "buildings"])] = (
                copy.deepcopy(rng.choice(WEIRD_VALUES))
            )
        elif kind < 0.35:
            _drop(result, rng.choice(paths))
        elif kind < 0.7:
            _set(result, rng.choice(paths), copy.deepcopy(rng.choice(WEIRD_VALUES)))
        elif kind < 0.8:
            clock = rng.choice([-120, -1, 0, 1, 59, 600, 1199, 3600, 10**6, -(10**6)])
            _set(result, ("map", "clock_time"), clock)
            _set(result, ("map", "game_time"), clock + rng.choice([0, 90, -500]))
        elif kind < 0.87:
            _set(result, ("hero", "name"), rng.choice(HEROES))
        elif kind < 0.92:
            _set(result, ("map", "game_state"), rng.choice(GAME_STATES))
        elif kind < 0.96:
            _set(result, ("map", "matchid"), str(rng.randint(1, 10**10)))
        else:
            # A spectator's payload: per-team player blocks.
            result["player"] = {"team2": {"player0": {"name": "x"}}, "team3": {}}
    return result


def run(payloads: int, seed: int, data_dir: Path | None = None) -> list[dict[str, Any]]:
    """Returns the failures (empty when every answer was below 500)."""
    from fastapi.testclient import TestClient

    from app.main import app
    from app.player_api import PLAYER_SERVICE

    PLAYER_SERVICE.configure(data_dir or Path(tempfile.mkdtemp()), client=None, auto_start=False)
    rng = random.Random(seed)
    streams = base_streams()
    failures: list[dict[str, Any]] = []
    with TestClient(app, raise_server_exceptions=False) as client:
        sent = 0
        while sent < payloads:
            stream = rng.choice(streams)
            start = rng.randrange(len(stream))
            for payload in stream[start : start + rng.randint(5, 60)]:
                if sent >= payloads:
                    break
                body = mutate(payload, rng) if rng.random() < 0.7 else payload
                sent += 1
                answers = [("POST /gsi", client.post("/gsi", json=body))]
                for path in (
                    "/overlay/recommendation?lang=ru",
                    "/overlay/recommendation?lang=en",
                    "/gsi/status",
                    "/player",
                ):
                    answers.append((path, client.get(path)))
                for name, answer in answers:
                    if answer.status_code >= 500:
                        failures.append(
                            {"request": name, "status": answer.status_code, "payload": body}
                        )
                if len(failures) >= 5:
                    return failures
    return failures


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--payloads", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=1)
    args = parser.parse_args()
    failures = run(args.payloads, args.seed)
    for failure in failures:
        print(json.dumps(failure, ensure_ascii=False, default=str)[:4000])
    print(f"{args.payloads} payloads, seed {args.seed}: {len(failures)} failures")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
