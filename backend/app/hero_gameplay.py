"""Owned readiness episodes for three heroes, using observed own signals only.

These are preparation variants, never assertions about a target or safe fight.
Only a real ready transition (including the first observation) queues a lesson.
Delivery consumes it; normal scheduler spacing still applies. Missing data,
gaps, hero/session changes and invalidated resources cancel pending lessons.
"""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from typing import Any

from app.hero_gameplay_texts import GAMEPLAY_VERSION, RULE_BY_ID, RULES, GameplayRule

PENDING_SECONDS = 180
HERO_SPACING_SECONDS = 90
RULE_REPEAT_SECONDS = 300
# A preparation tip teaches one thing about the hero: twice a match is enough.
MAX_SHOWS_PER_RULE = 2
OBSERVATION_GAP_SECONDS = 5
HEROES = frozenset(rule.hero for rule in RULES)
BLOCKING_STATUS = ("stunned", "hexed", "silenced", "muted", "disarmed", "smoked")


def _extra(state: Mapping[str, Any]) -> Mapping[str, Any]:
    value = state.get("extra_context")
    return value if isinstance(value, Mapping) else {}


def _number(value: Any) -> float | int | None:
    # GSI scalar normalization has already rejected nonfinite and huge numbers.
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return value if -10_000_000 <= value <= 10_000_000 else None


def _clock(state: Mapping[str, Any]) -> int | None:
    value = _extra(state).get("clock_time")
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _ability(extra: Mapping[str, Any], name: str) -> Mapping[str, Any]:
    abilities = extra.get("abilities")
    if not isinstance(abilities, list):
        return {}
    return next((a for a in abilities if isinstance(a, Mapping) and a.get("raw_name") == name), {})


def _ready(extra: Mapping[str, Any], name: str) -> bool:
    ability = _ability(extra, name)
    level = _number(ability.get("level"))
    return (
        level is not None
        and 0 < level <= 4
        and ability.get("cooldown") == 0
        and ability.get("can_cast_observed") is True
        and ability.get("ability_active") is True
    )


def _hp(extra: Mapping[str, Any]) -> float | None:
    health, maximum = _number(extra.get("health")), _number(extra.get("max_health"))
    if health is None or maximum is None or not 0 < health <= maximum:
        return None
    return 100 * health / maximum


def _own_context(state: Mapping[str, Any]) -> bool:
    extra, clock = _extra(state), _clock(state)
    observed = extra.get("observed_status")
    return (
        state.get("hero") in HEROES
        and extra.get("source_type") == "live_gsi"
        and extra.get("alive") is True
        and clock is not None
        and clock >= 90
        and extra.get("paused_observed") is False
        and isinstance(observed, Mapping)
        and all(observed.get(flag) is False for flag in BLOCKING_STATUS)
        and _hp(extra) is not None
    )


def rule_ready(state: Mapping[str, Any], rule: GameplayRule) -> bool:
    """Observed resources for preparation; says nothing about target applicability."""
    if not _own_context(state) or state.get("hero") != rule.hero:
        return False
    extra = _extra(state)
    if not _ready(extra, rule.ability):
        return False
    if rule.gate == "scepter":
        return extra.get("aghanims_scepter") is True
    if rule.gate == "shard":
        return extra.get("aghanims_shard") is True
    if rule.gate == "teleport":
        return extra.get("has_tp") is True
    if rule.gate == "slash_item":
        ready = extra.get("own_castable_items")
        return isinstance(ready, list) and bool({"item_black_king_bar", "item_manta"} & set(ready))
    if rule.gate == "meta_pair":
        return _ready(extra, "terrorblade_metamorphosis")
    if rule.gate == "recovery":
        hp = _hp(extra)
        return hp is not None and 55 <= hp <= 75
    return rule.gate == "ready"


