"""What works: format multipliers from the published videos' views
(GET /v1/admin/promo on the Worker), written to data/promo/weights.json for
topics.py. A format needs MIN_POSTS videos with numbers before it moves; the
multiplier is its median views over the median of all, bounded in topics.py.

    python -m scripts.promo.weights        # API_URL, API_ADMIN_TOKEN
"""

from __future__ import annotations

import json
import os
import statistics
import urllib.error
import urllib.request
from datetime import UTC, datetime
from typing import Any

from . import send, topics

MIN_POSTS = 3


def multipliers(posts: list[dict[str, Any]]) -> dict[str, float]:
    shown = [
        p for p in posts if p.get("status") in ("scheduled", "published") and p.get("views", 0) > 0
    ]
    if len(shown) < MIN_POSTS:
        return {}
    overall = statistics.median(p["views"] for p in shown) or 1
    out = {}
    for name in topics.WEIGHTS:
        views = [p["views"] for p in shown if p.get("format") == name]
        if len(views) >= MIN_POSTS:
            out[name] = round(statistics.median(views) / overall, 3)
    return out


def fetch(api: str, token: str) -> list[dict[str, Any]]:
    request = urllib.request.Request(
        f"{api}/v1/admin/promo",
        headers={"Authorization": f"Bearer {token}", "User-Agent": send.USER_AGENT},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return list(json.loads(response.read())["posts"])


def main() -> None:
    api, token = (
        os.environ.get("API_URL", "").rstrip("/"),
        os.environ.get("API_ADMIN_TOKEN", ""),
    )
    if not api or not token:
        print("no API_URL / API_ADMIN_TOKEN: weights unchanged")
        return
    try:
        posts = fetch(api, token)
    except (urllib.error.URLError, OSError, ValueError, KeyError) as error:
        # The numbers only tune the rotation: a missed read keeps the old
        # weights and never stops this week's video.
        print(f"weights unchanged: {type(error).__name__}: {error}")
        if os.environ.get("GITHUB_ACTIONS") == "true":
            print(f"::warning title=Promo weights::{type(error).__name__}: {error}")
        return
    found = multipliers(posts)
    topics.WEIGHTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    topics.WEIGHTS_FILE.write_text(
        json.dumps(
            {
                "updated": datetime.now(UTC).date().isoformat(),
                "posts": len(posts),
                "multipliers": found,
            },
            indent=1,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"weights from {len(posts)} posts: {found or 'not enough numbers yet'}")


if __name__ == "__main__":
    main()
