from __future__ import annotations

import json


SAMPLES = [
    "generic_carry_safe_laning.json",
    "juggernaut_laning_low_hp_warning.json",
    "juggernaut_low_lh_min5.json",
    "dead_buyback_available.json",
]


def _sample(repo_root, name: str) -> dict:
    path = repo_root / "data" / "gsi_samples" / name
    return json.loads(path.read_text(encoding="utf-8"))


def _post_sample(client, repo_root, name: str) -> dict:
    response = client.post("/gsi", json=_sample(repo_root, name))
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert isinstance(data["state"], dict)
    return data["state"]


def test_representative_gsi_samples_parse_without_exceptions(client, repo_root):
    for name in SAMPLES:
        state = _post_sample(client, repo_root, name)
        assert state["hero"]
        assert 0 <= state["hp_percent"] <= 100


def test_low_hp_sample_produces_safety_advice(client, repo_root):
    _post_sample(client, repo_root, "juggernaut_laning_low_hp_warning.json")

    response = client.get("/overlay/recommendation")
    data = response.json()

    assert response.status_code == 200
    assert data["decision_point"] in {"LOW_HP_WARNING", "LOW_HP", "FARMING_PHASE_PRESSURE"}
    assert data["advice_mode"] in {"coaching", "urgent", "status"}


def test_low_farm_sample_produces_laning_or_safe_fallback(client, repo_root):
    _post_sample(client, repo_root, "juggernaut_low_lh_min5.json")

    response = client.get("/overlay/recommendation")
    data = response.json()

    assert response.status_code == 200
    assert data["decision_point"] in {"LANING_FARM_CHECK", "SAFE_FARMING", "SOFT_STATUS"}


def test_dead_buyback_sample_surfaces_conservative_buyback_advice(client, repo_root):
    _post_sample(client, repo_root, "dead_buyback_available.json")

    response = client.get("/overlay/recommendation")
    data = response.json()

    assert response.status_code == 200
    assert data["decision_point"] == "BUYBACK_AVAILABLE"
    assert data["recommendation"] is not None
    assert "Buyback is available" in data["recommendation"]["action"]
