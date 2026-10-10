"""
«Перевірити виправлення на записі»: replay fixed role matches through the whole
live path and compare the advice with the accepted results.

Each case is a sanitized synthetic match (tests/match_fixtures.py: no names,
ids or chat) for one hero and position, replayed by simulate_live_gsi.simulate
with the scheduler clock on the game clock, so the run is reproducible. The
compact result is one line per advice card or map hint:
"MM:SS DECISION_POINT mode" — what was shown and when, not its wording, so a
copy edit does not count as a change in behavior. Accepted results live in
tests/replay_golden/<case>.json; tests/test_replay_golden.py runs every case.

Run from backend/:
    python scripts/replay_check.py                    # every case, diff vs accepted
    python scripts/replay_check.py --case support_cm  # one case
    python scripts/replay_check.py --text             # with the advice text
    python scripts/replay_check.py --update           # accept the current results
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))
sys.path.insert(0, str(BACKEND_DIR / "scripts"))

GOLDEN_DIR = BACKEND_DIR / "tests" / "replay_golden"


@dataclass(frozen=True)
class Case:
    hero: str
    role: str
    minutes: int
    deaths: tuple[int, ...]
    lh_per_minute: float
    note: str


CASES: dict[str, Case] = {
    "carry_juggernaut": Case(
        "npc_dota_hero_juggernaut",
        "carry",
        20,
        (7, 14, 15),
        6.0,
        "a carry who dies twice in a row after laning",
    ),
    "mid_shadow_fiend": Case(
        "npc_dota_hero_nevermore",
        "mid",
        20,
        (9,),
        7.0,
        "a mid with one death",
    ),
    "offlane_axe": Case(
        "npc_dota_hero_axe",
        "offlane",
        20,
        (6, 16),
        4.0,
        "an offlaner on a slow farm",
    ),
    "support_crystal_maiden": Case(
        "npc_dota_hero_crystal_maiden",
        "support",
        20,
        (5, 12, 13),
        1.0,
        "a support with little farm and repeated deaths",
    ),
}


def _clock(seconds: Any) -> str:
    if not isinstance(seconds, int):
        return "  ?  "
    sign = "-" if seconds < 0 else ""
    seconds = abs(seconds)
    return f"{sign}{seconds // 60:02d}:{seconds % 60:02d}"


def reset_live_state() -> None:
    """Every case starts from a fresh app: the synthetic matches share a match id,
    so match memory, the scheduler and the GSI state would otherwise carry over
    (the same reset as tests/conftest.py)."""
    from app import gsi_state
    from app.advice_scheduler import ADVICE_SCHEDULER
    from app.coach_summary import COACH_SESSION_HISTORY
    from app.gsi_census import GSI_CENSUS
    from app.main import _clear_demo_overlay_response, _map_hints
    from app.match_memory import MATCH_MEMORY
    from app.match_records import MATCH_RECORDS

    MATCH_MEMORY.reset()
    ADVICE_SCHEDULER.reset()
    ADVICE_SCHEDULER.set_frequency("normal")
    _map_hints["enabled"] = True
    COACH_SESSION_HISTORY.reset()
    GSI_CENSUS.reset()
    MATCH_RECORDS.set_enabled(False)
    _clear_demo_overlay_response()
    gsi_state.reset_latest_gsi()


def run(name: str, *, text: bool = False) -> list[str]:
    """The compact result of one case (one line per card / hint)."""
    from simulate_live_gsi import simulate, synthetic_stream

    reset_live_state()
    case = CASES[name]
    payloads = synthetic_stream(case.minutes, case.deaths, case.lh_per_minute)
    for payload in payloads:
        payload["hero"]["name"] = case.hero
    cards = simulate(payloads, "en", hints=True, role=case.role)
    lines = []
    for card in cards:
        mode = card["mode"] if card["decision_point"] != "MAP_HINT" else "hint"
        line = f"{_clock(card['clock'])} {card['decision_point']} {mode}"
        lines.append(f"{line} | {card['action']}" if text else line)
    return lines


def golden_path(name: str) -> Path:
    return GOLDEN_DIR / f"{name}.json"


def load_golden(name: str) -> list[str] | None:
    path = golden_path(name)
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return list(data["cards"])


def save_golden(name: str, lines: list[str]) -> None:
    GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
    case = CASES[name]
    payload = {
        "case": name,
        "note": case.note,
        "role": case.role,
        "hero": case.hero,
        "cards": lines,
    }
    golden_path(name).write_text(
        json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )


def diff(expected: list[str], actual: list[str]) -> list[str]:
    """Lines only in the accepted result (-) and only in this run (+), in order."""
    import difflib

    return [
        line
        for line in difflib.unified_diff(expected, actual, "accepted", "this run", n=0, lineterm="")
        if line[:1] in "+-" and not line.startswith(("+++", "---"))
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--case", choices=sorted(CASES), action="append")
    parser.add_argument("--update", action="store_true", help="accept the current results")
    parser.add_argument("--text", action="store_true", help="print each card's text")
    args = parser.parse_args()
    failed = 0
    for name in args.case or sorted(CASES):
        lines = run(name)
        if args.text:
            print(f"== {name}")
            print("\n".join(run(name, text=True)))
        if args.update:
            save_golden(name, lines)
            print(f"{name}: accepted {len(lines)} cards")
            continue
        expected = load_golden(name)
        if expected is None:
            print(f"{name}: no accepted result (run with --update)")
            failed += 1
            continue
        changes = diff(expected, lines)
        if changes:
            failed += 1
            print(f"{name}: {len(changes)} changed lines")
            print("\n".join(f"  {line}" for line in changes))
            print(f"  reproduce: python scripts/replay_check.py --case {name} --text")
        else:
            print(f"{name}: same {len(lines)} cards")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
