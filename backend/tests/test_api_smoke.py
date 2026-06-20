from __future__ import annotations


def test_health_returns_ok(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_gsi_status_before_any_gsi_is_idle(client):
    response = client.get("/gsi/status")
    data = response.json()

    assert response.status_code == 200
    assert data["gsi_connected"] is False
    assert data["current_mode"] in {"idle", "waiting"}


def test_overlay_recommendation_before_gsi_is_safe_status(client):
    response = client.get("/overlay/recommendation")
    data = response.json()

    assert response.status_code == 200
    assert data["status"] in {"waiting_for_gsi", "no_advice", "monitoring"}
    assert data["recommendation"] is None


def test_session_recording_endpoints_do_not_crash(client, tmp_path, monkeypatch):
    from app.main import LIVE_SESSION_RECORDER

    monkeypatch.setattr(LIVE_SESSION_RECORDER, "base_dir", tmp_path)

    start = client.post("/session-recording/start").json()
    status = client.get("/session-recording/status").json()
    stop = client.post("/session-recording/stop").json()

    assert start["active"] is True
    assert status["active"] is True
    assert stop["active"] is False
