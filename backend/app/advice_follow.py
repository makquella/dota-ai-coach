"""
advice_follow.py - did the player act on the urgent advice?

The app knows when it showed urgent advice (the live advice log) and when the
hero died (GSI timeline). A death within FOLLOW_WINDOW_SECONDS after urgent
advice (retreat, reset HP, back off) means the warning came in time but was
not acted on. Two or more such deaths in a match become a finding: the fix is
a habit, not a new skill — react to the warning at once.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

FOLLOW_WINDOW_SECONDS = 30
MIN_IGNORED_FOR_FINDING = 2


def analyze_advice_follow(
    facts: Mapping[str, Any],
) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    advice = [a for a in facts.get("advice_log") or [] if a.get("mode") == "urgent"]
    if not advice:
        return None, []
    deaths = sorted(d["t"] for d in facts.get("deaths_log") or [] if d.get("t") is not None)
    ignored = []
    counted: set[float] = set()  # one death answers at most one warning
    for item in sorted(advice, key=lambda a: a.get("t") if a.get("t") is not None else -1):
        t = item.get("t")
        if t is None:
            continue
        death = next(
            (d for d in deaths if t < d <= t + FOLLOW_WINDOW_SECONDS and d not in counted), None
        )
        if death is not None:
            counted.add(death)
            ignored.append({"t": t, "death_t": death, "action": item.get("action")})
    block = {"urgent": len(advice), "ignored": ignored, "window": FOLLOW_WINDOW_SECONDS}
    findings = []
    if len(ignored) >= MIN_IGNORED_FOR_FINDING:
        findings.append(
            {
                "id": "died_after_warning",
                "kind": "improve",
                "section": "survival",
                "severity": 2,
                "weight": float(len(ignored)) + 0.5,
                "params": {
                    "count": len(ignored),
                    "urgent": len(advice),
                    "t": ignored[0]["t"],
                    "window": FOLLOW_WINDOW_SECONDS,
                },
            }
        )
    return block, findings
