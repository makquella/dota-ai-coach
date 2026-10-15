"""Localized, reviewable YouTube metadata and Shorts-only approval buttons."""

from __future__ import annotations

import hashlib
import json
from typing import Any

COPY = {
    "uk": {
        "title": "Dota 2: шукаємо бета-тестерів Wardly до 4 000 MMR",
        "description": (
            "Граєш у Dota 2? Допоможи покращити Wardly — напиши «БЕТА» в коментарях.\n\n"
            "Wardly — безкоштовний Windows-тренер для Dota 2 з підказками під час гри "
            "та розбором після матчу. Зараз разом із гравцями покращуємо точність, "
            "своєчасність і корисність порад.\n\n"
            "Шукаємо добровольців приблизно 0–4 000 MMR, особливо на Свені, "
            "Джагернауті й Терорблейді. Зіграй кілька матчів і розкажи: "
            "які підказки допомогли, які запізнилися чи відволікали, де порада була хибною.\n\n"
            "Безкоштовно для Windows: https://luhovyimvp.dev/?ref=promo-beta-uk\n\n"
            "Долучитися до бета-тесту: «БЕТА» в коментарях.\n\n"
            "#Dota2 #Wardly #Shorts"
        ),
        "tags": [
            "Dota 2",
            "dota2",
            "Wardly",
            "Dota 2 українською",
            "дота 2",
            "тренер Dota 2",
            "бета-тест",
            "низький MMR",
            "Sven",
            "Juggernaut",
            "Terrorblade",
        ],
        "button": "▶️ Опублікувати в Shorts",
        "reject": "❌ Відхилити",
        "labels": ["Назва", "Опис і хештеги", "Теги", "Мова відео", "Категорія"],
        "ready": "Готово до YouTube Shorts. Метадані — у відповіді нижче.",
        "not_connected": "YouTube ще не підключено: /connect youtube. Метадані — нижче.",
    },
    "en": {
        "title": "Dota 2 beta testers wanted: help improve Wardly | 0–4K MMR",
        "description": (
            "Play Dota 2? Help us improve Wardly — comment BETA to join the beta test.\n\n"
            "Wardly is a free Windows coach for Dota 2, with in-game tips and post-match "
            "reviews. We're working with players to make its advice more accurate, "
            "better timed and more useful.\n\n"
            "Looking for volunteers around 0–4,000 MMR, especially Sven, Juggernaut "
            "and Terrorblade players. Play a few matches and tell us what helped, "
            "what came too late or distracted you, and which advice was wrong.\n\n"
            "Free for Windows: https://luhovyimvp.dev/en/?ref=promo-beta-en\n\n"
            "Want to help shape Wardly? Comment BETA below.\n\n"
            "#Dota2 #Wardly #Shorts"
        ),
        "tags": [
            "Dota 2",
            "dota2",
            "Wardly",
            "Dota 2 coach",
            "Dota 2 beta test",
            "Dota 2 low MMR",
            "Sven",
            "Juggernaut",
            "Terrorblade",
            "Dota 2 Windows app",
        ],
        "button": "▶️ Publish to Shorts",
        "reject": "❌ Reject",
        "labels": ["Title", "Description and hashtags", "Tags", "Video language", "Category"],
        "ready": "Ready for YouTube Shorts. Metadata is in the reply below.",
        "not_connected": "YouTube is not connected yet: /connect youtube. Metadata is below.",
    },
}


def package(language: str, video: dict[str, Any]) -> dict[str, Any]:
    copy = COPY[language]
    identity = {"video_sha256": video["sha256"], "language": language, "copy": copy}
    package_id = hashlib.sha256(
        json.dumps(identity, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()[:16]
    return {
        "id": package_id,
        "format": "release",
        "topic": f"beta-testers-{language}-v{video['visual_revision']}",
        "hook": 0,
        "title": copy["title"],
        "youtube_title": copy["title"],
        "caption": copy["description"],
        "telegram_caption": copy["title"],
        "youtube_tags": copy["tags"],
        "youtube_language": language,
    }


def keyboard(language: str, package_id: str) -> dict[str, Any]:
    copy = COPY[language]
    return {
        "inline_keyboard": [
            [
                {"text": copy["button"], "callback_data": f"promo:yt:{package_id}"},
                {"text": copy["reject"], "callback_data": f"promo:no:{package_id}"},
            ]
        ]
    }


def details(language: str, metadata: dict[str, Any]) -> str:
    title, description, tags, locale, category = COPY[language]["labels"]
    return (
        f"YouTube Shorts\n\n{title}: {metadata['youtube_title']}\n\n"
        f"{description}:\n{metadata['caption']}\n\n"
        f"{tags}: {', '.join(metadata['youtube_tags'])}\n"
        f"{locale}: {language}\n{category}: Gaming (20)"
    )
