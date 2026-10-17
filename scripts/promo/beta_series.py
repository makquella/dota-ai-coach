"""Build the remaining four films and a hash-bound six-video review manifest."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from . import beta, beta_shorts

CREATIVES = ("sven", "juggernaut", "terrorblade")
FOLLOWUPS = {"juggernaut": "juggernaut-review", "terrorblade": "terrorblade-feedback"}


def manifest(out: Path) -> dict:
    entries = []
    for creative in CREATIVES:
        for language in beta.LANGUAGES:
            folder = out / creative / language
            video = json.loads((folder / "package.json").read_text())
            speech = json.loads((folder / "speech-check.json").read_text())
            assert video["kind"] == beta.KIND and not video["draft"]
            assert video["language"] == speech["language"] == language
            assert video["layout"]["ok"] and speech["ok"]
            assert video["quality"]["ok"] and video["quality"]["fully_decoded"]
            assert beta.digest(folder / "video.mp4") == video["sha256"] == speech["sha256"]
            metadata = beta_shorts.package(language, video)
            beta.save(folder / "youtube-metadata.json", metadata)
            entries.append(
                {
                    "creative": creative,
                    "language": language,
                    "folder": f"{creative}/{language}",
                    "sha256": video["sha256"],
                    "package_id": metadata["id"],
                }
            )
    result = {"schema": 1, "entries": entries}
    beta.save(out / "series-manifest.json", result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("promo-out"))
    parser.add_argument("--draft", action="store_true")
    parser.add_argument("--speech-check", action="store_true")
    args = parser.parse_args()
    if args.speech_check:
        for name in FOLLOWUPS:
            beta.speech_check(args.out / name)
        manifest(args.out)
    else:
        for name, creative in FOLLOWUPS.items():
            beta.build(args.out / name, draft=args.draft, creative=creative)


if __name__ == "__main__":
    main()
