"""Copy the raw screenshots from <out-dir> into site/assets (JPEG / WebP, web sizes).

python scripts/site-shots/export.py <out-dir>
"""

import sys
from pathlib import Path

from PIL import Image

SITE = Path(__file__).resolve().parents[2] / "site" / "assets"
APP = ("home", "matches", "review", "review-ai", "progress", "progress-ai")
OVERLAY = ("lowhp", "plan", "tp", "spend", "timer", "farm")
CARDS = ("map", "build", "chart")


def main() -> None:
    raw = Path(sys.argv[1] if len(sys.argv) > 1 else "out")
    for lang in ("ru", "en"):
        (SITE / "app" / lang).mkdir(parents=True, exist_ok=True)
        (SITE / "overlay" / lang).mkdir(parents=True, exist_ok=True)
        for name in APP:
            image = Image.open(raw / f"{lang}-{name}.png").convert("RGB")
            image = image.resize((1080, 930), Image.LANCZOS)
            image.save(
                SITE / "app" / lang / f"{name}.jpg", quality=84, optimize=True, progressive=True
            )
        for name in CARDS:
            image = Image.open(raw / f"{lang}-card-{name}.png").convert("RGB")
            image.save(
                SITE / "shots" / lang / f"{name}.jpg", quality=86, optimize=True, progressive=True
            )
        for name in OVERLAY:
            Image.open(raw / f"{lang}-{name}.png").save(
                SITE / "overlay" / lang / f"{name}.webp", quality=90, method=6
            )
    print(f"exported to {SITE}")


if __name__ == "__main__":
    main()
