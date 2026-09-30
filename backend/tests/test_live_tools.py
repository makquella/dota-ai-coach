"""Survival advice names the tool that can be pressed right now (app/live_tools.py)."""

from __future__ import annotations

import copy

from match_fixtures import gsi_match_stream

from app.advice_i18n import translate_ru
from app.gsi_state import normalize_gsi_payload
from app.live_tools import (
    death_items_reason,
    disabled_copy,
    hero_tools,
    low_hp_copy,
    regen_items,
)
from app.player_api import PLAYER_SERVICE
from app.recommender import _fallback_text
from app.schemas import GameSituationRequest

READY = {"can_cast": True, "cooldown": 0}
WAND = {"name": "item_magic_wand", "charges": 14, **READY}
FORCE = {"name": "item_force_staff", **READY}
BKB = {"name": "item_black_king_bar", **READY}
MANTA = {"name": "item_manta", **READY}
SALVE = {"name": "item_flask", "charges": 1, **READY}


def _extra(*items, abilities=None, hero="npc_dota_hero_juggernaut", **flags):
    raw = {f"slot{i}": item for i, item in enumerate(items)}
    payload = copy.deepcopy(gsi_match_stream(minutes=20, death_minutes=())[-1])
    payload["items"] = raw
    payload["hero"]["name"] = hero
    if abilities is not None:
        payload["abilities"] = abilities
    return normalize_gsi_payload(payload)["extra_context"] | flags


def test_low_hp_names_an_escape_first_then_a_heal_then_regen():
    action, reason = low_hp_copy(_extra(WAND, FORCE))
    assert action == "Use Force Staff now to get out, then reset HP."
    action, reason = low_hp_copy(_extra(WAND, SALVE))
    assert action == "Use Magic Wand now, then step back."
    assert reason == "Magic Wand has 14 charges: that HP is yours right now."
    action, _ = low_hp_copy(_extra(SALVE))
    assert action == "Step out of enemy range and use Healing Salve."
    # A wand with few charges or a force staff on cooldown is not "ready".
    assert low_hp_copy(_extra({**WAND, "charges": 3}, {**FORCE, "cooldown": 12})) is None
    # No items block in GSI: nothing is claimed.
    assert low_hp_copy({"ready_savers": None}) is None


def test_a_disable_names_what_removes_it_or_gets_out_after_it():
    action, reason = disabled_copy(_extra(BKB, stunned=True))
    assert action == "The moment the disable ends, use Black King Bar."
    # A silence alone does not stop items: dispel it now.
    action, _ = disabled_copy(_extra(MANTA, silenced=True))
    assert action == "Use Manta Style now: it removes the silence."
    assert disabled_copy(_extra(WAND, stunned=True)) is None  # nothing that helps
    assert disabled_copy(_extra(BKB)) is None  # not disabled


def test_regen_needs_a_usable_item():
    assert regen_items({"slot0": {"name": "item_bottle", "charges": 0}}) == []
    assert regen_items({"slot0": {"name": "item_bottle", "charges": 2}}) == ["item_bottle"]
    assert regen_items({}) is None


def _request(extra, hero="Juggernaut"):
    payload = copy.deepcopy(gsi_match_stream(minutes=20, death_minutes=())[-1])
    state = normalize_gsi_payload(payload)
    return GameSituationRequest(**{**state, "hero": hero, "hp_percent": 15, "extra_context": extra})


def test_the_cards_use_the_tools_and_keep_the_plain_text_without_them():
    text = _fallback_text(_request(_extra(WAND)), "retreat_reset")
    assert text["action"] == "Use Magic Wand now, then step back."
    plain = _fallback_text(_request(_extra()), "retreat_reset")
    assert "Magic Wand" not in plain["action"]
    stunned = _fallback_text(_request(_extra(BKB, stunned=True)), "wait_out_disable")
    assert stunned["action"] == "The moment the disable ends, use Black King Bar."
    assert (
        _fallback_text(_request(_extra(stunned=True)), "wait_out_disable")["action"]
        == "Wait out the disable and avoid forcing actions."
    )


def test_the_death_review_says_which_item_was_left_unpressed():
    extra = _extra() | {"death_items": ["item_black_king_bar"]}
    text = _fallback_text(_request(extra), "plan_safer_respawn_route")
    assert text["reason"] == (
        "You died with Black King Bar ready: next time use it at the first big hit."
    )
    assert death_items_reason({"death_items": ["not_an_item"]}) is None


