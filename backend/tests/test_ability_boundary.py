"""Pure skill labeling, compatibility exports and actual live GSI consumers."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from test_gsi_snapshot import _packet

from app import ability_normalization, gsi_state, skill_tips
from app.gsi_values import MAX_GSI_NUMBER, optional_number


@pytest.mark.parametrize("gsi_first", [False, True])
def test_fresh_import_order_and_skill_labeling_need_no_reverse_gsi_dependency(
    gsi_first: bool,
) -> None:
    script = """
import json, sys
if sys.argv[1] == 'first':
    import app.gsi_state
from app.skill_build import label
assert label('juggernaut_blade_fury', 'juggernaut') == 'Blade Fury'
assert label('nevermore_shadowraze1', 'nevermore') == 'Shadowraze'
if sys.argv[1] != 'first':
    assert 'app.gsi_state' not in sys.modules
    assert 'app.skill_tips' not in sys.modules
from app.gsi_state import normalize_abilities
from app.ability_normalization import normalize_abilities as pure
raw = [{'name': 'antimage_blink', 'level': 2, 'can_cast': False, 'cooldown_remaining': 0}]
assert normalize_abilities(raw) == pure(raw)
print(json.dumps(pure(raw)))
"""
    result = subprocess.run(
        [sys.executable, "-c", script, "first" if gsi_first else "last"],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == [
        {
            "name": "Blink",
            "raw_name": "antimage_blink",
            "level": 2,
            "can_cast": False,
            "cooldown": 0,
        }
    ]


def test_actual_gsi_and_skill_tracker_share_names_without_counting_dota_plus(
    client: TestClient,
) -> None:
    payload = _packet()
    payload["hero"]["level"] = 6
    payload["abilities"] = {
        "ability0": {"name": "juggernaut_blade_fury", "level": 2, "cooldown": 0, "can_cast": False},
        "ability1": {"name": "juggernaut_blade_fury", "level": 2},
        "ability2": {"name": "plus_high_five", "level": 1},
        "ability3": {"name": "juggernaut_omni_slash", "level": 1, "ultimate": True},
    }
    response = client.post("/gsi", json=payload)
    assert response.status_code == 200
    extra = response.json()["state"]["extra_context"]
    assert [row["name"] for row in extra["abilities"]] == ["Blade Fury", "Juggernaut Omni Slash"]
    assert extra["abilities"][0]["cooldown"] == 0 and extra["abilities"][0]["can_cast"] is False
    assert "plus_high_five" not in extra["skills"]["levels"]
    assert extra["skills"]["ultimate"] == {"raw_name": "juggernaut_omni_slash", "level": 1}
    assert client.get("/overlay/recommendation").status_code == 200
    assert (
        client.get("/gsi/debug/latest").json()["latest_normalized_state"]["extra_context"][
            "abilities"
        ]
        == extra["abilities"]
    )


def test_legacy_exports_scalar_bounds_and_returned_rows_remain_detached() -> None:
    assert skill_tips.not_hero_ability is ability_normalization.not_hero_ability
    assert skill_tips.NOT_HERO_ABILITY_PREFIXES == ("plus_",)
    assert gsi_state.MAX_GSI_NUMBER == MAX_GSI_NUMBER
    raw = [{"name": "antimage_blink", "level": "2", "cooldown": "1.5", "ability_active": "false"}]
    first = gsi_state.normalize_abilities(raw)
    assert first == [
        {
            "name": "Blink",
            "raw_name": "antimage_blink",
            "level": 2,
            "cooldown": 1.5,
            "can_cast": False,
        }
    ]
    first[0]["name"] = "changed"
    assert gsi_state.normalize_abilities(raw)[0]["name"] == "Blink"
    assert ability_normalization.normalize_abilities(None) == []
    assert ability_normalization.normalize_abilities([None, {"level": 1}, " "]) == []
    assert optional_number(float("nan")) is None
    assert optional_number(float("inf")) is None
    assert optional_number(MAX_GSI_NUMBER + 1) is None
    assert optional_number("0") == 0 and optional_number("1.5") == 1.5
