"""
finding_history.py - does a mistake of this match keep coming back?

For every problem of a reviewed match, the player's earlier analysed matches
(played before it, newest first) answer the same question as the focus goal
(focus_goal.match_result): was the problem there too? Twins count as one
problem (focus_goal.FAMILIES), and a match that could not show it (no parsed
replay for vision, no build data...) is skipped instead of breaking the row.

- `in_a_row`: this match plus the earlier ones in an unbroken row;
- `in_last`: how many of the last LOOKBACK earlier matches (that could show it) had it.

Only earlier matches are read, so a review's history does not change when new
matches are played (the AI coach's cached review stays valid).
"""

from __future__ import annotations

from typing import Any

from app.focus_goal import NOT_FOCUSABLE, family, match_result

LOOKBACK = 10
# Worth a line in the review: the third time in a row, or often in the last games.
MIN_IN_A_ROW = 3
MIN_IN_LAST = 4


def finding_history(
    match: dict[str, Any], analysis: dict[str, Any] | None, earlier: list[dict[str, Any]]
) -> dict[str, dict[str, int]]:
    """{finding id: {"in_a_row", "in_last", "of"}} for the problems that repeat.

    `earlier`: the player's matches newest first with their stored analysis
    (PlayerStore.matches_for_career); matches not played before `match` are ignored."""
    if not analysis:
        return {}
    start = match.get("start_time") or 0
    previous = [
        m
        for m in earlier
        if m.get("match_id") != match.get("match_id")
        and m.get("analysis")
        and (m.get("start_time") or 0) < start
    ]
    history: dict[str, dict[str, int]] = {}
    for finding in analysis.get("improvements") or []:
        finding_id = str(finding.get("id"))
        if finding_id in NOT_FOCUSABLE or finding_id in history:
            continue
        # The family, not the twin: a match without peers still shows the generic finding;
        # a match without the finding's section (no data for it) is skipped.
        probe = {
            "id": family(finding_id),
            "family": family(finding_id),
            "section": finding.get("section"),
        }
        row, streak_open, seen, had = 1, True, 0, 0
        for other in previous:
            avoided = match_result(other["analysis"], probe)
            if avoided is None:
                continue
            if streak_open:
                if avoided:
                    streak_open = False
                else:
                    row += 1
            if seen < LOOKBACK:
                seen += 1
                had += 0 if avoided else 1
            if not streak_open and seen >= LOOKBACK:
                break
        if row >= MIN_IN_A_ROW or (seen >= LOOKBACK // 2 and had >= MIN_IN_LAST):
            history[finding_id] = {"in_a_row": row, "in_last": had, "of": seen}
    return history
