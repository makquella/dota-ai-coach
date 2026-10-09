"""Match-list contract with actual SQLite filters, paging and legacy wire fields."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient
from match_fixtures import MATCH_ID, ME
from pydantic import ValidationError

from app.player_api import PLAYER_SERVICE
from app.player_contracts import MatchListResponse
from app.player_service import SKIPPED_MODES_META


def _store_matches() -> None:
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
            timeline={"match_id": MATCH_ID + index},
        )


def test_unlinked_and_empty_linked_tables_preserve_distinct_shapes(client: TestClient) -> None:
    unlinked = client.get("/player/matches").json()
    assert unlinked == {"linked": False, "items": [], "total": 0}
    PLAYER_SERVICE.store.set_primary(ME, source="manual")
    body = client.get("/player/matches").json()
    assert body == PLAYER_SERVICE.list_matches()
    assert body["linked"] is True and body["items"] == body["heroes"] == []
    assert body["stats"] == {"games": 0, "wins": 0, "winrate": None, "avg_score": None}
    assert body["skipped"] is None and body["filters"]["hero_id"] is None


@pytest.mark.parametrize(
    "query,args",
    [
        ("limit=2", {"limit": 2}),
        ("limit=2&offset=2", {"limit": 2, "offset": 2}),
        (
            "hero_id=8&result=win&sort=gpm&order=asc",
            {"hero_id": 8, "win": True, "sort": "gpm", "ascending": True},
        ),
        ("hero_id=8&result=loss", {"hero_id": 8, "win": False}),
        ("hero_id=999", {"hero_id": 999}),
        ("sort=kda", {"sort": "kda"}),
        ("sort=invalid&result=draw", {}),
    ],
)
def test_filtered_pages_equal_the_real_service_without_dropping_extensions(
    client: TestClient, query: str, args: dict[str, Any]
) -> None:
    _store_matches()
    response = client.get(f"/player/matches?{query}")
    assert response.status_code == 200
    body = response.json()
    assert body == PLAYER_SERVICE.list_matches(**args)
    assert body["total"] == body["stats"]["games"]
    assert body["heroes"] == [
        {"hero_id": 8, "hero": "Juggernaut", "games": 3},
        {"hero_id": 1, "hero": "Anti-Mage", "games": 1},
    ]


def test_pages_keep_nulls_zero_partial_kda_notes_items_and_skipped_counts(
    client: TestClient,
) -> None:
    _store_matches()
    store = PLAYER_SERVICE.store
    store.set_note(ME, MATCH_ID, "Тест / Test")
    store.upsert_match(ME, MATCH_ID, source=None, fields={"items": '["tango","boots"]'})
    store.set_meta(f"{SKIPPED_MODES_META}:{ME}", '{"count":2,"turbo":1,"of":6}')
    first = client.get("/player/matches?limit=2&order=asc").json()
    second = client.get("/player/matches?limit=2&offset=2&order=asc").json()
    assert [r["match_id"] for r in first["items"] + second["items"]] == list(
        range(MATCH_ID, MATCH_ID + 4)
    )
    assert first["total"] == second["total"] == 4
    row = first["items"][0]
    assert (row["kills"], row["deaths"], row["assists"]) == (0, 4, None)
    assert row["items"] == ["tango", "boots"] and row["note"] == "Тест / Test"
    assert row["sources"] == ["gsi"] and row["has_timeline"] is True
    assert row["has_analysis"] is False and second["items"][0]["win"] is None
    assert first["skipped"] == {"count": 2, "turbo": 1, "of": 6}
    assert first["stats"] == {"games": 4, "wins": 2, "winrate": 67, "avg_score": 70}


@pytest.mark.parametrize(
    "path,value",
    [
        ("linked", "true"),
        ("total", -1),
        ("items.0.match_id", True),
        ("items.0.kills", 1.5),
        ("items.0.win", 1),
        ("items.0.has_timeline", "true"),
        ("stats.games", "4"),
        ("stats.winrate", 101),
        ("filters.ascending", 1),
        ("heroes.0.games", -1),
    ],
)
def test_nested_core_rejects_coercion_and_invalid_counts(
    client: TestClient, path: str, value: object
) -> None:
    _store_matches()
    body = client.get("/player/matches").json()
    target: Any = body
    keys = path.split(".")
    for key in keys[:-1]:
        target = target[int(key)] if isinstance(target, list) else target[key]
    target[keys[-1]] = value
    with pytest.raises(ValidationError):
        MatchListResponse.model_validate(body)


def test_absent_legacy_counters_and_future_nested_extensions_remain_intact(
    client: TestClient,
) -> None:
    _store_matches()
    body = client.get("/player/matches").json()
    del body["items"][0]["kills"]
    body["items"][0]["future"] = {"keep": True}
    body["stats"]["future"] = [None, 0]
    body["filters"]["sort"] = "future_sort"
    body["future"] = {"keep": True}
    assert MatchListResponse.model_validate(body).model_dump(exclude_unset=True) == body


def test_openapi_publishes_list_item_stats_and_filter_contracts(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()
    success = schema["paths"]["/player/matches"]["get"]["responses"]["200"]
    assert (
        success["content"]["application/json"]["schema"]["$ref"]
        == "#/components/schemas/MatchListResponse"
    )
    models = schema["components"]["schemas"]
    assert models["MatchListResponse"]["required"] == ["linked", "items", "total"]
    assert models["MatchListItem"]["properties"]["win"]["anyOf"] == [
        {"type": "boolean"},
        {"type": "null"},
    ]
    assert models["MatchListStats"]["properties"]["winrate"]["anyOf"][0]["maximum"] == 100
