"""finding_history: problems of a review that the player's earlier matches had too."""

from __future__ import annotations

from typing import Any

from app.coach_review import match_facts
from app.finding_history import finding_history


def _analysis(*problems: str, sections: tuple[str, ...] = ("laning", "survival")) -> dict:
    return {
        "improvements": [{"id": p, "section": "survival"} for p in problems],
        "problems": list(problems),
        "sections": {name: {"score": 50} for name in sections},
    }


def _match(match_id: int, start: int, analysis: dict | None) -> dict[str, Any]:
    return {"match_id": match_id, "start_time": start, "analysis": analysis}


def test_a_problem_in_three_matches_in_a_row_is_a_habit():
    current = _match(10, 1000, _analysis("death_streak", "lh10_low"))
    earlier = [
        _match(9, 900, _analysis("death_streak")),
        _match(8, 800, None),  # not analysed: skipped, the row goes on
        _match(7, 700, _analysis("death_streak", "lh10_low")),
        _match(6, 600, _analysis("lh10_low")),
        _match(11, 1100, _analysis("death_streak")),  # played later: ignored
    ]
    history = finding_history(current, current["analysis"], earlier)
    assert history["death_streak"] == {"in_a_row": 3, "in_last": 2, "of": 3}
    # Twice in three earlier games but not in a row, and too few games to count.
    assert "lh10_low" not in history


def test_often_in_the_last_matches_counts_without_a_row():
    current = _match(20, 2000, _analysis("peer_gpm_behind"))
    earlier = [
        _match(19 - i, 1900 - i * 10, _analysis("gpm_low_static" if i % 2 else "death_streak"))
        for i in range(10)
    ]
    history = finding_history(current, current["analysis"], earlier)
    # The peer finding and the static one are one problem (focus_goal.FAMILIES).
    assert history["peer_gpm_behind"] == {"in_a_row": 1, "in_last": 5, "of": 10}


def test_a_match_that_could_not_show_the_problem_does_not_break_the_row():
    lane = {"id": "peer_lh10_behind", "section": "laning"}
    current = _match(5, 500, {**_analysis(), "improvements": [lane], "problems": [lane["id"]]})
    no_laning = _analysis("death_streak", sections=("survival",))  # no last hits at 10:00
    static = _analysis("lh10_low")  # the generic twin, without peers
    earlier = [_match(4, 400, no_laning), _match(3, 300, static), _match(2, 200, static)]
    history = finding_history(current, current["analysis"], earlier)
    assert history["peer_lh10_behind"]["in_a_row"] == 3
    # A match with the laning data and no such problem ends the row.
    earlier.insert(1, _match(35, 350, _analysis("death_streak")))
    assert "peer_lh10_behind" not in finding_history(current, current["analysis"], earlier)


def test_lineup_advice_and_a_single_match_have_no_history():
    current = _match(3, 300, _analysis("draft_better_pick"))
    earlier = [_match(2, 200, _analysis("draft_better_pick"))] * 3
    assert finding_history(current, current["analysis"], earlier) == {}
    assert finding_history(current, None, earlier) == {}


def test_the_coach_hears_about_repeats_and_deaths():
    analysis = {
        "headline": {"hero": "Juggernaut", "win": False, "duration": 1800},
        "improvements": [{"id": "death_streak", "title": "Death streak", "text": "x"}],
        "death_review": {
            "deaths": [
                {
                    "t": 1140,
                    "killer": "Lion",
                    "zone": "jungle",
                    "side": "enemy",
                    "gold": 1400,
                    "warning": {"t": 1125, "action": "Back off now.", "mode": "urgent"},
                    "notes": ["enemy_half", "unspent_gold", "warned"],
                }
            ],
            "notes": {"enemy_half": 1, "unspent_gold": 1, "warned": 1},
        },
    }
    detail = {
        "analysis": analysis,
        "repeats": {"death_streak": {"in_a_row": 3, "in_last": 4, "of": 9}},
    }
    facts = match_facts(detail)
    assert facts is not None
    finding = facts["findings_to_improve"][0]
    assert finding["matches_in_a_row_with_it"] == 3
    assert finding["earlier_matches_with_it"] == "4 of 9"
    deaths = facts["deaths"]
    assert deaths["count"] == 1 and deaths["on_enemy_half"] == 1
    assert deaths["list"][0] == {
        "time": "19:00",
        "killed_by": "Lion",
        "where": "jungle",
        "map_half": "enemy",
        "unspent_gold": 1400,
        "advice_shown_before": "18:45 Back off now.",
    }
    # Counts that did not happen stay out of the facts.
    assert "within_60s_after_respawn" not in deaths
