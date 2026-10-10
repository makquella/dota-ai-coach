"""«На чому ґрунтується розбір?»: what a stored review was built from, and whether
the reviews Progress averages are comparable (audit E).

`stamp` records on every analysis the rules version (ANALYSIS_VERSION), the
OpenDota trim version, the Dota patch, the data it read (OpenDota, a parsed
replay, the app's own GSI recording), when it was built and why: `new`, `rules`
(the rules changed since the previous build) or `data` (the same rules, more or
newer data). Old analyses without a stamp read as unknown, never as current.

`career_basis` summarizes a Progress window: every review is rebuilt to the
current rules before Progress averages them (player_service._career_result),
so the rules are the same; what can still differ is the patch and the data
(parsed replays and live recordings unlock more metrics). The launcher shows
it so a change in the averages is not read as a change in skill.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from typing import Any

REASONS = ("new", "rules", "data")


def stamp(
    *,
    rules: int,
    trim: int,
    opendota: Mapping[str, Any] | None,
    sources: Sequence[str] | None,
    parsed: bool,
    has_timeline: bool,
    previous: Mapping[str, Any] | None,
) -> dict[str, Any]:
    patch = (opendota or {}).get("patch")
    data = ([str(source) for source in sources or []], bool(parsed), bool(has_timeline))
    old = previous.get("basis") if previous is not None else None
    if (
        isinstance(old, Mapping)
        and previous is not None
        and previous.get("version") == rules
        and (old.get("sources"), old.get("parsed"), old.get("recorded")) == data
    ):
        # Rebuilt with the same rules and the same data: nothing new to say.
        return dict(old)
    if previous is None:
        reason, previous_rules = "new", None
    else:
        previous_rules = previous.get("version")
        reason = "rules" if previous_rules != rules else "data"
    return {
        "rules": rules,
        "trim": trim,
        "patch": patch if isinstance(patch, int) and not isinstance(patch, bool) else None,
        "sources": [str(source) for source in sources or []],
        "parsed": bool(parsed),
        "recorded": bool(has_timeline),
        "built_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "reason": reason,
        "previous_rules": previous_rules if isinstance(previous_rules, int) else None,
    }


def career_basis(analyses: Sequence[Mapping[str, Any] | None], rules: int) -> dict[str, Any]:
    """Counts over a Progress window: rules versions, patches, parsed and recorded."""
    stamps: list[Mapping[str, Any]] = []
    for analysis in analyses:
        if analysis is None:
            continue
        raw = analysis.get("basis") if isinstance(analysis, Mapping) else None
        stamps.append(raw if isinstance(raw, Mapping) else {})
    versions = Counter(
        str(a.get("version")) for a in analyses if isinstance(a, Mapping) and a.get("version")
    )
    patches = Counter(str(s.get("patch")) for s in stamps if s.get("patch") is not None)
    parsed = sum(1 for s in stamps if s.get("parsed"))
    recorded = sum(1 for s in stamps if s.get("recorded"))
    total = len(stamps)
    return {
        "rules": rules,
        "matches": total,
        "same_rules": versions.get(str(rules), 0) == total and total > 0,
        "rules_versions": dict(versions),
        "patches": dict(patches),
        "unknown_patch": total - sum(patches.values()),
        "parsed": parsed,
        "recorded": recorded,
        "mixed_patches": len(patches) > 1,
        "mixed_data": 0 < parsed < total,
    }
