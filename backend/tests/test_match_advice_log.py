"""The post-match review lists the live advice shown during that match."""

from __future__ import annotations

from match_fixtures import MATCH_ID, gsi_match_stream

from app.match_tracker import MAX_ADVICE_NOTES, MatchTracker


def test_live_advice_is_kept_for_the_review(client):
    stream = gsi_match_stream(death_minutes=(7, 18, 19, 20), win=False, step_seconds=5)
    for payload in stream:
        client.post("/gsi", json=payload)
        client.get("/overlay/recommendation?lang=ru")  # the overlay asks every tick
    detail_ru = client.get(f"/player/matches/{MATCH_ID}?lang=ru").json()
    advice = detail_ru["analysis"]["advice"]
    assert advice, "no live advice recorded"
    times = [item["t"] for item in advice]
    assert times == sorted(times) and all(t >= 0 for t in times)
    assert {item["mode"] for item in advice} <= {"urgent", "coaching", "status"}
    # Stored in English, rendered in the review's language.
    detail_en = client.get(f"/player/matches/{MATCH_ID}?lang=en").json()
    first_en = detail_en["analysis"]["advice"][0]["action"]
    assert first_en and all(ord(c) < 128 for c in first_en)
    assert any(any("а" <= c.lower() <= "я" for c in item["action"]) for item in advice)


def test_notes_need_a_match_and_are_capped(tmp_path):
    tracker = MatchTracker(tmp_path / "live.json")
    tracker.note_advice(100, "LOW_HP", "Back off.", "Low HP.", "urgent")  # no match yet
    assert tracker.current() is None
    for payload in gsi_match_stream(minutes=1, step_seconds=30)[:3]:
        tracker.observe(payload)
    for index in range(MAX_ADVICE_NOTES + 10):
        tracker.note_advice(60 + index, "SAFE_FARMING", f"Tip {index}", "", "coaching")
    tracker.note_advice(-30, "LOW_HP", "Before the horn", "", "urgent")
    assert len(tracker._current["advice"]) == MAX_ADVICE_NOTES


def test_deaths_right_after_urgent_advice_become_a_finding():
    from app.advice_follow import analyze_advice_follow
    from app.analysis_texts import render_finding

    facts = {
        "advice_log": [
            {
                "t": 400,
                "mode": "urgent",
                "action": "Leave the wave now and reset HP before rejoining.",
            },
            {
                "t": 900,
                "mode": "coaching",
                "action": "Recover farm through the safest wave-and-camp route.",
            },
            {"t": 1100, "mode": "urgent", "action": "Reset HP before showing on another lane."},
            {"t": 1500, "mode": "urgent", "action": "Reset HP before showing on another lane."},
        ],
        "deaths_log": [{"t": 415}, {"t": 905}, {"t": 1120}, {"t": 1600}],
    }
    block, findings = analyze_advice_follow(facts)
    assert block["urgent"] == 3
    assert [item["death_t"] for item in block["ignored"]] == [415, 1120]
    assert findings[0]["id"] == "died_after_warning"
    assert findings[0]["params"] == {"count": 2, "urgent": 3, "t": 400, "window": 30}
    text = render_finding(findings[0], "ru")["text"]
    assert text.startswith(
        "2 раза вы погибли в течение 30 с после срочной подсказки (первый раз — 6:40)"
    )
    # One ignored warning is not a pattern.
    one = {**facts, "deaths_log": [{"t": 415}]}
    assert analyze_advice_follow(one)[1] == []
    assert analyze_advice_follow({"deaths_log": [{"t": 1}]}) == (None, [])


def test_one_death_answers_only_one_warning():
    from app.advice_follow import analyze_advice_follow

    facts = {
        "advice_log": [
            {"t": 600, "mode": "urgent", "action": "Back off now"},
            {"t": 610, "mode": "urgent", "action": "Reset HP"},
        ],
        "deaths_log": [{"t": 620}],
    }
    block, findings = analyze_advice_follow(facts)
    assert [item["death_t"] for item in block["ignored"]] == [620]
    assert findings == []