def rule_valid(state: Mapping[str, Any], rule_id: object) -> bool:
    rule = RULE_BY_ID.get(rule_id) if isinstance(rule_id, str) else None
    if rule is None or not rule_ready(state, rule):
        return False
    extra, hp = _extra(state), _hp(_extra(state))
    # HP loss can be a self-cost too. It suppresses coaching; it is never proof
    # of an enemy hit, physical damage, an active buff or the end of a fight.
    return (
        hp is not None
        and hp >= (55 if rule.gate == "recovery" else 75)
        and not extra.get("recent_damage_taken")
        and not extra.get("hp_falling_fast")
        and not extra.get("overstay_warning")
        and not state.get("near_teamfight")
        and not state.get("near_objective")
        and not any(
            word in str(state.get("game_state") or "").lower()
            for word in ("fight", "pressure", "danger", "dead", "paused", "draft", "strategy")
        )
    )


def selected_rule(state: Mapping[str, Any]) -> GameplayRule | None:
    value = _extra(state).get("hero_gameplay")
    if not isinstance(value, Mapping) or value.get("version") != GAMEPLAY_VERSION:
        return None
    rule_id = value.get("rule_id")
    return RULE_BY_ID[rule_id] if isinstance(rule_id, str) and rule_valid(state, rule_id) else None


class HeroGameplay:
    """Owned by MatchMemory. No I/O, locks, target inference or LLM calls."""

    def __init__(self) -> None:
        self._clock: int | None = None
        self._ready: set[str] = set()
        self._pending: dict[str, dict[str, Any]] = {}
        self._shown: dict[str, int] = {}
        self._shown_count: dict[str, int] = {}
        self._last_shown: int | None = None
        self._episode = 0

    def observe(self, state: Mapping[str, Any]) -> None:
        clock = _clock(state)
        if clock is None or not _own_context(state):
            self._ready.clear()
            self._pending.clear()
            self._clock = clock
            return
        if self._clock is not None and (
            clock < self._clock or clock - self._clock > OBSERVATION_GAP_SECONDS
        ):
            # Never carry an old tactical episode across a gap or replay seek.
            self._pending.clear()
            self._ready.clear()
        ready = {rule.id for rule in RULES if rule_ready(state, rule)}
        self._pending = {
            key: value
            for key, value in self._pending.items()
            if key in ready and clock - value["created"] <= PENDING_SECONDS
        }
        for rule in RULES:
            if rule.id in ready - self._ready:
                if self._shown_count.get(rule.id, 0) >= MAX_SHOWS_PER_RULE:
                    continue
                previous = self._shown.get(rule.id)
                if previous is not None and clock - previous < RULE_REPEAT_SECONDS:
                    continue
                self._episode += 1
                self._pending[rule.id] = {
                    "rule_id": rule.id,
                    "version": GAMEPLAY_VERSION,
                    "episode_id": self._episode,
                    "created": clock,
                    "mechanics": list(rule.evidence),
                }
        self._clock, self._ready = clock, ready

    def context(self, state: Mapping[str, Any]) -> dict[str, Any] | None:
        clock = _clock(state)
        if clock is None or clock != self._clock:
            return None
        if self._last_shown is not None and clock - self._last_shown < HERO_SPACING_SECONDS:
            return None
        for rule in RULES:
            pending = self._pending.get(rule.id)
            if pending is not None and rule_valid(state, rule.id):
                extra = _extra(state)
                return {
                    **deepcopy(pending),
                    "observed": {
                        "ability": dict(_ability(extra, rule.ability)),
                        "health": extra.get("health"),
                        "max_health": extra.get("max_health"),
                        "aghanims_scepter": extra.get("aghanims_scepter"),
                        "aghanims_shard": extra.get("aghanims_shard"),
                        "has_tp": extra.get("has_tp"),
                        "status": dict(extra.get("observed_status") or {}),
                        "ready_items": [
                            item
                            for item in (extra.get("own_castable_items") or [])
                            if item in {"item_black_king_bar", "item_manta"}
                        ],
                        "metamorphosis": dict(_ability(extra, "terrorblade_metamorphosis"))
                        if rule.gate == "meta_pair"
                        else None,
                    },
                }
        return None

    def shown(self, context: Mapping[str, Any], clock: int) -> None:
        rule_id = context.get("rule_id")
        if not isinstance(rule_id, str):
            return
        pending = self._pending.get(rule_id)
        if pending is None or pending.get("episode_id") != context.get("episode_id"):
            return
        self._pending.pop(rule_id)
        self._shown[rule_id] = clock
        self._shown_count[rule_id] = self._shown_count.get(rule_id, 0) + 1
        self._last_shown = clock
