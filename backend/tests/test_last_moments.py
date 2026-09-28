"""The last seconds before a death (live GSI): HP curve, disables, saving items ready."""

from __future__ import annotations

from match_fixtures import gsi_match_stream

from app.analysis_texts import render_finding
from app.death_review import review_deaths
from app.focus_goal import match_result, new_focus
from app.last_moments import LastSeconds, ready_savers
from app.match_facts import facts_from_timeline
from app.match_tracker import MatchTracker
from app.post_match_analysis import analyze_match

BKB = {"name": "item_black_king_bar", "can_cast": True, "cooldown": 0, "passive": False}


def test_ready_savers_only_what_gsi_says_is_castable():
    items = {
        "slot0": BKB,
        "slot1": {"name": "item_blink", "can_cast": False, "cooldown": 3},
        "slot2": {"name": "item_force_staff"},  # no fields: not claimed
        "slot3": {"name": "item_magic_wand", "can_cast": True, "cooldown": 0, "charges": 4},
        "slot4": {"name": "item_bfury", "can_cast": True, "cooldown": 0},
        "stash0": {"name": "item_glimmer_cape", "can_cast": True, "cooldown": 0},
        "slot5": {"name": "item_manta", "cooldown": 0, "passive": False},
    }
    assert ready_savers(items) == ["item_black_king_bar", "item_manta"]
    items["slot3"]["charges"] = 15
    assert "item_magic_wand" in ready_savers(items)


def test_summary_of_the_last_seconds():
    buffer = LastSeconds()
    hero = {"alive": True, "health_percent": 90, "mana_percent": 50}
    for t in range(100, 118):
        buffer.observe(t, hero, {})
    # A burst: 90% at 117, then 40% and 10% while stunned, dead at 120.
    buffer.observe(118, {**hero, "health_percent": 40, "stunned": True}, {"slot0": BKB})
    buffer.observe(118, {**hero, "health_percent": 35, "stunned": True}, {"slot0": BKB})
    buffer.observe(119, {**hero, "health_percent": 10, "stunned": True}, {"slot0": BKB})
    summary = buffer.summarize(120)
    assert summary["hp"][0] == [-20, 90] and summary["hp"][-2:] == [[-2, 35], [-1, 10]]
    assert summary["ready"] == ["item_black_king_bar"]
    assert summary["usable"] == []  # the BKB only while stunned
    assert summary["free_s"] == 3  # 115-117 free, 118-119 stunned
    assert summary["burst_s"] == 3
    assert buffer.summarize(120) is None  # used once per death


def _stream(unused_minutes, stunned_minutes=()):
    """A whole match at 1 s steps; before each death the HP falls with a BKB ready."""
    stream = gsi_match_stream(death_minutes=(7, 18, 24, 28), step_seconds=1)
    for payload in stream:
        t = payload["map"]["clock_time"]
        for minute in (*unused_minutes, *stunned_minutes):
            before = minute * 60 - t
            if 0 < before <= 6:
                payload["hero"]["health_percent"] = 12 * before
                payload["items"]["slot5"] = dict(BKB)
                if minute in stunned_minutes:
                    payload["hero"]["stunned"] = True
    return stream


def _review(stream, tmp_path):
    finished = []
    tracker = MatchTracker(tmp_path / "live.json", on_finished=finished.append)
    for payload in stream:
        tracker.observe(payload)
    timeline = finished[0]
    return timeline, analyze_match(facts_from_timeline(timeline))


def test_deaths_with_a_ready_bkb_become_a_finding(tmp_path):
    stream = _stream(unused_minutes=(18, 24), stunned_minutes=(28,))
    timeline, analysis = _review(stream, tmp_path)
    deaths = {d["t"]: d for d in timeline["deaths"]}
    assert deaths[18 * 60]["last"]["ready"] == ["item_black_king_bar"]
    review = analysis["death_review"]
    assert review["with_last"] == 4 and analysis["last_moments"] == 4
    by_t = {row["t"]: row for row in review["deaths"]}
    assert "saver_ready" in by_t[18 * 60]["notes"]
    assert "saver_ready" not in by_t[28 * 60]["notes"], "stunned the whole time"
    assert "saver_ready" not in by_t[7 * 60]["notes"], "no BKB then"
    finding = next(f for f in analysis["improvements"] if f["id"] == "died_with_saver_ready")
    assert finding["params"]["count"] == 2 and finding["params"]["times"] == [1080, 1440]
    text = render_finding(finding, "ru")["text"]
    assert text.startswith("2 раза вы погибли, когда Black King Bar был готов")
    assert "18:00, 24:00" in text


def test_one_unused_saver_is_not_a_habit_and_old_matches_cannot_show_it(tmp_path):
    _, analysis = _review(_stream(unused_minutes=(18,)), tmp_path)
    assert "died_with_saver_ready" not in analysis["problems"]
    focus = new_focus("died_with_saver_ready", "survival", {})
    assert match_result(analysis, focus) is True
    # A match without the last seconds (OpenDota only, or recorded before 0.8).
    assert match_result({**analysis, "last_moments": 0}, focus) is None


def test_ready_only_while_disabled_is_not_an_unpressed_item():
    # Free seconds without the item, then BKB comes off cooldown on the last
    # tick while the hero is stunned: never ready and usable on the same second.
    buffer = LastSeconds()
    hero = {"alive": True, "health_percent": 60, "mana_percent": 50}
    for t in range(100, 118):
        buffer.observe(t, hero, {})
    buffer.observe(118, {**hero, "health_percent": 20, "stunned": True}, {})
    buffer.observe(119, {**hero, "health_percent": 5, "stunned": True}, {"slot0": BKB})
    last = buffer.summarize(120)
    assert last["ready"] == ["item_black_king_bar"] and last["usable"] == []
    assert last["free_s"] == 3
    review = review_deaths({"deaths_log": [{"t": 120, "last": last}]})
    assert "saver_ready" not in review["deaths"][0]["notes"]

    # Ready on a free second, then stunned: that one was not pressed.
    for t in range(200, 218):
        buffer.observe(t, hero, {"slot0": BKB} if t == 216 else {})
    buffer.observe(218, {**hero, "stunned": True}, {"slot0": BKB})
    last = buffer.summarize(219)
    assert last["usable"] == ["item_black_king_bar"]
    assert (
        "saver_ready"
        in review_deaths({"deaths_log": [{"t": 219, "last": last}]})["deaths"][0]["notes"]
    )
