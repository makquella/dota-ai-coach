"""Build the remaining four films and a hash-bound six-video schedule manifest."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from . import beta, beta_shorts, experiments, send

CREATIVES = ("sven", "juggernaut", "terrorblade")
FOLLOWUPS = {"juggernaut": "juggernaut-review", "terrorblade": "terrorblade-feedback"}


def manifest(out: Path) -> dict:
    entries = []
    for day, creative in zip((16, 17, 18), CREATIVES, strict=True):
        at = datetime(2026, 10, day, 17, tzinfo=ZoneInfo("Europe/Kyiv"))
        for language in beta.LANGUAGES:
            folder = out / creative / language
            video = json.loads((folder / "package.json").read_text())
            speech = json.loads((folder / "speech-check.json").read_text())
            assert video["kind"] == beta.KIND and not video["draft"]
            assert video["language"] == speech["language"] == language
            assert video["layout"]["ok"] and speech["ok"]
            assert video["quality"]["ok"] and video["quality"]["fully_decoded"]
            assert (
                beta.digest(folder / "video.mp4") == video["sha256"] == speech["sha256"]
            )
            metadata = beta_shorts.package(language, video)
            beta.save(folder / "youtube-metadata.json", metadata)
            entries.append(
                {
                    "creative": creative,
                    "language": language,
                    "folder": f"{creative}/{language}",
                    "sha256": video["sha256"],
                    "package_id": metadata["id"],
                    "publish_at": at.isoformat(),
                    "publish_at_utc": at.astimezone(ZoneInfo("UTC"))
                    .isoformat()
                    .replace("+00:00", "Z"),
                }
            )
    result = {
        "schema": 1,
        "timezone": "Europe/Kyiv",
        "explicit_owner_schedule": "2026-10-15: publish all six October 16/17/18 at 17:00 Kyiv",
        "entries": entries,
    }
    beta.save(out / "series-manifest.json", result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("promo-out"))
    parser.add_argument("--draft", action="store_true")
    parser.add_argument("--speech-check", action="store_true")
    parser.add_argument("--manifest", action="store_true")
    parser.add_argument("--deliver", action="store_true")
    args = parser.parse_args()
    if args.manifest:
        manifest(args.out)
    elif args.deliver:
        series = manifest(args.out)
        scheduled = json.loads((args.out / "series-schedule.json").read_text())
        assert scheduled["complete"] and len(scheduled["videos"]) == 6
        assert {row["package_id"] for row in series["entries"]} == {
            row["package_id"] for row in scheduled["videos"] if row["verified"]
        }
        for name in FOLLOWUPS:
            beta.deliver(args.out / name)
        receipt_path = args.out / "series-telegram-receipt.json"
        if not receipt_path.exists():
            lines = [
                "Все 6 Shorts поставлены на автопубликацию в YouTube.",
                "Время — 17:00 по Киеву (14:00 UTC).",
                "",
            ]
            for row in scheduled["videos"]:
                lines.extend(
                    [
                        f"{row['publish_at'][:10]} · {row['creative']} · {row['language']}",
                        row["url"],
                    ]
                )
            answer = send._request(
                f"{experiments.TELEGRAM_API}/bot{send._env('TELEGRAM_BOT_TOKEN')}/sendMessage",
                method="POST",
                data=json.dumps(
                    {
                        "chat_id": send._env("TELEGRAM_CHAT_ID"),
                        "text": "\n".join(lines),
                        "disable_web_page_preview": True,
                    },
                    ensure_ascii=False,
                ).encode(),
                headers={"Content-Type": "application/json"},
            )
            if not answer.get("ok") or not answer.get("result", {}).get("message_id"):
                raise ValueError(
                    "Telegram did not confirm the schedule summary; do not retry blindly"
                )
            beta.save(
                receipt_path,
                {
                    "ok": True,
                    "message_id": answer["result"]["message_id"],
                    "scheduled_videos": 6,
                },
            )
    elif args.speech_check:
        for name in FOLLOWUPS:
            beta.speech_check(args.out / name)
        manifest(args.out)
    else:
        for name, creative in FOLLOWUPS.items():
            beta.build(args.out / name, draft=args.draft, creative=creative)


if __name__ == "__main__":
    main()
