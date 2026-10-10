"""
Real Dota 2 pictures for the website: gameplay frames from the Dota 2 Steam
page (tile backgrounds and the in-game view with the real overlay card) and the
portraits of the heroes with the full advisor (Valve's CDN). Needs the
overlay card renders from overlay_shots.js and Pillow.

    python scripts/site-shots/game_frames.py <raw-dir>
"""

import io
import json
import sys
import urllib.request
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
SITE = ROOT / "site" / "assets"
STORE = "https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/570/"
CDN = "https://cdn.cloudflare.steamstatic.com/apps/dota2/images/dota_react/heroes/"
# Store screenshots (1920x1080) by their Steam ids.
FRAMES = {
    "chrono": "ss_ad8eee787704745ccdecdfde3a5cd2733704898d",
    "hook": "ss_7ab506679d42bfc0c0e40639887176494e0466d9",
    "forest": "ss_c9118375a2400278590f29a3537769c986ef6e39",
    "base": "ss_f9ebafedaf2d5cfb80ef1f74baa18eb08cad6494",  # Juggernaut at 1:12
    "dark": "ss_27b6345f22243bd6b885cc64c5cda74e4bd9c3e8",
    "fight": "ss_b33a65678dc71cc98df4890e22a89601ee56a918",
}
# 16:10 crops of the action for the tiles (the HUD at the bottom left out).
CROPS = {
    "fight": (380, 160, 1580, 910),
    "forest": (300, 60, 1500, 810),
    "base": (420, 140, 1620, 890),
    "dark": (360, 90, 1560, 840),
    "hook": (500, 60, 1700, 810),
    "chrono": (300, 40, 1500, 790),
}


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


def carries() -> list[tuple[str, str]]:
    sys.path.insert(0, str(ROOT / "backend"))
    from app.schemas import SUPPORTED_HEROES

    source = (ROOT / "frontend/launcher/renderer/dota-data.js").read_text(encoding="utf-8")
    data = json.loads(source[source.index("{") : source.rindex("}") + 1])
    keys = {name: key for name, key in data["heroes"].values()}
    return [(name, keys[name]) for name in SUPPORTED_HEROES]


def main() -> None:
    raw = Path(sys.argv[1] if len(sys.argv) > 1 else "out")
    (SITE / "game").mkdir(parents=True, exist_ok=True)
    (SITE / "heroes").mkdir(parents=True, exist_ok=True)
    frames = {
        name: Image.open(io.BytesIO(fetch(f"{STORE}{shot}.1920x1080.jpg"))).convert("RGB")
        for name, shot in FRAMES.items()
    }
    for name, box in CROPS.items():
        tile = frames[name].crop(box).resize((800, 500), Image.LANCZOS)
        tile.save(SITE / "game" / f"{name}.jpg", quality=78, optimize=True, progressive=True)
    # The in-game view: Juggernaut at 1:12 with the plan card where the overlay
    # sits (top right inside Dota's window), at the "large" card size.
    for lang in ("uk", "en"):
        frame = frames["base"].convert("RGBA")
        card = Image.open(raw / f"{lang}-plan.png").convert("RGBA")
        width = int(404 * 1.25)
        card = card.resize((width, int(card.height * width / card.width)), Image.LANCZOS)
        frame.alpha_composite(card, (1920 - width - 36, 96))
        frame = frame.convert("RGB").resize((1600, 900), Image.LANCZOS)
        frame.save(
            SITE / "game" / f"ingame-{lang}.jpg", quality=82, optimize=True, progressive=True
        )
    for _name, key in carries():
        portrait = Image.open(io.BytesIO(fetch(f"{CDN}{key}.png"))).convert("RGB")
        portrait.save(SITE / "heroes" / f"{key}.webp", quality=84, method=6)
    print(f"game frames and portraits in {SITE}")


if __name__ == "__main__":
    main()
