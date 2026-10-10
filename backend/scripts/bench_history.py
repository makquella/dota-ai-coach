"""
How the match store reads a large history: timings of the reads the launcher
makes and the SQLite query plans behind them.

Builds a throwaway store with N synthetic matches (no real data) and prints
milliseconds per call and EXPLAIN QUERY PLAN for the list orders. Run from
backend/ after changing player_store.py queries or indexes:

    python scripts/bench_history.py            # 3000 matches
    python scripts/bench_history.py 10000
"""

from __future__ import annotations

import random
import sys
import tempfile
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.player_store import PlayerStore  # noqa: E402

ACCOUNT = 111
# Every list order of the app and its expected index (tests/test_store_plans.py).
PLANS = {
    "newest first": (
        "SELECT match_id FROM matches WHERE account_id = ? "
        "ORDER BY COALESCE(start_time, 0) DESC, match_id DESC LIMIT 30",
        (ACCOUNT,),
    ),
    "one hero, newest first": (
        "SELECT match_id FROM matches WHERE account_id = ? AND hero_id = ? "
        "ORDER BY COALESCE(start_time, 0) DESC, match_id DESC LIMIT 30",
        (ACCOUNT, 8),
    ),
    "heroes played": (
        "SELECT hero_id, COUNT(*) FROM matches "
        "WHERE account_id = ? AND hero_id IS NOT NULL GROUP BY hero_id",
        (ACCOUNT,),
    ),
}


def build(directory: Path, count: int) -> PlayerStore:
    store = PlayerStore(directory / "coach.sqlite3")
    rnd = random.Random(1)
    analysis = {"version": 21, "headline": {"score": 50}, "pad": ["x" * 200] * 40}
    for index in range(count):
        store.upsert_match(
            ACCOUNT,
            8_000_000_000 + index,
            source=rnd.choice(["opendota", "gsi"]),
            fields={
                "start_time": 1_700_000_000 + index * 3600,
                "hero_id": rnd.choice([1, 8, 11, 44, 70]),
                "hero": "Hero",
                "win": rnd.random() < 0.5,
                "score": rnd.randint(0, 100),
                "duration": 2000,
                "deaths": rnd.randint(0, 12),
            },
            analysis=analysis,
        )
    return store


def plan(store: PlayerStore, sql: str, params: tuple[Any, ...]) -> list[str]:
    with store._lock:
        return [row[3] for row in store._conn.execute(f"EXPLAIN QUERY PLAN {sql}", params)]


def timed(fn: Callable[[], object], repeat: int = 20) -> float:
    fn()
    started = time.perf_counter()
    for _ in range(repeat):
        fn()
    return 1000 * (time.perf_counter() - started) / repeat


def main() -> None:
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 3000
    store = build(Path(tempfile.mkdtemp()), count)
    reads: dict[str, Callable[[], object]] = {
        "match table, first page": lambda: store.list_matches(ACCOUNT, limit=30),
        "match table, page 40": lambda: store.list_matches(ACCOUNT, limit=30, offset=1170),
        "match table, one hero": lambda: store.list_matches(ACCOUNT, limit=30, hero_id=8),
        "match table, by score": lambda: store.list_matches(ACCOUNT, limit=30, sort="score"),
        "filter stats": lambda: store.match_stats(ACCOUNT, hero_id=8),
        "heroes played": lambda: store.hero_counts(ACCOUNT),
        "Progress (50 reviews)": lambda: store.matches_for_career(ACCOUNT, limit=50),
        "Profile (whole history)": lambda: store.profile_rows(ACCOUNT, limit=5000),
    }
    print(f"{count} matches")
    for label, fn in reads.items():
        print(f"  {label:<26} {timed(fn):7.2f} ms")
    for label, (sql, params) in PLANS.items():
        print(f"  plan, {label}: {'; '.join(plan(store, sql, params))}")


if __name__ == "__main__":
    main()
