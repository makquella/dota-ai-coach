"""Live GSI positions are world coordinates (centre 0); advice context uses absolute ones.

Before the conversion every Dire player was "deep on the enemy side, high risk"
wherever they stood, and Radiant players were always "safe side".
"""

from __future__ import annotations

import pytest

from app.advice_context import MAP_CENTER
from app.gsi_state import update_latest_gsi


def _payload(team: str, x: float, y: float) -> dict:
    return {
        "provider": {"name": "Dota 2", "appid": 570},
        "map": {
            "matchid": "8012345678",
            "game_state": "DOTA_GAMERULES_STATE_GAME_IN_PROGRESS",
            "clock_time": 900,
            "game_time": 990,
        },
        "player": {"team_name": team, "last_hits": 80, "denies": 5, "gold": 900, "gpm": 480},
        "hero": {
            "name": "npc_dota_hero_juggernaut",
            "level": 12,
            "alive": True,
            "health": 1200,
            "max_health": 1400,
            "health_percent": 86,
            "mana": 300,
            "max_mana": 400,
            "mana_percent": 75,
            "xpos": x,
            "ypos": y,
        },
    }


def _zone(team: str, x: float, y: float) -> tuple[str, str]:
    extra = update_latest_gsi(_payload(team, x, y))["state"]["extra_context"]
    return extra["position_zone"], extra["position_risk"]


@pytest.mark.parametrize(
    ("team", "x", "y", "zone", "risk"),
    [
        # In their own base.
        ("radiant", -6500, -6200, "safe_side", "low"),
        ("dire", 6600, 6100, "safe_side", "low"),
        # Deep in the other team's base.
        ("radiant", 6200, 6000, "deep_enemy_side", "high"),
        ("dire", -6200, -6000, "deep_enemy_side", "high"),
        # A Dire hero near the middle of the map is not "deep on the enemy side".
        ("dire", 2800, 2400, "river_or_mid", "medium"),
        # A Radiant hero in the top lane is not "safe side".
        ("radiant", -3300, 2700, "lane_area", "medium"),
    ],
)
def test_live_positions_map_to_the_right_zone(team, x, y, zone, risk):
    assert _zone(team, x, y) == (zone, risk)


def test_live_position_is_stored_in_absolute_coordinates():
    extra = update_latest_gsi(_payload("radiant", -1000, 250.5))["state"]["extra_context"]
    assert extra["xpos"] == MAP_CENTER - 1000
    assert extra["ypos"] == MAP_CENTER + 250.5
