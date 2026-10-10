"""The career's hardest and easiest enemy heroes (lineups of OpenDota matches)."""

from __future__ import annotations

from match_fixtures import ME, FakeOpenDota, opendota_match, recent_matches

from app.career_analysis import opponents
from app.player_api import PLAYER_SERVICE


def _match(win: bool, enemies: list[int]) -> dict:
    return {"win": win, "analysis": {"enemy_heroes": enemies}}


def test_record_against_each_enemy_hero():
    matches = [
        _match(False, [11, 2, 3]),
        _match(False, [11, 2, 4]),
        _match(True, [11, 5, 6]),
        _match(False, [11, 7, 8]),
        _match(True, [2, 9, 10]),
        _match(True, [9, 12, 13]),
        _match(True, [9, 14, 15]),
        _match(None, [11, 9, 1]),  # not finished: not counted
        {"win": True, "analysis": {}},  # no lineup
    ]
    result = opponents(matches)
    assert result["matches"] == 7 and result["min_games"] == 3
    hard = result["hard"]
    assert [r["hero"] for r in hard] == ["Shadow Fiend", "Axe"]  # 1-3, then 1-2
    assert hard[0] == {
        "hero_id": 11,
        "hero": "Shadow Fiend",
        "games": 4,
        "wins": 1,
        "losses": 3,
        "winrate": 25,
    }
    assert [r["hero"] for r in result["easy"]] == ["Mirana"]  # id 9: 3-0
    assert opponents([_match(True, [1])]) is None


def test_progress_lists_the_hardest_opponents(client, tmp_path):
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
    career = client.get("/player/career?lang=uk").json()
    record = career["opponents"]
    # Every fixture match has the same enemy lineup: 12 games against each hero.
    assert record["matches"] == 12
    rows = record["hard"] or record["easy"]
    assert rows and all(r["games"] == 12 for r in rows)
