"""
self_compare.py - the player's best matches against their worst ones.

On the most played hero (enough reviewed matches), the best third of the
matches by review score is compared with the worst third: last hits at 10:00,
GPM, deaths, lane deaths, kill participation, first big item timing. The
biggest differences become short plain-language lines ("in your best games
Battle Fury comes at 14:10, in your worst at 19:40").
"""

from __future__ import annotations

from statistics import mean
from typing import Any

from app.analysis_texts import SELF_COMPARE, clock

MIN_MATCHES = 6
MAX_HIGHLIGHTS = 3


def _score(match: dict[str, Any]) -> float | None:
    value = (match["analysis"].get("headline") or {}).get("score")
    return float(value) if isinstance(value, (int, float)) else None


def _section(match: dict[str, Any], name: str, key: str) -> Any:
    return ((match["analysis"].get("sections") or {}).get(name) or {}).get(key)


def _first_item(match: dict[str, Any]) -> dict[str, Any] | None:
    item = _section(match, "items", "first_item")
    return item if isinstance(item, dict) and item.get("t") is not None else None


# key -> (getter, lower is better)
METRICS: dict[str, tuple[Any, bool]] = {
    "lh_10": (lambda m: _section(m, "laning", "lh10"), False),
    "gpm": (lambda m: (m["analysis"].get("headline") or {}).get("gpm"), False),
    "deaths": (lambda m: (m["analysis"].get("headline") or {}).get("deaths"), True),
    "lane_deaths": (lambda m: _section(m, "laning", "lane_deaths"), True),
    "kill_participation": (lambda m: _section(m, "fights", "kill_participation"), False),
    "first_item_t": (lambda m: (_first_item(m) or {}).get("t"), True),
}


def _avg(values: list[Any]) -> float | None:
    numbers = [float(v) for v in values if isinstance(v, (int, float)) and not isinstance(v, bool)]
    return mean(numbers) if numbers else None


def _group(matches: list[dict[str, Any]]) -> dict[str, Any]:
    decided = [m for m in matches if m.get("win") is not None]
    return {
        "count": len(matches),
        "winrate": round(100 * sum(1 for m in decided if m["win"]) / len(decided))
        if decided
        else None,
        "score": round(_avg([_score(m) for m in matches]) or 0),
    }


def compare_best_worst(matches: list[dict[str, Any]], lang: str) -> dict[str, Any] | None:
    """`matches`: career rows (newest first) with their stored analyses."""
    analyzed = [m for m in matches if m.get("analysis") and _score(m) is not None]
    by_hero: dict[str, list[dict[str, Any]]] = {}
    for match in analyzed:
        by_hero.setdefault(match.get("hero") or "", []).append(match)
    hero, games = max(by_hero.items(), key=lambda kv: len(kv[1]), default=("", []))
    if len(games) < MIN_MATCHES or not hero:
        return None
    ranked = sorted(games, key=lambda m: -(_score(m) or 0))
    third = max(2, len(ranked) // 3)
    best, worst = ranked[:third], ranked[-third:]

    rows = []
    for key, (getter, lower_better) in METRICS.items():
        good = _avg([getter(m) for m in best])
        bad = _avg([getter(m) for m in worst])
        if good is None or bad is None:
            continue
        diff = good - bad
        scale = max(abs(good), abs(bad), 1.0)
        rows.append(
            {
                "key": key,
                "best": round(good, 1),
                "worst": round(bad, 1),
                "gap": abs(diff) / scale,
                # True when the best games are better on this metric (they usually are).
                "best_is_better": (diff < 0) if lower_better else (diff > 0),
            }
        )

    item_best, item_worst = _common_item(best), _common_item(worst)
    highlights = []
    for row in sorted(rows, key=lambda r: -r["gap"]):
        if len(highlights) >= MAX_HIGHLIGHTS or row["gap"] < 0.15 or not row["best_is_better"]:
            continue
        if row["key"] == "first_item_t" and not (item_best and item_worst):
            continue
        template = SELF_COMPARE[lang][row["key"]]
        highlights.append(
            template.format(
                best=_fmt(row["key"], row["best"]),
                worst=_fmt(row["key"], row["worst"]),
                item_best=item_best,
                item_worst=item_worst,
            )
        )
    for row in rows:
        row["gap"] = round(row["gap"], 3)
    return {
        "hero": hero,
        "matches": len(games),
        "first_items": {"best": item_best, "worst": item_worst},
        "best": _group(best),
        "worst": _group(worst),
        "rows": rows,
        "highlights": highlights,
    }


def _common_item(matches: list[dict[str, Any]]) -> str | None:
    items = [(_first_item(m) or {}).get("item") for m in matches]
    named = [i for i in items if i]
    return max(set(named), key=named.count) if named else None


def _fmt(key: str, value: float) -> str:
    if key == "first_item_t":
        return clock(value)
    if key == "kill_participation":
        return f"{round(value)}%"
    if key in {"deaths", "lane_deaths"}:
        return f"{value:.1f}".rstrip("0").rstrip(".")
    return str(round(value))