def test_the_last_death_of_the_live_match_names_its_unpressed_item():
    stream = gsi_match_stream(death_minutes=(18,), step_seconds=1, minutes=19)
    for payload in stream:
        before = 18 * 60 - payload["map"]["clock_time"]
        if 0 < before <= 6:
            payload["hero"]["health_percent"] = 12 * before
            payload["items"]["slot5"] = dict(BKB)
        PLAYER_SERVICE.tracker.observe(payload)
        if payload["map"]["clock_time"] == 18 * 60 + 5:
            death = PLAYER_SERVICE.recent_death(18 * 60 + 5)
            assert death["items"] == ["item_black_king_bar"]
    assert PLAYER_SERVICE.recent_death(18 * 60 + 200) is None  # long ago
    assert PLAYER_SERVICE.recent_death(None) is None


def test_the_live_card_through_gsi(client):
    payload = copy.deepcopy(gsi_match_stream(minutes=20, death_minutes=())[-1])
    payload["hero"]["health_percent"] = 12
    payload["hero"]["health"] = 200
    payload["items"]["slot4"] = dict(WAND)
    client.post("/gsi", json=payload)
    body = client.get("/overlay/recommendation").json()
    assert body["recommendation"]["action"] == "Use Magic Wand now, then step back."
    russian = client.get("/overlay/recommendation?lang=ru").json()["recommendation"]
    assert russian["action"] == "Нажмите Magic Wand сейчас и отойдите."


def test_every_new_text_has_russian():
    texts = [
        "Use Force Staff now to get out, then reset HP.",
        "Your HP is low and Force Staff is ready: use it before the next hit, not after.",
        "Use Magic Wand now, then step back.",
        "Magic Wand has 14 charges: that HP is yours right now.",
        "Magic Wand is charged: that HP is yours right now.",
        "Guardian Greaves is ready and heals you at once.",
        "Faerie Fire heals you at once.",
        "Step out of enemy range and use Healing Salve.",
        "Consider: step out of enemy range and use Healing Salve.",
        "Healing Salve heals over time: use it where enemies cannot hit you.",
        "Use Manta Style now: it removes the silence.",
        "A silence does not stop items: get rid of it before the next spell lands.",
        "The moment the disable ends, use Black King Bar.",
        "Black King Bar is ready: the second after a disable is when most kills finish.",
        "You died with Eul's Scepter ready: next time use it at the first big hit.",
    ]
    for text in texts:
        assert translate_ru(text), text


def _feed_until(client, clock, **stream_args):
    for payload in gsi_match_stream(positions=True, **stream_args):
        if payload["map"]["clock_time"] > clock:
            break
        client.post("/gsi", json=payload)


def test_repeated_deaths_in_one_place_are_named(client):
    # The fixture's Radiant Juggernaut dies at 18:00, 19:00 and 20:00 at (3600, 3200):
    # next to the mid lane on the Dire half.
    _feed_until(client, 19 * 60 + 5, death_minutes=(18, 19, 20), minutes=21)
    death = PLAYER_SERVICE.recent_death(19 * 60 + 5)
    assert death["place"] == {"zone": "mid", "side": "enemy", "count": 2, "minutes": 1}
    body = client.get("/overlay/recommendation").json()
    assert body["recommendation"]["action"] == (
        "After respawn, stay away from the mid lane on the enemy side."
    )
    assert body["recommendation"]["reason"] == (
        "2 deaths in the mid lane on the enemy side in 1 minute: "
        "farm somewhere safer until your team is there."
    )
    russian = client.get("/overlay/recommendation?lang=ru").json()["recommendation"]
    assert (
        russian["action"]
        == "После возрождения держитесь подальше от центральной линии на половине врага."
    )
    assert russian["reason"].startswith("2 смерти на центральной линии на половине врага за 1 мин")


def test_one_death_on_the_enemy_half_says_to_farm_your_own():
    extra = _extra() | {"death_place": {"zone": "top", "side": "enemy", "count": 1, "minutes": 1}}
    text = _fallback_text(_request(extra), "plan_safer_respawn_route")
    assert text["reason"] == (
        "You died in the top lane on the enemy side: "
        "farm your own half until your team is with you."
    )
    # One death on your own side: nothing to add.
    own = _extra() | {"death_place": {"zone": "top", "side": "own", "count": 1, "minutes": 1}}
    assert "top lane" not in _fallback_text(_request(own), "plan_safer_respawn_route")["reason"]
    # The unpressed item is the lesson and wins the reason; the place keeps the action.
    both = _extra() | {
        "death_items": ["item_black_king_bar"],
        "death_place": {"zone": "mid", "side": "river", "count": 3, "minutes": 6},
    }
    text = _fallback_text(_request(both), "break_repeated_death_pattern")
    assert text["action"] == "After respawn, stay away from the mid lane by the river."
    assert text["reason"].startswith("You died with Black King Bar ready")


