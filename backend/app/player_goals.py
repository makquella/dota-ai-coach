"""
player_goals.py - streak goals and the tilt warning on the home screen.

Both read the match table only (`PlayerStore.list_matches`, newest first), since
the player status that carries them is polled every few seconds:
- goals: small streaks with a target, e.g. «5 матчей подряд — не больше 5 смертей»:
  the current run from the newest match, the best run of the rows read and
  whether the target is met. A match without the number (no score before its
  review) is skipped, it neither breaks nor extends a run.
- tilt: the session still going (the last match ended under TILT_SESSION_GAP ago,
  earlier matches chained by starts TILT_CHAIN_GAP apart) with 3+ losses in a row
  at its end, or its last two scores both TILT_SCORE_DROP+ below the player's usual
  score (average of up to 20 earlier scored matches, 5+ needed). Facts only; the
  launcher words it («Три поражения подряд — может, перерыв?»).
"""

from __future__ import annotations

from typing import Any

GOALS = (
    # id, the match field, the rule, target run
    ("few_deaths", "deaths", lambda v: v <= 5, 5),
    ("good_score", "score", lambda v: v >= 60, 3),
)

TILT_LOSSES = 3
TILT_SESSION_GAP = 2 * 3600  # since the end of the last match
TILT_CHAIN_GAP = 3 * 3600  # between the starts of two matches of one session
TILT_SCORE_DROP = 20
TILT_BASELINE = 20
TILT_BASELINE_MIN = 5


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value != value:
        return None
    return float(value)


def goal_streaks(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """`rows` newest first. One entry per goal with any data."""
    result = []
    for goal_id, field, rule, target in GOALS:
        values = [v for v in (_number(r.get(field)) for r in rows) if v is not None]
        if not values:
            continue
        current = 0
        for value in values:
            if not rule(value):
                break
            current += 1
        best = run = 0
        for value in values:
            run = run + 1 if rule(value) else 0
            best = max(best, run)
        result.append(
            {
                "id": goal_id,
                "current": current,
                "best": best,
                "target": target,
                "met": current >= target,
            }
        )
    return result


def _session(rows: list[dict[str, Any]], now: int) -> list[dict[str, Any]]:
    """The matches of the session still going, newest first."""
    started = [r for r in rows if isinstance(r.get("start_time"), int)]
    if not started:
        return []
    newest = started[0]
    ended = newest["start_time"] + (newest.get("duration") or 0)
    if now - ended > TILT_SESSION_GAP:
        return []
    session = [newest]
    for row in started[1:]:
        if session[-1]["start_time"] - row["start_time"] > TILT_CHAIN_GAP:
            break
        session.append(row)
    return session


def tilt(rows: list[dict[str, Any]], now: int) -> dict[str, Any] | None:
    """`rows` newest first; `now` epoch seconds."""
    session = _session(rows, now)
    if not session:
        return None
    losses = 0
    for row in session:
        if row.get("win") is not False:
            break
        losses += 1
    if losses >= TILT_LOSSES:
        return {"reason": "losses", "losses": losses, "games": len(session)}
    scored = [(r, _number(r.get("score"))) for r in rows]
    scored = [(r, s) for r, s in scored if s is not None]
    last_two = [(r, s) for r, s in scored[:2] if r in session]
    earlier = [s for _, s in scored[2 : 2 + TILT_BASELINE]]
    if len(last_two) < 2 or len(earlier) < TILT_BASELINE_MIN:
        return None
    usual = sum(earlier) / len(earlier)
    if all(s <= usual - TILT_SCORE_DROP for _, s in last_two):
        return {
            "reason": "score_drop",
            "scores": [round(s) for _, s in last_two],
            "usual": round(usual),
            "games": len(session),
        }
    return None
