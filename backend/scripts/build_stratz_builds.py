"""
Write data/meta/stratz_builds.json: what high-rank players (STRATZ, the Divine
and Immortal bracket) buy on every hero in every position — the starting
purchase and the build in the order it is finished, with the usual minute.

    STRATZ_TOKEN=... python scripts/build_stratz_builds.py           # all heroes
    STRATZ_TOKEN=... python scripts/build_stratz_builds.py --heroes 11 1

The token comes from the environment only (the repository secret STRATZ_TOKEN
in .github/workflows/stratz-builds.yml); it is never written anywhere. STRATZ
allows one token two IP addresses per 15 minutes, which is why this runs once a
week on one runner and the app reads the file (app/stratz_builds.py) instead of
asking STRATZ itself. One request per hero (all five positions at once), a
second apart.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from statistics import median
from typing import Any

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.dota_constants import HEROES  # noqa: E402

API = "https://api.stratz.com/graphql"
ITEMS_URL = "https://raw.githubusercontent.com/odota/dotaconstants/master/build/items.json"
OUT = BACKEND_DIR.parent / "data" / "meta" / "stratz_builds.json"
BRACKET = "DIVINE_IMMORTAL"
POSITIONS = ("POSITION_1", "POSITION_2", "POSITION_3", "POSITION_4", "POSITION_5")
MIN_GAMES = 150
# A start item is listed when this share of the games buys it (each copy apart).
START_SHARE = 0.4
# A build item: bought in this share of the games, at least this expensive.
BUILD_SHARE = 0.2
BUILD_MIN_COST = 1000
BUILD_LIMIT = 8
# Never a start buy or a build step of note: everyone gets them or they are no choice.
SKIP_ITEMS = {"tpscroll", "ward_observer", "ward_sentry", "ward_dispenser", "aegis", "cheese"}
BOOTS = {
    "power_treads",
    "phase_boots",
    "arcane_boots",
    "tranquil_boots",
    "guardian_greaves",
    "boots_of_bearing",
    "travel_boots",
    "travel_boots_2",
}

QUERY = """
query Builds {
  heroStats {
    stats(heroIds: [%(hero)d], bracketBasicIds: [%(bracket)s], groupByPosition: true) {
      position
      matchCount
      winCount
    }
    %(fields)s
  }
}
"""

FIELDS = """
    start_%(p)s: itemStartingPurchase(heroId: %(hero)d, bracketBasicIds: [%(bracket)s], positionIds: [%(p)s]) {
      itemId instance matchCount wasGiven
    }
    full_%(p)s: itemFullPurchase(heroId: %(hero)d, bracketBasicIds: [%(bracket)s], positionIds: [%(p)s]) {
      itemId instance time matchCount winCount
    }
