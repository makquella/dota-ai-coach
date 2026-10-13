"""«What Wardly says on <hero>»: real overlay cards for a promo video.

A synthetic match (backend/tests/match_fixtures via simulate_live_gsi) goes
through the real backend (/gsi -> rules -> scheduler -> /overlay/recommendation),
with two moments built for the hero from its profile (hero_profiles.json):

  1. HP falls fast while the hero's escape (or an escape item) is ready;
  2. a stun while a dispel or escape item is ready.

Nothing is written by hand: the cards are what the app would show, in the
language asked for (advice_i18n at the API edge)."""

from __future__ import annotations

import copy
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"

# Each moment is its own match (the scheduler rightly keeps quiet for a while
# after an urgent card): a quiet match to MATCH_END, then the moment at MOMENT_AT.
MATCH_END = 11 * 60
MOMENT_AT = MATCH_END + 20
MOMENTS = ("fall", "stun")
# Items for the moments by position: what a player of that role usually holds.
ROLE_ITEMS = {
    "carry": ("item_black_king_bar", "item_manta"),
    "mid": ("item_black_king_bar", "item_blink"),
    "offlane": ("item_blink", "item_black_king_bar"),
    "support": ("item_force_staff", "item_glimmer_cape"),
}


def _backend_path() -> None:
    for path in (BACKEND, BACKEND / "scripts"):
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))


def _raw(hero_key: str, ability: str) -> str:
    return f"{hero_key}_" + re.sub(r"[^a-z0-9]+", "_", ability.lower()).strip("_")


def _abilities(hero_key: str, profile: dict[str, Any]) -> dict[str, Any]:
    names = (
        list(profile.get("key_escape_abilities") or [])
        + list(profile.get("key_defensive_abilities") or [])
        + list(profile.get("key_fight_abilities") or [])
    )
    seen: list[str] = []
    for name in names:
        if name not in seen:
            seen.append(name)
    return {
        f"ability{i}": {
            "name": _raw(hero_key, name),
            "level": 2,
            "can_cast": True,
            "passive": False,
            "ability_active": True,
            "cooldown": 0,
            "ultimate": False,
        }
        for i, name in enumerate(seen[:4])
    }


def _ready_items(base: dict[str, Any], names: tuple[str, ...]) -> dict[str, Any]:
    items = copy.deepcopy(base)
    slot = len([k for k in items if k.startswith("slot")])
    for name in names:
        items[f"slot{slot}"] = {
            "name": name,
            "can_cast": True,
            "cooldown": 0,
            "passive": False,
        }
        slot += 1
    return items


def demo_stream(
    hero_key: str, profile: dict[str, Any], role: str, moment: str
) -> list[dict[str, Any]]:
    """The payloads: a quiet match, then one moment, a second apart."""
    _backend_path()
    from simulate_live_gsi import synthetic_stream

    stream = list(synthetic_stream(MATCH_END // 60, (), 6.0)[:-1])
    abilities = _abilities(hero_key, profile)
    extra_items = ROLE_ITEMS.get(role, ROLE_ITEMS["carry"])
    for payload in stream:
        payload["hero"]["name"] = f"npc_dota_hero_{hero_key}"
        payload["hero"]["health_percent"] = 100
        payload["abilities"] = copy.deepcopy(abilities)
    last = stream[-1]

    def at(t: int, **hero: Any) -> dict[str, Any]:
        payload = copy.deepcopy(last)
        payload["map"]["clock_time"] = t
        payload["map"]["game_time"] = t + 90
        payload["items"] = _ready_items(last["items"], extra_items)
        payload["hero"].update({"health_percent": 100, "stunned": False, **hero})
        return payload

    moments = [at(t) for t in range(MATCH_END + 1, MOMENT_AT)]
    if moment == "fall":
        for step, hp in enumerate((100, 82, 64, 47, 38, 38, 38)):
            moments.append(at(MOMENT_AT + step, health_percent=hp))
    elif moment == "stun":
        for step in range(4):
            moments.append(at(MOMENT_AT + step, health_percent=72, stunned=True))
        moments.append(at(MOMENT_AT + 4, health_percent=70))
    else:
        raise ValueError(moment)
    return stream + moments


def cards(
    hero_key: str, profile: dict[str, Any], role: str, lang: str = "uk"
) -> list[dict[str, Any]]:
    """The first card of each moment, as the overlay shows it, with its moment."""
    _backend_path()
    import replay_check
    from simulate_live_gsi import simulate

    found = []
    for moment in MOMENTS:
        replay_check.reset_live_state()
        shown = simulate(demo_stream(hero_key, profile, role, moment), lang, role=role)
        card = next(
            (c for c in shown if isinstance(c.get("clock"), int) and c["clock"] >= MOMENT_AT),
            None,
        )
        if card is not None:
            found.append({**card, "moment": moment})
    return found
