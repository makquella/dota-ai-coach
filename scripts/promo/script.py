"""Promo scripts: what a short video says and shows, built only from the
project's data. Every number on screen comes from a source listed in
`Script.sources`; the voice text is the screen text said aloud.

Formats (topics.py picks one):
  coach    «What Wardly says on <hero>»: real overlay cards (coach_demo.py)
  meta     the week's strongest heroes (data/news/posts, OpenDota)
  hero     three things about a hero (the site's hero page data)
  fact     one surprising number from the week (most picked vs win rate)
  release  what a new version brings (docs/release-notes)
"""

from __future__ import annotations

import random
import re
from dataclasses import asdict, dataclass, field
from typing import Any

from .pronounce import percent_word

SITE = "https://luhovyimvp.dev"
HASHTAGS = ("#dota2", "#дота2", "#дота", "#wardly")
CTA_VOICE = "Wardly безкоштовний. Посилання в профілі."
YOUTUBE_TITLE_LIMIT = 100


@dataclass
class Scene:
    kind: str  # hook | card | stat | list | tips | cta
    voice: str  # what is said (screen spelling; pronounce.py turns it into Cyrillic)
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class Script:
    format: str
    topic: str  # the hero key, the week, the version
    title: str  # the on-screen headline and the YouTube title
    scenes: list[Scene]
    caption: str  # TikTok / Instagram / Telegram text
    sources: list[str]
    hook: int = 0  # which hook variant, for the history and the statistics
    link: str = SITE

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def voice_text(self) -> str:
        return " ".join(scene.voice for scene in self.scenes)


def whole_percent(value: float) -> int:
    return round(value * 100)


def decimal(value: float) -> str:
    return f"{value:.1f}".replace(".", ",")


NBSP = "\u00a0"


def percent_text(value: float) -> str:
    return decimal(value * 100) + NBSP + "%"


def percent_said(number: int) -> str:
    return f"{number} {percent_word(number)}"


def hashtag(name: str) -> str:
    return "#" + re.sub(r"[^0-9A-Za-zА-Яа-яІіЇїЄєҐґ]", "", name).lower()


def caption(lines: list[str], tags: list[str], link_ref: str) -> str:
    body = "\n".join(line for line in lines if line)
    link = f"{SITE}/?ref={link_ref}"
    return f"{body}\n\nБезкоштовно для Windows: {link}\n\n{' '.join(dict.fromkeys(tags))}"


def _cta(extra: str = "") -> Scene:
    return Scene("cta", f"{extra} {CTA_VOICE}".strip(), {"site": "luhovyimvp.dev"})


# --- coach: real overlay cards --------------------------------------------------------

COACH_HOOKS = (
    "Граєш на {name}? Ось що Wardly скаже тобі просто в матчі.",
    "{name}: дві секунди, які вирішують бійку. Wardly підкаже обидві.",
    "Чому {name} помирає з готовим порятунком? Ось як Wardly це виправляє.",
)
MOMENT_VOICE = {
    "fall": "HP тане на очах. Wardly одразу каже, що натиснути.",
    "stun": "Тебе застанили. Wardly нагадує, що робити в першу ж секунду після контролю.",
}


def coach(
    hero: dict[str, Any], cards: list[dict[str, Any]], rng: random.Random, version: str
) -> Script:
    if not cards:
        raise ValueError(f"no cards for {hero['name']}")
    hook = rng.randrange(len(COACH_HOOKS))
    name = hero["name"]
    scenes = [
        Scene(
            "hook",
            COACH_HOOKS[hook].format(name=name),
            {"hero": hero["key"], "name": name},
        )
    ]
    for card in cards:
        scenes.append(
            Scene(
                "card",
                f"{MOMENT_VOICE.get(card['moment'], '')} {card['action']}".strip(),
                {
                    "hero": hero["key"],
                    "mode": card.get("mode") or "urgent",
                    "action": card["action"],
                    "reason": card.get("reason") or "",
                    "moment": card["moment"],
                },
            )
        )
    profile = hero["profile"]
    scenes.append(
        Scene(
            "stat",
            f"А ще Wardly стежить за HP: на {name} відходь, коли лишилося менше "
            f"{percent_said(profile['low_hp_warning_threshold'])}.",
            {
                "hero": hero["key"],
                "value": f"{profile['low_hp_warning_threshold']}{NBSP}%",
                "label": f"HP — час відходити на {name}",
            },
        )
    )
    scenes.append(_cta("Підказки поверх гри, українською, без читів: лише офіційні дані Valve."))
    return Script(
        format="coach",
        topic=hero["key"],
        title=f"{name}: що підкаже Wardly в матчі",
        scenes=scenes,
        caption=caption(
            [
                f"Що Wardly скаже на {name} просто в матчі 👇",
                *(f"• {card['action']}" for card in cards),
                "Підказки поверх Доти, голосом і текстом. Лише офіційна Game State Integration від Valve.",
            ],
            [*HASHTAGS, hashtag(name)],
            "promo-coach",
        ),
        sources=[
            (
                f"Картки — справжній вивід Wardly {version}: синтетичний матч пройшов через бекенд "
                "(/gsi → правила → планувальник), scripts/promo/coach_demo.py"
            ),
            f"Пороги HP — профіль героя {name} (data/heroes/hero_profiles.json)",
        ],
        hook=hook,
    )


