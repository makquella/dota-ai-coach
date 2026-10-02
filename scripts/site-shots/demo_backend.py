"""
Demo backend for the website screenshots: 20 synthetic matches (the test
fixtures, with varied heroes and numbers), a scripted AI coach whose texts
still pass the real fact check, no network. Run with the backend venv:

    backend/.venv/bin/python scripts/site-shots/demo_backend.py 8777
"""

from __future__ import annotations

import os
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
BACKEND = HERE.parents[1] / "backend"
sys.path[:0] = [str(BACKEND), str(BACKEND / "tests"), str(HERE)]
os.chdir(BACKEND)
os.environ["OPENDOTA_ENABLED"] = "false"

import uvicorn  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from match_fixtures import ME, FakeOpenDota, gsi_match_stream, recent_matches  # noqa: E402

from app.main import app  # noqa: E402
from app.player_api import PLAYER_SERVICE  # noqa: E402
from demo_data import PRO_SKILLS, DemoLLM, friend_row, vary, with_route  # noqa: E402


def main() -> None:
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8777
    recent = recent_matches(20)
    # Played this week (the newest three hours ago, then every nine hours), so
    # Home has a week, "today" and fresh "last matches" like a regular player.
    now = int(time.time())
    for index, row in enumerate(recent):
        row["start_time"] = now - 3 * 3600 - index * 9 * 3600
    fake = FakeOpenDota(matches=vary(recent), recent=recent)
    fake.skill_orders[8] = PRO_SKILLS
    profile = fake.player
    fake.player = lambda account_id: {
        **profile(account_id),
        "persona_name": "farm_or_die",
    }
    # A friend to compare with (made-up account): other heroes, less farm, more deaths.
    friend_id = 900001
    recent_of = fake.recent_matches
    fake.recent_matches = lambda account_id, *, limit=30: (
        [friend_row(row, i) for i, row in enumerate(recent_of(account_id, limit=limit))]
        if account_id == friend_id
        else recent_of(account_id, limit=limit)
    )
    player_of = fake.player
    fake.player = lambda account_id: (
        {**player_of(account_id), "persona_name": "mid_or_feed", "rank_tier": 55}
        if account_id == friend_id
        else player_of(account_id)
    )
    data = Path(tempfile.mkdtemp(prefix="site-shots-"))
    PLAYER_SERVICE.configure(data / "svc", client=fake, auto_start=False, llm=DemoLLM())
    with TestClient(app) as client:
        client.post("/player/link", json={"steam": str(ME)})
        # The first match was also recorded live: the hero's path and deaths on the map.
        first = recent[0]["match_id"]
        for payload in with_route(
            gsi_match_stream(match_id=first, minutes=38, win=False, death_minutes=())
        ):
            client.post("/gsi", json=payload)
        PLAYER_SERVICE.jobs.run_pending(until=float("inf"))
        # DEMO_LOOKS=frame_arcana,banner_aurora,…: the profile wears those looks
        # (owned without sparks, for pictures of the shop's rare items).
        looks = [i for i in os.environ.get("DEMO_LOOKS", "").split(",") if i]
        if looks:
            from app import cosmetics

            state = {"owned": [], "equipped": {}}
            for item_id in looks:
                item = cosmetics.BY_ID[item_id]
                state["owned"].append(item_id)
                state["equipped"][item["kind"]] = item_id
            PLAYER_SERVICE.store.set_meta(f"cosmetics:{ME}", cosmetics.dump(state))
            PLAYER_SERVICE.store.set_meta(f"mmr:{ME}", None)
        client.post("/player/friend", json={"steam": str(friend_id)})
        PLAYER_SERVICE.jobs.run_pending(until=float("inf"))
        for lang in ("ru", "en"):
            for path in (
                f"/player/matches/{first}?lang={lang}",
                f"/player/career?lang={lang}",
            ):
                client.get(path)
                PLAYER_SERVICE.ai_jobs.run_pending(until=float("inf"))
                state = client.get(path).json()["coach"]["state"]
                print(f"{path}: AI review {state}", flush=True)
    print("ready", flush=True)
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")


if __name__ == "__main__":
    main()
