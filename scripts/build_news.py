"""News posts: the weekly meta post and the Telegram channel (scripts/news.py).

    python scripts/build_news.py meta                    # a post from OpenDota for today
    python scripts/build_news.py meta --input stats.json --date 2026-10-10
    python scripts/build_news.py telegram-meta [DATE] [--send]
    python scripts/build_news.py telegram-release 0.55.0 [--send]

`--send` posts to the channel named by TELEGRAM_CHANNEL (@name or a numeric id)
with the bot token TELEGRAM_BOT_TOKEN (the bot must be an admin of the channel);
without it the text is printed. Neither value is ever printed.
After `meta`, run scripts/build_site.py to write the pages.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import news  # noqa: E402 - after the scripts path

HERO_STATS = "https://api.opendota.com/api/heroStats"
NOTES = news.ROOT / "docs" / "release-notes"


def fetch_hero_stats() -> list[dict]:
    request = urllib.request.Request(HERO_STATS, headers={"User-Agent": "Wardly news"})
    with urllib.request.urlopen(request, timeout=60) as response:  # noqa: S310 - fixed https URL
        return json.loads(response.read().decode("utf-8"))


def dump(post: dict) -> str:
    """The post as JSON, one hero per line (a readable weekly diff)."""
    head = {key: value for key, value in post.items() if key != "heroes"}
    lines = [json.dumps(hero, ensure_ascii=False) for hero in post["heroes"]]
    body = json.dumps(head, ensure_ascii=False, indent=1)[:-2]
    return body + ',\n "heroes": [\n  ' + ",\n  ".join(lines) + "\n ]\n}\n"


def write_meta(stats: list[dict], today: date) -> Path:
    post = news.meta_post(stats, today)
    news.POSTS.mkdir(parents=True, exist_ok=True)
    path = news.POSTS / f"{news.slug(post)}.json"
    path.write_text(dump(post), encoding="utf-8")
    # A new hero has no picture yet: the page shows their initials until one is added.
    posts = news.load_posts()
    data = news.summary(post, news.previous_of(post, posts))
    have = {image.stem for image in news.HERO_IMAGES.glob("*.webp")}
    for key in sorted(news.image_keys(data) - have):
        print(f"no picture site/assets/heroes/{key}.webp: the page shows initials")
    return path


def send(text: str) -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    channel = os.environ.get("TELEGRAM_CHANNEL", "")
    if not token or not channel:
        raise SystemExit("TELEGRAM_BOT_TOKEN and TELEGRAM_CHANNEL are needed to send")
    body = urllib.parse.urlencode(
        {
            "chat_id": channel,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": "false",
        }
    ).encode()
    request = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage", data=body, method="POST"
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310 - Telegram API
            answer = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        # The API's own description says why (never the URL: it holds the token).
        detail = json.loads(error.read().decode("utf-8") or "{}").get("description", "")
        raise SystemExit(f"Telegram refused the post: HTTP {error.code} {detail}") from None
    if not answer.get("ok"):
        raise SystemExit(f"Telegram refused the post: {answer.get('description', '')}")
    print("sent to the Telegram channel")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    meta = sub.add_parser("meta", help="write this week's meta post")
    meta.add_argument("--input", help="a saved /heroStats response instead of fetching it")
    meta.add_argument("--date", help="the post date (YYYY-MM-DD), today by default")
    tg_meta = sub.add_parser("telegram-meta", help="the channel text of a meta post")
    tg_meta.add_argument("date", nargs="?", help="the post date; the newest post by default")
    tg_meta.add_argument("--send", action="store_true")
    tg_release = sub.add_parser("telegram-release", help="the channel text of a release")
    tg_release.add_argument("version")
    tg_release.add_argument("--send", action="store_true")
    args = parser.parse_args()

    if args.command == "meta":
        stats = (
            json.loads(Path(args.input).read_text(encoding="utf-8"))
            if args.input
            else fetch_hero_stats()
        )
        today = date.fromisoformat(args.date) if args.date else datetime.now(UTC).date()
        path = write_meta(stats, today)
        print(f"wrote {path.relative_to(news.ROOT)}")
        return 0
    if args.command == "telegram-meta":
        posts = news.load_posts()
        post = next((p for p in posts if p["date"] == args.date), None) if args.date else None
        post = post or (posts[0] if posts and not args.date else None)
        if post is None:
            raise SystemExit("no such post in data/news/posts")
        text = news.telegram_meta(post, news.summary(post, news.previous_of(post, posts)))
    else:
        notes = NOTES / f"v{args.version}.md"
        if not notes.exists():
            raise SystemExit(f"no release notes: {notes.relative_to(news.ROOT)}")
        text = news.telegram_release(args.version, notes.read_text(encoding="utf-8"))
    if args.send:
        send(text)
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
