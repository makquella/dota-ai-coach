"""Moving pictures for the videos, all Valve's own, from dota2.com's CDN:

  heroes/renders/<hero>.webm          the hero's idle animation (VP9 with alpha)
  abilities/<hero>/<ability>.webm     a short in-game clip of the ability

Valve's hero data feed names each hero's abilities (internal name and the
English name the overlay cards use), so a card that says «use Shackles» gets
the Shackles clip. Each clip is decoded once per run into numbered frames
(WebP with alpha for the renders, JPEG for the gameplay, cropped to 9:16):
the page shows frame N at time t, so every video frame stays exact.

Nothing here is required: a missing clip only means a still picture."""

from __future__ import annotations

import json
import re
import subprocess
import urllib.request
from pathlib import Path
from typing import Any

from . import render

FEED = "https://www.dota2.com/datafeed"
CDN = "https://cdn.akamai.steamstatic.com/apps/dota2"
RENDER_VIDEO = CDN + "/videos/dota_react/heroes/renders/{hero}.webm"
ABILITY_VIDEO = CDN + "/videos/dota_react/abilities/{hero}/{ability}.webm"
ABILITY_ICON = CDN + "/images/dota_react/abilities/{ability}.png"
ITEM_ICON = CDN + "/images/dota_react/items/{item}.png"
USER_AGENT = "Wardly promo"
TIMEOUT = 60

IDLE_FPS = 24  # the renders are 24 fps loops
CLIP_FPS = 30  # = scenes.FPS: one clip frame per video frame
IDLE_SIZE = 860
# A 9:16 window of CLIP_ZOOM of the clip's height, placed where the clip moves
# most (`focus`), with the action at ACTION_AT of the window's height: above
# the overlay card, which covers the middle of the video.
CLIP_ZOOM = 0.8
ACTION_AT = 0.32
FOCUS_SIZE = (96, 54)

# Enemy moments for the coach video, by kind: a stun that lands, a burst that
# drops HP. One is picked per video (never the video's own hero).
THREATS = {
    "stun": (
        ("sven", "sven_storm_bolt"),
        ("lion", "lion_impale"),
        ("earthshaker", "earthshaker_fissure"),
        ("tiny", "tiny_avalanche"),
        ("skeleton_king", "skeleton_king_hellfire_blast"),
    ),
    "fall": (
        ("lina", "lina_laguna_blade"),
        ("zuus", "zuus_lightning_bolt"),
        ("lion", "lion_finger_of_death"),
    ),
}


