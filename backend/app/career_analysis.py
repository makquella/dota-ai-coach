"""
career_analysis.py - statistics and advice over many matches of one player.

Input: rows from PlayerStore.matches_for_career (newest first; summary columns
from OpenDota or GSI, plus the stored post-match analysis when there is one).
Output: win rate and averages, the trend of the last 10 matches against the 10
before, a hero table, problems that keep coming back across analysed matches,
and a short focus plan built from the most frequent ones.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from statistics import mean
from typing import Any

from app.analysis_texts import FINDINGS, PEER_ROLES, rank_label, render_finding
from app.hero_meta import bracket_winrate, rank_bracket
from app.peer_analysis import career_peers

TREND_WINDOW = 10
RECURRING_MIN_SHARE = 0.25
RECURRING_MIN_COUNT = 2
# For these metrics a lower value is better.
LOWER_IS_BETTER = {"deaths"}


def _avg(values: list[Any]) -> float | None:
    numbers = [float(v) for v in values if isinstance(v, (int, float)) and not isinstance(v, bool)]
    return round(mean(numbers), 1) if numbers else None


def _score(match: dict[str, Any]) -> int | None:
    analysis = match.get("analysis") or {}
    value = (analysis.get("headline") or {}).get("score", match.get("score"))
    return int(value) if isinstance(value, (int, float)) else None


def _kda(match: dict[str, Any]) -> float | None:
    if match.get("kills") is None or match.get("deaths") is None:
        return None
    return ((match.get("kills") or 0) + (match.get("assists") or 0)) / max(
        1, match.get("deaths") or 0
    )


def analyze_career(
    matches: list[dict[str, Any]],
    lang: str = "en",
    *,
    rank_tier: Any = None,
    hero_stats: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """`rank_tier` of the player (OpenDota profile) and cached /heroStats are optional."""
    lang = "ru" if lang == "ru" else "en"
    decided = [m for m in matches if m.get("win") is not None]
    wins = sum(1 for m in decided if m["win"])
    analyzed = [m for m in matches if m.get("analysis")]
    rank = career_peers([m["analysis"] for m in analyzed], rank_tier)
    if rank:
        rank["rank_label"] = rank_label(rank.get("rank_tier"), lang)
        rank["role_label"] = PEER_ROLES.get(rank["role"], {}).get(lang)
    bracket = rank["bracket"] if rank else rank_bracket(rank_tier)
    return {
        "matches": len(matches),
        "analyzed": len(analyzed),
        "wins": wins,
        "losses": len(decided) - wins,
        "winrate": round(100 * wins / len(decided)) if decided else None,
        "streak": _streak(decided),
        "averages": _averages(matches),
        "trend": _trend(matches),
        "heroes": _heroes(matches, hero_stats, bracket),
        "rank": rank,
        "rank_bracket_label": rank_label(bracket * 10 if bracket else None, lang),
        "recurring": _recurring(analyzed, "improve", lang),
        "recurring_strengths": _recurring(analyzed, "strength", lang)[:3],
        "focus_plan": [item for item in _recurring(analyzed, "improve", lang) if item.get("drill")][
            :3
        ],
        "series": _series(matches),
        "best_match": _best(matches),
    }


def _averages(matches: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "kills": _avg([m.get("kills") for m in matches]),
        "deaths": _avg([m.get("deaths") for m in matches]),
        "assists": _avg([m.get("assists") for m in matches]),
        "kda": _avg([_kda(m) for m in matches]),
        "gpm": _avg([m.get("gpm") for m in matches]),
        "xpm": _avg([m.get("xpm") for m in matches]),
        "last_hits": _avg([m.get("last_hits") for m in matches]),
        "lh_10": _avg([m.get("lh_10") for m in matches]),
        "score": _avg([_score(m) for m in matches]),
        "duration": _avg([m.get("duration") for m in matches]),
    }


def _trend(matches: list[dict[str, Any]]) -> dict[str, Any]:
    recent = matches[:TREND_WINDOW]
    previous = matches[TREND_WINDOW : TREND_WINDOW * 2]
    result: dict[str, Any] = {"window": TREND_WINDOW, "enough": len(previous) >= 3}
    getters = {
        "gpm": lambda m: m.get("gpm"),
        "lh_10": lambda m: m.get("lh_10"),
        "deaths": lambda m: m.get("deaths"),
        "kda": _kda,
        "score": _score,
        "winrate": lambda m: None if m.get("win") is None else (100 if m["win"] else 0),
    }
    for name, getter in getters.items():
        now = _avg([getter(m) for m in recent])
        before = _avg([getter(m) for m in previous])
        delta = round(now - before, 1) if now is not None and before is not None else None
        direction = None
        if delta is not None:
            threshold = max(1.0, abs(before or 0) * 0.05)
            direction = "flat" if abs(delta) < threshold else ("up" if delta > 0 else "down")
        better = None
        if direction in {"up", "down"}:
            better = (direction == "down") if name in LOWER_IS_BETTER else (direction == "up")
        result[name] = {
            "recent": now,
            "previous": before,
            "delta": delta,
            "direction": direction,
            "better": better,
        }
    return result


def _heroes(
    matches: list[dict[str, Any]],
    hero_stats: list[dict[str, Any]] | None = None,
    bracket: int | None = None,
) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for match in matches:
        if match.get("hero"):
            groups[match["hero"]].append(match)
    rows = []
    for hero, games in groups.items():
        decided = [g for g in games if g.get("win") is not None]
        wins = sum(1 for g in decided if g["win"])
        rows.append(
            {
                "hero": hero,
                "hero_id": games[0].get("hero_id"),
                "matches": len(games),
                "wins": wins,
                "winrate": round(100 * wins / len(decided)) if decided else None,
                "kda": _avg([_kda(g) for g in games]),
                "gpm": _avg([g.get("gpm") for g in games]),
                "score": _avg([_score(g) for g in games]),
                # The hero's win rate among all players of the same rank bracket.
                "bracket_winrate": (
                    bracket_winrate(hero_stats, games[0].get("hero_id"), bracket) or {}
                ).get("winrate"),
            }
        )
    return sorted(rows, key=lambda r: (-int(r["matches"]), -int(r["winrate"] or 0)))[:12]


def _recurring(analyzed: list[dict[str, Any]], kind: str, lang: str) -> list[dict[str, Any]]:
    if not analyzed:
        return []
    counts: Counter[str] = Counter()
    latest: dict[str, dict[str, Any]] = {}
    for match in analyzed:
        analysis = match["analysis"]
        findings = analysis.get("improvements" if kind == "improve" else "strengths") or []
        for finding_id in {f["id"] for f in findings}:
            counts[finding_id] += 1
            if finding_id not in latest:
                latest[finding_id] = next(f for f in findings if f["id"] == finding_id)
    total = len(analyzed)
    result = []
    for finding_id, count in counts.most_common():
        share = count / total
        if count < RECURRING_MIN_COUNT or share < RECURRING_MIN_SHARE or finding_id not in FINDINGS:
            continue
        rendered = render_finding(latest[finding_id], lang)
        result.append(
            {
                "id": finding_id,
                "kind": kind,
                "section": rendered.get("section"),
                "section_label": rendered.get("section_label"),
                "title": rendered["title"],
                "drill": rendered.get("drill"),
                "count": count,
                "of": total,
                "share": round(100 * share),
                "text": (
                    f"В {count} из {total} последних разобранных матчей"
                    if lang == "ru"
                    else f"In {count} of your last {total} analysed matches"
                ),
            }
        )
    return result


def _streak(decided: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not decided:
        return None
    first = decided[0]["win"]
    length = 0
    for match in decided:
        if match["win"] != first:
            break
        length += 1
    return {"win": first, "length": length}


def _series(matches: list[dict[str, Any]]) -> list[dict[str, Any]]:
    chronological = list(reversed(matches[:20]))
    return [
        {
            "match_id": m.get("match_id"),
            "start_time": m.get("start_time"),
            "hero": m.get("hero"),
            "win": m.get("win"),
            "gpm": m.get("gpm"),
            "deaths": m.get("deaths"),
            "lh_10": m.get("lh_10"),
            "score": _score(m),
        }
        for m in chronological
    ]


def _best(matches: list[dict[str, Any]]) -> dict[str, Any] | None:
    scored = [m for m in matches if _score(m) is not None]
    if not scored:
        return None
    best = max(scored, key=lambda m: _score(m) or 0)
    return {
        "match_id": best.get("match_id"),
        "hero": best.get("hero"),
        "score": _score(best),
        "win": best.get("win"),
    }
