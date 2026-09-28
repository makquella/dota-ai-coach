"""
weekly_summary.py - the last seven days on the home screen.

From the stored match table and reviews (no network): games, wins and losses,
the average review score and how it moved against the seven days before, the
best match of the week, the mistake that came back most often this week, and
the focus as a short training plan: the last PLAN_MATCHES matches judged by it
(match_result) with the drill to repeat. `now` may be a past moment (the end of
a calendar week for the Discord post): matches after it are left out.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from app.analysis_texts import render_finding
from app.focus_goal import NOT_FOCUSABLE, focus_summary

WEEK_SECONDS = 7 * 24 * 3600
PLAN_MATCHES = 3
# Findings that describe one lineup, not a habit.
NOT_A_HABIT = {"draft_better_pick", *NOT_FOCUSABLE}
MIN_REPEATS = 2
TOP_HEROES = 3


def _scores(rows: list[dict[str, Any]]) -> list[float]:
    return [float(r["score"]) for r in rows if isinstance(r.get("score"), (int, float))]


def weekly_summary(
    matches: list[dict[str, Any]],
    now: float,
    lang: str,
    focus: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """`matches`: newest first with their analysis (PlayerStore.matches_for_career).
    None when no match was played in the last seven days."""
    week = [m for m in matches if now - WEEK_SECONDS <= (m.get("start_time") or 0) < now]
    if not week:
        return None
    before = [
        m
        for m in matches
        if now - 2 * WEEK_SECONDS <= (m.get("start_time") or 0) < now - WEEK_SECONDS
    ]
    decided = [m for m in week if m.get("win") is not None]
    wins = sum(1 for m in decided if m["win"])
    scores, previous = _scores(week), _scores(before)
    summary: dict[str, Any] = {
        "games": len(week),
        "wins": wins,
        "losses": len(decided) - wins,
        "avg_score": round(sum(scores) / len(scores)) if scores else None,
        "prev_avg_score": round(sum(previous) / len(previous)) if previous else None,
    }
    if summary["avg_score"] is not None and summary["prev_avg_score"] is not None:
        summary["score_change"] = summary["avg_score"] - summary["prev_avg_score"]
    scored = [m for m in week if isinstance(m.get("score"), (int, float))]
    if scored:
        best = max(scored, key=lambda m: (m["score"], m.get("start_time") or 0))
        summary["best"] = {
            "match_id": best["match_id"],
            "hero": best.get("hero"),
            "hero_id": best.get("hero_id"),
            "score": best["score"],
            "win": best.get("win"),
        }
    heroes: dict[str, dict[str, Any]] = {}
    for match in week:
        if not match.get("hero"):
            continue
        row = heroes.setdefault(
            match["hero"],
            {"hero": match["hero"], "hero_id": match.get("hero_id"), "games": 0, "wins": 0},
        )
        row["games"] += 1
        row["wins"] += 1 if match.get("win") else 0
    summary["heroes"] = sorted(heroes.values(), key=lambda h: (-h["games"], -h["wins"]))[
        :TOP_HEROES
    ]
    counts: Counter[str] = Counter()
    latest: dict[str, dict[str, Any]] = {}
    for match in week:  # newest first: `latest` keeps the newest wording
        findings = (match.get("analysis") or {}).get("improvements") or []
        for finding in {f["id"]: f for f in reversed(findings)}.values():
            if finding["id"] in NOT_A_HABIT:
                continue
            counts[finding["id"]] += 1
            latest.setdefault(finding["id"], finding)
    repeated = [(fid, n) for fid, n in counts.most_common() if n >= MIN_REPEATS and fid in latest]
    if repeated:
        finding_id, count = repeated[0]
        rendered = render_finding(latest[finding_id], lang)
        summary["top_problem"] = {
            "id": finding_id,
            "title": rendered.get("title"),
            "count": count,
            "of": len(week),
        }
    if focus is not None:
        plan = focus_summary(focus, matches, lang)
        last = plan["results"][-PLAN_MATCHES:]
        summary["focus"] = {
            "id": plan["id"],
            "title": plan["title"],
            "drill": plan["drill"],
            "results": last,
            "met": sum(1 for r in last if r["met"]),
            "plan": PLAN_MATCHES,
        }
    return summary
