"""0.50: the match table shows each match's final inventory (the `items` column)."""

from __future__ import annotations

import sqlite3

from match_fixtures import ME, FakeOpenDota, gsi_match_stream, opendota_match, recent_matches

from app.match_facts import facts_from_opendota, facts_from_timeline
from app.match_tracker import MatchTracker, _inventory
from app.opendota import trim_match
from app.player_api import PLAYER_SERVICE
from app.player_store import _SCHEMA, PlayerStore


def test_the_tracker_keeps_the_last_inventory(tmp_path):
    finished = []
    tracker = MatchTracker(tmp_path / "live.json", on_finished=finished.append)
    for payload in gsi_match_stream():
        tracker.observe(payload)
    timeline = finished[0]
    expected = ["item_tango", "item_power_treads", "item_bfury", "item_manta"]
    assert timeline["final"]["inventory"] == expected
    assert facts_from_timeline(timeline)["inventory"] == expected
    # The six inventory slots only, in slot order; no items block → unknown.
    items = {
        "slot1": {"name": "item_bfury"},
        "slot0": {"name": "empty"},
        "slot6": {"name": "item_tango"},
        "stash0": {"name": "item_clarity"},
    }
    assert _inventory(items) == ["item_bfury"]
    assert _inventory({}) is None


def test_opendota_inventory_is_the_six_slots():
    match = opendota_match(good=True)
    me = next(p for p in match["players"] if p.get("account_id") == ME)
    me.update({"item_1": 44, "backpack_0": "tango"})
    facts = facts_from_opendota(trim_match(match, ME))
    assert facts["inventory"] == ["bfury", 44]  # a backpack item is not on the bar


def _synced(client, tmp_path, *, ids: bool):
    recent = recent_matches(4)
    matches = {}
    for row in recent:
        match = opendota_match(good=True, match_id=row["match_id"])
        if ids:  # as OpenDota sends them: numbers, named by the item constants
            me = next(p for p in match["players"] if p.get("account_id") == ME)
            me.update({"item_0": 145, "item_1": 44})
        matches[row["match_id"]] = match
    PLAYER_SERVICE.configure(
        tmp_path / "svc", client=FakeOpenDota(matches=matches, recent=recent), auto_start=False
    )
    client.post("/player/link", json={"steam": str(ME)})
    PLAYER_SERVICE.jobs.run_pending(until=float("inf"))
    return client.get("/player/matches?limit=50").json()["items"]


def test_the_table_carries_the_items_of_reviewed_matches(client, tmp_path):
    rows = _synced(client, tmp_path, ids=True)
    reviewed = [row for row in rows if row["has_analysis"]]
    assert reviewed and all(row["items"] == ["bfury", "tango"] for row in reviewed)
    # A match only listed (no full fetch): nothing known, no icons.
    assert all(row["items"] is None for row in rows if not row["has_analysis"])


def test_stored_reviews_get_their_items_when_the_table_is_read(client, tmp_path):
    rows = _synced(client, tmp_path, ids=False)
    store = PLAYER_SERVICE.store
    reviewed = [row["match_id"] for row in rows if row["has_analysis"]]
    with store._lock:  # as a database written before 0.50
        store._conn.execute("UPDATE matches SET items = NULL")
        store._conn.commit()
    rows = client.get("/player/matches?limit=50").json()["items"]
    assert [row["items"] for row in rows if row["match_id"] in reviewed] == [["bfury"]] * len(
        reviewed
    )
    # The review's header reads them too, also for a row the table has not filled.
    with store._lock:
        store._conn.execute("UPDATE matches SET items = NULL")
        store._conn.commit()
    detail = client.get(f"/player/matches/{reviewed[0]}?lang=ru").json()
    assert detail["summary"]["items"] == ["bfury"]


def test_an_old_database_gets_the_column(tmp_path):
    path = tmp_path / "coach.sqlite3"
    old = _SCHEMA.replace("    items TEXT,\n", "")
    assert old != _SCHEMA
    with sqlite3.connect(path) as conn:
        conn.executescript(old)
        conn.execute(
            "INSERT INTO matches (account_id, match_id, hero_id, score) VALUES (?, ?, ?, ?)",
            (ME, 7, 8, 60),
        )
    store = PlayerStore(path)
    rows = store.list_matches(ME)
    assert rows[0]["match_id"] == 7 and rows[0]["items"] is None
    store.upsert_match(ME, 7, source="gsi", fields={"items": '["bfury"]'})
    assert store.list_matches(ME)[0]["items"] == ["bfury"]
    assert store.get_match(ME, 7)["items"] == ["bfury"]
    store.close()
    PlayerStore(path).close()  # opening it again changes nothing
