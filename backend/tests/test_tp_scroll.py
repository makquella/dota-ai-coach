"""Live reminder to carry a TP scroll (tp_tracker.py -> post_laning_carry_tp)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

from match_fixtures import gsi_match_stream

from app.tp_tracker import TpTracker, has_teleport

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "simulate_live_gsi.py"


def test_teleport_slots():
    assert has_teleport({"slot0": {"name": "item_tango"}, "teleport0": {"name": "item_tpscroll"}})
    assert has_teleport({"slot0": {"name": "item_tango"}, "teleport0": {"name": "empty"}}) is False
    assert has_teleport({"slot2": {"name": "item_travel_boots"}, "teleport0": {"name": "empty"}})
    assert has_teleport({"stash0": {"name": "item_tpscroll"}}) is False
    assert has_teleport(None) is None and has_teleport({}) is None


def test_tracker_waits_a_minute_after_minute_ten_and_clears_on_purchase():
    tracker = TpTracker()
    tracker.observe(300, False, True)
    tracker.observe(590, False, True)
    assert tracker.signal() is None  # before 10:00
    tracker.observe(660, False, True)
    assert tracker.signal() == {"seconds": 360, "minutes": 6}
    tracker.observe(670, False, False)
    assert tracker.signal() is None  # dead: nothing to say now
    tracker.observe(700, True, True)
    tracker.observe(740, False, True)
    tracker.observe(780, False, True)
    assert tracker.signal() is None  # missing only 40 s
    tracker.observe(801, None, True)  # items unknown: no change
    assert tracker.signal() == {"seconds": 61, "minutes": 1}
    tracker.observe(500, False, True)  # clock jumped back: count again
    tracker.observe(640, False, True)
    assert tracker.signal() == {"seconds": 140, "minutes": 2}


def _stream(tp_until: int | None):
    stream = gsi_match_stream(minutes=17, death_minutes=(), step_seconds=1)
    for payload in stream:
        t = payload["map"]["clock_time"]
        has = tp_until is None or t < tp_until
        payload["items"]["teleport0"] = {"name": "item_tpscroll" if has else "empty"}
    return stream


def _simulate(stream):
    spec = importlib.util.spec_from_file_location("simulate_live_gsi", SCRIPT)
    script = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(script)
    return script.simulate(stream, "ru")


def test_overlay_reminds_once_the_tp_is_gone():
    cards = _simulate(_stream(12 * 60))
    tp = [c for c in cards if c["action"].startswith("Держите свиток телепортации")]
    assert len(tp) == 1
    assert 13 * 60 <= tp[0]["clock"] < 17 * 60
    assert "свитка телепортации уже" in tp[0]["reason"]


def test_no_reminder_while_the_tp_is_there():
    cards = _simulate(_stream(None))
    assert not [c for c in cards if "телепортации" in c["action"]]
