"""The rank medal over time: noted at every sync when it changes."""

from __future__ import annotations

from match_fixtures import ME, FakeOpenDota, opendota_match, recent_matches

from app import rank_history
from app.player_api import PLAYER_SERVICE


def test_a_step_is_noted_only_when_the_medal_changes():
    raw = rank_history.note(None, 52, today="2026-09-01")
    assert rank_history.note(raw, 52, today="2026-09-05") is None
    raw = rank_history.note(raw, 54, today="2026-09-20")
    assert rank_history.note(raw, None) is None and rank_history.note(raw, 99) is None
    summary = rank_history.summary(raw, "ru")
    assert summary["current"] == "Легенда 4" and summary["first"] == "Легенда 2"
    assert summary["change"] == 2 and summary["since"] == "2026-09-01"
    assert [s["date"] for s in summary["steps"]] == ["2026-09-01", "2026-09-20"]
    assert rank_history.summary("not json", "en") is None


def test_sync_notes_the_medal_and_progress_shows_it(client, tmp_path):
    recent = recent_matches(4)
    fake = FakeOpenDota(
        matches={r["match_id"]: opendota_match(match_id=r["match_id"]) for r in recent},
        recent=recent,
    )
    PLAYER_SERVICE.configure(tmp_path / "svc", client=fake, auto_start=False)
    client.post("/player/link", json={"steam": str(ME)})
    PLAYER_SERVICE.jobs.run_pending(until=float("inf"))
    history = client.get("/player/career?lang=en").json()["rank_history"]
    assert history["current"] == "Legend 4" and len(history["steps"]) == 1
    # A second sync with the same medal adds nothing.
    PLAYER_SERVICE.request_sync()
    PLAYER_SERVICE.jobs.run_pending(until=float("inf"))
    assert len(client.get("/player/career?lang=en").json()["rank_history"]["steps"]) == 1
