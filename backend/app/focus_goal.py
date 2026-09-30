"""
focus_goal.py - one problem the player chose to work on, checked in every match after.

The player picks a recurring problem on the Progress page. Every analysed match
played after that answers one question: did the problem come back?

- True (done): no finding of that problem, or of its twins, in the match;
- False: it is there again;
- None: the match could not show it (no data for it: no parsed replay for
  vision, no map positions, no advice given by the app during the match...).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.analysis_texts import FINDINGS, render_finding

# Findings that say the same thing: a peer comparison replaces the generic one,
# and the static variants apply when no benchmark is known.
FAMILIES = {
    "gpm_low_static": "gpm_low",
    "peer_gpm_behind": "gpm_low",
    "peer_lh10_behind": "lh10_low",
    "peer_deaths_more": "deaths_high",
}
# The analysis block a finding needs; without it the match cannot show it.
REQUIRES = {
    "died_after_warning": "advice",
    "deaths_enemy_half": "map",
    "deaths_same_place": "map",
    "counter_item_missing": "draft",
    # The last seconds before deaths exist only for live-recorded matches.
    "died_with_saver_ready": "last_moments",
    "burst_deaths": "last_moments",
    # Needs the player's skill order and the pro one.
    "skill_first_max": "skills",
}
MAX_RESULTS = 10
# Findings whose title names one item or hero ("Late Battle Fury"). The check works
# on the finding, not on that item or hero, so the goal gets a general title.
GENERAL_TITLES = {
    "build_timing_late": {"ru": "Поздние ключевые предметы", "en": "Late key items"},
    "counter_item_missing": {
        "ru": "Нет предметов против вражеских героев",
        "en": "No answer to the enemy heroes",
    },
    "killed_by_one": {
        "ru": "Один и тот же враг убивает вас снова и снова",
        "en": "The same enemy keeps killing you",
    },
}
# Advice about one match's lineup, not a habit (same as the career's NOT_RECURRING).
NOT_FOCUSABLE = {"draft_better_pick"}


def family(finding_id: str) -> str:
    return FAMILIES.get(finding_id, finding_id)


def can_focus(finding_id: str) -> bool:
    return (
        finding_id in FINDINGS
        and FINDINGS[finding_id].get("en") is not None
        and finding_id not in NOT_FOCUSABLE
    )


def new_focus(
    finding_id: str, section: str | None, params: dict[str, Any] | None
) -> dict[str, Any]:
    now = datetime.now(UTC)
    return {
        "id": finding_id,
        "family": family(finding_id),
        "section": section,
        "params": params or {},
        "since": now.isoformat(),
        "since_ts": int(now.timestamp()),
    }


def _required_block(finding_id: str) -> str | None:
    if finding_id in REQUIRES:
        return REQUIRES[finding_id]
    if finding_id.startswith("build_"):
        return "build"
    if finding_id.startswith("peer_"):
        return "peers"
    return None


def match_result(analysis: dict[str, Any] | None, focus: dict[str, Any]) -> bool | None:
    """Did the match avoid the focus problem? None when it could not show it."""
    if not analysis:
        return None
    problems = analysis.get("problems")
    if problems is None:  # stored before `problems` existed: the visible list
        problems = [f.get("id") for f in analysis.get("improvements") or []]
    if any(family(str(p)) == focus["family"] for p in problems):
        return False
    section = focus.get("section")
    if section and section not in (analysis.get("sections") or {}):
        return None
    block = _required_block(focus["id"])
    if block and not analysis.get(block):
        return None
    return True


def played_after(match: dict[str, Any], focus: dict[str, Any]) -> bool:
    start = match.get("start_time")
    return isinstance(start, (int, float)) and start >= focus.get("since_ts", 0)


def focus_summary(
    focus: dict[str, Any], matches: list[dict[str, Any]], lang: str
) -> dict[str, Any]:
    """`matches`: newest first, with their stored analysis (PlayerStore.matches_for_career)."""
    rendered = render_finding(
        {"id": focus["id"], "section": focus.get("section"), "params": focus.get("params") or {}},
        lang,
    )
    general = GENERAL_TITLES.get(focus["id"])
    if general:
        # The drill names the item or hero of one match too.
        rendered = {**rendered, "title": general["ru" if lang == "ru" else "en"], "drill": None}
    results = []
    for match in matches:
        if not played_after(match, focus):
            continue
        met = match_result(match.get("analysis"), focus)
        if met is None:
            continue
        results.append({"match_id": match["match_id"], "hero": match.get("hero"), "met": met})
        if len(results) >= MAX_RESULTS:
            break
    results.reverse()  # oldest first, as a row of marks
    met_count = sum(1 for r in results if r["met"])
    streak = 0
    for result in reversed(results):
        if not result["met"]:
            break
        streak += 1
    return {
        "id": focus["id"],
        "title": rendered.get("title"),
        "drill": rendered.get("drill"),
        "section_label": rendered.get("section_label"),
        "since": focus.get("since"),
        "results": results,
        "met": met_count,
        "total": len(results),
        "streak": streak,
    }
