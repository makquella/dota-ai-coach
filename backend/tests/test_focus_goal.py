"""The focus goal: one recurring problem the player works on, checked per match."""

from __future__ import annotations

import copy

from match_fixtures import MATCH_ID, ME, gsi_match_stream

from app.focus_goal import focus_summary, match_result, new_focus
from app.player_api import PLAYER_SERVICE


def _analysis(problems, sections=("laning", "farm", "survival"), **blocks):
    return {"problems": problems, "sections": {name: {} for name in sections}, **blocks}


def test_twins_count_as_the_same_problem():
    focus = new_focus("deaths_high", "survival", {})
    assert match_result(_analysis(["peer_deaths_more"]), focus) is False
    assert match_result(_analysis(["deaths_high"]), focus) is False
    assert match_result(_analysis(["gpm_low"]), focus) is True
    gpm = new_focus("peer_gpm_behind", "farm", {})
    assert match_result(_analysis(["gpm_low_static"]), gpm) is False


def test_a_match_that_cannot_show_the_problem_does_not_count():
    vision = new_focus("wards_low", "vision", {})
    assert match_result(_analysis([]), vision) is None
    warned = new_focus("died_after_warning", "survival", {})
    assert match_result(_analysis([]), warned) is None
    assert match_result(_analysis([], advice=[{"t": 60}]), warned) is True
    assert match_result(None, warned) is None


def test_problems_beyond_the_visible_list_still_count():
    focus = new_focus("lane_deaths", "laning", {})
    analysis = _analysis(["lane_deaths"])
    analysis["improvements"] = []  # cut by the per-section cap
    assert match_result(analysis, focus) is False
    # Reviews stored before `problems` existed fall back to the visible list.
    old = {"improvements": [{"id": "lane_deaths"}], "sections": {"laning": {}}}
    assert match_result(old, focus) is False


def test_summary_counts_matches_after_the_focus_was_set():
    focus = new_focus("death_streak", "survival", {})
    since = focus["since_ts"]
    matches = [  # newest first
        {"match_id": 4, "start_time": since + 300, "analysis": _analysis([])},
        {"match_id": 3, "start_time": since + 200, "analysis": _analysis([])},
        {"match_id": 2, "start_time": since + 100, "analysis": _analysis(["death_streak"])},
        {"match_id": 1, "start_time": since - 100, "analysis": _analysis([])},
    ]
    summary = focus_summary(focus, matches, "ru")
    assert [r["match_id"] for r in summary["results"]] == [2, 3, 4]
    assert (summary["met"], summary["total"], summary["streak"]) == (2, 3, 2)
    assert summary["title"] == "Серия смертей"


def _play(client, match_id, death_minutes):
    for payload in gsi_match_stream(match_id=match_id, death_minutes=death_minutes):
        client.post("/gsi", json=payload)


def test_focus_end_to_end(client, tmp_path):
    PLAYER_SERVICE.configure(tmp_path / "svc", client=None, auto_start=False)
    _play(client, MATCH_ID, (7, 18, 19, 20))
    career = client.get("/player/career?lang=ru").json()
    assert career["focus"] is None

    bad = client.post("/player/focus", json={"finding_id": "nope"})
    assert bad.status_code == 400 and bad.json()["code"] == "bad_focus"
    focus = client.post("/player/focus?lang=ru", json={"finding_id": "death_streak"}).json()
    assert focus["title"] == "Серия смертей" and focus["total"] == 0

    # Played after the focus was set: one with the death streak, one clean.
    _play(client, MATCH_ID + 1, (7, 18, 19, 20))
    _play(client, MATCH_ID + 2, ())
    focus = client.get("/player/career?lang=ru").json()["focus"]
    assert [r["met"] for r in focus["results"]] == [False, True]
    assert (focus["met"], focus["total"], focus["streak"]) == (1, 2, 1)

    detail = client.get(f"/player/matches/{MATCH_ID + 2}?lang=en").json()
    assert detail["focus"] == {"id": "death_streak", "title": "Death streak", "met": True}
    # The match before the focus is not judged.
    assert client.get(f"/player/matches/{MATCH_ID}?lang=en").json()["focus"] is None

    # The in-game plan reminds of the chosen focus.
    payload = copy.deepcopy(gsi_match_stream(match_id=MATCH_ID + 3, minutes=1)[0])
    payload["map"]["clock_time"] = -30
    client.post("/gsi", json=payload)
    plan = client.get("/overlay/recommendation?lang=ru").json()["game_plan"]
    assert plan["lines"][-1] == "Ваш фокус: серия смертей"

    assert client.delete("/player/focus").json() == {"status": "ok"}
    assert client.get("/player/career").json()["focus"] is None
    assert client.get("/player").json()["account_id"] == ME