def _get(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:  # noqa: S310 - fixed hosts
        return response.read()


def download(url: str, target: Path) -> Path | None:
    if target.exists() and target.stat().st_size > 0:
        return target
    try:
        data = _get(url)
    except OSError:
        return None
    if not data:
        return None
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    return target


class Library:
    """Downloads and frames for one package, kept under `workdir/media`."""

    def __init__(self, workdir: Path, online: bool = True) -> None:
        self.root = workdir / "media"
        self.online = online
        self._hero_ids: dict[str, int] | None = None
        self._abilities: dict[str, list[dict[str, str]]] = {}

    # --- Valve's data feed ------------------------------------------------------------

    def _json(self, name: str, url: str) -> Any:
        cache = self.root / f"{name}.json"
        if cache.exists():
            return json.loads(cache.read_text(encoding="utf-8"))
        if not self.online:
            return None
        try:
            data = json.loads(_get(url))
        except (OSError, ValueError):
            return None
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(data), encoding="utf-8")
        return data

    def hero_id(self, hero: str) -> int | None:
        if self._hero_ids is None:
            data = self._json("herolist", f"{FEED}/herolist?language=english")
            heroes = (((data or {}).get("result") or {}).get("data") or {}).get("heroes") or []
            self._hero_ids = {
                str(h.get("name", "")).removeprefix("npc_dota_hero_"): int(h["id"])
                for h in heroes
                if h.get("id")
            }
        return self._hero_ids.get(hero)

    def abilities(self, hero: str) -> list[dict[str, str]]:
        """[{"key": "shadow_shaman_shackles", "name": "Shackles"}, ...] in Valve's order."""
        if hero in self._abilities:
            return self._abilities[hero]
        hero_id = self.hero_id(hero)
        found: list[dict[str, str]] = []
        if hero_id is not None:
            data = self._json(f"hero-{hero}", f"{FEED}/herodata?language=english&hero_id={hero_id}")
            heroes = (((data or {}).get("result") or {}).get("data") or {}).get("heroes") or []
            for ability in (heroes[0].get("abilities") or []) if heroes else []:
                key, name = ability.get("name"), ability.get("name_loc")
                if key and name and not str(key).startswith("generic_"):
                    found.append({"key": str(key), "name": str(name)})
        self._abilities[hero] = found
        return found

    def ability_in(self, hero: str, text: str) -> dict[str, str] | None:
        """The hero's ability a card names (the longest name found in the text)."""
        hits = [
            a
            for a in self.abilities(hero)
            if re.search(rf"(?<!\w){re.escape(a['name'])}(?!\w)", text, re.IGNORECASE)
        ]
        return max(hits, key=lambda a: len(a["name"])) if hits else None

    # --- videos -> frames -------------------------------------------------------------

    def _video(self, url: str, name: str) -> Path | None:
        if not self.online and not (self.root / name).exists():
            return None
        return download(url, self.root / name)

    def _frames(self, video: Path, name: str, args: list[str], ext: str) -> list[str]:
        folder = self.root / name
        if not folder.exists() or not any(folder.iterdir()):
            folder.mkdir(parents=True, exist_ok=True)
            command = [
                render.ffmpeg(),
                "-y",
                "-loglevel",
                "error",
                *args,
                str(folder / f"f_%04d.{ext}"),
            ]
            result = subprocess.run(command, capture_output=True, timeout=300, check=False)
            if result.returncode != 0:
                return []
        return [p.resolve().as_uri() for p in sorted(folder.glob(f"f_*.{ext}"))]

    def idle(self, hero: str) -> list[str]:
        """The hero's idle animation, frames with transparency (IDLE_FPS)."""
        video = self._video(RENDER_VIDEO.format(hero=hero), f"idle-{hero}.webm")
        if video is None:
            return []
        return self._frames(
            video,
            f"idle-{hero}",
            [
                # libvpx keeps the alpha channel the built-in VP9 decoder drops
                "-c:v",
                "libvpx-vp9",
                "-i",
                str(video),
                "-vf",
                f"fps={IDLE_FPS},scale={IDLE_SIZE}:-1",
                "-c:v",
                "libwebp",
                "-quality",
                "82",
            ],
            "webp",
        )

    def focus(self, video: Path) -> tuple[float, float]:
        """Where the clip moves most, as fractions of its width and height: the
        start of the best 9:16 window and the centre of the motion's height."""
        w, h = FOCUS_SIZE
        result = subprocess.run(
            [
                render.ffmpeg(),
                "-loglevel",
                "error",
                "-i",
                str(video),
                "-vf",
                f"fps=10,scale={w}:{h},format=gray",
                "-f",
                "rawvideo",
                "-",
            ],
            capture_output=True,
            timeout=300,
            check=False,
        )
        return motion_focus(result.stdout, w, h)

    def clip(self, hero: str, ability: str) -> list[str]:
        """An ability's in-game clip, cropped to 9:16 around the action (CLIP_FPS)."""
        video = self._video(
            ABILITY_VIDEO.format(hero=hero, ability=ability), f"clip-{ability}.webm"
        )
        if video is None:
            return []
        left, middle = self.focus(video)
        h = f"ih*{CLIP_ZOOM}"
        crop = (
            f"crop=w='{h}*9/16':h='{h}':"
            f"x='max(0,min(iw-{h}*9/16,iw*{left:.4f}))':"
            f"y='max(0,min(ih-{h},ih*{middle:.4f}-{h}*{ACTION_AT}))'"
        )
        return self._frames(
            video,
            f"clip-{ability}",
            [
                "-i",
                str(video),
                "-vf",
                f"fps={CLIP_FPS},{crop},scale=1080:1920:flags=lanczos",
                "-q:v",
                "3",
            ],
            "jpg",
        )

    def icon(self, ability: str) -> str | None:
        path = (
            download(ABILITY_ICON.format(ability=ability), self.root / f"icon-{ability}.png")
            if self.online
            else None
        )
        return path.resolve().as_uri() if path else None

    def item_in(self, text: str) -> dict[str, str] | None:
        """The item a card names, from Valve's item list (recipes left out)."""
        data = self._json("itemlist", f"{FEED}/itemlist?language=english")
        items = (((data or {}).get("result") or {}).get("data") or {}).get("itemabilities") or []
        hits = [
            {"key": str(i["name"]).removeprefix("item_"), "name": str(i["name_english_loc"])}
            for i in items
            if i.get("name")
            and i.get("name_english_loc")
            and not str(i["name"]).startswith("item_recipe")
            and re.search(rf"(?<!\w){re.escape(str(i['name_english_loc']))}(?!\w)", text)
        ]
        return max(hits, key=lambda i: len(i["name"])) if hits else None

    def item_icon(self, item: str) -> str | None:
        path = (
            download(ITEM_ICON.format(item=item), self.root / f"item-{item}.png")
            if self.online
            else None
        )
        return path.resolve().as_uri() if path else None


