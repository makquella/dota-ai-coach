"""
usage_stats.py - what the opt-in anonymous statistics send about advice.

The launcher posts one row a day (services/api `POST /v1/stats`) when the player
switched «Анонимная статистика» on; this is its advice part, from the analysed
matches that started in [since, until):
- `matches`: analysed matches, `with_advice`: those with live advice (recorded
  by the app);
- `advice`: live advice shown per decision point (the whole advice log of each
  match, `analysis.advice_counts`, not only the 40 cards the review shows);
- `ignored`: urgent advice followed by a death within 30 s (advice_follow), per
  decision point: which warnings come too late or are not believed.
Counts only: no match ids, heroes, times, texts or account.
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Any

DECISION_POINT = re.compile(r"^[A-Z][A-Z0-9_]{1,47}$")
MAX_KINDS = 60


def _kind(value: Any) -> str | None:
    return value if isinstance(value, str) and DECISION_POINT.match(value) else None


def advice_counts(
    advice_log: list[dict[str, Any]] | None, follow: dict[str, Any] | None
) -> dict[str, dict[str, int]]:
    """Per decision point over the whole advice log of a match (the review shows
    only the first 40 cards): `shown`, and `ignored` = urgent advice followed by a
    death (advice_follow). Stored on the analysis as `advice_counts`."""
    shown: Counter[str] = Counter()
    ignored: Counter[str] = Counter()
    urgent_at: dict[Any, str] = {}
    for item in advice_log or []:
        if not isinstance(item, dict):
            continue
        kind = _kind(item.get("dp"))
        if kind:
            shown[kind] += 1
            if item.get("mode") == "urgent":
                urgent_at.setdefault(item.get("t"), kind)
    for miss in (follow or {}).get("ignored") or []:
        kind = urgent_at.get(miss.get("t")) if isinstance(miss, dict) else None
        if kind:
            ignored[kind] += 1
    return {"shown": dict(shown), "ignored": dict(ignored)}


def usage_stats(matches: list[dict[str, Any]], since: int, until: int) -> dict[str, Any]:
    advice: Counter[str] = Counter()
    ignored: Counter[str] = Counter()
    counted = with_advice = 0
    for match in matches:
        start = match.get("start_time")
        analysis = match.get("analysis")
        if not isinstance(start, int) or not since <= start < until or not analysis:
            continue
        counted += 1
        if analysis.get("advice"):
            with_advice += 1
        # The whole log's counts (ANALYSIS_VERSION 15+); older reviews only have
        # the first 40 cards shown in the review.
        counts = analysis.get("advice_counts")
        if not isinstance(counts, dict):
            counts = advice_counts(analysis.get("advice"), analysis.get("advice_follow"))
        for target, key in ((advice, "shown"), (ignored, "ignored")):
            for kind, n in (counts.get(key) or {}).items():
                if _kind(kind) and isinstance(n, int) and n > 0:
                    target[kind] += n
    return {
        "matches": counted,
        "with_advice": with_advice,
        "advice": dict(advice.most_common(MAX_KINDS)),
        "ignored": dict(ignored.most_common(MAX_KINDS)),
    }
