"""Map hints (timers + role tips) and the live position they depend on."""

from __future__ import annotations

import copy

from match_fixtures import MATCH_ID, gsi_match_stream

from app.advice_context import MAP_CENTER
from app.live_role import LiveRoleTracker, lane_kind, lane_of, set_role_setting
from app.map_hints import RoleTips, has_observer_ward, map_hint, next_timer, timers
from app.match_memory import MATCH_MEMORY


def _world(x, y):
    return MAP_CENTER + x, MAP_CENTER + y


def test_lanes_on_the_map():
    assert lane_of(*_world(0, 0)) == "mid"
    assert lane_of(*_world(-6500, 3000)) == "top"
    assert lane_of(*_world(4000, -6500)) == "bot"
    assert lane_of(*_world(-7000, -6800)) is None  # Radiant fountain
    assert (lane_kind("bot", "radiant"), lane_kind("top", "radiant")) == ("safe", "off")
    assert (lane_kind("top", "dire"), lane_kind("mid", "dire")) == ("safe", "mid")


def _lane(tracker, point, lh_per_min, team="radiant", until=6 * 60):
    for clock in range(0, until + 1, 5):
        tracker.observe(
            clock,
            x=point[0],
            y=point[1],
            last_hits=int(clock / 60 * lh_per_min),
            team=team,
            alive=True,
        )


def test_the_lane_and_the_farm_decide_the_position():
    safe = _world(4000, -6500)
    for lh, role in ((5, "carry"), (1, "support")):
        tracker = LiveRoleTracker()
        _lane(tracker, safe, lh)
        assert tracker.role() == {"role": role, "source": "lane", "lane": "safe"}
    off = _world(-6500, 3000)
    tracker = LiveRoleTracker()
    _lane(tracker, off, 3)
    assert tracker.role()["role"] == "offlane"
    tracker = LiveRoleTracker()
    _lane(tracker, _world(0, 0), 4, team="dire")
    assert tracker.role()["role"] == "mid"


def test_before_the_lane_is_known_the_prior_is_used_and_the_read_stays():
    tracker = LiveRoleTracker()
    _lane(tracker, _world(4000, -6500), 1, until=120)
    prior = {"role": "carry", "source": "history"}
    assert tracker.role(prior) == prior  # 2:00: too early for the lane
    assert tracker.role() is None
    _lane(tracker, _world(4000, -6500), 1)
    assert tracker.role(prior)["role"] == "support"
    # Farming a lane at 20:00 does not change a support into a carry.
    for clock in range(1200, 1300, 5):
        tracker.observe(clock, x=0, y=0, last_hits=200, team="radiant", alive=True)
    assert tracker.role()["role"] == "support"


def test_the_setting_wins():
    tracker = LiveRoleTracker()
    _lane(tracker, _world(4000, -6500), 6)
    set_role_setting("support")
    assert tracker.role() == {"role": "support", "source": "setting"}
    assert set_role_setting("jungle") == "auto"
    assert tracker.role()["role"] == "carry"


def test_timers_follow_the_patch_data_and_the_role():
    data = timers()
    assert data["patch"] and {e["id"] for e in data["events"]} >= {
        "power_rune",
        "wisdom_shrine",
        "tormentor",
    }
    rune = next_timer(6 * 60 - 15, "mid", "ru")
    assert rune["title"] == "Руна силы" and rune["in_seconds"] == 15 and rune["at_label"] == "6:00"
    assert next_timer(6 * 60 - 15, "carry", "en") is None  # not a carry's business
    assert next_timer(6 * 60 - 25, "mid", "en") is None  # 20 s lead
    shrine = next_timer(14 * 60 - 10, "offlane", "en")
    assert shrine["id"] == "wisdom_shrine@840" and shrine["speak"] is True
    tormentor = next_timer(20 * 60 - 5, "carry", "en")
    assert tormentor["title"] == "Tormentor"
    # Power runes stop being a support's timer after 18:00, a mid's later.
    assert next_timer(20 * 60 + 2 * 60 - 10, "support", "en") is None
    assert next_timer(20 * 60 + 2 * 60 - 10, "mid", "en")["title"] == "Power rune"


def test_every_event_has_both_languages():
    for event in timers()["events"]:
        assert event["en"] and event["ru"] and event["hint_en"] and event["hint_ru"], event["id"]
        assert set(event["roles"]) <= {"carry", "mid", "offlane", "support"}


