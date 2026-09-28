"""The public part of Progress: numbers, heroes and advice, nothing that identifies anyone."""

from __future__ import annotations

import json

from match_fixtures import ME, ME_STEAM64, FakeOpenDota, opendota_match, recent_matches

from app.player_api import PLAYER_SERVICE
from app.share_progress import public_progress


def _synced(client, tmp_path, count=14):
    recent = recent_matches(count)
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
    return recent


def test_progress_payload_has_the_numbers_and_nothing_personal(client, tmp_path):
    recent = _synced(client, tmp_path)
    answer = client.get("/player/career/share?lang=ru")
    assert answer.status_code == 200
    progress = answer.json()["progress"]
    career = client.get("/player/career?lang=ru").json()
    assert progress["kind"] == "progress" and progress["lang"] == "ru"
    assert progress["matches"] == career["matches"] == 14
    assert (progress["wins"], progress["losses"]) == (career["wins"], career["losses"])
    assert progress["rank"] == "Легенда"
    assert progress["period"]["from"] <= progress["period"]["to"]
    assert progress["heroes"][0] == {
        "hero": "Juggernaut",
        "hero_key": "juggernaut",
        "matches": 13,
        "winrate": career["heroes"][0]["winrate"],
    }
    assert [t["key"] for t in progress["trend"]] == ["score", "winrate", "gpm", "lh_10", "deaths"]
    assert progress["problems"][0]["title"] == career["recurring"][0]["title"]
    assert progress["problems"][0]["drill"]
    assert "drill" not in progress["strengths"][0]
    text = json.dumps(progress, ensure_ascii=False)
    # No match ids, account, Steam ID or nicknames.
    for secret in [str(ME), ME_STEAM64, "Player 1"] + [str(r["match_id"]) for r in recent]:
        assert secret not in text
    assert "coach" not in progress and "focus" not in progress


def test_focus_and_coach_only_when_there():
    career = {
        "linked": True,
        "analyzed": 3,
        "matches": 3,
        "focus": {"title": "Deaths in lane", "met": 2, "total": 3, "results": [{"match_id": 5}]},
        "coach": {
            "state": "ready",
            "review": {"summary": "Farm is steady; lane deaths cost games."},
        },
    }
    shared = public_progress(career, "en", with_coach=True)
    assert shared["focus"] == {"title": "Deaths in lane", "met": 2, "total": 3}
    assert shared["coach"].startswith("Farm is steady")
    assert "coach" not in public_progress(career, "en", with_coach=False)
    assert public_progress({"linked": True, "analyzed": 0}, "en", with_coach=True) is None


def test_no_progress_to_share_before_a_review(client, tmp_path):
    PLAYER_SERVICE.configure(tmp_path / "empty", client=None, auto_start=False)
    answer = client.get("/player/career/share")
    assert answer.status_code == 404 and answer.json()["code"] == "no_progress"
