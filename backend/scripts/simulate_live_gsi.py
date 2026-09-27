"""
Replay raw Dota 2 GSI through the live endpoints and print the overlay advice.

Unlike simulate_match_advice.py (prepared replay states straight into the
scheduler), this goes through the whole live path: POST /gsi (normalization,
match memory, trackers) -> GET /overlay/recommendation (decision points,
coaches, scheduler, UX policy, translation). The scheduler clock follows the
game clock, so a 40-minute match runs in seconds with realistic card
lifetimes and spacing.

Run from backend/:
    python scripts/simulate_live_gsi.py                      # synthetic match
    python scripts/simulate_live_gsi.py --deaths 7,18,19,33 --lang ru
    python scripts/simulate_live_gsi.py --session session_records/<id>/raw_gsi_states.jsonl
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from collections import Counter
from collections.abc import Iterable, Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

import app.advice_scheduler as scheduler_module  # noqa: E402

START = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
_clock = [START]
_real_utcnow = scheduler_module._utcnow


def _game_clock_now(value: datetime | None = None) -> datetime:
    return _real_utcnow(value) if value is not None else _clock[0]


def synthetic_stream(minutes: int, deaths: tuple[int, ...]) -> list[dict[str, Any]]:
    sys.path.insert(0, str(BACKEND_DIR / "tests"))
    from match_fixtures import gsi_match_stream

    return gsi_match_stream(minutes=minutes, death_minutes=deaths, step_seconds=1, positions=True)


def session_stream(path: Path) -> Iterator[dict[str, Any]]:
    """raw_gsi_states.jsonl of the live session recorder (or plain payload lines)."""
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                entry = json.loads(line)
                yield entry.get("raw_payload", entry)


def simulate(payloads: Iterable[dict[str, Any]], lang: str = "en") -> list[dict[str, Any]]:
    """Feed the payloads; returns every new advice card as {clock, decision_point, ...}."""
    from fastapi.testclient import TestClient

    from app.main import app
    from app.player_api import PLAYER_SERVICE

    scheduler_module._utcnow = _game_clock_now
    PLAYER_SERVICE.configure(Path(tempfile.mkdtemp()), client=None, auto_start=False)
    cards: list[dict[str, Any]] = []
    last = None
    try:
        with TestClient(app) as client:
            for payload in payloads:
                clock = (payload.get("map") or {}).get("clock_time")
                if isinstance(clock, int):
                    _clock[0] = START + timedelta(seconds=clock + 90)
                client.post("/gsi", json=payload)
                response = client.get(f"/overlay/recommendation?lang={lang}").json()
                recommendation = response.get("recommendation")
                if response.get("status") != "active_advice" or not recommendation:
                    last = None
                    continue
                key = (response["decision_point"], recommendation["action"])
                if key == last:
                    continue
                last = key
                cards.append(
                    {
                        "clock": clock,
                        "decision_point": response["decision_point"],
                        "mode": response.get("advice_mode"),
                        "action": recommendation["action"],
                        "reason": recommendation["reason"],
                    }
                )
    finally:
        scheduler_module._utcnow = _real_utcnow
    return cards


def _clock_label(seconds: Any) -> str:
    if not isinstance(seconds, int):
        return "  ?  "
    sign = "-" if seconds < 0 else ""
    seconds = abs(seconds)
    return f"{sign}{seconds // 60:02d}:{seconds % 60:02d}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--session", type=Path, help="raw_gsi_states.jsonl to replay")
    parser.add_argument("--minutes", type=int, default=40, help="synthetic match length")
    parser.add_argument("--deaths", default="7,18,19,33", help="synthetic death minutes")
    parser.add_argument("--lang", default="en", choices=("en", "ru"))
    parser.add_argument("--reasons", action="store_true", help="print the reasons too")
    args = parser.parse_args()

    if args.session:
        payloads: Iterable[dict[str, Any]] = session_stream(args.session)
    else:
        deaths = tuple(int(m) for m in args.deaths.split(",") if m.strip())
        payloads = synthetic_stream(args.minutes, deaths)
    cards = simulate(payloads, args.lang)
    for card in cards:
        print(f"{_clock_label(card['clock'])}  {card['decision_point']:<26} {card['action']}")
        if args.reasons:
            print(f"{'':7}{'':27}{card['reason']}")
    per_point = Counter(card["decision_point"] for card in cards)
    print(f"\n{len(cards)} cards: " + ", ".join(f"{k} {v}" for k, v in per_point.most_common()))


if __name__ == "__main__":
    main()