# --- meta: the strongest heroes of the week -------------------------------------------

META_HOOKS = (
    "Хто тягне ігри цього тижня? Три герої з найвищим відсотком перемог.",
    "Хочеш легких перемог? Ось хто виграє найчастіше цього тижня.",
    "Мета змінилась. Топ-3 героїв тижня за перемогами.",
)


def meta(post: dict[str, Any], data: dict[str, Any], period: str, rng: random.Random) -> Script:
    top = data["win"][:3]
    if len(top) < 3:
        raise ValueError("not enough heroes in the week")
    hook = rng.randrange(len(META_HOOKS))
    scenes = [
        Scene(
            "hook",
            META_HOOKS[hook],
            {"hero": top[0]["key"], "name": "Мета тижня", "sub": period},
        )
    ]
    rows = [
        {
            "name": h["name"],
            "key": h["key"],
            "value": percent_text(h["win"]),
            "bar": h["win"],
        }
        for h in top
    ]
    voice = ". ".join(
        f"{place}. {h['name']}: {percent_said(whole_percent(h['win']))} перемог"
        for place, h in zip(("Третє місце", "Друге", "І перше"), reversed(top), strict=True)
    )
    scenes.append(Scene("list", voice + ".", {"title": "Найбільше перемог", "rows": rows}))
    up = (data.get("up") or [None])[0]
    if up and up.get("change", 0) >= 0.5:
        scenes.append(
            Scene(
                "stat",
                f"Найбільше виріс {up['name']}: плюс {decimal(up['change'])} пункту за тиждень.",
                {
                    "hero": up["key"],
                    "value": f"+{decimal(up['change'])}",
                    "label": f"пункту перемог за тиждень · {up['name']}",
                },
            )
        )
    scenes.append(_cta("Що робити на цих героях у грі, Wardly підкаже сам."))
    matches = round(data["matches"] / 1_000_000, 1)
    return Script(
        format="meta",
        topic=post["date"],
        title=f"Мета тижня {period}: топ-3 героїв за перемогами",
        scenes=scenes,
        caption=caption(
            [
                f"Мета тижня ({period}) — найбільше перемог:",
                *(f"{i}. {r['name']} — {r['value']}" for i, r in enumerate(rows, 1)),
                f"Дані OpenDota, публічні матчі, ≈{str(matches).replace('.', ',')} млн ігор.",
            ],
            [*HASHTAGS, "#метадота", *(hashtag(r["name"]) for r in rows)],
            "promo-meta",
        ),
        sources=[
            (
                f"OpenDota /heroStats, тиждень {period}: data/news/posts/{post['date']}-meta.json "
                "(герої з часткою піків від 2 %)"
            )
        ],
        hook=hook,
    )


# --- hero: three things about a hero ----------------------------------------------------

HERO_HOOKS = (
    "Три речі, які треба знати про {name}.",
    "{name} без зайвих смертей: три правила.",
    "Граєш на {name}? Запам'ятай три речі.",
)


