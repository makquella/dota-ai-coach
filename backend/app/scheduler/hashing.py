"""
scheduler.hashing - stateless bucketing and hashing helpers.

Pure functions, no scheduler state, no ``self``. Extracted verbatim from
advice_scheduler.py as part of the Phase 2 split (no behavior change).

These are the building blocks used by the state-hash builders. The top-level
builders ``build_state_hash`` / ``build_tactical_state_hash`` themselves stay in
advice_scheduler.py for now: they reference DEATH_REVIEW_DECISIONS, which still
lives in the facade until step 7. Moving them here today would create a
leaf -> facade import cycle. They move here once DEATH_REVIEW_DECISIONS lands in
scheduler.constants (leaf -> leaf, no cycle).
"""

from __future__ import annotations

import hashlib
from typing import Any

KEY_ITEMS = {
    "battle fury",
    "manta style",
    "black king bar",
    "bkb",
    "butterfly",
    "satanic",
    "abyssal blade",
    "eye of skadi",
    "dragon lance",
    "hurricane pike",
    "silver edge",
    "desolator",
    "diffusal blade",
}


def _action_hash(action: str) -> str:
    normalized = " ".join(str(action or "").strip().lower().split())
    if not normalized:
        return ""
    return hashlib.sha1(normalized.encode("utf-8")).hexdigest()[:12]


def _game_phase(minute: int) -> str:
    if minute < 10:
        return "laning"
    if minute < 20:
        return "early_mid"
    if minute < 35:
        return "mid_game"
    return "late_game"


def _minute_bucket(minute: int) -> str:
    if minute < 10:
        return "0-10"
    if minute < 20:
        return "10-20"
    if minute < 35:
        return "20-35"
    return "35+"


def _hp_bucket(hp_percent: int) -> str:
    if hp_percent <= 20:
        return "0-20"
    if hp_percent <= 35:
        return "21-35"
    if hp_percent <= 60:
        return "36-60"
    return "61-100"


def _simplify_team_status(value: Any) -> str:
    text = str(value or "").strip().lower().replace("_", " ")
    if not text:
        return "unknown"

    categories = [
        ("objective", ("objective", "roshan", "tower", "barracks", "push", "highground")),
        ("pressure", ("pressure", "gank", "danger", "smoke", "under attack")),
        ("bad_fight", ("bad fight", "dive", "chase", "skirmish", "brawl")),
        ("fight", ("fight", "teamfight", "contest", "engage")),
        ("safe_farm", ("farm", "farming", "calm", "safe", "jungle", "lane")),
        ("dead_or_paused", ("dead", "paused", "disconnected")),
    ]
    matches = [
        label for label, keywords in categories if any(keyword in text for keyword in keywords)
    ]
    return "+".join(matches) if matches else "generic"


def _key_item_signature(items: Any) -> str:
    if not isinstance(items, list):
        return "none"
    normalized = {
        str(item).strip().lower().replace("_", " ").replace("-", " ")
        for item in items
        if str(item).strip()
    }
    key_items = sorted(item for item in normalized if item in KEY_ITEMS)
    return "|".join(key_items) if key_items else "none"
