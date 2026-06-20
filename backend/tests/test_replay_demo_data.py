from __future__ import annotations

import json


DEMO_FILES = [
    "replay_gsi_like_match_8843382732_pl_20_30.jsonl",
    "replay_gsi_like_match_8843471434_jugg_10_20.jsonl",
]


def _jsonl_rows(path):
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def test_launcher_demo_jsonl_files_exist_and_have_601_states(repo_root):
    for filename in DEMO_FILES:
        path = repo_root / "data" / "match_simulations" / filename
        assert path.exists(), filename
        rows = _jsonl_rows(path)
        assert len(rows) == 601
        assert all(isinstance(row.get("state"), dict) for row in rows)


def test_short_demo_playback_path_does_not_crash(client, repo_root):
    path = repo_root / "data" / "match_simulations" / DEMO_FILES[0]
    rows = _jsonl_rows(path)[:5]

    for row in rows:
        response = client.post(
            "/demo/replay-state",
            json={
                "timestamp_seconds": row["timestamp_seconds"],
                "state": row["state"],
                "simulation_file": str(path),
                "speed": 5,
            },
        )
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


def test_pl_20_30_demo_spacing_stays_useful_without_spam(client, repo_root):
    path = repo_root / "data" / "match_simulations" / DEMO_FILES[0]
    shown = []

    for row in _jsonl_rows(path):
        response = client.post(
            "/demo/replay-state",
            json={
                "timestamp_seconds": row["timestamp_seconds"],
                "state": row["state"],
                "simulation_file": str(path),
                "speed": 5,
            },
        )
        assert response.status_code == 200
        overlay = response.json()["overlay"]
        if overlay.get("new_advice"):
            shown.append(overlay)

    stats = client.get("/overlay/stats").json()
    assert 5 <= len(shown) <= 8
    assert stats["heartbeat_nudge_count"] >= 1
    assert stats["max_game_time_silence_seconds"] <= 180
    for advice in shown[1:]:
        gap = advice["game_time_gap_since_previous_advice"]
        if advice["decision_point"] != "LOW_HP":
            assert gap >= 45
