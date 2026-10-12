"""News posts: the weekly meta post and the Telegram channel (scripts/news.py).

    python scripts/build_news.py meta                    # a post from OpenDota for today
    python scripts/build_news.py meta --input stats.json --date 2026-10-10
    python scripts/build_news.py telegram-meta [DATE] [--send] [--out DIR]
    python scripts/build_news.py telegram-hero [--date DATE] [--hero NAME] [--send] [--out DIR]
    python scripts/build_news.py telegram-release 0.55.0 [--send] [--out DIR]

Channel posts are a picture card with a caption (scripts/news_cards.py); without
a browser to draw the card the post goes as text. `--out DIR` writes the card
and the caption there instead of printing the caption.
`--send` posts to the channel named by TELEGRAM_CHANNEL (@name or a numeric id)
with the bot token TELEGRAM_BOT_TOKEN (the bot must be an admin of the channel).
Neither value is ever printed. `telegram-hero --send` also records the hero in
data/news/hero-week.json, so the next weeks pick someone else.
After `meta`, run scripts/build_site.py to write the pages.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import news  # noqa: E402 - after the scripts path
import news_cards as cards  # noqa: E402

HERO_WEEK = news.ROOT / "data" / "news" / "hero-week.json"

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


def _telegram() -> tuple[str, str]:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    channel = os.environ.get("TELEGRAM_CHANNEL", "")
    if not token or not channel:
        raise SystemExit("TELEGRAM_BOT_TOKEN and TELEGRAM_CHANNEL are needed to send")
    return token, channel


def send(text: str) -> None:
    token, channel = _telegram()
    body = urllib.parse.urlencode(
        {
            "chat_id": channel,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": "false",
        }
    ).encode()
    _post(
        urllib.request.Request(
            f"https://api.telegram.org/bot{token}/sendMessage", data=body, method="POST"
        )
    )


def send_photo(picture: Path, caption: str) -> None:
    """The card with its caption, as multipart/form-data."""
    token, channel = _telegram()
    boundary = "wardly-card-boundary"
    parts = []
    for name, value in (("chat_id", channel), ("caption", caption), ("parse_mode", "HTML")):
        parts.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode()
        )
    parts.append(
        f'--{boundary}\r\nContent-Disposition: form-data; name="photo"; filename="card.png"\r\n'
        "Content-Type: image/png\r\n\r\n".encode()
        + picture.read_bytes()
        + b"\r\n"
    )
    parts.append(f"--{boundary}--\r\n".encode())
    _post(
        urllib.request.Request(
            f"https://api.telegram.org/bot{token}/sendPhoto",
            data=b"".join(parts),
            method="POST",
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        )
    )


def _post(request: urllib.request.Request) -> None:
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


def publish(
    card: str, caption: str, fallback: str, send_it: bool, out: str | None, name: str
) -> None:
    """Draw the card; send it (or the text post when it cannot be drawn), save it
    with its caption to `out`, or print the caption."""
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(out) / f"{name}.png" if out else Path(tmp) / f"{name}.png"
        if out:
            Path(out).mkdir(parents=True, exist_ok=True)
            (Path(out) / f"{name}.txt").write_text(caption + "\n", encoding="utf-8")
        drawn = (send_it or bool(out)) and cards.render(card, target)
        if send_it:
            if drawn:
                send_photo(target, caption)
            else:
                send(fallback)
        elif out:
            print(f"wrote {target if drawn else 'no card'} and {Path(out) / f'{name}.txt'}")
        else:
            print(caption)


def load_history() -> list[dict]:
    if not HERO_WEEK.exists():
        return []
    return json.loads(HERO_WEEK.read_text(encoding="utf-8")).get("weeks", [])


def save_history(weeks: list[dict]) -> None:
    HERO_WEEK.write_text(
        json.dumps({"weeks": weeks}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    meta = sub.add_parser("meta", help="write this week's meta post")
    meta.add_argument("--input", help="a saved /heroStats response instead of fetching it")
    meta.add_argument("--date", help="the post date (YYYY-MM-DD), today by default")
    tg_meta = sub.add_parser("telegram-meta", help="the channel post of a meta post")
    tg_meta.add_argument("date", nargs="?", help="the post date; the newest post by default")
    tg_hero = sub.add_parser("telegram-hero", help="the hero of the week")
    tg_hero.add_argument("--date", help="today by default; uses the newest meta post up to it")
    tg_hero.add_argument("--hero", help="this hero (a name on the site) instead of the pick")
    tg_release = sub.add_parser("telegram-release", help="the channel post of a release")
    tg_release.add_argument("version")
    for command in (tg_meta, tg_hero, tg_release):
        command.add_argument("--send", action="store_true")
        command.add_argument("--out", help="write the card and its caption to this folder")
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

    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        if args.command == "telegram-meta":
            posts = news.load_posts()
            post = next((p for p in posts if p["date"] == args.date), None) if args.date else None
            post = post or (posts[0] if posts and not args.date else None)
            if post is None:
                raise SystemExit("no such post in data/news/posts")
            data = news.summary(post, news.previous_of(post, posts))
            publish(
                cards.meta_card(post, data, work),
                cards.meta_caption(post, data),
                news.telegram_meta(post, data),
                args.send,
                args.out,
                f"meta-{post['date']}",
            )
        elif args.command == "telegram-hero":
            import build_site as site  # the hero pages' data (needs the backend packages)

            today = args.date or datetime.now(UTC).date().isoformat()
            posts = [p for p in news.load_posts() if p["date"] <= today]
            if not posts:
                raise SystemExit("no meta post up to this date in data/news/posts")
            heroes = site.heroes()
            weeks = load_history()
            if args.hero:
                hero = next((h for h in heroes if h["name"] == args.hero), None)
                if hero is None:
                    raise SystemExit(f"no hero page for {args.hero}")
                found = {h["key"]: h for h in posts[0]["heroes"]}.get(hero["key"])
                matches = sum(h["picks"] for h in posts[0]["heroes"]) / 10 or 1
                stats = (
                    {"win": found["wins"] / found["picks"], "pick": found["picks"] / matches}
                    if found and found["picks"]
                    else None
                )
            else:
                hero, stats = cards.pick_hero(posts[0], heroes, [w["hero"] for w in weeks])
            facts = cards.hero_facts(hero, site)
            caption = cards.hero_caption(hero, facts, stats)
            publish(
                cards.hero_card(hero, facts, stats, work),
                caption,
                caption,
                args.send,
                args.out,
                f"hero-{today}",
            )
            if args.send:
                save_history([*weeks, {"date": today, "hero": hero["name"]}])
        else:
            notes = NOTES / f"v{args.version}.md"
            if not notes.exists():
                raise SystemExit(f"no release notes: {notes.relative_to(news.ROOT)}")
            text = notes.read_text(encoding="utf-8")
            points = cards.release_points(text)
            publish(
                cards.release_card(args.version, points),
                cards.release_caption(args.version, points),
                news.telegram_release(args.version, text),
                args.send,
                args.out,
                f"release-{args.version}",
            )
    return 0


if __name__ == "__main__":
    sys.exit(main())
