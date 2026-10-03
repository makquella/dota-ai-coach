"""
hero_meta.py - OpenDota meta data used for build advice and rank comparison.

Everything here works on data the service already cached (player_store cache
table), so reviews can be rebuilt offline:

- item constants (/constants/items): id -> key, display name, cost, whether
  the item is assembled from components;
- hero item popularity (/heroes/{id}/itemPopularity, professional matches):
  the usual build by game phase;
- hero item timings (/scenarios/itemTimings, public matches): games and wins
  per item and purchase-time bucket -> "win rate when bought by 15:00";
- hero stats (/heroStats): picks and wins per rank bracket.
"""

from __future__ import annotations

from typing import Any

from app.item_timing import classify_item_timing, normalize_item_name

# A timing bucket needs this many games before its win rate is quoted.
MIN_BUCKET_GAMES = 50
# Consumables, wards and similar never count as build items.
NON_BUILD_ITEMS = {
    "tpscroll",
    "ward_observer",
    "ward_sentry",
    "ward_dispenser",
    "dust",
    "smoke_of_deceit",
    "tango",
    "flask",
    "clarity",
    "faerie_fire",
    "enchanted_mango",
    "blood_grenade",
    "tome_of_knowledge",
    "cheese",
    "aegis",
    "refresher_shard",
    "aghanims_shard_roshan",
    "ultimate_scepter_roshan",
}
BUILD_ITEM_MIN_COST = 1800

RANK_BRACKETS = {1, 2, 3, 4, 5, 6, 7, 8}


def item_key(raw: Any) -> str:
    """ "item_bfury" (GSI) / "bfury" (OpenDota) -> "bfury"."""
    key = str(raw or "").strip().lower()
    return key[5:] if key.startswith("item_") else key


def item_name(key: str, constants: dict[str, Any] | None) -> str:
    info = ((constants or {}).get("items") or {}).get(key)
    if info and info.get("name"):
        return str(info["name"])
    return normalize_item_name(key)


def is_build_item(key: str, constants: dict[str, Any] | None) -> bool:
    """Completed items worth talking about (no components, consumables, recipes)."""
    if not key or key in NON_BUILD_ITEMS or key.startswith("recipe"):
        return False
    info = ((constants or {}).get("items") or {}).get(key)
    if info is not None:
        if info.get("assembled") and int(info.get("cost") or 0) >= BUILD_ITEM_MIN_COST:
            return True
    return bool(classify_item_timing(key)["is_meaningful"])


def _purchase_time(entry: dict[str, Any]) -> int:
    t = entry.get("t")
    return int(t) if isinstance(t, (int, float)) else 10**9


def build_items(
    items_log: list[dict[str, Any]], constants: dict[str, Any] | None
) -> list[dict[str, Any]]:
    """First purchase of every build item, in order: [{t, key, name}]."""
    seen: set[str] = set()
    result = []
    for entry in sorted(items_log, key=_purchase_time):
        key = item_key(entry.get("item"))
        if entry.get("t") is None or key in seen or not is_build_item(key, constants):
            continue
        seen.add(key)
        result.append({"t": int(entry["t"]), "key": key, "name": item_name(key, constants)})
    return result


# Items everyone gets at the start or that are no choice: never named as a start buy.
NOT_START_ITEMS = {"tpscroll", "ward_observer", "ward_sentry", "ward_dispenser"}


def start_items(
    popularity: dict[str, dict[str, int]] | None,
    constants: dict[str, Any] | None,
    *,
    limit: int = 6,
    min_share: float = 0.4,
) -> list[dict[str, Any]]:
    """The hero's usual starting purchase from OpenDota's `start_game_items`:
    the items bought in at least `min_share` as many games as the most bought
    one, most bought first, as [{key, name}]; [] when unknown."""
    if not popularity or not constants:
        return []
    counts = popularity.get("start_game_items") or {}
    if not counts:
        return []
    by_id = constants.get("by_id") or {}
    top = max(counts.values())
    rows = []
    for item_id, count in sorted(counts.items(), key=lambda kv: -kv[1]):
        key = by_id.get(str(item_id))
        if not key or key in NOT_START_ITEMS or count < top * min_share:
            continue
        rows.append({"key": key, "name": item_name(key, constants)})
        if len(rows) >= limit:
            break
    return rows


