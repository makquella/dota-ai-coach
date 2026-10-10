"""«Корисно / не до речі / повторювалося» on the live advice cards of a review:
kept per card on this computer, carried by a history backup, counted per
decision point without any advice text (advice_feedback.py)."""

from __future__ import annotations

import json

from match_fixtures import MATCH_ID, gsi_match_stream

from app import advice_feedback
from app.player_api import PLAYER_SERVICE


def _recorded_match(client) -> list[dict]:
    for payload in gsi_match_stream(death_minutes=(7, 18), win=False, step_seconds=5):
        client.post("/gsi", json=payload)
        client.get("/overlay/recommendation?lang=uk")
    advice = client.get(f"/player/matches/{MATCH_ID}?lang=uk").json()["analysis"]["advice"]
    assert len(advice) >= 2
    return advice


def _rate(client, key, verdict, match_id=MATCH_ID):
    return client.post(
        f"/player/matches/{match_id}/advice-feedback", json={"key": key, "verdict": verdict}
    )


def test_cards_are_rated_kept_and_cleared(client):
    advice = _recorded_match(client)
    first, second = advice[0]["key"], advice[1]["key"]
    assert first == f"{advice[0]['t']}:{advice[0]['dp']}"
    assert _rate(client, first, "useful").json() == {"status": "ok", "feedback": {first: "useful"}}
    _rate(client, second, "repeated")
    detail = client.get(f"/player/matches/{MATCH_ID}?lang=en").json()
    assert detail["advice_feedback"] == {first: "useful", second: "repeated"}
    # Changing and clearing a verdict.
    _rate(client, first, "irrelevant")
    assert _rate(client, second, None).json()["feedback"] == {first: "irrelevant"}
    _rate(client, first, None)
    assert client.get(f"/player/matches/{MATCH_ID}").json()["advice_feedback"] == {}


def test_bad_feedback_and_unknown_matches_are_refused(client):
    advice = _recorded_match(client)
    key = advice[0]["key"]
    assert _rate(client, key, "great").status_code == 400
    assert _rate(client, "not a key", "useful").status_code == 400
    assert _rate(client, key, "useful", match_id=123).status_code == 404


def test_summary_counts_verdicts_per_decision_point_without_text(client):
    advice = _recorded_match(client)
    for item, verdict in zip(advice[:3], ("useful", "repeated", "repeated"), strict=False):
        _rate(client, item["key"], verdict)
    summary = client.get("/player/advice-feedback").json()
    assert summary["matches"] == 1
    assert sum(summary["totals"].values()) == min(3, len(advice))
    assert set(summary["by_decision_point"]) <= {item["dp"] for item in advice}
    report = json.dumps(client.get("/diagnostics").json()["player"]["advice_feedback"])
    assert all(item["action"] not in report for item in advice[:3])


def test_verdicts_travel_with_a_history_backup(client, tmp_path):
    advice = _recorded_match(client)
    _rate(client, advice[0]["key"], "useful")
    backup = client.get("/player/backup").json()
    keys = [row["key"] for row in backup["tables"]["meta"]]
    assert any(key.startswith("advice_feedback:") for key in keys)
    PLAYER_SERVICE.configure(tmp_path / "other", client=None, auto_start=False)
    assert client.post("/player/backup", json=backup).status_code == 200
    detail = client.get(f"/player/matches/{MATCH_ID}").json()
    assert detail["advice_feedback"] == {advice[0]["key"]: "useful"}


def test_stored_garbage_reads_as_no_feedback(client):
    _recorded_match(client)
    account = PLAYER_SERVICE.store.primary_account_id()
    PLAYER_SERVICE.store.set_meta(f"advice_feedback:{account}:{MATCH_ID}", "{broken")
    assert client.get(f"/player/matches/{MATCH_ID}").json()["advice_feedback"] == {}
    PLAYER_SERVICE.store.set_meta(
        f"advice_feedback:{account}:{MATCH_ID}",
        json.dumps({"1:x": "useful", "bad": "useful", "2:y": "?"}),
    )
    assert advice_feedback.load(PLAYER_SERVICE.store, account, MATCH_ID) == {"1:x": "useful"}
    assert advice_feedback.advice_key({"t": True, "dp": "x"}) is None
    assert advice_feedback.advice_key({"t": 5}) is None


def test_mostly_unwanted_advice_is_made_quieter_but_never_safety():
    counts = {
        "SAFE_FARMING": {"useful": 1, "irrelevant": 2, "repeated": 1},
        "ITEM_TIMING": {"useful": 2, "irrelevant": 1, "repeated": 0},
        "LANING_FARM_CHECK": {"useful": 0, "irrelevant": 1, "repeated": 1},  # too few marks
        "LOW_HP": {"useful": 0, "irrelevant": 5, "repeated": 0},
        "DEATH_REVIEW": {"useful": 0, "irrelevant": 0, "repeated": 4},
        "LOW_MANA": {"useful": 0, "irrelevant": 3, "repeated": 0},
    }
    assert advice_feedback.quieter_decisions(counts) == ["SAFE_FARMING"]


def test_the_scheduler_follows_the_marks(client):
    from app.advice_scheduler import ADVICE_SCHEDULER

    advice = _recorded_match(client)
    account = PLAYER_SERVICE.store.primary_account_id()
    marks = {f"{60 * i}:SAFE_FARMING": "irrelevant" for i in range(1, 4)}
    PLAYER_SERVICE.store.set_meta(f"advice_feedback:{account}:1", json.dumps(marks))
    assert client.get("/player/advice-feedback").json()["quieter"] == ["SAFE_FARMING"]
    # Rating any card refreshes the live scheduler.
    _rate(client, advice[0]["key"], "useful")
    assert "SAFE_FARMING" in ADVICE_SCHEDULER.quieter
    career = client.get("/player/career?lang=uk").json()
    assert career["advice_feedback"]["quieter"] == ["SAFE_FARMING"]
    PLAYER_SERVICE.store.set_meta(f"advice_feedback:{account}:1", None)
    _rate(client, advice[0]["key"], None)
    assert ADVICE_SCHEDULER.quieter == frozenset()
