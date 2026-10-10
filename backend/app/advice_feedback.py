"""«Корисно / не до речі / повторювалося»: the player's own verdict on the live
advice of a match, given after it in the review (audit D, a local experiment).

The overlay never asks during a game. A verdict is kept per advice card, keyed
by the card's match clock and decision point (`<t>:<dp>`), in the store's meta
(`advice_feedback:<account>:<match>`), so it travels with a history backup and
stays on this computer otherwise: nothing here is sent anywhere. `summary`
counts the verdicts per decision point over all matches, for the developer
section and the problem report (counts only, no advice text), which is what
separates advice that was irrelevant or repeated from advice that was right
but ignored (advice_follow.py only sees deaths after urgent cards).

`quieter` lists the decision points the player mostly marks as irrelevant or
repeated: the scheduler spaces them out more (advice_scheduler.set_quieter) and
Progress shows the report. Safety advice (low HP, disables, deaths) is never
made quieter, whatever the marks.
"""

from __future__ import annotations

import json
import re
from typing import Any

from app.player_store import PlayerStore
from app.scheduler.constants import DEATH_REVIEW_DECISIONS
from app.scheduler.frequency import UNSCALED_DECISIONS

VERDICTS = ("useful", "irrelevant", "repeated")
# A decision point is made quieter after this many marks, most of them «not to
# the point» or «repeated».
QUIET_MIN_MARKS = 3
QUIET_SHARE = 0.6
NEVER_QUIET = frozenset(
    {"LOW_HP", "DISABLED_STATUS", "NO_ADVICE", "SOFT_STATUS", *DEATH_REVIEW_DECISIONS}
    | UNSCALED_DECISIONS
)
PREFIX = "advice_feedback"
KEY = re.compile(r"^\d{1,5}:[A-Za-z0-9_]{1,64}$")
MAX_PER_MATCH = 200


def advice_key(item: dict[str, Any]) -> str | None:
    """`<t>:<dp>` of an advice card of the review, None when it lacks either."""
    t, dp = item.get("t"), item.get("dp")
    if not isinstance(t, int) or isinstance(t, bool) or not isinstance(dp, str):
        return None
    key = f"{t}:{dp}"
    return key if KEY.match(key) else None


def _meta_key(account_id: int, match_id: int) -> str:
    return f"{PREFIX}:{int(account_id)}:{int(match_id)}"


def _clean(raw: Any) -> dict[str, str]:
    if not isinstance(raw, dict):
        return {}
    return {
        key: verdict
        for key, verdict in raw.items()
        if isinstance(key, str) and KEY.match(key) and verdict in VERDICTS
    }


def load(store: PlayerStore, account_id: int, match_id: int) -> dict[str, str]:
    raw = store.get_meta(_meta_key(account_id, match_id))
    try:
        return _clean(json.loads(raw)) if raw else {}
    except ValueError:
        return {}


def set_verdict(
    store: PlayerStore, account_id: int, match_id: int, key: str, verdict: str | None
) -> dict[str, str]:
    """One card's verdict (None clears it); the match's verdicts after it."""
    if not KEY.match(str(key)) or (verdict is not None and verdict not in VERDICTS):
        raise ValueError("bad_feedback")
    current = load(store, account_id, match_id)
    if verdict is None:
        current.pop(key, None)
    elif key in current or len(current) < MAX_PER_MATCH:
        current[key] = verdict
    store.set_meta(
        _meta_key(account_id, match_id),
        json.dumps(current, sort_keys=True) if current else None,
    )
    return current


def summary(store: PlayerStore, account_id: int) -> dict[str, Any]:
    """Verdict counts per decision point over the account's matches."""
    by_dp: dict[str, dict[str, int]] = {}
    totals = dict.fromkeys(VERDICTS, 0)
    matches = 0
    for _key, raw in store.meta_with_prefix(f"{PREFIX}:{int(account_id)}:"):
        try:
            verdicts = _clean(json.loads(raw))
        except ValueError:
            continue
        if not verdicts:
            continue
        matches += 1
        for key, verdict in verdicts.items():
            dp = key.split(":", 1)[1]
            counts = by_dp.setdefault(dp, dict.fromkeys(VERDICTS, 0))
            counts[verdict] += 1
            totals[verdict] += 1
    return {
        "matches": matches,
        "totals": totals,
        "by_decision_point": by_dp,
        "quieter": quieter_decisions(by_dp),
    }


def quieter_decisions(by_dp: dict[str, dict[str, int]]) -> list[str]:
    """Decision points mostly marked irrelevant or repeated (safety never)."""
    quiet = []
    for dp, counts in by_dp.items():
        marks = sum(counts.get(verdict, 0) for verdict in VERDICTS)
        unwanted = counts.get("irrelevant", 0) + counts.get("repeated", 0)
        if dp not in NEVER_QUIET and marks >= QUIET_MIN_MARKS and unwanted >= QUIET_SHARE * marks:
            quiet.append(dp)
    return sorted(quiet)
