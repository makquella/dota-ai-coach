"""Profile DTOs through actual SQLite reads, MMR writes and cosmetic actions."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient
from match_fixtures import MATCH_ID, ME
from pydantic import ValidationError

from app.player_api import PLAYER_SERVICE
from app.player_contracts import ProfileResponse
from app.player_profile import add_anchor


def _history() -> None:
    store = PLAYER_SERVICE.store
    store.set_primary(ME, source="manual")
    store.upsert_player(ME, source="manual", persona_name="<b>Profile</b>")
    for index, win in enumerate([True, False, None]):
        store.upsert_match(
            ME,
            MATCH_ID + index,
            source="gsi",
            fields={
                "start_time": 100 + index,
                "duration": 1800,
                "lobby_type": 7,
                "hero_id": 8,
                "hero": "Juggernaut",
                "win": win,
                "kills": 0,
            },
        )


def test_unlinked_and_empty_linked_profile_preserve_nulls_and_known_zero(
    client: TestClient,
) -> None:
    assert client.get("/player/profile").json() == {"profile": None}
    assert client.delete("/player/profile/mmr").json() == {"profile": None}
    PLAYER_SERVICE.store.set_primary(ME, source="manual")
    response = client.get("/player/profile")
    assert response.status_code == 200
    body = response.json()
    assert body == {"profile": PLAYER_SERVICE.profile("en")}
    profile = body["profile"]
    assert profile["rating"] is profile["player"]["name"] is None
    assert profile["stats"] == {
        "app_games": 0,
        "app_wins": 0,
        "app_winrate": None,
        "app_hours": 0.0,
        "all_games": 0,
        "week_games": 0,
    }
    assert profile["level"] == {"level": 1, "xp": 0, "into": 0, "need": 300}
    assert profile["sparks"] == {"balance": 0, "earned": 0, "spent": 0}


@pytest.mark.parametrize("language", ["ru", "en"])
@pytest.mark.parametrize("source", [None, "manual_zero", "manual", "medal"])
def test_complete_profile_matches_service_for_missing_manual_and_medal_rating(
    client: TestClient,
    language: str,
    source: str | None,
) -> None:
    _history()
    if source == "medal":
        PLAYER_SERVICE.store.upsert_player(ME, source="manual", rank_tier=54)
    elif source:
        mmr = 0 if source == "manual_zero" else 3200
        response = client.post(f"/player/profile/mmr?lang={language}", json={"mmr": mmr})
        assert response.status_code == 200
        assert response.json() == {"profile": PLAYER_SERVICE.profile(language)}
    response = client.get(f"/player/profile?lang={language}")
    assert response.status_code == 200
    body = response.json()
    assert body == {"profile": PLAYER_SERVICE.profile(language)}
    profile = body["profile"]
    assert profile["player"]["name"] == "<b>Profile</b>"
    assert profile["stats"]["app_games"] == 3
    assert profile["stats"]["app_wins"] == 1 and profile["stats"]["app_winrate"] == 50
    assert profile["stats"]["app_hours"] == 1.5
    assert profile["shop"] and profile["achievements"] and profile["equipped"]
    if source is None:
        assert profile["rating"] is None
    else:
        graph = profile["rating"]
        assert graph["source"] == ("medal" if source == "medal" else "manual")
        assert graph["games"] == 2
        assert sum("win" in p for p in graph["points"]) == 2
        assert all(p["win"] is not None for p in graph["points"] if "win" in p)
        if source == "manual_zero":
            assert graph["current"] == 0


@pytest.mark.parametrize("language", ["ru", "en"])
def test_rating_estimates_keep_signed_changes_and_negative_extrapolation(
    client: TestClient,
    language: str,
) -> None:
    _history()
    for index in range(2):
        PLAYER_SERVICE.store.upsert_match(ME, MATCH_ID + index, source="gsi", fields={"win": False})
    PLAYER_SERVICE.store.set_meta(f"mmr:{ME}", add_anchor(None, 0, 50))
    response = client.get(f"/player/profile?lang={language}")
    assert response.status_code == 200
    assert response.json() == {"profile": PLAYER_SERVICE.profile(language)}
    rating = response.json()["profile"]["rating"]
    assert rating["current"] == rating["lowest"] == rating["change_20"] == -50
    assert [p["mmr"] for p in rating["points"]] == [0, -25, -50]
    assert "win" not in rating["points"][0] and rating["points"][0]["anchor"] is True
    assert "anchor" not in rating["points"][1]


@pytest.mark.parametrize("language", ["ru", "en"])
def test_mmr_clear_and_cosmetic_mutations_return_the_same_complete_contract(
    client: TestClient,
    language: str,
) -> None:
    _history()
    # Earn the purchase price through real stored games, preserving shop rules.
    for index in range(3, 10):
        PLAYER_SERVICE.store.upsert_match(
            ME,
            MATCH_ID + index,
            source="gsi",
            fields={"start_time": 100 + index, "duration": 1800, "win": True},
        )
    query = f"?lang={language}"
    mmr = client.post(f"/player/profile/mmr{query}", json={"mmr": 3200})
    assert mmr.status_code == 200 and mmr.json()["profile"]["rating"]["current"] == 3200
    cleared = client.delete(f"/player/profile/mmr{query}")
    assert cleared.status_code == 200
    assert cleared.json() == {"profile": PLAYER_SERVICE.profile(language)}
    assert cleared.json()["profile"]["rating"] is None
    for path, item in [("buy", "title_farmer"), ("equip", "title_none")]:
        response = client.post(f"/player/shop/{path}{query}", json={"id": item})
        assert response.status_code == 200
        assert response.json() == {"profile": PLAYER_SERVICE.profile(language)}
        assert response.json()["profile"]["equipped"]["title"] == item
    error = client.post(f"/player/shop/buy{query}", json={"id": "unknown"})
    assert error.status_code == 400
    assert error.json() == {"status": "error", "code": "unknown_item"}


@pytest.mark.parametrize(
    "path,value",
    [
        ("level.level", 0),
        ("level.xp", "100"),
        ("level.into", True),
        ("level.need", -1),
        ("player.name", 1),
        ("player.rank_tier", "54"),
        ("stats.app_games", True),
        ("stats.app_wins", -1),
        ("stats.app_winrate", 101),
        ("stats.app_hours", "1.5"),
        ("stats.app_hours", float("nan")),
        ("stats.app_hours", float("inf")),
        ("stats.app_hours", -0.5),
        ("stats.all_games", 1.5),
        ("stats.week_games", 2**53),
        ("sparks.balance", "0"),
        ("sparks.earned", True),
        ("sparks.spent", -1),
        ("rating.source", "measured"),
        ("rating.current", "3200"),
        ("rating.change_20", True),
        ("rating.games", -1),
        ("rating.points.0.mmr", 1.5),
        ("rating.points.0.t", "100"),
        ("rating.points.0.win", 1),
        ("rating.points.0.match_id", True),
    ],
)
def test_profile_core_rejects_coercion_nonfinite_values_and_invalid_nested_counts(
    client: TestClient,
    path: str,
    value: object,
) -> None:
    _history()
    assert client.post("/player/profile/mmr", json={"mmr": 3200}).status_code == 200
    body = client.get("/player/profile").json()
    target: Any = body["profile"]
    keys = path.split(".")
    for key in keys[:-1]:
        target = target[int(key)] if isinstance(target, list) else target[key]
    target[keys[-1]] = value
    with pytest.raises(ValidationError):
        ProfileResponse.model_validate(body)


def test_profile_nested_extensions_and_optional_point_keys_survive_validation(
    client: TestClient,
) -> None:
    _history()
    assert client.post("/player/profile/mmr", json={"mmr": 3200}).status_code == 200
    body = client.get("/player/profile").json()
    for block in [
        body,
        body["profile"],
        *[body["profile"][key] for key in ["player", "level", "stats", "sparks", "rating"]],
    ]:
        block["future"] = {"keep": [None, 0]}
    body["profile"]["rating"]["points"][0]["future"] = {"keep": True}
    body["profile"]["shop"][0]["future"] = "keep"
    body["profile"]["achievements"][0]["future"] = 1.5
    assert ProfileResponse.model_validate(body).model_dump(exclude_unset=True) == body


def test_openapi_publishes_profile_core_for_all_five_success_endpoints(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()
    for path, method in [
        ("/player/profile", "get"),
        ("/player/profile/mmr", "post"),
        ("/player/profile/mmr", "delete"),
        ("/player/shop/buy", "post"),
        ("/player/shop/equip", "post"),
    ]:
        wire = schema["paths"][path][method]["responses"]["200"]
        assert (
            wire["content"]["application/json"]["schema"]["$ref"]
            == "#/components/schemas/ProfileResponse"
        )
    models = schema["components"]["schemas"]
    assert models["ProfileResponse"]["required"] == ["profile"]
    assert models["ProfileStats"]["properties"]["app_winrate"]["anyOf"][0]["maximum"] == 100
    assert models["ProfileRating"]["properties"]["current"]["minimum"] < 0
    assert models["ProfileRatingPoint"]["required"] == ["t", "mmr"]
