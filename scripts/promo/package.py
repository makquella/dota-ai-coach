"""Build one promo package: pick a topic, write the script, voice it, render
the video, check it. Run from the repository root:

    python -m scripts.promo.package --out promo-out            # the next video
    python -m scripts.promo.package --out promo-out --format coach --no-video

The package directory holds video.mp4, cover.jpg and package.json (the
script, captions per network, sources, the quality report). Nothing is sent
or published here: send.py hands it to the approval step."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import sys
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import build_site  # noqa: E402 - scripts/build_site.py
import news  # noqa: E402
import news_cards  # noqa: E402

from . import quality, render, scenes, script, topics, voice  # noqa: E402


def backend_version() -> str:
    text = (ROOT / "frontend" / "launcher" / "package.json").read_text(encoding="utf-8")
    return json.loads(text)["version"]


def latest_week() -> tuple[dict[str, Any] | None, dict[str, Any] | None, str]:
    posts = news.load_posts()
    if not posts:
        return None, None, ""
    post = posts[-1]
    return (
        post,
        news.summary(post, news.previous_of(post, posts)),
        news.period(post, "uk"),
    )


def build_script(choice: topics.Choice, today: date) -> script.Script | None:
    rng = random.Random(f"{today.isoformat()}:{choice.format}:{choice.topic}")
    if choice.format == "coach":
        from . import coach_demo

        hero = choice.data["hero"]
        cards = coach_demo.cards(hero["key"], hero["profile"], hero["position"])
        return script.coach(hero, cards, rng, backend_version())
    if choice.format == "hero":
        hero = choice.data["hero"]
        return script.hero_tips(hero, news_cards.hero_facts(hero, build_site), rng)
    post, data, period = latest_week()
    if choice.format == "meta" and post and data:
        return script.meta(post, data, period, rng)
    if choice.format == "fact" and post and data:
        return script.fact(post, data, period)
    if choice.format == "release":
        version, notes = choice.data["version"], choice.data["notes"]
        return script.release(version, news_cards.release_points(notes))
    return None


def telegram_caption(item: script.Script) -> str:
    text = item.caption
    return (
        text
        if len(text) <= quality.TELEGRAM_CAPTION_LIMIT
        else text[: quality.TELEGRAM_CAPTION_LIMIT - 1] + "…"
    )


def make(
    out: Path, today: date, forced: str | None, with_video: bool, allow_silent: bool
) -> dict[str, Any]:
    out.mkdir(parents=True, exist_ok=True)
    history = topics.load_history()
    post, _, _ = latest_week()
    heroes = build_site.heroes()
    tried: set[str] = set()
    item = None
    while item is None:
        choice = topics.choose(today, heroes, post, history, forced=forced)
        if choice.format in tried:
            raise SystemExit(f"nothing to make for {choice.format}")
        tried.add(choice.format)
        item = build_script(choice, today)
        if item is None:
            history = [
                *history,
                {"format": choice.format, "topic": choice.topic, "skipped": True},
            ]
            forced = None
    package_id = hashlib.sha256(
        f"{today}:{item.format}:{item.topic}:{item.hook}".encode()
    ).hexdigest()[:16]
    timeline_in = [{"kind": s.kind, "voice": s.voice, "data": s.data} for s in item.scenes]
    voices: list[Path | None] = []
    seconds: list[float | None] = []
    guessed: list[str] = []
    for index, scene in enumerate(item.scenes):
        result = voice.synthesize(scene.voice, out / f"voice-{index}.wav") if with_video else None
        if result is None:
            voices.append(None)
            seconds.append(None)
            continue
        path, words = result
        voices.append(path)
        seconds.append(voice.duration(path))
        guessed += [w for w in words if w not in guessed]
    if not with_video:
        guessed = []
        for scene in item.scenes:
            for word in voice.pronounce.for_voice(scene.voice)[1]:
                if word not in guessed:
                    guessed.append(word)
    timeline = scenes.timeline(timeline_in, seconds)
    total = timeline[-1]["end"]
    package: dict[str, Any] = {
        "id": package_id,
        "created": today.isoformat(),
        "format": item.format,
        "topic": item.topic,
        "hook": item.hook,
        "title": item.title,
        "youtube_title": script.youtube_title(item),
        "caption": item.caption,
        "telegram_caption": telegram_caption(item),
        "link": item.link,
        "seconds": round(total, 2),
        "script": item.to_dict(),
        "pronunciation_guesses": guessed,
        "voice": "piper" if any(v is not None for v in voices) else "none",
    }
    media = None
    if with_video:
        audio = None
        if any(v is not None for v in voices):
            audio = voice.join(
                [
                    (path, scene["end"] - scene["start"])
                    for path, scene in zip(voices, timeline, strict=True)
                ],
                out / "voice.wav",
            )
        assets = render.assets_for(timeline, out)
        seed = int(package_id[:4], 16)
        page_html = scenes.page(item.format, timeline, assets, seed)
        video = render.render(page_html, total, out / "video.mp4", audio, cover=out / "cover.jpg")
        media = render.probe(video)
        package["media"] = media
        for path in [
            *(v for v in voices if v),
            out / "voice.wav",
            *out.glob("render-*.png"),
        ]:
            path.unlink(missing_ok=True)
    package["quality"] = quality.check(package, media, allow_silent=allow_silent)
    (out / "package.json").write_text(
        json.dumps(package, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    return package


def annotate(level: str, message: str) -> None:
    """On GitHub Actions, also as a check annotation: the job log is not
    always at hand, the annotations are (check-runs/<id>/annotations)."""
    if os.environ.get("GITHUB_ACTIONS") == "true":
        clean = message.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
        print(f"::{level} title=Promo quality::{clean}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--format", choices=sorted(topics.WEIGHTS))
    parser.add_argument("--date", type=date.fromisoformat, default=datetime.now(UTC).date())
    parser.add_argument("--no-video", action="store_true", help="the script and captions only")
    parser.add_argument(
        "--allow-silent",
        action="store_true",
        help="no voice model: a silent video is fine",
    )
    parser.add_argument(
        "--record",
        action="store_true",
        help="add the package to data/promo/history.json",
    )
    args = parser.parse_args()
    package = make(args.out, args.date, args.format, not args.no_video, args.allow_silent)
    report = package["quality"]
    print(f"{package['format']} · {package['topic']} · {package['seconds']} s · {package['title']}")
    for line in report["errors"]:
        print(f"  error: {line}")
        annotate("error", line)
    for line in report["warnings"]:
        print(f"  warning: {line}")
        annotate("warning", line)
    if args.record and report["ok"]:
        history = topics.load_history()
        history.append(
            {
                "id": package["id"],
                "date": package["created"],
                "format": package["format"],
                "topic": package["topic"],
                "hook": package["hook"],
            }
        )
        topics.save_history(history)
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