def hero_tips(hero: dict[str, Any], facts: dict[str, str], rng: random.Random) -> Script:
    hook = rng.randrange(len(HERO_HOOKS))
    name = hero["name"]
    low = int(facts["low"])
    candidates = [
        (
            "heart",
            f"Відходь, коли HP нижче {low}{NBSP}%",
            f"відходь, коли HP нижче {percent_said(low)}.",
        ),
    ]
    if facts.get("saves"):
        candidates.append(
            (
                "shield",
                f"Рятує: {facts['saves']}",
                f"тебе рятує {facts['saves']}: не лізь уперед, поки воно не готове.",
            )
        )
    if facts.get("fight"):
        candidates.append(
            (
                "swords",
                f"У бійці: {facts['fight']}",
                f"у бійці все вирішує {facts['fight']}.",
            )
        )
    if facts.get("pace"):
        pace = facts["pace"].replace("–", " – ")
        candidates.append(
            (
                "coins",
                f"До 10:00 — {facts['pace']} добивань",
                f"до десятої хвилини — {pace} добивань.",
            )
        )
    if facts.get("note"):
        candidates.append(("spark", facts["note"], facts["note"]))
    tips = [
        {
            "icon": icon_name,
            "text": text,
            "voice": f"{place}. {said[:1].upper()}{said[1:]}",
        }
        for (icon_name, text, said), place in zip(
            candidates[:3], ("Перше", "Друге", "Третє"), strict=False
        )
    ]
    if len(tips) < 3:
        raise ValueError(f"not enough facts for {name}")
    scenes = [
        Scene(
            "hook",
            HERO_HOOKS[hook].format(name=name),
            {"hero": hero["key"], "name": name, "sub": facts["role"]},
        ),
        Scene(
            "tips",
            " ".join(t["voice"] for t in tips),
            {"hero": hero["key"], "tips": tips},
        ),
        _cta("Wardly нагадає про все це просто в матчі."),
    ]
    return Script(
        format="hero",
        topic=hero["key"],
        title=f"{name}: три правила без зайвих смертей",
        scenes=scenes,
        caption=caption(
            [f"{name} — {facts['archetype']}.", *(f"• {t['text']}" for t in tips)],
            [*HASHTAGS, hashtag(name)],
            "promo-hero",
        ),
        sources=[
            (
                f"Сторінка героя {SITE}/heroes/{hero['slug']}.html: профіль (data/heroes/hero_profiles.json) "
                "і темп добивань для позиції"
            )
        ],
        hook=hook,
    )


# --- fact: one surprising number ---------------------------------------------------------


def fact(post: dict[str, Any], data: dict[str, Any], period: str) -> Script | None:
    """The most picked hero against its win rate: a fact only when it loses
    more than it wins, or wins clearly more."""
    popular = (data.get("pick") or [None])[0]
    if not popular:
        return None
    win = popular["win"]
    if 0.49 <= win <= 0.53:
        return None
    name = popular["name"]
    losing = win < 0.5
    head = (
        f"{name} — у кожній {round(1 / popular['pick'])}-й грі. І програє частіше, ніж виграє."
        if losing
        else f"{name} — у кожній {round(1 / popular['pick'])}-й грі. І виграє {percent_said(whole_percent(win))}."
    )
    scenes = [
        Scene(
            "hook",
            "Найпопулярніший герой тижня. Варто його брати?",
            {"hero": popular["key"], "name": name, "sub": period},
        ),
        Scene(
            "stat",
            head,
            {
                "hero": popular["key"],
                "value": percent_text(win),
                "label": f"перемог · {name} · {period}",
            },
        ),
        _cta("Бери кого хочеш: Wardly підкаже, як на ньому не помирати."),
    ]
    return Script(
        format="fact",
        topic=f"{post['date']}:{popular['key']}",
        title=f"{name}: найпопулярніший герой тижня {'програє' if losing else 'виграє'}",
        scenes=scenes,
        caption=caption(
            [
                (
                    f"{name} — найчастіший пік тижня ({period}): {percent_text(popular['pick'])} матчів, "
                    f"{percent_text(win)} перемог."
                ),
                "Дані OpenDota, публічні матчі.",
            ],
            [*HASHTAGS, hashtag(name)],
            "promo-fact",
        ),
        sources=[
            f"OpenDota /heroStats, тиждень {period}: data/news/posts/{post['date']}-meta.json"
        ],
    )


# --- release: what a new version brings --------------------------------------------------


def release(version: str, points: list[tuple[str, str]]) -> Script:
    points = points[:3]
    if not points:
        raise ValueError("no release points")
    tips = [{"icon": "spark", "text": head, "voice": f"{head}. {body}"} for head, body in points]
    scenes = [
        Scene(
            "hook",
            f"Wardly {version} вже тут. Ось що нового.",
            {"name": f"Wardly {version}", "sub": "оновлення"},
        ),
        Scene("tips", " ".join(t["voice"] for t in tips), {"tips": tips}),
        _cta("Встановлена версія оновиться сама."),
    ]
    return Script(
        format="release",
        topic=version,
        title=f"Wardly {version}: що нового",
        scenes=scenes,
        caption=caption(
            [f"Wardly {version} 🚀", *(f"• {head}" for head, _ in points)],
            [*HASHTAGS, "#оновлення"],
            "promo-release",
        ),
        sources=[f"docs/release-notes/v{version}.md"],
    )


def youtube_title(script: Script) -> str:
    title = f"{script.title} #shorts"
    return (
        title
        if len(title) <= YOUTUBE_TITLE_LIMIT
        else script.title[: YOUTUBE_TITLE_LIMIT - 8] + "… #shorts"
    )