"""


def query_text(hero_id: int, bracket: str = BRACKET) -> str:
    fields = "".join(FIELDS % {"p": p, "bracket": bracket, "hero": hero_id} for p in POSITIONS)
    return QUERY % {"bracket": bracket, "fields": fields, "hero": hero_id}


def fetch_hero(hero_id: int, token: str) -> dict[str, Any]:
    body = json.dumps({"query": query_text(int(hero_id))})
    request = urllib.request.Request(  # noqa: S310 - fixed URL
        API,
        data=body.encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "STRATZ_API",
        },
    )
    with urllib.request.urlopen(request, timeout=60) as response:  # noqa: S310
        answer = json.loads(response.read().decode("utf-8"))
    if answer.get("errors"):
        raise RuntimeError(f"hero {hero_id}: {answer['errors'][0].get('message')}")
    return answer["data"]["heroStats"]


def load_items() -> dict[str, dict[str, Any]]:
    with urllib.request.urlopen(ITEMS_URL, timeout=30) as response:  # noqa: S310 - fixed URL
        return json.loads(response.read().decode("utf-8"))


def by_id(items: dict[str, dict[str, Any]]) -> dict[int, str]:
    return {
        int(info["id"]): key
        for key, info in items.items()
        if isinstance(info, dict) and "id" in info
    }


def start_items(rows: list[dict[str, Any]], games: int, keys: dict[int, str]) -> list[list[Any]]:
    """[[key, count]] bought by START_SHARE+ of the games (a copy given by a
    teammate — a support's branches — is not a buy), most bought first."""
    counts: dict[str, int] = {}
    best: dict[str, int] = {}
    for row in rows:
        key = keys.get(int(row.get("itemId") or 0))
        if not key or key in SKIP_ITEMS or row.get("wasGiven"):
            continue
        if (row.get("matchCount") or 0) < games * START_SHARE:
            continue
        counts[key] = counts.get(key, 0) + 1
        best[key] = max(best.get(key, 0), int(row["matchCount"]))
    return [[key, counts[key]] for key in sorted(counts, key=lambda k: -best[k])]


def build_items(
    rows: list[dict[str, Any]], games: int, keys: dict[int, str], items: dict[str, dict[str, Any]]
) -> list[list[Any]]:
    """[[key, minute, share %, win %]]: the first copy of every finished item of
    BUILD_MIN_COST+ (or boots) bought in BUILD_SHARE+ of the games, in the order
    of its median minute."""
    per_item: dict[str, list[tuple[int, int, int]]] = {}
    for row in rows:
        key = keys.get(int(row.get("itemId") or 0))
        if not key or key in SKIP_ITEMS or row.get("instance", 0) != 0:
            continue
        info = items.get(key) or {}
        if key not in BOOTS and int(info.get("cost") or 0) < BUILD_MIN_COST:
            continue
        per_item.setdefault(key, []).append(
            (
                int(row.get("time") or 0),
                int(row.get("matchCount") or 0),
                int(row.get("winCount") or 0),
            )
        )
    result = []
    for key, buckets in per_item.items():
        bought = sum(count for _, count, _ in buckets)
        if bought < games * BUILD_SHARE:
            continue
        minutes = [minute for minute, count, _ in buckets for _ in range(count)]
        wins = sum(win for _, _, win in buckets)
        result.append(
            [key, int(median(minutes)), round(100 * bought / games), round(100 * wins / bought)]
        )
    # A part of another build item (Yasha for Sange and Yasha) is that item's step,
    # not a build line of its own.
    parts = {
        part
        for row in result
        for part in (items.get(row[0]) or {}).get("components") or []
        if isinstance(part, str)
    }
    result = [row for row in result if row[0] not in parts]
    result.sort(key=lambda row: row[1])
    return result[:BUILD_LIMIT]


def hero_entry(
    stats: dict[str, Any], keys: dict[int, str], items: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    """{pos1: {games, win, start, build}, …} for the positions with MIN_GAMES+ games."""
    games_by_position = {
        row["position"]: (int(row.get("matchCount") or 0), int(row.get("winCount") or 0))
        for row in stats.get("stats") or []
    }
    entry = {}
    for position in POSITIONS:
        games, wins = games_by_position.get(position, (0, 0))
        if games < MIN_GAMES:
            continue
        start = start_items(stats.get(f"start_{position}") or [], games, keys)
        build = build_items(stats.get(f"full_{position}") or [], games, keys, items)
        if start or build:
            entry[f"pos{position[-1]}"] = {
                "games": games,
                "win": round(100 * wins / games),
                "start": start,
                "build": build,
            }
    return entry


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--heroes", nargs="*", type=int, help="only these hero ids")
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()
    token = os.environ.get("STRATZ_TOKEN", "").strip()
    if not token:
        print("STRATZ_TOKEN is not set", file=sys.stderr)
        return 2
    items = load_items()
    keys = by_id(items)
    old = json.loads(args.out.read_text(encoding="utf-8")) if args.out.exists() else {}
    heroes = dict(old.get("heroes") or {})
    failed = []
    for hero_id in args.heroes or sorted(HEROES):
        try:
            entry = hero_entry(fetch_hero(hero_id, token), keys, items)
        except Exception as error:  # noqa: BLE001 - one hero failing keeps the others
            failed.append(hero_id)
            print(f"hero {hero_id}: {error}", file=sys.stderr)
        else:
            if entry:
                heroes[str(hero_id)] = entry
        time.sleep(1)
    used = {
        row[0]
        for entry in heroes.values()
        for position in entry.values()
        for row in position.get("start", []) + position.get("build", [])
    }
    data = {
        "source": "STRATZ",
        "bracket": BRACKET,
        "generated": datetime.now(UTC).strftime("%Y-%m-%d"),
        # In-game names of every item used, for the cards (the app may have no
        # item constants cached yet).
        "names": {key: (items.get(key) or {}).get("dname") or key for key in sorted(used)},
        "heroes": dict(sorted(heroes.items(), key=lambda kv: int(kv[0]))),
    }
    args.out.write_text(
        json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8"
    )
    print(f"{len(heroes)} heroes written to {args.out}; {len(failed)} failed: {failed}")
    # Most heroes failing means the token or the API is broken: fail the run.
    return 1 if len(failed) > len(HEROES) // 2 else 0


if __name__ == "__main__":
    raise SystemExit(main())
