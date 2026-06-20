"""
gsi_state.py — in-memory Dota 2 Game State Integration state for MVP overlay use.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from app.advice_context import build_advice_context
from app.config import GSI_DEBUG_LOG, GSI_DEBUG_SAMPLES_DIR
from app.hero_profiles import evaluate_laning_context
from app.hero_safety import evaluate_hero_safety
from app.item_timing import normalize_item_name
from app.signal_capabilities import capability_summary, live_gsi_observed_capabilities


_latest_raw_payload: dict[str, Any] | None = None
_latest_normalized_state: dict[str, Any] | None = None
_latest_timestamp: str | None = None
_previous_extra_context: dict[str, Any] | None = None

_DEBUG_TOP_LEVEL_FIELDS = (
    "map",
    "player",
    "hero",
    "items",
    "abilities",
    "buildings",
    "draft",
    "provider",
)

_HERO_NAME_MAP = {
    "npc_dota_hero_antimage": "Anti-Mage",
    "npc_dota_hero_drow_ranger": "Drow Ranger",
    "npc_dota_hero_ember_spirit": "Ember Spirit",
    "npc_dota_hero_gyrocopter": "Gyrocopter",
    "npc_dota_hero_juggernaut": "Juggernaut",
    "npc_dota_hero_kez": "Kez",
    "npc_dota_hero_life_stealer": "Lifestealer",
    "npc_dota_hero_luna": "Luna",
    "npc_dota_hero_medusa": "Medusa",
    "npc_dota_hero_monkey_king": "Monkey King",
    "npc_dota_hero_morphling": "Morphling",
    "npc_dota_hero_muerta": "Muerta",
    "npc_dota_hero_naga_siren": "Naga Siren",
    "npc_dota_hero_phantom_assassin": "Phantom Assassin",
    "npc_dota_hero_phantom_lancer": "Phantom Lancer",
    "npc_dota_hero_slark": "Slark",
    "npc_dota_hero_sniper": "Sniper",
    "npc_dota_hero_spectre": "Spectre",
    "npc_dota_hero_sven": "Sven",
    "npc_dota_hero_terrorblade": "Terrorblade",
    "npc_dota_hero_ursa": "Ursa",
    "antimage": "Anti-Mage",
    "anti-mage": "Anti-Mage",
    "drow ranger": "Drow Ranger",
    "ember spirit": "Ember Spirit",
    "emberspirit": "Ember Spirit",
    "gyrocopter": "Gyrocopter",
    "juggernaut": "Juggernaut",
    "kez": "Kez",
    "lifestealer": "Lifestealer",
    "life stealer": "Lifestealer",
    "luna": "Luna",
    "medusa": "Medusa",
    "monkey king": "Monkey King",
    "morphling": "Morphling",
    "muerta": "Muerta",
    "naga siren": "Naga Siren",
    "phantom assassin": "Phantom Assassin",
    "phantom lancer": "Phantom Lancer",
    "slark": "Slark",
    "sniper": "Sniper",
    "spectre": "Spectre",
    "sven": "Sven",
    "terrorblade": "Terrorblade",
    "ursa": "Ursa",
}

_ITEM_NAME_MAP = {
    "item_bfury": "Battle Fury",
    "item_power_treads": "Power Treads",
    "item_phase_boots": "Phase Boots",
    "item_ring_of_health": "Ring of Health",
    "item_claymore": "Claymore",
    "item_magic_wand": "Magic Wand",
    "item_manta": "Manta Style",
    "item_maelstrom": "Maelstrom",
    "item_helm_of_the_dominator": "Helm of the Dominator",
    "item_tango": "Tango",
    "item_branches": "Iron Branch",
}

_EMPTY_ITEM_NAMES = {"", "empty", "item_empty", "item_unknown", "item_none"}

_ABILITY_NAME_MAP = {
    "antimage_blink": "Blink",
    "anti_mage_blink": "Blink",
    "juggernaut_blade_fury": "Blade Fury",
    "life_stealer_rage": "Rage",
    "lifestealer_rage": "Rage",
    "medusa_mana_shield": "Mana Shield",
    "slark_dark_pact": "Dark Pact",
    "slark_pounce": "Pounce",
    "morphling_morph_agi": "Attribute Shift",
    "morphling_morph_str": "Attribute Shift",
    "morphling_attribute_shift": "Attribute Shift",
    "phantom_assassin_blur": "Blur",
    "drow_ranger_wave_of_silence": "Gust",
    "drow_ranger_gust": "Gust",
    "luna_lucent_beam": "Lucent Beam",
    "sven_warcry": "Warcry",
    "kez_grappling_claw": "Grappling Claw",
    "kez_raptor_dance": "Raptor Dance",
    "kez_echo_slash": "Echo Slash",
    "kez_talon_toss": "Talon Toss",
    "kez_falcon_rush": "Falcon Rush",
    "kez_ravens_veil": "Raven's Veil",
    "kez_kazurai_katana": "Kazurai Katana",
    "kez_switch_weapons": "Switch Weapons",
}


def update_latest_gsi(payload: dict[str, Any]) -> dict[str, Any]:
    global _latest_raw_payload, _latest_normalized_state, _latest_timestamp, _previous_extra_context

    _latest_raw_payload = payload
    _latest_normalized_state = normalize_gsi_payload(payload, previous_extra_context=_previous_extra_context)
    _previous_extra_context = dict(_latest_normalized_state.get("extra_context") or {})
    _latest_timestamp = datetime.now(timezone.utc).isoformat()
    _write_debug_payload_sample(payload, _latest_timestamp)
    return {
        "status": "ok",
        "timestamp": _latest_timestamp,
        "state": _latest_normalized_state,
    }


def get_current_state() -> dict[str, Any]:
    if _latest_normalized_state is None:
        return {
            "status": "waiting_for_gsi",
            "timestamp": None,
            "state": None,
        }

    return {
        "status": "ok",
        "timestamp": _latest_timestamp,
        "state": _latest_normalized_state,
    }


def get_gsi_debug_latest() -> dict[str, Any]:
    fields = get_gsi_debug_fields()
    if _latest_raw_payload is None:
        return {
            "status": "waiting_for_gsi",
            "timestamp": None,
            "latest_raw_payload": None,
            "latest_normalized_state": None,
            "top_level_keys": [],
            "detected_available_fields": _detected_available_fields(None),
            "fields_summary": fields,
        }

    return {
        "status": "ok",
        "timestamp": _latest_timestamp,
        "latest_raw_payload": _latest_raw_payload,
        "latest_normalized_state": _latest_normalized_state,
        "top_level_keys": sorted(_latest_raw_payload.keys()),
        "detected_available_fields": _detected_available_fields(_latest_raw_payload),
        "fields_summary": fields,
    }


def get_gsi_debug_fields() -> dict[str, Any]:
    payload = _latest_raw_payload or {}
    hero_block = _dict_value(payload.get("hero"))
    player_block = _dict_value(payload.get("player"))
    map_block = _dict_value(payload.get("map"))
    return {
        "has_map": _has_payload_field(payload, "map"),
        "has_player": _has_payload_field(payload, "player"),
        "has_hero": _has_payload_field(payload, "hero"),
        "has_items": _has_payload_field(payload, "items"),
        "has_abilities": _has_payload_field(payload, "abilities"),
        "has_buildings": _has_payload_field(payload, "buildings"),
        "has_draft": _has_payload_field(payload, "draft"),
        "available_hero_fields": sorted(hero_block.keys()),
        "available_player_fields": sorted(player_block.keys()),
        "available_map_fields": sorted(map_block.keys()),
    }


def _detected_available_fields(payload: dict[str, Any] | None) -> dict[str, bool]:
    payload = payload or {}
    return {
        field: _has_payload_field(payload, field)
        for field in _DEBUG_TOP_LEVEL_FIELDS
    }


def _has_payload_field(payload: dict[str, Any], field: str) -> bool:
    value = payload.get(field)
    if value is None:
        return False
    if isinstance(value, (dict, list, str)):
        return bool(value)
    return True


def _write_debug_payload_sample(payload: dict[str, Any], timestamp: str) -> None:
    if not GSI_DEBUG_LOG:
        return

    safe_timestamp = timestamp.replace(":", "").replace("-", "").replace("+", "_").replace(".", "_")
    GSI_DEBUG_SAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    path = GSI_DEBUG_SAMPLES_DIR / f"gsi_payload_{safe_timestamp}.json"
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def normalize_gsi_payload(
    payload: dict[str, Any],
    previous_extra_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    hero_block = _dict_value(payload.get("hero"))
    player_block = _dict_value(payload.get("player"))
    map_block = _dict_value(payload.get("map"))

    hero = _normalize_hero_name(
        _first_value(
            payload.get("hero_name"),
            payload.get("hero") if isinstance(payload.get("hero"), str) else None,
            hero_block.get("name"),
        )
    )
    if payload.get("minute") is not None:
        minute = _clamp_int(payload.get("minute"), 0, 90, default=0)
    else:
        minute = _normalize_minute(_first_value(map_block.get("clock_time"), map_block.get("game_time")))
    level = _clamp_int(_first_value(payload.get("level"), hero_block.get("level")), 1, 30, default=1)
    gold = _clamp_int(_first_value(payload.get("gold"), player_block.get("gold")), 0, None, default=0)
    hp_percent = _normalize_hp_percent(payload, hero_block)
    game_state = _normalize_game_state(payload, map_block)
    team_status = _normalize_team_status(payload, hero_block)
    items = _normalize_items(payload.get("items"))
    extra_context = _normalize_extra_context(
        payload,
        map_block=map_block,
        player_block=player_block,
        hero_block=hero_block,
        previous_extra_context=previous_extra_context,
    )

    state = {
        "hero": hero,
        "role": "carry",
        "minute": minute,
        "level": level,
        "gold": gold,
        "items": items,
        "hp_percent": hp_percent,
        "game_state": game_state,
        "team_status": team_status,
        "extra_context": extra_context,
    }
    state["extra_context"].update(evaluate_hero_safety(state))
    state["extra_context"]["laning_context"] = evaluate_laning_context(state)
    state["extra_context"].update(build_advice_context(state))
    return state


def _dict_value(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _normalize_extra_context(
    payload: dict[str, Any],
    *,
    map_block: dict[str, Any],
    player_block: dict[str, Any],
    hero_block: dict[str, Any],
    previous_extra_context: dict[str, Any] | None,
) -> dict[str, Any]:
    reliable_gold = _optional_int(player_block.get("gold_reliable"))
    unreliable_gold = _optional_int(player_block.get("gold_unreliable"))
    gold = _optional_int(_first_value(player_block.get("gold"), payload.get("gold")))
    available_gold = _available_gold(
        reliable_gold=reliable_gold,
        unreliable_gold=unreliable_gold,
        gold=gold,
    )
    buyback_cost = _optional_int(hero_block.get("buyback_cost"))
    buyback_cooldown = _optional_int(hero_block.get("buyback_cooldown"))
    status_effects = _status_effects(hero_block)
    abilities = _normalize_abilities(payload.get("abilities"))
    minute = _normalize_minute(_first_value(map_block.get("clock_time"), map_block.get("game_time")))
    match_id, is_demo_or_lobby = _normalize_match_id(_first_value(map_block.get("matchid"), map_block.get("match_id")))
    demo_values_detected = _demo_values_detected(gold=gold, gpm=_optional_int(player_block.get("gpm")), minute=minute)
    has_abilities = _has_payload_field(payload, "abilities")
    has_buildings = _has_payload_field(payload, "buildings")
    has_position = hero_block.get("xpos") is not None and hero_block.get("ypos") is not None
    previous_for_deltas = (
        previous_extra_context
        if previous_extra_context and previous_extra_context.get("match_id") == match_id
        else None
    )
    capabilities = capability_summary(
        "live_gsi",
        observed=live_gsi_observed_capabilities(
            has_abilities=has_abilities,
            has_buildings=has_buildings,
            has_position=has_position,
        ),
    )

    context: dict[str, Any] = {
        "source_type": "live_gsi",
        "context_confidence": "high",
        **capabilities,
        "mana_percent": _normalize_mana_percent(hero_block),
        "mana": _optional_int(hero_block.get("mana")),
        "max_mana": _optional_int(hero_block.get("max_mana")),
        "health": _optional_int(hero_block.get("health")),
        "max_health": _optional_int(hero_block.get("max_health")),
        "alive": _optional_bool(hero_block.get("alive")),
        "respawn_seconds": _optional_int(hero_block.get("respawn_seconds")),
        "xpos": _optional_number(hero_block.get("xpos")),
        "ypos": _optional_number(hero_block.get("ypos")),
        "stunned": _optional_bool(hero_block.get("stunned")) or False,
        "silenced": _optional_bool(hero_block.get("silenced")) or False,
        "hexed": _optional_bool(hero_block.get("hexed")) or False,
        "disarmed": _optional_bool(hero_block.get("disarmed")) or False,
        "muted": _optional_bool(hero_block.get("muted")) or False,
        "break_status": _optional_bool(hero_block.get("break")) or False,
        "magicimmune": _optional_bool(hero_block.get("magicimmune")) or False,
        "smoked": _optional_bool(hero_block.get("smoked")) or False,
        "buyback_cost": buyback_cost,
        "buyback_cooldown": buyback_cooldown,
        "gold_reliable": reliable_gold,
        "gold_unreliable": unreliable_gold,
        "available_gold": available_gold,
        "buyback_available": _buyback_available(
            available_gold=available_gold,
            buyback_cost=buyback_cost,
            buyback_cooldown=buyback_cooldown,
        ),
        "kills": _optional_int(player_block.get("kills")),
        "deaths": _optional_int(player_block.get("deaths")),
        "assists": _optional_int(player_block.get("assists")),
        "last_hits": _optional_int(player_block.get("last_hits")),
        "denies": _optional_int(player_block.get("denies")),
        "gpm": _optional_int(player_block.get("gpm")),
        "xpm": _optional_int(player_block.get("xpm")),
        "player_slot": _optional_int(player_block.get("player_slot")),
        "team_name": _optional_str(player_block.get("team_name")),
        "team_slot": _optional_int(player_block.get("team_slot")),
        "radiant_score": _optional_int(map_block.get("radiant_score")),
        "dire_score": _optional_int(map_block.get("dire_score")),
        "match_id": match_id,
        "is_demo_or_lobby": is_demo_or_lobby,
        "demo_values_detected": demo_values_detected,
        "game_time": _optional_int(map_block.get("game_time")),
        "daytime": _optional_bool(map_block.get("daytime")),
        "paused": _optional_bool(map_block.get("paused")) or False,
        "has_abilities": has_abilities,
        "has_buildings": has_buildings,
        "status_effects": status_effects,
        "abilities": abilities,
    }

    context["death_count_changed"] = _value_changed(previous_for_deltas, context, "deaths")
    context["score_changed"] = (
        _value_changed(previous_for_deltas, context, "radiant_score")
        or _value_changed(previous_for_deltas, context, "dire_score")
    )
    context["farm_rate_state"] = _farm_rate_state(
        minute=minute,
        last_hits=context.get("last_hits"),
        gpm=context.get("gpm"),
        demo_values_detected=demo_values_detected,
    )
    return {key: value for key, value in context.items() if value is not None}


def _normalize_mana_percent(hero_block: dict[str, Any]) -> int | None:
    direct = hero_block.get("mana_percent")
    if direct is not None:
        return _clamp_int(direct, 0, 100, default=100)

    mana = hero_block.get("mana")
    max_mana = hero_block.get("max_mana")
    try:
        if int(max_mana) > 0:
            return _clamp_int(round((int(mana) / int(max_mana)) * 100), 0, 100, default=100)
    except (TypeError, ValueError):
        return None
    return None


def _status_effects(hero_block: dict[str, Any]) -> list[str]:
    effect_fields = {
        "stunned": "stunned",
        "silenced": "silenced",
        "hexed": "hexed",
        "disarmed": "disarmed",
        "muted": "muted",
        "break": "break",
    }
    return [
        label
        for field, label in effect_fields.items()
        if _optional_bool(hero_block.get(field)) is True
    ]


def _available_gold(*, reliable_gold: int | None, unreliable_gold: int | None, gold: int | None) -> int | None:
    if reliable_gold is not None or unreliable_gold is not None:
        return max(0, reliable_gold or 0) + max(0, unreliable_gold or 0)
    return gold


def _buyback_available(
    *,
    available_gold: int | None,
    buyback_cost: int | None,
    buyback_cooldown: int | None,
) -> bool:
    if available_gold is None or buyback_cost is None or buyback_cooldown is None:
        return False
    return buyback_cooldown == 0 and buyback_cost > 0 and available_gold >= buyback_cost


def _normalize_match_id(value: Any) -> tuple[str, bool]:
    text = str(value or "").strip()
    if text in {"", "0", "0.0"}:
        return "local_demo", True
    return text, False


def _demo_values_detected(*, gold: int | None, gpm: int | None, minute: int) -> bool:
    return (gpm is not None and gpm > 2000) or (gold is not None and minute < 10 and gold > 30000)


def _farm_rate_state(
    *,
    minute: int,
    last_hits: int | None,
    gpm: int | None,
    demo_values_detected: bool = False,
) -> str:
    if minute < 10 or demo_values_detected or (gpm is not None and gpm > 2000):
        return "unknown"
    if _farm_threshold_missed(minute, last_hits) or (minute >= 15 and gpm is not None and gpm < 400):
        return "slow"
    if last_hits is not None or gpm is not None:
        return "good"
    return "unknown"


def _farm_threshold_missed(minute: int, last_hits: int | None) -> bool:
    if last_hits is None:
        return False
    thresholds = ((25, 170), (20, 120), (15, 80), (10, 45))
    return any(minute >= threshold_minute and last_hits < threshold_lh for threshold_minute, threshold_lh in thresholds)


def _value_changed(previous: dict[str, Any] | None, current: dict[str, Any], key: str) -> bool:
    if not previous or previous.get(key) is None or current.get(key) is None:
        return False
    return previous.get(key) != current.get(key)


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _optional_number(value: Any) -> float | int | None:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return int(number) if number.is_integer() else number


def _optional_bool(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "on"}:
            return True
        if lowered in {"0", "false", "no", "off"}:
            return False
    if isinstance(value, (int, float)):
        return bool(value)
    return None


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _first_value(*values: Any) -> Any:
    for value in values:
        if value is not None:
            return value
    return None


def _clamp_int(value: Any, minimum: int, maximum: int | None, default: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = default
    number = max(minimum, number)
    if maximum is not None:
        number = min(maximum, number)
    return number


def _normalize_minute(value: Any) -> int:
    try:
        seconds = int(value)
    except (TypeError, ValueError):
        return 0
    if seconds < 0:
        return 0
    return min(seconds // 60, 90)


def _normalize_hp_percent(payload: dict[str, Any], hero_block: dict[str, Any]) -> int:
    direct = _first_value(payload.get("hp_percent"), hero_block.get("health_percent"))
    if direct is not None:
        return _clamp_int(direct, 0, 100, default=100)

    health = hero_block.get("health")
    max_health = hero_block.get("max_health")
    try:
        if int(max_health) > 0:
            return _clamp_int(round((int(health) / int(max_health)) * 100), 0, 100, default=100)
    except (TypeError, ValueError):
        pass
    return 100


def _normalize_hero_name(value: Any) -> str:
    raw_name = str(value or "").strip()
    key = raw_name.lower()
    if key in _HERO_NAME_MAP:
        return _HERO_NAME_MAP[key]
    if key.startswith("npc_dota_hero_"):
        key = key.removeprefix("npc_dota_hero_")
    return _title_from_token(key) if key else "Unknown"


def _normalize_items(value: Any) -> list[str]:
    if isinstance(value, list):
        items: list[str] = []
        for item in value:
            normalized = _normalize_item_name(item)
            if normalized:
                items.append(normalized)
        return items
    if not isinstance(value, dict):
        return []

    items: list[str] = []
    for slot_name in sorted(value):
        slot = value[slot_name]
        item_name = slot.get("name") if isinstance(slot, dict) else slot
        normalized = _normalize_item_name(item_name)
        if normalized:
            items.append(normalized)
    return items


def _normalize_item_name(value: Any) -> str:
    raw_name = str(value or "").strip()
    key = raw_name.lower()
    if key in _EMPTY_ITEM_NAMES:
        return ""
    if key in _ITEM_NAME_MAP:
        return _ITEM_NAME_MAP[key]
    return normalize_item_name(key)


def _normalize_abilities(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        raw_abilities = value
    elif isinstance(value, dict):
        raw_abilities = [value[key] for key in sorted(value)]
    else:
        raw_abilities = []

    abilities: list[dict[str, Any]] = []
    seen_names: set[str] = set()
    for raw_ability in raw_abilities:
        ability = _normalize_ability(raw_ability)
        if not ability:
            continue
        dedupe_key = str(ability.get("name") or ability.get("raw_name") or "").lower()
        if dedupe_key in seen_names:
            continue
        seen_names.add(dedupe_key)
        abilities.append(ability)
    return abilities


def _normalize_ability(value: Any) -> dict[str, Any] | None:
    if isinstance(value, dict):
        raw_name = _optional_str(value.get("name"))
        level = _optional_int(value.get("level"))
        cooldown = _optional_number(
            _first_value(value.get("cooldown"), value.get("cooldown_remaining"), value.get("cooldown_time"))
        )
        can_cast = _optional_bool(value.get("can_cast"))
        if can_cast is None:
            can_cast = _optional_bool(value.get("ability_active"))
    else:
        raw_name = _optional_str(value)
        level = None
        cooldown = None
        can_cast = None

    if not raw_name:
        return None

    return {
        "name": _normalize_ability_name(raw_name),
        "raw_name": raw_name,
        "level": level,
        "cooldown": cooldown,
        "can_cast": can_cast,
    }


def _normalize_ability_name(value: Any) -> str:
    raw_name = str(value or "").strip()
    key = raw_name.lower().removeprefix("ability_")
    if key in _ABILITY_NAME_MAP:
        return _ABILITY_NAME_MAP[key]
    return _title_from_token(key)


def _normalize_game_state(payload: dict[str, Any], map_block: dict[str, Any]) -> str:
    state = _first_value(
        payload.get("game_state"),
        payload.get("event"),
        map_block.get("name"),
        map_block.get("game_state"),
    )
    return str(state or "gsi_update").strip() or "gsi_update"


def _normalize_team_status(payload: dict[str, Any], hero_block: dict[str, Any]) -> str:
    if payload.get("team_status"):
        return str(payload["team_status"]).strip()
    if hero_block.get("alive") is False:
        return "hero_dead"
    return "unknown"


def _title_from_token(value: str) -> str:
    return value.replace("_", " ").replace("-", " ").title()
