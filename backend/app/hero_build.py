"""
hero_build.py - "your build on the hero": the player's own items in their wins
and losses on the hero they play most (or the one Progress is filtered to).

From the reviewed matches with a known result and a purchase log
(sections.items.big_items: the first purchase of every meaningful item):
- every item bought in MIN_ITEM_GAMES+ of those matches: games, win rate when
  bought, win rate when not bought (MIN_WITHOUT+ games without it), and the
  median timing in wins and in losses;
- the most common first big item in wins and in losses;
- up to MAX_HIGHLIGHTS plain lines, only for clear gaps: an item that comes
  TIMING_GAP+ seconds later in losses, an item whose win rate with and without
  differs by WINRATE_GAP+ points;
- the key item's timing game by game and its last games against the ones before
  (`timing_trend`): is the player getting it sooner.

The player's own games decide, nothing from other players: what works for
them, in their bracket, with their habits.
"""

from __future__ import annotations

from collections import Counter
from statistics import median
from typing import Any

from app.analysis_texts import HERO_BUILD, _plural_uk, clock

MIN_MATCHES = 6
MIN_ITEM_GAMES = 3
MIN_WITHOUT = 3
TIMING_GAP = 120
WINRATE_GAP = 20
MAX_ITEMS = 8
MAX_HIGHLIGHTS = 3
# The key item's timing trend: a core item, not boots or a wand.
KEY_ITEM_MIN_SECONDS = 9 * 60
TREND_GAMES = 5
TREND_MIN_POINTS = 4
TREND_MIN_BEFORE = 3
TREND_MAX_POINTS = 20


def _items(match: dict[str, Any]) -> list[dict[str, Any]]:
    section = ((match.get("analysis") or {}).get("sections") or {}).get("items") or {}
    return [
        item
        for item in section.get("big_items") or []
        if isinstance(item, dict) and item.get("item") and isinstance(item.get("t"), int)
    ]


def _winrate(games: list[dict[str, Any]]) -> int | None:
    return round(100 * sum(1 for g in games if g["win"]) / len(games)) if games else None


def hero_build(matches: list[dict[str, Any]], lang: str) -> dict[str, Any] | None:
    """`matches`: career rows (newest first) with their stored analyses."""
    lang = "uk" if lang == "uk" else "en"
    usable = [m for m in matches if m.get("win") is not None and m.get("hero") and _items(m)]
    by_hero = Counter(m["hero"] for m in usable)
    if not by_hero:
        return None
    hero, count = by_hero.most_common(1)[0]
    games = [m for m in usable if m["hero"] == hero]
    if count < MIN_MATCHES:
        return None

    bought: dict[str, list[tuple[dict[str, Any], int]]] = {}
    for game in games:
        for item in _items(game):
            bought.setdefault(item["item"], []).append((game, item["t"]))
    rows = []
    for name, entries in bought.items():
        if len(entries) < MIN_ITEM_GAMES:
            continue
        with_item = [game for game, _ in entries]
        without = [g for g in games if g not in with_item]
        win_times = [t for game, t in entries if game["win"]]
        loss_times = [t for game, t in entries if not game["win"]]
        rows.append(
            {
                "item": name,
                "games": len(entries),
                "winrate": _winrate(with_item),
                "without_games": len(without),
                "winrate_without": _winrate(without) if len(without) >= MIN_WITHOUT else None,
                "t_win": round(median(win_times)) if win_times else None,
                "t_loss": round(median(loss_times)) if loss_times else None,
            }
        )
    rows.sort(key=lambda r: (-r["games"], r["t_win"] or r["t_loss"] or 0))
    rows = rows[:MAX_ITEMS]

    firsts = {
        key: Counter(_items(g)[0]["item"] for g in games if bool(g["win"]) == won)
        for key, won in (("win", True), ("loss", False))
    }
    first_items = {
        key: counter.most_common(1)[0][0] if counter else None for key, counter in firsts.items()
    }
    return {
        "hero": hero,
        "hero_id": next((g.get("hero_id") for g in games if g.get("hero_id")), None),
        "matches": len(games),
        "wins": sum(1 for g in games if g["win"]),
        "items": rows,
        "first_items": first_items,
        "highlights": _highlights(rows, first_items, lang),
        "timing_trend": timing_trend(games, rows),
    }


def timing_trend(games: list[dict[str, Any]], rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    """The key item's timing game by game (oldest first): the most bought item
    finished at KEY_ITEM_MIN_SECONDS+ in a typical game (not boots or a wand), with
    the median of the last TREND_GAMES games against the TREND_GAMES before."""
    key = None
    for row in rows:
        times = [t for t in (row["t_win"], row["t_loss"]) if t is not None]
        if times and median(times) >= KEY_ITEM_MIN_SECONDS:
            key = row["item"]
            break
    if key is None:
        return None
    points = []
    for game in reversed(games):  # oldest first
        t = next((item["t"] for item in _items(game) if item["item"] == key), None)
        if t is not None:
            points.append({"match_id": game.get("match_id"), "t": t, "win": bool(game["win"])})
    if len(points) < TREND_MIN_POINTS:
        return None
    recent = [p["t"] for p in points[-TREND_GAMES:]]
    before = [p["t"] for p in points[-2 * TREND_GAMES : -TREND_GAMES]]
    result: dict[str, Any] = {
        "item": key,
        "points": points[-TREND_MAX_POINTS:],
        "recent": round(median(recent)),
        "recent_games": len(recent),
    }
    if len(before) >= TREND_MIN_BEFORE:
        result["before"] = round(median(before))
        result["before_games"] = len(before)
        result["change"] = result["recent"] - result["before"]
    return result


def _highlights(
    rows: list[dict[str, Any]], first_items: dict[str, str | None], lang: str
) -> list[str]:
    text = HERO_BUILD[lang]
    candidates: list[tuple[float, str]] = []
    for row in rows:
        if row["t_win"] is not None and row["t_loss"] is not None:
            gap = row["t_loss"] - row["t_win"]
            if gap >= TIMING_GAP:
                candidates.append(
                    (
                        gap / 60,
                        text["timing"].format(
                            item=row["item"], win=clock(row["t_win"]), loss=clock(row["t_loss"])
                        ),
                    )
                )
        if row["winrate_without"] is not None and row["winrate"] is not None:
            gap = row["winrate"] - row["winrate_without"]
            if abs(gap) >= WINRATE_GAP:
                key = "with_better" if gap > 0 else "without_better"
                candidates.append(
                    (
                        abs(gap) / 10,
                        text[key].format(
                            item=row["item"],
                            winrate=row["winrate"],
                            without=row["winrate_without"],
                            games_text=_games(row["games"], lang),
                            without_text=_games(row["without_games"], lang),
                        ),
                    )
                )
    win_first, loss_first = first_items.get("win"), first_items.get("loss")
    if win_first and loss_first and win_first != loss_first:
        candidates.append((2.5, text["first"].format(win=win_first, loss=loss_first)))
    candidates.sort(key=lambda c: -c[0])
    return [line for _, line in candidates[:MAX_HIGHLIGHTS]]


def _games(count: int, lang: str) -> str:
    if lang == "uk":
        return f"{count} {_plural_uk(count, 'гра', 'гри', 'ігор')}"
    return f"{count} game{'' if count == 1 else 's'}"
