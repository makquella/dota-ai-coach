"""Match table filters: hero and result, with totals and stats of the filtered set."""

from __future__ import annotations

from match_fixtures import ME, FakeOpenDota, opendota_match, recent_matches

from app.player_api import PLAYER_SERVICE


def _synced(client, tmp_path):
    recent = recent_matches(26)
    PLAYER_SERVICE.configure(tmp_path / "svc", client=FakeOpenDota(recent=recent), auto_start=False)
    client.post("/player/link", json={"steam": str(ME)})
    PLAYER_SERVICE.jobs.run_pending(until=float("inf"))
    return recent


def test_filters_by_hero_and_result(client, tmp_path):
    recent = _synced(client, tmp_path)
    everything = client.get("/player/matches?limit=200").json()
    assert everything["total"] == len(recent) == everything["stats"]["games"]
    heroes = everything["heroes"]
    assert heroes and heroes[0]["games"] >= heroes[-1]["games"]
    assert sum(h["games"] for h in heroes) == len(recent)

    hero = heroes[0]
    by_hero = client.get(f"/player/matches?limit=200&hero_id={hero['hero_id']}").json()
    assert by_hero["total"] == hero["games"] == len(by_hero["items"])
    assert {row["hero_id"] for row in by_hero["items"]} == {hero["hero_id"]}
    assert by_hero["filters"] == {"hero_id": hero["hero_id"], "win": None}

    wins = client.get("/player/matches?limit=200&result=win").json()
    losses = client.get("/player/matches?limit=200&result=loss").json()
    assert all(row["win"] is True for row in wins["items"])
    assert all(row["win"] is False for row in losses["items"])
    assert wins["total"] + losses["total"] == len(recent)
    assert wins["stats"]["winrate"] == 100 and losses["stats"]["winrate"] == 0
    expected = round(100 * wins["total"] / len(recent))
    assert everything["stats"]["winrate"] == expected


def test_unknown_result_means_no_filter(client, tmp_path):
    recent = _synced(client, tmp_path)
    assert client.get("/player/matches?result=draw&limit=200").json()["total"] == len(recent)


def test_progress_for_one_hero(client, tmp_path):
    recent = recent_matches(26)
    matches = {
        r["match_id"]: opendota_match(good=r["radiant_win"], match_id=r["match_id"]) for r in recent
    }
    PLAYER_SERVICE.configure(
        tmp_path / "svc", client=FakeOpenDota(matches=matches, recent=recent), auto_start=False
    )
    client.post("/player/link", json={"steam": str(ME)})
    PLAYER_SERVICE.jobs.run_pending(until=float("inf"))
    everything = client.get("/player/career?lang=ru").json()
    heroes = everything["hero_choices"]
    assert everything["hero_filter"] is None and len(heroes) >= 2
    assert "bracket_winrate" in everything["heroes"][0]  # the career's own hero table stays
    other = heroes[-1]
    one = client.get(f"/player/career?lang=ru&hero_id={other['hero_id']}").json()
    assert one["hero_filter"] == other["hero_id"]
    assert one["matches"] == other["games"] < everything["matches"]
    assert one["coach"] == {"state": "none"}
    assert [h["hero"] for h in one["hero_choices"]] == [h["hero"] for h in heroes]
