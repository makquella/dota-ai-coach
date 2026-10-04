"""A role locked in the settings by accident (report R-PREDN7: support chosen,
the player on a core): the lane read says so once, and Home can offer «Auto»."""

from app.live_role import MAP_CENTER, LiveRoleTracker, set_role_setting
from app.map_hints import ROLE_CHECK_FROM, ROLE_CHECK_SHOW, RoleTips


def _play_mid(tracker, last_hits_per_min=6, until=4 * 60):
    for clock in range(60, until + 1, 5):
        tracker.observe(
            clock,
            x=MAP_CENTER + 300,
            y=MAP_CENTER + 300,
            last_hits=int(last_hits_per_min * clock / 60),
            team="radiant",
            alive=True,
        )


def test_a_support_setting_on_a_mid_is_a_mismatch():
    set_role_setting("support")
    tracker = LiveRoleTracker()
    _play_mid(tracker)
    role = tracker.role()
    assert role["role"] == "support" and role["source"] == "setting"
    assert role["mismatch"] == "mid"


def test_matching_or_auto_or_a_lost_lane_is_no_mismatch():
    set_role_setting("mid")
    tracker = LiveRoleTracker()
    _play_mid(tracker)
    assert "mismatch" not in tracker.role()
    set_role_setting("auto")
    assert tracker.mismatch() is None
    # A carry with a lost lane reads as a support: never called a mismatch.
    set_role_setting("carry")
    lost = LiveRoleTracker()
    for clock in range(60, 4 * 60 + 1, 5):
        lost.observe(
            clock, x=MAP_CENTER + 5000, y=MAP_CENTER - 5000, last_hits=3, team="radiant", alive=True
        )
    assert lost.mismatch() is None
    # A support with a few last hits in its own safe lane: still a support.
    set_role_setting("support")
    farming = LiveRoleTracker()
    for clock in range(60, 4 * 60 + 1, 5):
        farming.observe(
            clock,
            x=MAP_CENTER + 5000,
            y=MAP_CENTER - 5000,
            last_hits=int(2.5 * clock / 60),
            team="radiant",
            alive=True,
        )
    assert farming.role()["lane"] == "safe" and farming.mismatch() is None


def test_the_tip_is_said_once_after_the_lane_decision():
    tips = RoleTips()
    assert tips.role_mismatch(ROLE_CHECK_FROM - 1, "ru", "support", "mid") is None
    hint = tips.role_mismatch(ROLE_CHECK_FROM, "ru", "support", "mid")
    assert hint["title"] == "Роль в настройках: саппорт" and "как мид" in hint["hint"]
    assert tips.role_mismatch(ROLE_CHECK_FROM + ROLE_CHECK_SHOW, "en", "support", "mid")
    assert tips.role_mismatch(ROLE_CHECK_FROM + ROLE_CHECK_SHOW + 1, "en", "support", "mid") is None


def test_the_overlay_says_it_with_map_timers_off(client):
    from match_fixtures import gsi_match_stream

    client.post("/settings/advice", json={"map_hints": False, "role": "support"})
    seen = None
    for payload in gsi_match_stream(minutes=6, death_minutes=(), step_seconds=5):
        payload["hero"]["xpos"], payload["hero"]["ypos"] = 300, 300  # the mid lane
        payload["player"]["last_hits"] = max(0, payload["map"]["clock_time"]) // 10
        client.post("/gsi", json=payload)
        hint = client.get("/overlay/recommendation?lang=en").json().get("map_hint")
        if hint and hint["id"].startswith("role_mismatch"):
            seen = hint
            break
    assert seen is not None, "no role mismatch tip"
    assert seen["title"] == "Role in the settings: support"
    status = client.get("/gsi/status").json()
    assert status["live_role"]["mismatch"] == "mid"
