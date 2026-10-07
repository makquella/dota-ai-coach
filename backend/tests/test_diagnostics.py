"""Problem report: /diagnostics state, recorded errors, key redaction, log pruning."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
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
        "gemini AIzaSyA1234567890abcdefghijklmn and AQ.Zz9TestKeyOnly0000-abcdefg "
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


@pytest.mark.parametrize(
    "endpoint", ["/recommend", "/overlay/recommendation", "/demo/replay-state"]
)
@pytest.mark.parametrize("failure", ["directory", "write"])
def test_recommendation_log_failure_keeps_advice_and_records_diagnostics(
    client: TestClient,
    repo_root: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    endpoint: str,
    failure: str,
) -> None:
    from app import logger

    logs = tmp_path / "recommendation-logs"
    monkeypatch.setattr(logger, "LOGS_DIR", logs)
    if failure == "directory":
        logs.write_text("A file is blocking the log directory.")
    else:
        write_text = Path.write_text

        def fail_log_write(path: Path, text: str, **kwargs: Any) -> int:
            if path.parent == logs:
                raise OSError("No space left on device")
            return write_text(path, text, **kwargs)

        monkeypatch.setattr(Path, "write_text", fail_log_write)

    sample = json.loads(
        (repo_root / "data/gsi_samples/juggernaut_laning_low_hp_warning.json").read_text()
    )
    state_response = client.post("/gsi", json=sample)
    assert state_response.status_code == 200
    state = state_response.json()["state"]
    if endpoint == "/overlay/recommendation":
        response = client.get(endpoint)
    elif endpoint == "/demo/replay-state":
        response = client.post(endpoint, json={"timestamp_seconds": 600, "state": state})
    else:
        response = client.post(endpoint, json=state)

    assert response.status_code == 200
    data = response.json()
    if endpoint == "/recommend":
        assert data["action"] == "Use Blade Fury now and walk out of the fight."
        assert data["priority"] == "medium"
        assert "X-Log-File" not in response.headers
    else:
        overlay = data["overlay"] if endpoint == "/demo/replay-state" else data
        assert overlay["status"] == "advice"
        assert overlay["recommendation"]["action"]
        assert "log_file" not in overlay

    errors = client.get("/diagnostics").json()["errors"]
    assert errors["counts"] == {"recommendation-log": 1}
    assert errors["last"][-1]["scope"] == "recommendation-log"


def test_recommendation_logging_recovers_after_a_temporary_directory_failure(
    client: TestClient,
    repo_root: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app import logger

    logs = tmp_path / "recommendation-logs"
    logs.write_text("Temporarily unavailable")
    monkeypatch.setattr(logger, "LOGS_DIR", logs)
    sample = json.loads(
        (repo_root / "data/gsi_samples/juggernaut_laning_low_hp_warning.json").read_text()
    )
    state = client.post("/gsi", json=sample).json()["state"]
    first = client.post("/recommend", json=state)
    assert first.status_code == 200 and "X-Log-File" not in first.headers

    logs.unlink()
    second = client.post("/recommend", json=state)
    assert second.status_code == 200 and second.json() == first.json()
    entry = json.loads((logs / second.headers["X-Log-File"]).read_text())
    assert entry["output"] == second.json()
    assert client.get("/diagnostics").json()["errors"]["counts"] == {"recommendation-log": 1}


def test_opendota_key_is_not_in_offline_errors():
    import requests

    from app.opendota import OpenDotaClient, OpenDotaError

    key = "00000000-1111-2222-3333-444455556666"

    class _Session:
        def request(self, method, url, params=None, timeout=None):
            query = "&".join(f"{k}={v}" for k, v in params)
            raise requests.ConnectionError(f"Max retries exceeded with url: {url}?{query}")

    client = OpenDotaClient("https://api.example", api_key=key, session=_Session(), min_interval=0)
    with pytest.raises(OpenDotaError) as caught:
        client.player(1)
    assert caught.value.code == "offline"
    assert key not in str(caught.value) and "[key]" in str(caught.value)
    assert key not in diagnostics.redact(f"GET /api/players/1?api_key={key}&x=1")


def test_a_slow_opendota_answer_is_asked_once_more():
    import requests

    from app.opendota import DEFAULT_TIMEOUT_SECONDS, OpenDotaClient, OpenDotaError

    # OpenDota can take half a minute for a player's history on a cold cache.
    assert DEFAULT_TIMEOUT_SECONDS[1] >= 45
    key = "00000000-1111-2222-3333-444455556666"

    class _Slow:
        def __init__(self, timeouts):
            self.timeouts = timeouts
            self.calls = 0

        def request(self, method, url, params=None, timeout=None):
            self.calls += 1
            if self.calls <= self.timeouts:
                raise requests.ReadTimeout(f"Read timed out. url: {url}?api_key={key}")

            class _Response:
                status_code = 200

                def json(self):
                    return {"profile": {"account_id": 1, "personaname": "Me"}}

            return _Response()

    once = _Slow(timeouts=1)
    client = OpenDotaClient("https://api.example", api_key=key, session=once, min_interval=0)
    assert client.player(1)["persona_name"] == "Me"
    assert once.calls == 2

    always = _Slow(timeouts=5)
    client = OpenDotaClient("https://api.example", api_key=key, session=always, min_interval=0)
    with pytest.raises(OpenDotaError) as caught:
        client.player(1)
    assert always.calls == 2
    assert caught.value.code == "offline" and "in time" in str(caught.value)
    assert key not in str(caught.value)


def test_the_report_says_which_match_was_last_recorded(client):
    """Report R-QXW4K6 came the day after a match the app had recorded: the
    report must say so, in counts only."""
    from match_fixtures import gsi_match_stream

    assert client.get("/diagnostics").json()["player"]["last_recorded_match"] is None
    for payload in gsi_match_stream(minutes=12, death_minutes=(7,)):
        client.post("/gsi", json=payload)
    PLAYER_SERVICE.jobs.run_pending(until=float("inf"))
    last = client.get("/diagnostics").json()["player"]["last_recorded_match"]
    assert last["match_id"] == MATCH_ID and last["hero"] == "Juggernaut"
    assert last["samples"] > 10 and last["deaths"] == 1
    assert set(last) >= {"advice", "analysed", "score", "deaths_with_last_seconds"}
    assert str(ME) not in json.dumps(last)