def test_deaths_in_different_places_are_counted():
    from app.advice_i18n import translate_ru
    from app.player_service import _recent_deaths

    assert _recent_deaths([{"t": 600}], 600) is None
    # 20:00 is outside ten minutes of 31:00; 25:00 and 31:00 count.
    assert _recent_deaths([{"t": 1200}, {"t": 1500}, {"t": 1860}], 1860) == {
        "count": 2,
        "minutes": 6,
    }
    extra = _extra() | {
        "death_place": {"zone": "top", "side": "own", "count": 1, "minutes": 1},
        "recent_deaths": {"count": 3, "minutes": 7},
    }
    text = _fallback_text(_request(extra), "break_repeated_death_pattern")
    assert text["action"] == "After respawn, change your route: 3 deaths in the last 7 minutes."
    assert translate_ru(text["action"]) == "После возрождения смените маршрут: 3 смерти за 7 мин."
    # Deaths spread over the game: the total.
    spread = _extra() | {"match_deaths": 4}
    text = _fallback_text(_request(spread), "break_repeated_death_pattern")
    assert text["action"] == "After respawn, change your route: 4 deaths this game."
    assert translate_ru(text["action"]) == "После возрождения смените маршрут: 4 смерти за игру."
    assert (
        "change your route"
        not in _fallback_text(_request(_extra() | {"match_deaths": 1}), "plan_safer_respawn_route")[
            "action"
        ]
    )
    # The same place wins: it says where not to go.
    same = extra | {"death_place": {"zone": "mid", "side": "river", "count": 2, "minutes": 3}}
    assert "stay away" in _fallback_text(_request(same), "break_repeated_death_pattern")["action"]


def test_satanic_is_not_an_instant_heal():
    """Satanic heals through lifesteal while attacking: never «press it and step back»."""
    satanic = {"name": "item_satanic", **READY}
    copy_ = low_hp_copy(_extra(satanic))
    assert copy_ is None or "Satanic" not in copy_[0]
    greaves = {"name": "item_guardian_greaves", **READY}
    assert low_hp_copy(_extra(greaves))[0] == "Use Guardian Greaves now, then step back."


def test_low_hp_while_stunned_waits_for_the_disable_to_end():
    """No item can be pressed while stunned, hexed or muted."""
    for flag in ("stunned", "hexed", "muted"):
        action, _ = low_hp_copy(_extra(FORCE, **{flag: True}))
        assert action == "The moment the disable ends, use Force Staff."
    assert low_hp_copy(_extra(WAND, stunned=True)) is None  # a wand is no way out of a stun


def _ability(name, cooldown=0, level=1, can_cast=True):
    return {
        "name": name,
        "level": level,
        "can_cast": can_cast,
        "passive": False,
        "ability_active": True,
        "cooldown": cooldown,
        "ultimate": False,
    }


BLADE_FURY = {"ability0": _ability("juggernaut_blade_fury")}


def test_the_heros_own_ability_comes_before_items():
    extra = _extra(FORCE, abilities=BLADE_FURY)
    assert low_hp_copy(extra, "Juggernaut") == (
        "Use Blade Fury now and walk out of the fight.",
        "Blade Fury is ready: it buys you the seconds to get away.",
    )
    blink = {"ability0": _ability("antimage_blink")}
    extra = _extra(abilities=blink, hero="npc_dota_hero_antimage")
    assert low_hp_copy(extra, "Anti-Mage")[0] == "Use Blink now to get out, then reset HP."
    # On cooldown or not learned: the items decide.
    on_cooldown = _extra(FORCE, abilities={"ability0": _ability("juggernaut_blade_fury", 7)})
    assert low_hp_copy(on_cooldown, "Juggernaut")[0].startswith("Use Force Staff")
    unlearned = _extra(abilities={"ability0": _ability("juggernaut_blade_fury", level=0)})
    assert low_hp_copy(unlearned, "Juggernaut") is None


def test_hero_tools_reads_cooldowns_and_skips_passives():
    extra = _extra(abilities={"ability0": _ability("antimage_blink", 5.2)})
    tools = hero_tools("Anti-Mage", extra["abilities"])
    assert tools == {"ready": [], "cooldowns": {"Blink": 6}}
    shield = _extra(abilities={"ability0": _ability("medusa_mana_shield")})
    assert hero_tools("Medusa", shield["abilities"])["ready"] == []


def test_a_stun_names_the_ability_to_press_when_it_ends():
    extra = _extra(abilities=BLADE_FURY, stunned=True)
    assert disabled_copy(extra, "Juggernaut")[0] == "The moment the disable ends, use Blade Fury."
    assert low_hp_copy(extra, "Juggernaut")[0] == "The moment the disable ends, use Blade Fury."


