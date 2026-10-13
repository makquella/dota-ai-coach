"""The video file: scenes.py's page, frame by frame in headless Chrome
(Playwright), piped as JPEG frames into ffmpeg with the voice track.

H.264 High, yuv420p, 1080x1920, 30 fps, AAC 48 kHz: what TikTok, Reels,
Shorts and Telegram all take. The cover is the hook frame at COVER_AT."""

from __future__ import annotations

import os
import shutil
import subprocess
import urllib.request
from pathlib import Path
from typing import Any

from . import scenes as scene_page

RENDER_URL = (
    "https://cdn.cloudflare.steamstatic.com/apps/dota2/videos/dota_react/heroes/renders/{key}.png"
)
HERO_PICTURES = scene_page.SITE / "assets" / "heroes"
COVER_AT = 1.2
JPEG_QUALITY = 92


def ffmpeg() -> str:
    exe = os.environ.get("FFMPEG") or shutil.which("ffmpeg")
    if exe:
        return exe
    try:
        import imageio_ffmpeg
    except ImportError as error:  # pragma: no cover - environment
        raise SystemExit("ffmpeg is needed: install it or `pip install imageio-ffmpeg`") from error
    return imageio_ffmpeg.get_ffmpeg_exe()


def chrome() -> str | None:
    """CHROME, if set; else Playwright's own browser (`playwright install chromium`)."""
    return os.environ.get("CHROME") or None


def hero_keys(timeline: list[dict[str, Any]]) -> set[str]:
    keys = set()
    for scene in timeline:
        data = scene.get("data") or {}
        if data.get("hero"):
            keys.add(data["hero"])
        for row in data.get("rows") or []:
            keys.add(row["key"])
    return keys


def assets_for(
    timeline: list[dict[str, Any]], workdir: Path, download: bool = True
) -> dict[str, str]:
    """file:// URIs of the pictures: Valve's big renders (downloaded once per
    run), the site's small hero pictures."""
    assets: dict[str, str] = {}
    for key in hero_keys(timeline):
        small = HERO_PICTURES / f"{key}.webp"
        if small.exists():
            assets[f"small:{key}"] = small.as_uri()
        target = workdir / f"render-{key}.png"
        if download and not target.exists():
            try:
                request = urllib.request.Request(
                    RENDER_URL.format(key=key), headers={"User-Agent": "Wardly promo"}
                )
                with urllib.request.urlopen(request, timeout=30) as response:
                    target.write_bytes(response.read())
            except OSError:
                pass
        if target.exists():
            assets[f"render:{key}"] = target.resolve().as_uri()
    return assets


def render(
    page_html: str,
    total: float,
    out: Path,
    audio: Path | None,
    cover: Path | None = None,
    fps: int = scene_page.FPS,
) -> Path:
    from playwright.sync_api import sync_playwright

    page_file = out.with_suffix(".html")
    page_file.write_text(page_html, encoding="utf-8")
    frames = max(1, round(total * fps))
    command = [
        ffmpeg(),
        "-y",
        "-loglevel",
        "error",
        "-f",
        "image2pipe",
        "-framerate",
        str(fps),
        "-c:v",
        "mjpeg",
        "-i",
        "-",
    ]
    if audio is not None:
        command += ["-i", str(audio)]
    command += [
        "-c:v",
        "libx264",
        "-profile:v",
        "high",
        "-preset",
        "medium",
        "-crf",
        "19",
        "-pix_fmt",
        "yuv420p",
        "-r",
        str(fps),
        "-movflags",
        "+faststart",
    ]
    if audio is not None:
        command += [
            "-c:a",
            "aac",
            "-b:a",
            "160k",
            "-ar",
            "48000",
            "-ac",
            "2",
            "-af",
            "loudnorm=I=-14:TP=-1.5:LRA=11",
            "-shortest",
        ]
    command.append(str(out))
    executable = chrome()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            executable_path=executable,
            args=[
                "--allow-file-access-from-files",
                "--disable-web-security",
                "--font-render-hinting=none",
            ],
        )
        page = browser.new_page(viewport={"width": scene_page.WIDTH, "height": scene_page.HEIGHT})
        page.goto(page_file.resolve().as_uri(), wait_until="load")
        page.evaluate("document.fonts.ready.then(() => true)")
        encoder = subprocess.Popen(command, stdin=subprocess.PIPE)
        assert encoder.stdin is not None
        try:
            for index in range(frames):
                t = index / fps
                page.evaluate(f"window.renderAt({t})")
                encoder.stdin.write(page.screenshot(type="jpeg", quality=JPEG_QUALITY))
                if cover is not None and abs(t - COVER_AT) < 0.5 / fps:
                    page.screenshot(path=str(cover), type="jpeg", quality=90)
        finally:
            encoder.stdin.close()
            code = encoder.wait()
            browser.close()
    if code != 0:
        raise RuntimeError(f"ffmpeg failed with code {code}")
    page_file.unlink(missing_ok=True)
    return out


def probe(path: Path) -> dict[str, Any]:
    """Duration, size and streams of the result (ffmpeg -i parsing, no ffprobe needed)."""
    result = subprocess.run(
        [ffmpeg(), "-hide_banner", "-i", str(path)],
        capture_output=True,
        text=True,
        check=False,
    )
    text = result.stderr
    info: dict[str, Any] = {
        "bytes": path.stat().st_size,
        "video": "Video:" in text,
        "audio": "Audio:" in text,
    }
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("Duration:"):
            h, m, s = line.split(",")[0].split()[1].split(":")
            info["seconds"] = int(h) * 3600 + int(m) * 60 + float(s)
        if "Video:" in line and "x" in line:
            for part in line.split(","):
                part = part.strip().split(" ")[0]
                if "x" in part and part.replace("x", "").isdigit():
                    width, height = part.split("x")
                    info["width"], info["height"] = int(width), int(height)
    return info


def stills(page_html: str, times: list[float], out_dir: Path) -> list[Path]:
    """Screenshots of single moments (a preview without a whole render)."""
    from playwright.sync_api import sync_playwright

    page_file = out_dir / "stills.html"
    page_file.write_text(page_html, encoding="utf-8")
    paths = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            executable_path=chrome(),
            args=["--allow-file-access-from-files", "--disable-web-security"],
        )
        page = browser.new_page(viewport={"width": scene_page.WIDTH, "height": scene_page.HEIGHT})
        page.goto(page_file.resolve().as_uri(), wait_until="load")
        page.evaluate("document.fonts.ready.then(() => true)")
        for t in times:
            page.evaluate(f"window.renderAt({t})")
            path = out_dir / f"still-{t:05.1f}.jpg"
            page.screenshot(path=str(path), type="jpeg", quality=85)
            paths.append(path)
        browser.close()
    page_file.unlink(missing_ok=True)
    return paths
