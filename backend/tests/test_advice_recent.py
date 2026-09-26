from __future__ import annotations

import json


def _post_sample(client, repo_root, name: str) -> None:
    sample = repo_root / "data" / "gsi_samples" / name
    client.post("/gsi", json=json.loads(sample.read_text(encoding="utf-8")))


def test_recent_advice_is_empty_before_any_advice(client):
    response = client.get("/advice/recent")

    assert response.status_code == 200
    assert response.json() == {"items": []}


def test_recent_advice_lists_shown_advice_newest_first(client, repo_root):
    _post_sample(client, repo_root, "calm_farming_antimage.json")
    first = client.get("/overlay/recommendation").json()
    # Bypass anti-spam spacing between the two samples; keep the session history.
    from app.advice_scheduler import ADVICE_SCHEDULER

    ADVICE_SCHEDULER.reset()
    _post_sample(client, repo_root, "low_hp_juggernaut.json")
    second = client.get("/overlay/recommendation").json()

    items = client.get("/advice/recent").json()["items"]

    assert [item["action"] for item in items[:2]] == [
        second["recommendation"]["action"],
        first["recommendation"]["action"],
    ]
    assert items[0]["priority"] == second["recommendation"]["priority"]
    assert items[0]["hero"] == "Juggernaut"


def test_recent_advice_limit_is_clamped(client, repo_root):
    _post_sample(client, repo_root, "calm_farming_antimage.json")
    client.get("/overlay/recommendation")

    assert len(client.get("/advice/recent?limit=0").json()["items"]) == 1
    assert client.get("/advice/recent?limit=500").status_code == 200