def test_the_escape_cooldown_card_says_when_it_is_back():
    extra = _extra(abilities={"ability0": _ability("antimage_blink", 6)}) | {
        "hero_safety_ability": "Blink",
        "hero_safety_kind": "escape",
        "hero_safety_flags": ["escape_on_cooldown"],
    }
    text = _fallback_text(_request(extra, "Anti-Mage"), "respect_hero_safety_window")
    assert text["reason"] == (
        "Blink is back in 6 s: without it, escaping a bad trade or fight is harder."
    )
    assert translate_ru(text["reason"]).startswith("Blink откатится через 6 с")


def test_a_death_with_the_heros_ability_ready_is_named(tmp_path):
    from app.match_tracker import MatchTracker

    tracker = MatchTracker(tmp_path / "live.json", on_finished=lambda _: None)
    # The last payload is the score screen, which closes the recording: left out.
    for payload in gsi_match_stream(death_minutes=(18,), step_seconds=1, minutes=19)[:-1]:
        before = 18 * 60 - payload["map"]["clock_time"]
        payload["abilities"] = BLADE_FURY
        if 0 < before <= 6:
            payload["hero"]["health_percent"] = 12 * before
        tracker.observe(payload)
    usable = tracker.last_death()["usable"]
    assert usable == ["ability:Blade Fury"]
    assert death_items_reason({"death_items": usable}) == (
        "You died with Blade Fury ready: next time use it at the first big hit."
    )


def test_the_ability_texts_have_russian():
    for text in (
        "Use Blade Fury now and walk out of the fight.",
        "Blade Fury is ready: it buys you the seconds to get away.",
        "Blink is back in 6 s: without it, escaping a bad trade or fight is harder.",
        "Blade Fury is back in 9 s: until then, disables and slows are harder to avoid.",
    ):
        assert translate_ru(text), text


def test_only_abilities_that_can_be_pressed_as_a_save_count():
    """A target is needed (Sunder, Phantom Strike) or it is passive (Dispersion)."""
    cases = {
        "Terrorblade": {"ability0": _ability("terrorblade_sunder")},
        "Phantom Assassin": {"ability0": _ability("phantom_assassin_phantom_strike")},
        "Spectre": {"ability0": _ability("spectre_dispersion")},
    }
    for hero, abilities in cases.items():
        extra = _extra(FORCE, abilities=abilities)
        assert hero_tools(hero, extra["abilities"])["ready"] == [], hero
        assert low_hp_copy(extra, hero)[0] == "Use Force Staff now to get out, then reset HP."
    blur = _extra(abilities={"ability0": _ability("phantom_assassin_blur")})
    assert hero_tools("Phantom Assassin", blur["abilities"])["ready"] == [("Blur", "defensive")]


def test_a_mute_stops_items_not_the_heros_spells():
    muted = _extra(FORCE, abilities=BLADE_FURY, muted=True)
    assert low_hp_copy(muted, "Juggernaut")[0] == "Use Blade Fury now and walk out of the fight."
    assert disabled_copy(muted, "Juggernaut")[0] == (
        "Use Blade Fury now: a mute blocks items, not spells."
    )
    # Muted with no spell ready: the items wait for the mute to end.
    muted_items = _extra(FORCE, muted=True)
    assert low_hp_copy(muted_items, "Juggernaut")[0] == (
        "The moment the disable ends, use Force Staff."
    )
    # Silenced: the spell cannot be cast, the items can.
    silenced = _extra(FORCE, abilities=BLADE_FURY, silenced=True)
    assert low_hp_copy(silenced, "Juggernaut")[0] == (
        "Use Force Staff now to get out, then reset HP."
    )
    assert translate_ru("Use Blade Fury now: a mute blocks items, not spells.")


def _stunned_payload(*items):
    payload = copy.deepcopy(gsi_match_stream(minutes=20, death_minutes=())[-1])
    payload["hero"]["stunned"] = True
    payload["items"] = {f"slot{i}": item for i, item in enumerate(items)}
    return payload


def test_a_disable_card_only_when_something_can_be_pressed(client):
    """«Wait out the disable» alone changes nothing: no card for it."""
    client.post("/gsi", json=_stunned_payload())
    body = client.get("/overlay/recommendation").json()
    assert body["decision_point"] == "NO_ADVICE" and body["recommendation"] is None
    client.post("/gsi", json=_stunned_payload(BKB))
    body = client.get("/overlay/recommendation").json()
    assert body["decision_point"] == "DISABLED_STATUS"
    assert body["recommendation"]["action"] == "The moment the disable ends, use Black King Bar."
