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
from pathlib import Path

HERE = Path(__file__).resolve().parent
BACKEND = HERE.parents[1] / "backend"
sys.path[:0] = [str(BACKEND), str(BACKEND / "tests"), str(HERE)]
os.chdir(BACKEND)
os.environ["OPENDOTA_ENABLED"] = "false"

import uvicorn  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from match_fixtures import ME, FakeOpenDota, recent_matches  # noqa: E402

from app.main import app  # noqa: E402
from app.player_api import PLAYER_SERVICE  # noqa: E402
from demo_data import DemoLLM, vary  # noqa: E402


def main() -> None:
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8777
    recent = recent_matches(20)
    fake = FakeOpenDota(matches=vary(recent), recent=recent)
    profile = fake.player
    fake.player = lambda account_id: {
        **profile(account_id),
        "persona_name": "farm_or_die",
    }
    data = Path(tempfile.mkdtemp(prefix="site-shots-"))
    PLAYER_SERVICE.configure(data / "svc", client=fake, auto_start=False, llm=DemoLLM())
    with TestClient(app) as client:
        client.post("/player/link", json={"steam": str(ME)})
        PLAYER_SERVICE.jobs.run_pending(until=float("inf"))
        first = recent[0]["match_id"]
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
