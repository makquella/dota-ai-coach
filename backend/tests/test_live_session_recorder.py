from __future__ import annotations

import json

from app.live_session_recorder import LiveSessionRecorder


def test_live_session_recorder_writes_expected_files(tmp_path):
    recorder = LiveSessionRecorder(base_dir=tmp_path)
    start = recorder.start()
    state = {
        "hero": "Juggernaut",
        "minute": 3,
        "game_state": "laning",
        "hp_percent": 42,
        "extra_context": {
            "game_time": 180,
            "alive": True,
            "mana_percent": 55,
            "last_hits": 12,
            "source_type": "live_gsi",
            "context_confidence": "high",
        },
    }
    advice = {
        "new_advice": True,
        "decision_point": "LOW_HP_WARNING",
        "source": "fallback",
        "context_confidence": "high",
        "recommendation": {
            "action": "Use regen or play back until your HP is safer.",
            "reason": "Low lane HP makes trades and last hits risky.",
            "priority": "medium",
        },
    }

    recorder.record_gsi({"hero": {"name": "npc_dota_hero_juggernaut"}}, state)
    recorder.record_advice(advice, state)
    stop = recorder.stop()

    session_dir = tmp_path / start["session_dir"].split("/")[-1]
    assert session_dir.exists()
    raw_path = session_dir / "raw_gsi_states.jsonl"
    advice_path = session_dir / "shown_advice.jsonl"
    metadata_path = session_dir / "metadata.json"
    assert raw_path.exists()
    assert advice_path.exists()
    assert metadata_path.exists()

    raw_entry = json.loads(raw_path.read_text(encoding="utf-8").splitlines()[0])
    advice_entry = json.loads(advice_path.read_text(encoding="utf-8").splitlines()[0])
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

    assert raw_entry["state_summary"]["hero"] == "Juggernaut"
    assert advice_entry["decision_point"] == "LOW_HP_WARNING"
    assert metadata["status"] == "stopped"
    assert stop["gsi_count"] == 1
    assert stop["advice_count"] == 1
