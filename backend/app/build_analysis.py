"""
build_analysis.py - item build advice for one match.

Uses the player's purchase order (OpenDota purchase log or the app's GSI
recording) and cached OpenDota meta data (hero_meta.py):

- timing: for the first build items, the win rate of the hero when the item is
  bought at the player's time vs the typical (median) purchase time (public
  matches);
- build: the popular build of the hero (professional matches) vs what the
  player bought.

Returns a "build" block for the review and adds findings (texts in
analysis_texts.py). Without meta data (offline, never synced) it returns None
and the review simply has no build section.
"""

from __future__ import annotations

from typing import Any

from app.hero_meta import build_items, popular_build, timing_verdict

TIMING_ITEMS_CHECKED = 4
# How much worse than the typical bucket (percentage points) is worth a finding.
LATE_TIMING_GAP = 8
SERIOUS_TIMING_GAP = 10
GOOD_TIMING_MARGIN = 3


def analyze_build(
    facts: dict[str, Any], meta: dict[str, Any] | None, role: str
) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    findings: list[dict[str, Any]] = []
    if not meta or not facts.get("items_log"):
        return None, findings
    constants = meta.get("constants")
    timings = meta.get("timings")
    items = build_items(facts.get("items_log") or [], constants)
    popular = popular_build(meta.get("popularity"), constants)
    hero = facts.get("hero")

    rows = []
    worst: dict[str, Any] | None = None
    best_own: dict[str, Any] | None = None
    for item in items[:TIMING_ITEMS_CHECKED]:
        verdict = timing_verdict(timings, item["key"], item["t"])
        rows.append({**item, "timing": verdict})
        if not verdict:
            continue
        # Late = slower than most players of the hero, and it costs win rate.
        gap = verdict["typical_winrate"] - verdict["winrate"]
        if gap >= LATE_TIMING_GAP and verdict["bucket"] > verdict["typical_bucket"]:
            if worst is None or gap > worst["gap"]:
                worst = {"item": item, "verdict": verdict, "gap": gap}
        elif (
            verdict["average_winrate"] is not None
            and verdict["winrate"] >= verdict["average_winrate"] + GOOD_TIMING_MARGIN
        ):
            if best_own is None or verdict["winrate"] > best_own["verdict"]["winrate"]:
                best_own = {"item": item, "verdict": verdict}
    for item in items[TIMING_ITEMS_CHECKED:]:
        rows.append({**item, "timing": None})

    if worst:
        verdict = worst["verdict"]
        findings.append(
            _finding(
                "build_timing_late",
                "improve",
                severity=3 if worst["gap"] >= SERIOUS_TIMING_GAP else 2,
                weight=worst["gap"] / 4,
                item=worst["item"]["name"],
                t=worst["item"]["t"],
                hero=hero,
                winrate=verdict["winrate"],
                typical_t=verdict["typical_bucket"],
                typical_winrate=verdict["typical_winrate"],
            )
        )
    if best_own:
        verdict = best_own["verdict"]
        findings.append(
            _finding(
                "build_timing_good",
                "strength",
                weight=1.8,
                item=best_own["item"]["name"],
                t=best_own["item"]["t"],
                hero=hero,
                winrate=verdict["winrate"],
                average=verdict["average_winrate"],
            )
        )

    core = [row for row in (popular.get("mid") or [])[:3]]
    bought = {item["key"] for item in items}
    matched = [row for row in core if row["key"] in bought]
    if role != "support" and core and len(items) >= 2:
        if not matched:
            findings.append(
                _finding(
                    "build_off_meta",
                    "improve",
                    severity=1,
                    weight=1,
                    hero=hero,
                    popular=", ".join(row["name"] for row in core),
                    mine=", ".join(item["name"] for item in items[:4]),
                )
            )
        elif len(matched) >= 2:
            findings.append(
                _finding(
                    "build_on_meta",
                    "strength",
                    weight=0.6,
                    hero=hero,
                    items=", ".join(row["name"] for row in matched),
                )
            )

    block = {
        "items": rows,
        "popular": {
            phase: [{**row, "bought": row["key"] in bought} for row in entries]
            for phase, entries in popular.items()
        },
        "has_timings": any(row["timing"] for row in rows),
    }
    return block, findings


def _finding(
    finding_id: str, kind: str, *, severity: int = 1, weight: float = 1.0, **params: Any
) -> dict[str, Any]:
    return {
        "id": finding_id,
        "kind": kind,
        "section": "items",
        "severity": severity,
        "weight": weight,
        "params": params,
    }
