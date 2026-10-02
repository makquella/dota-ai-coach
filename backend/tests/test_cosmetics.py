"""Profile looks bought with sparks (app/cosmetics.py)."""

from __future__ import annotations

import pytest

from app import cosmetics

NO_TIERS: dict[str, int] = {}


def _state(raw=None):
    return cosmetics.load(raw)


def test_free_items_are_owned_and_worn_by_default():
    state = _state()
    worn = cosmetics.equipped(state, 1, NO_TIERS)
    assert worn == cosmetics.DEFAULTS
    rows = {
        r["id"]: r for r in cosmetics.shop(state, balance=0, level=1, tiers=NO_TIERS, lang="ru")
    }
    assert rows["frame_plain"]["owned"] and rows["frame_plain"]["equipped"]
    assert rows["frame_gold"]["locked"] == "level" and not rows["frame_gold"]["affordable"]
    assert rows["frame_bronze"]["locked"] is None and not rows["frame_bronze"]["affordable"]
    assert rows["frame_champion"]["locked"] == "achievement"
    assert rows["frame_gold"]["name"] == "Золото"


def test_buying_spends_sparks_once_and_wears_the_item():
    state = cosmetics.buy(_state(), "frame_bronze", balance=200, level=1, tiers=NO_TIERS)
    assert state["owned"] == ["frame_bronze"]
    assert cosmetics.equipped(state, 1, NO_TIERS)["frame"] == "frame_bronze"
    assert cosmetics.spent(state) == 150
    with pytest.raises(ValueError, match="owned"):
        cosmetics.buy(state, "frame_bronze", balance=1000, level=1, tiers=NO_TIERS)
    with pytest.raises(ValueError, match="not_enough"):
        cosmetics.buy(state, "frame_silver", balance=100, level=1, tiers=NO_TIERS)
    with pytest.raises(ValueError, match="locked_level"):
        cosmetics.buy(state, "frame_gold", balance=9999, level=4, tiers=NO_TIERS)
    with pytest.raises(ValueError, match="unknown_item"):
        cosmetics.buy(state, "frame_nope", balance=9999, level=99, tiers=NO_TIERS)
    # Back to a free one, then the bought one again.
    state = cosmetics.equip(state, "frame_plain", level=1, tiers=NO_TIERS)
    assert cosmetics.equipped(state, 1, NO_TIERS)["frame"] == "frame_plain"
    with pytest.raises(ValueError, match="not_owned"):
        cosmetics.equip(state, "frame_silver", level=1, tiers=NO_TIERS)


def test_achievement_items_come_with_the_tier():
    tiers = {"app_wins": 3}
    rows = {
        r["id"]: r for r in cosmetics.shop(_state(), balance=0, level=1, tiers=tiers, lang="en")
    }
    assert rows["frame_champion"]["owned"] and rows["frame_champion"]["locked"] is None
    state = cosmetics.equip(_state(), "frame_champion", level=1, tiers=tiers)
    assert cosmetics.equipped(state, 1, tiers)["frame"] == "frame_champion"
    # Lost the tier (history deleted): the frame falls back to the default.
    assert cosmetics.equipped(state, 1, NO_TIERS)["frame"] == "frame_plain"


def test_a_broken_state_is_read_as_empty():
    assert cosmetics.load("{oops") == {"owned": [], "equipped": {}}
    state = cosmetics.load(
        '{"owned": ["frame_bronze", "x", 5], "equipped": {"frame": "banner_dusk"}}'
    )
    assert state == {"owned": ["frame_bronze"], "equipped": {}}


def test_the_shop_through_the_api(client):
    from match_fixtures import ME, FakeOpenDota

    from app.player_api import PLAYER_SERVICE

    PLAYER_SERVICE.configure(PLAYER_SERVICE.data_dir, client=FakeOpenDota(), auto_start=False)
    client.post("/player/link", json={"steam": str(ME)})
    profile = client.get("/player/profile").json()["profile"]
    assert profile["equipped"] == cosmetics.DEFAULTS
    assert len(profile["shop"]) == len(cosmetics.CATALOG)
    # No matches with the app yet: no sparks.
    response = client.post("/player/shop/buy", json={"id": "frame_bronze"})
    assert response.status_code == 400 and response.json()["code"] == "not_enough"
    # Sparks from matches recorded with the app.
    from match_fixtures import gsi_match_stream

    for match_id in range(3):
        for payload in gsi_match_stream(
            match_id=7_000_000_000 + match_id, minutes=21, death_minutes=()
        ):
            client.post("/gsi", json=payload)
    PLAYER_SERVICE.jobs.run_pending(until=float("inf"))
    balance = client.get("/player/profile").json()["profile"]["sparks"]["balance"]
    assert balance >= 120
    body = client.post("/player/shop/buy", json={"id": "title_farmer"}).json()["profile"]
    assert body["equipped"]["title"] == "title_farmer"
    assert body["sparks"]["balance"] == balance - 120
    body = client.post("/player/shop/equip", json={"id": "title_none"}).json()["profile"]
    assert body["equipped"]["title"] == "title_none"
