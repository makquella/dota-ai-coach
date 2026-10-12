"""Checks a package must pass before it goes to Telegram for approval.
Errors stop it; warnings ride along in the approval message."""

from __future__ import annotations

import re
from typing import Any

MIN_SECONDS, MAX_SECONDS = 12.0, 59.0  # Shorts: under a minute
CAPTION_LIMIT = 2200  # TikTok and Instagram
TELEGRAM_CAPTION_LIMIT = 1024
YOUTUBE_TITLE_LIMIT = 100
# Promises nobody can keep, or what the coach must never claim.
FORBIDDEN = (
    "гарантовано",
    "гарантуємо",
    "100 % перемог",
    "100% перемог",
    "бачить ворогів",
    "крізь туман",
    "чит,",
    "wallhack",
    "maphack",
)
LEFTOVERS = re.compile(r"\{[a-z_]+\}|\bNone\b|\bnan\b|\bundefined\b")


def check(
    package: dict[str, Any], media: dict[str, Any] | None, allow_silent: bool = False
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    script = package["script"]
    texts = [scene["voice"] for scene in script["scenes"]] + [
        package["caption"],
        package["youtube_title"],
        package["telegram_caption"],
    ]
    for scene in script["scenes"]:
        data = scene.get("data") or {}
        texts += [str(v) for v in data.values() if isinstance(v, (str, int, float))]
    blob = "\n".join(texts)
    for word in FORBIDDEN:
        if word in blob.lower():
            errors.append(f"заборонене формулювання: «{word}»")
    if LEFTOVERS.search(blob):
        errors.append(f"незаповнене місце в тексті: {LEFTOVERS.search(blob).group(0)}")  # type: ignore[union-attr]
    if len(package["caption"]) > CAPTION_LIMIT:
        errors.append(f"підпис задовгий: {len(package['caption'])} > {CAPTION_LIMIT}")
    if len(package["telegram_caption"]) > TELEGRAM_CAPTION_LIMIT:
        errors.append("підпис для Telegram задовгий")
    if len(package["youtube_title"]) > YOUTUBE_TITLE_LIMIT:
        errors.append("назва для YouTube задовга")
    if not script.get("sources"):
        errors.append("немає джерел даних")
    if media is None:
        warnings.append("відео не зібране (лише текст)")
    else:
        seconds = media.get("seconds", 0)
        if not MIN_SECONDS <= seconds <= MAX_SECONDS:
            errors.append(
                f"тривалість {seconds:.1f} с поза межами {MIN_SECONDS:.0f}–{MAX_SECONDS:.0f} с"
            )
        if (media.get("width"), media.get("height")) != (1080, 1920):
            errors.append(
                f"розмір кадру {media.get('width')}x{media.get('height')}, потрібно 1080x1920"
            )
        if not media.get("audio"):
            (warnings if allow_silent else errors).append("у відео немає голосу")
        if media.get("bytes", 0) > 200 * 1024 * 1024:
            errors.append("файл більший за 200 МБ")
    guessed = package.get("pronunciation_guesses") or []
    if guessed:
        warnings.append(
            "вимова за правилами (додати в data/promo/pronounce.json): " + ", ".join(guessed)
        )
    return {"ok": not errors, "errors": errors, "warnings": warnings}
