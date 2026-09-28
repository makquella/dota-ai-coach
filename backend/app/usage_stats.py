"""
usage_stats.py - what the opt-in anonymous statistics send about advice.

The launcher posts one row a day (services/api `POST /v1/stats`) when the player
switched «Анонимная статистика» on; this is its advice part, from the analysed
matches that started in [since, until):
- `matches`: analysed matches, `with_advice`: those with live advice (recorded
  by the app);
- `advice`: live advice shown per decision point (the review's advice log);
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
        log = [a for a in analysis.get("advice") or [] if isinstance(a, dict)]
        if log:
            with_advice += 1
        kinds_at: dict[Any, str] = {}
        for item in log:
            kind = _kind(item.get("dp"))
            if kind:
                advice[kind] += 1
                if item.get("mode") == "urgent":
                    kinds_at.setdefault(item.get("t"), kind)
        for miss in (analysis.get("advice_follow") or {}).get("ignored") or []:
            kind = kinds_at.get(miss.get("t")) if isinstance(miss, dict) else None
            if kind:
                ignored[kind] += 1
    return {
        "matches": counted,
        "with_advice": with_advice,
        "advice": dict(advice.most_common(MAX_KINDS)),
        "ignored": dict(ignored.most_common(MAX_KINDS)),
    }