def motion_focus(raw: bytes, w: int, h: int) -> tuple[float, float]:
    """Grey frames (w*h bytes each) -> (left of the busiest 9:16 window, centre
    of the motion's height), both as fractions. No motion: the middle."""
    size = w * h
    count = len(raw) // size
    cols, rows = [0] * w, [0] * h
    for index in range(1, count):
        prev = raw[(index - 1) * size : index * size]
        cur = raw[index * size : (index + 1) * size]
        for y in range(h):
            base = y * w
            for x in range(w):
                diff = abs(cur[base + x] - prev[base + x])
                if diff > 12:
                    cols[x] += diff
                    rows[y] += diff
    window = max(1, round(h * CLIP_ZOOM * 9 / 16))
    if not any(cols) or window >= w:
        return max(0.0, (1 - window / w) / 2), 0.5
    sums = [sum(cols[x : x + window]) for x in range(w - window + 1)]
    left = sums.index(max(sums))
    total = sum(rows)
    middle = sum(y * v for y, v in enumerate(rows)) / total / h if total else 0.5
    return left / w, middle


def threat(kind: str, hero: str, seed: int) -> tuple[str, str] | None:
    options = [t for t in THREATS.get(kind, ()) if t[0] != hero]
    return options[seed % len(options)] if options else None


def prepare(timeline: list[dict[str, Any]], library: Library, seed: int) -> dict[str, Any]:
    """Frame sequences for the timeline; each scene gets its `media` choice:
    idle (the hero's animation), bg (a clip behind it) and, for a coach moment,
    threat (the enemy's stun or burst) and pay (the ability the card names)."""
    seqs: dict[str, dict[str, Any]] = {}

    def idle(hero: str) -> str | None:
        name = f"idle:{hero}"
        if name not in seqs:
            frames = library.idle(hero)
            if not frames:
                return None
            seqs[name] = {"frames": frames, "fps": IDLE_FPS}
        return name

    def clip(hero: str, ability: str) -> str | None:
        name = f"clip:{ability}"
        if name not in seqs:
            frames = library.clip(hero, ability)
            if not frames:
                return None
            seqs[name] = {"frames": frames, "fps": CLIP_FPS}
        return name

    signature: dict[str, str | None] = {}

    def hero_clip(hero: str) -> str | None:
        if hero not in signature:
            signature[hero] = None
            for ability in library.abilities(hero)[:4]:
                found = clip(hero, ability["key"])
                if found:
                    signature[hero] = found
                    break
        return signature[hero]

    main: str | None = None
    for index, scene in enumerate(timeline):
        data = scene.get("data") or {}
        hero = data.get("hero") or ((data.get("rows") or [{}])[0].get("key"))
        chosen: dict[str, Any] = {}
        if hero:
            chosen["idle"] = idle(hero)
            if scene["kind"] == "card":
                ability = library.ability_in(hero, data.get("action", ""))
                item = None if ability else library.item_in(data.get("action", ""))
                if ability:
                    chosen["pay"] = clip(hero, ability["key"])
                    chosen["pay_name"] = ability["name"]
                    chosen["pay_icon"] = library.icon(ability["key"])
                elif item:
                    chosen["pay_name"] = item["name"]
                    chosen["pay_icon"] = library.item_icon(item["key"])
                enemy = threat(data.get("moment", ""), hero, seed + index)
                if enemy:
                    chosen["threat"] = clip(*enemy)
                if chosen.get("pay"):
                    signature.setdefault(hero, chosen["pay"])
            chosen["bg"] = hero_clip(hero)
            main = main or chosen["bg"]
        elif main:
            chosen["bg"] = main
        scene["media"] = {k: v for k, v in chosen.items() if v}
    return seqs
