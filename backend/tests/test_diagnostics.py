"""Problem report: /diagnostics state, recorded errors, key redaction, log pruning."""

from __future__ import annotations

import json

import pytest
from match_fixtures import MATCH_ID, ME, FakeOpenDota, opendota_match

from app import diagnostics
from app.coach_llm import CoachLLMError
from app.logger import prune_logs
from app.player_api import PLAYER_SERVICE
from app.player_service import JobQueue


@pytest.fixture(autouse=True)
def _clean_errors():
    diagnostics.clear()
    yield
    diagnostics.clear()


class _FailingLLM:
    label = {"provider": "gemini", "model": "gemini-3.8-flash"}

    def complete(self, messages, **kwargs):
        raise CoachLLMError("invalid_key")

    def check(self):
        pass


def test_diagnostics_reports_state_without_secrets(client, tmp_path):
    PLAYER_SERVICE.configure(tmp_path / "svc", client=None, auto_start=False)
    client.post(
        "/player/ai", json={"provider": "gemini", "api_key": "AIzaSyTESTKEY1234567890abcdefgh"}
    )
    report = client.get("/diagnostics").json()
    assert set(report) >= {"runtime", "config", "gsi", "scheduler", "player", "errors"}
    assert report["player"]["ai"] == {
        "configured": True,
        "provider": "gemini",
        "model": "gemini-3.8-flash",
        "source": "app",
    }
    assert report["gsi"]["gsi_connected"] is False
    assert "AIzaSy" not in json.dumps(report)


def test_background_errors_end_up_in_the_report(client, tmp_path):
    fake = FakeOpenDota(matches={MATCH_ID: opendota_match(good=False)})
    PLAYER_SERVICE.configure(tmp_path / "svc", client=fake, auto_start=False, llm=_FailingLLM())
    client.post("/player/link", json={"steam": str(ME)})
    PLAYER_SERVICE.fetch_match(MATCH_ID, request_parse=False)
    PLAYER_SERVICE.jobs.run_pending(until=float("inf"))
    client.get(f"/player/matches/{MATCH_ID}?lang=ru")
    PLAYER_SERVICE.ai_jobs.run_pending(until=float("inf"))

    report = client.get("/diagnostics").json()
    assert report["errors"]["counts"] == {"coach-ai": 1}
    assert report["errors"]["last"][0]["message"] == "match review: invalid_key"
    assert report["player"]["matches"] == 1
    assert report["player"]["match_sources"] == {"parsed": 1}
    assert list(report["player"]["coach_jobs"].values())[0]["error"] == "invalid_key"


def test_a_crashing_job_is_recorded_and_the_worker_goes_on():
    queue = JobQueue(auto_start=False, name="player-jobs")
    ran = []

    def boom():
        raise RuntimeError("bad data Bearer abcdefghijklmnop123")

    queue.submit("a", boom)
    queue.submit("b", lambda: ran.append("b"))
    assert queue.run_due(until=float("inf")) == 2 and ran == ["b"]
    entry = diagnostics.recent_errors()["last"][-1]
    assert entry["scope"] == "player-jobs"
    assert "abcdefghijklmnop" not in entry["message"] and "[redacted]" in entry["message"]


def test_redact_hides_every_provider_key_format():
    text = (
        "gemini AIzaSyA1234567890abcdefghijklmn and AQ.Ab8RN6IA45YlMUcYlW-JCtqm "
        "groq gsk_1234567890abcdefXYZ openrouter sk-or-v1-1234567890abcdef"
    )
    redacted = diagnostics.redact(text)
    assert redacted.count("[redacted]") == 4
    assert "1234567890" not in redacted


def test_old_recommendation_logs_are_pruned(tmp_path):
    for index in range(12):
        (tmp_path / f"2026-09-{index + 10:02d}T10-00-00_Juggernaut.json").write_text("{}")
    (tmp_path / "notes.txt").write_text("kept")
    assert prune_logs(tmp_path, keep=5) == 7
    names = sorted(path.name for path in tmp_path.glob("*.json"))
    assert len(names) == 5 and names[0].startswith("2026-09-17")
    assert (tmp_path / "notes.txt").exists()
