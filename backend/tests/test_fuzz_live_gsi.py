"""Broken GSI never breaks the live path (scripts/fuzz_live_gsi.py, short run)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

from app.gsi_state import normalize_gsi_payload

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "fuzz_live_gsi.py"


def _fuzzer():
    spec = importlib.util.spec_from_file_location("fuzz_live_gsi", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_a_short_fuzz_run_has_no_server_errors(tmp_path):
    assert _fuzzer().run(250, seed=7, data_dir=tmp_path) == []


def test_absurd_numbers_count_as_missing():
    # respawn_seconds 1e308 used to overflow the scheduler's timedelta (HTTP 500).
    state = normalize_gsi_payload(
        {
            "map": {"clock_time": 225, "game_state": "DOTA_GAMERULES_STATE_GAME_IN_PROGRESS"},
            "player": {"gold": 2**40, "last_hits": "12"},
            "hero": {
                "name": "npc_dota_hero_juggernaut",
                "respawn_seconds": 1e308,
                "xpos": float("inf"),
            },
        }
    )
    extra = state["extra_context"]
    assert "respawn_seconds" not in extra and "xpos" not in extra
    assert extra["last_hits"] == 12 and extra["clock_time"] == 225
