"""
scheduler.hashing - stateless bucketing and hashing helpers.

Pure functions, no scheduler state, no ``self``. Extracted verbatim from
advice_scheduler.py as part of the Phase 2 split (no behavior change).

Includes the top-level state-hash builders ``build_state_hash`` and
``build_tactical_state_hash``. They depend on DEATH_REVIEW_DECISIONS
(scheduler.constants), build_advice_policy (app.advice_policy), and the
state_utils _to_int — all leaf modules, so no import cycle.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from app.advice_policy import build_advice_policy
from app.scheduler.constants import DEATH_REVIEW_DECISIONS
from app.scheduler.state_utils import _to_int

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


def build_state_hash(state: dict[str, Any], decision_point: str) -> str:
    minute = _to_int(state.get("minute"), 0)
    hp_percent = _to_int(state.get("hp_percent"), 100)
    extra_context = (
        state.get("extra_context") if isinstance(state.get("extra_context"), dict) else {}
    )
    payload = {
        "hero": str(state.get("hero", "")).strip().lower(),
        "minute_bucket": minute,
        "hp_bucket": hp_percent // 10,
        "items": sorted(str(item).strip().lower() for item in state.get("items", [])),
        "game_state": str(state.get("game_state", "")).strip().lower(),
        "team_status": str(state.get("team_status", "")).strip().lower(),
        "decision_point": decision_point,
        "death_event_id": extra_context.get("last_death_event_id")
        if decision_point in DEATH_REVIEW_DECISIONS
        else None,
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def build_tactical_state_hash(
    state: dict[str, Any],
    decision_point: str,
    *,
    action_type: str | None = None,
) -> str:
    if not action_type:
        action_type = str(build_advice_policy(state, decision_point)["action_type"])
    extra_context = (
        state.get("extra_context") if isinstance(state.get("extra_context"), dict) else {}
    )
    payload = {
        "hero": str(state.get("hero", "")).strip().lower(),
        "decision_point": decision_point,
        "action_type": action_type,
        "game_phase": _game_phase(_to_int(state.get("minute"), 0)),
        "hp_bucket": _hp_bucket(_to_int(state.get("hp_percent"), 100)),
        "minute_bucket": _minute_bucket(_to_int(state.get("minute"), 0)),
        "team_status": _simplify_team_status(state.get("team_status", "")),
        "key_items": _key_item_signature(state.get("items", [])),
        "death_event_id": extra_context.get("last_death_event_id")
        if decision_point in DEATH_REVIEW_DECISIONS
        else None,
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]