def popular_build(
    popularity: dict[str, dict[str, int]] | None,
    constants: dict[str, Any] | None,
    *,
    per_phase: int = 4,
) -> dict[str, list[dict[str, Any]]]:
    """Most bought build items per phase: {"early": [...], "mid": [...], "late": [...]}."""
    if not popularity or not constants:
        return {}
    by_id = constants.get("by_id") or {}
    result: dict[str, list[dict[str, Any]]] = {}
    for phase, label in (
        ("early_game_items", "early"),
        ("mid_game_items", "mid"),
        ("late_game_items", "late"),
    ):
        counts = popularity.get(phase) or {}
        total = sum(counts.values()) or 1
        rows = []
        for item_id, count in sorted(counts.items(), key=lambda kv: -kv[1]):
            key = by_id.get(str(item_id))
            if not key or not is_build_item(key, constants):
                continue
            rows.append(
                {"key": key, "name": item_name(key, constants), "share": round(count / total, 3)}
            )
            if len(rows) >= per_phase:
                break
        result[label] = rows
    return result


def timing_rows(timings: list[dict[str, Any]] | None, key: str) -> list[dict[str, Any]]:
    rows = [
        {**row, "winrate": row["wins"] / row["games"]}
        for row in timings or []
        if row.get("item") == key and row.get("games", 0) >= MIN_BUCKET_GAMES
    ]
    return sorted(rows, key=lambda r: r["time"])


def timing_verdict(timings: list[dict[str, Any]] | None, key: str, t: int) -> dict[str, Any] | None:
    """Win rate at the player's purchase time vs the typical and best buckets and the average."""
    rows = timing_rows(timings, key)
    if len(rows) < 2:
        return None
    mine = next((row for row in rows if row["time"] >= t), rows[-1])
    best = max(rows, key=lambda r: r["winrate"])
    games = sum(r["games"] for r in rows)
    wins = sum(r["wins"] for r in rows)
    # The median purchase time. Very early buckets mostly hold games that were
    # already won, so the realistic target is "as fast as most players".
    typical, seen = rows[-1], 0
    for row in rows:
        seen += row["games"]
        if seen * 2 >= games:
            typical = row
            break
    return {
        "bucket": mine["time"],
        "winrate": round(100 * mine["winrate"]),
        "games": mine["games"],
        "best_bucket": best["time"],
        "best_winrate": round(100 * best["winrate"]),
        "typical_bucket": typical["time"],
        "typical_winrate": round(100 * typical["winrate"]),
        "average_winrate": round(100 * wins / games) if games else None,
        "buckets": [
            {"time": r["time"], "winrate": round(100 * r["winrate"]), "games": r["games"]}
            for r in rows
        ],
    }


def rank_bracket(rank_tier: Any) -> int | None:
    """rank_tier 54 -> bracket 5 (Legend). 8x = Immortal."""
    try:
        bracket = int(rank_tier) // 10
    except (TypeError, ValueError):
        return None
    return bracket if bracket in RANK_BRACKETS else None


def rank_stars(rank_tier: Any) -> int | None:
    try:
        stars = int(rank_tier) % 10
    except (TypeError, ValueError):
        return None
    return stars if 1 <= stars <= 5 else None


def bracket_winrate(
    hero_stats: list[dict[str, Any]] | None, hero_id: Any, bracket: int | None
) -> dict[str, Any] | None:
    if not hero_stats or bracket is None:
        return None
    try:
        hero_id = int(hero_id)
    except (TypeError, ValueError):
        return None
    row = next((h for h in hero_stats if h.get("hero_id") == hero_id), None)
    if not row:
        return None
    picks, wins = (row.get("brackets") or {}).get(str(bracket), [0, 0])
    if not picks:
        return None
    return {"winrate": round(100 * wins / picks, 1), "picks": picks, "bracket": bracket}