def test_support_tips_stack_and_wards():
    tips = RoleTips()
    stack = tips.tip(7 * 60 + 45, "support", alive=True, has_ward=True, lang="ru")
    assert stack["title"] == "Застакайте лагерь" and stack["at_label"] == "7:53"
    assert stack["in_seconds"] == 8
    assert tips.tip(7 * 60 + 45, "carry", alive=True, has_ward=False, lang="en") is None
    assert tips.tip(7 * 60 + 45, "support", alive=False, has_ward=False, lang="en") is None
    # No ward: shown for 20 s, then again 5 minutes later.
    assert tips.tip(300, "support", alive=True, has_ward=False, lang="en")["id"] == "wards@300"
    assert tips.tip(315, "support", alive=True, has_ward=False, lang="en") is not None
    assert tips.tip(330, "support", alive=True, has_ward=False, lang="en") is None
    assert tips.tip(600, "support", alive=True, has_ward=False, lang="en")["id"] == "wards@600"
    assert tips.tip(900, "support", alive=True, has_ward=None, lang="en") is None  # unknown
    # A tip wins over a minor timer (runes), a major timer over a tip.
    hint = map_hint(4 * 60 - 10, "support", RoleTips(), alive=True, has_ward=True, lang="en")
    assert hint["kind"] == "timer" and hint["title"] == "Bounty runes"
    hint = map_hint(7 * 60 + 45, "support", RoleTips(), alive=True, has_ward=True, lang="en")
    assert hint["title"] == "Stack a camp"  # not the 8:00 power rune
    hint = map_hint(20 * 60 - 10, "support", RoleTips(), alive=True, has_ward=False, lang="en")
    assert hint["title"] == "Tormentor"
    # Nothing without a role or before the horn.
    assert map_hint(-30, "support", RoleTips(), alive=True, has_ward=False, lang="en") is None
    assert map_hint(600, None, RoleTips(), alive=True, has_ward=False, lang="en") is None


def test_observer_ward_in_the_raw_items():
    assert has_observer_ward({"slot0": {"name": "item_ward_observer"}}) is True
    assert has_observer_ward({"slot1": {"name": "item_ward_dispenser"}}) is True
    assert has_observer_ward({"stash0": {"name": "item_ward_observer"}}) is False
    assert has_observer_ward({"slot0": {"name": "empty"}}) is False
    assert has_observer_ward(None) is None


def _play_until(client, payloads, clock):
    last = None
    for payload in payloads:
        if payload["map"]["clock_time"] > clock:
            break
        client.post("/gsi", json=payload)
        last = client.get("/overlay/recommendation?lang=ru").json()
    return last


def test_live_support_gets_timers_and_tips_through_the_api(client):
    # Juggernaut played as a support: bottom (Radiant safe) lane, 1 LH per minute.
    stream = gsi_match_stream(
        match_id=MATCH_ID, minutes=9, lh_per_minute=1.0, death_minutes=(), positions=True
    )
    for payload in stream:
        payload["items"] = {"slot0": {"name": "item_tango"}}
    answer = _play_until(client, stream, 6 * 60 + 30)
    assert answer["live_role"] == {"role": "support", "source": "lane", "lane": "safe"}
    assert MATCH_MEMORY.role.role()["role"] == "support"
    # 6:45: the wisdom shrine is 15 s away.
    rest = [p for p in stream if p["map"]["clock_time"] > 6 * 60 + 30]
    answer = _play_until(client, rest, 6 * 60 + 45)
    assert answer["map_hint"]["title"] == "Святилище мудрости"
    assert answer["map_hint"]["in_seconds"] == 15
    # 7:45: stack the camp (wins over the 8:00 power rune).
    rest = [p for p in stream if p["map"]["clock_time"] > 6 * 60 + 45]
    answer = _play_until(client, rest, 7 * 60 + 45)
    assert answer["map_hint"]["title"] == "Застакайте лагерь"
    status = client.get("/gsi/status").json()
    assert status["live_role"]["role"] == "support"
    # Hints off in the launcher: no hint, the role is still there.
    client.post("/settings/advice", json={"map_hints": False})
    answer = client.get("/overlay/recommendation").json()
    assert "map_hint" not in answer and answer["live_role"]["role"] == "support"


def test_a_carry_gets_only_shared_timers(client):
    stream = gsi_match_stream(match_id=MATCH_ID, minutes=21, death_minutes=(), positions=True)
    _play_until(client, stream, 6 * 60 + 30)
    assert MATCH_MEMORY.role.role()["role"] == "carry"
    power = [p for p in stream if 6 * 60 + 30 < p["map"]["clock_time"] <= 8 * 60 - 10]
    answer = _play_until(client, power, 8 * 60 - 10)
    assert "map_hint" not in answer  # the 8:00 power rune is not a carry timer
    late = copy.deepcopy([p for p in stream if 8 * 60 - 10 < p["map"]["clock_time"] <= 1190])
    answer = _play_until(client, late, 1190)
    assert answer["map_hint"]["title"] == "Торментор"


def test_a_carry_hero_played_as_support_gets_no_farm_advice(client):
    stream = gsi_match_stream(
        match_id=MATCH_ID, minutes=16, lh_per_minute=1.0, death_minutes=(), positions=True
    )
    shown = set()
    for payload in stream:
        client.post("/gsi", json=payload)
        answer = client.get("/overlay/recommendation").json()
        if answer.get("recommendation") and payload["map"]["clock_time"] > 4 * 60:
            shown.add(answer["decision_point"])
    assert MATCH_MEMORY.role.role()["role"] == "support"
    assert not shown & {"LANING_FARM_CHECK", "FARMING_PHASE_PRESSURE", "SAFE_FARMING"}
