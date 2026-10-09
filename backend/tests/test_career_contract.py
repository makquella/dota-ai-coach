"""Progress response contract through actual SQLite history/filter/analysis reads."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from match_fixtures import MATCH_ID, ME
from pydantic import ValidationError
from test_coach_ai import _reviewed_match

from app.player_api import PLAYER_SERVICE
from app.player_contracts import CareerResponse


def _history() -> None:
    store = PLAYER_SERVICE.store
    store.set_primary(ME, source="manual")
    for index, fields in enumerate(
        [
            {"hero_id": 8, "hero": "Juggernaut", "win": True, "kills": 0, "deaths": 4, "gpm": 500},
            {"hero_id": 8, "hero": "Juggernaut", "win": False, "kills": 7, "assists": 0},
            {"hero_id": 1, "hero": "Anti-Mage", "win": None, "kills": None, "gpm": 500},
            {"hero_id": 8, "hero": "Juggernaut", "win": True, "gpm": 300, "score": 70},
        ]
    ):
        store.upsert_match(
            ME,
            MATCH_ID + index,
            source="gsi",
            fields={"start_time": 100 + index, "duration": 1800, **fields},
        )


def test_unlinked_and_empty_linked_progress_keep_distinct_wire_shapes(client: TestClient) -> None:
    assert client.get("/player/career").json() == {"linked": False}
    PLAYER_SERVICE.store.set_primary(ME, source="manual")
    response = client.get("/player/career")
    assert response.status_code == 200
    body = response.json()
    assert body == PLAYER_SERVICE.career("en")
    assert body["matches"] == body["analyzed"] == body["wins"] == body["losses"] == 0
    assert body["winrate"] is body["streak"] is None
    assert body["heroes"] == body["hero_choices"] == body["series"] == []


@pytest.mark.parametrize("language", ["ru", "en"])
@pytest.mark.parametrize("hero", [None, 8, 999])
def test_filtered_progress_equals_real_service_with_all_nested_extensions(
    client: TestClient,
    language: str,
    hero: int | None,
) -> None:
    _history()
    query = f"lang={language}" + (f"&hero_id={hero}" if hero is not None else "")
    response = client.get(f"/player/career?{query}")
    assert response.status_code == 200
    body = response.json()
    assert body == PLAYER_SERVICE.career(language, hero_id=hero)
    assert body["hero_filter"] == hero
    assert body["hero_choices"] == [
        {"hero_id": 8, "hero": "Juggernaut", "games": 3},
        {"hero_id": 1, "hero": "Anti-Mage", "games": 1},
    ]
    assert body["matches"] == (4 if hero is None else 3 if hero == 8 else 0)
    assert body["coach"] == {"state": "off" if hero is None else "none"}
    assert ("questions" in body) is (hero is None)


@pytest.mark.parametrize("language", ["ru", "en"])
def test_parsed_progress_keeps_analysis_and_nested_extensions(
    client: TestClient,
    tmp_path: Path,
    language: str,
) -> None:
    service = _reviewed_match(client, tmp_path, None)
    response = client.get(f"/player/career?lang={language}")
    assert response.status_code == 200
    body = response.json()
    assert body == service.career(language)
    assert body["matches"] == body["analyzed"] == 1
    assert body["series"][0]["match_id"] == MATCH_ID
    assert body["hero_choices"][0]["hero_id"] == 8
    assert body["averages"]["gpm"] == 390
    assert body["coach"] == {"state": "off"}


def test_unknown_results_and_partial_averages_do_not_turn_into_losses_or_zero(
    client: TestClient,
) -> None:
    _history()
    body = client.get("/player/career").json()
    assert (body["matches"], body["wins"], body["losses"], body["winrate"]) == (4, 2, 1, 67)
    assert body["averages"]["kills"] == 3.5 and body["averages"]["assists"] == 0
    assert body["averages"]["deaths"] == 4
    unknown = client.get("/player/career?hero_id=1").json()
    assert (unknown["matches"], unknown["wins"], unknown["losses"]) == (1, 0, 0)
    assert unknown["winrate"] is unknown["streak"] is unknown["averages"]["kda"] is None
    assert unknown["heroes"][0]["winrate"] is unknown["series"][0]["win"] is None


@pytest.mark.parametrize(
    "path,value",
    [
        ("linked", 1),
        ("matches", "4"),
        ("analyzed", True),
        ("wins", -1),
        ("losses", 1.5),
        ("winrate", 101),
        ("streak.win", "true"),
        ("streak.length", -1),
        ("heroes.0.hero_id", "8"),
        ("heroes.0.matches", True),
        ("heroes.0.winrate", -1),
        ("hero_choices.0.games", "3"),
        ("series.0.match_id", True),
        ("series.0.win", 0),
    ],
)
def test_progress_core_rejects_coercion_and_invalid_nested_counts(
    client: TestClient,
    path: str,
    value: object,
) -> None:
    _history()
    body = client.get("/player/career").json()
    target: Any = body
    keys = path.split(".")
    for key in keys[:-1]:
        target = target[int(key)] if isinstance(target, list) else target[key]
    target[keys[-1]] = value
    with pytest.raises(ValidationError):
        CareerResponse.model_validate(body)


def test_unset_optional_fields_and_future_extensions_are_preserved(client: TestClient) -> None:
    _history()
    body = client.get("/player/career").json()
    del body["hero_filter"]
    body["future"] = {"keep": [None, 0]}
    body["heroes"][0]["future"] = {"keep": True}
    body["series"][0]["future"] = [None, 0]
    body["streak"]["future"] = "keep"
    body["averages"]["future"] = 1.5
    assert CareerResponse.model_validate(body).model_dump(exclude_unset=True) == body


def test_openapi_publishes_progress_hero_streak_and_series_contracts(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()
    wire = schema["paths"]["/player/career"]["get"]["responses"]["200"]
    assert (
        wire["content"]["application/json"]["schema"]["$ref"]
        == "#/components/schemas/CareerResponse"
    )
    models = schema["components"]["schemas"]
    assert models["CareerResponse"]["required"] == ["linked"]
    assert models["CareerStreak"]["properties"]["win"] == {"type": "boolean", "title": "Win"}
    assert models["CareerHero"]["properties"]["winrate"]["anyOf"][0]["maximum"] == 100
    assert models["CareerSeriesItem"]["properties"]["win"]["anyOf"] == [
        {"type": "boolean"},
        {"type": "null"},
    ]
