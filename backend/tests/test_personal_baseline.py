"""This match against the player's usual numbers on the same hero."""

from __future__ import annotations

from match_fixtures import MATCH_ID, ME, FakeOpenDota, opendota_match, recent_matches

from app.personal_baseline import personal_baseline
from app.player_api import PLAYER_SERVICE


def _match(match_id, score, gpm, deaths, lh_10=50):
    return {
        "match_id": match_id,
        "hero": "Juggernaut",
        "gpm": gpm,
        "deaths": deaths,
        "lh_10": lh_10,
        "analysis": {"headline": {"score": score}},
    }


def test_better_worse_and_as_usual():
    others = [_match(i, 60, 500, 6) for i in range(1, 5)]
    result = personal_baseline(_match(99, 80, 510, 3), others)
    tones = {m["key"]: (m["delta"], m["tone"]) for m in result["metrics"]}
    assert tones == {
        "score": (20.0, "good"),
        "gpm": (10.0, "same"),
        "lh_10": (0.0, "same"),
        "deaths": (-3.0, "good"),
    }
    assert result["games"] == 4
    worse = personal_baseline(_match(99, 40, 380, 9), others)
    assert {m["key"]: m["tone"] for m in worse["metrics"]}["deaths"] == "bad"


def test_no_baseline_without_enough_other_games():
    others = [_match(i, 60, 500, 6) for i in range(1, 3)]
    assert personal_baseline(_match(99, 80, 510, 3), others) is None
    # The match itself is never part of its own baseline.
    assert personal_baseline(_match(1, 80, 510, 3), [*others, _match(1, 80, 510, 3)]) is None
    empty = [{"match_id": i, "gpm": None, "deaths": None} for i in range(1, 6)]
    assert personal_baseline(_match(99, 80, 510, 3), empty) is None


def test_match_review_carries_the_baseline(client, tmp_path):
    recent = recent_matches(12)
    fake = FakeOpenDota(
        matches={
            row["match_id"]: opendota_match(good=row["radiant_win"], match_id=row["match_id"])
            for row in recent
        },
        recent=recent,
    )
    PLAYER_SERVICE.configure(tmp_path / "svc", client=fake, auto_start=False)
    client.post("/player/link", json={"steam": str(ME)})
    PLAYER_SERVICE.jobs.run_pending(until=float("inf"))
    detail = client.get(f"/player/matches/{MATCH_ID}?lang=ru").json()
    baseline = detail["baseline"]
    assert baseline["hero"] == "Juggernaut" and baseline["games"] >= 3
    assert {m["key"] for m in baseline["metrics"]} >= {"score", "gpm", "deaths"}
