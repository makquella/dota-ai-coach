"""Bilingual beta recruitment storyboard; rendered by the existing promo renderer."""

from __future__ import annotations

import base64
import html
import json
import mimetypes
from pathlib import Path
from typing import Any

from .scenes import SITE

COPY = {
    "uk": {
        "label": "ШУКАЄМО БЕТА-ТЕСТЕРІВ",
        "free": "Безкоштовно для Windows",
        "site": "luhovyimvp.dev",
        "cta": "БЕТА",
        "titles": [
            "Твоя Дота.\nТвій фідбек.",
            "Підказки в матчі.\nРозбір після.",
            "Граєш на цих героях?",
            "Кілька матчів.\nЧесний відгук.",
            "Що варто змінити?",
            "Покращимо\nWardly разом.",
            "Напиши «БЕТА»\nу коментарях",
        ],
        "voice": [
            "Граєш у Доту? Допоможи зробити Wardly кращим.",
            "Це безкоштовний Windows-тренер: підказки в матчі та розбір після гри.",
            "Шукаємо добровольців до чотирьох тисяч MMR. Особливо на Свені, Джагернауті й Терорблейді.",
            "Зіграй кілька матчів і розкажи, що справді допомогло.",
            "Що запізнилося чи відволікало? Де порада була неправильною?",
            "Разом зробимо поради точнішими, вчаснішими й кориснішими.",
            "Хочеш долучитися? Напиши «БЕТА» в коментарях.",
        ],
        "heroes": ["Свен", "Джагернаут", "Терорблейд"],
        "live": "ПІД ЧАС МАТЧУ",
        "review": "ПІСЛЯ ГРИ",
        "interface": "Реальний інтерфейс Wardly",
        "volunteers": "Добровільне бета-тестування",
        "feedback": [
            "Що допомогло?",
            "Що запізнилось / відволікало?",
            "Де порада була хибною?",
        ],
        "goals": ["Точніше", "Вчасніше", "Корисніше"],
        "join": "Долучайся до бета-тестування",
    },
    "en": {
        "label": "BETA TESTERS WANTED",
        "free": "Free for Windows",
        "site": "luhovyimvp.dev/en/",
        "cta": "BETA",
        "titles": [
            "Your Dota.\nYour feedback.",
            "In-game tips.\nPost-match reviews.",
            "Play these heroes?",
            "A few matches.\nHonest feedback.",
            "What should change?",
            "Let's improve\nWardly together.",
            "Comment “BETA”\nbelow",
        ],
        "voice": [
            "Play Dota? Help us make Wardly better.",
            "It's a free Windows coach, with in-game tips and post-match reviews.",
            "We're looking for volunteers around zero to four thousand MMR. Especially Sven, Juggernaut and Terrorblade players.",
            "Play a few matches and tell us what actually helped.",
            "What came too late or distracted you? Which advice was wrong?",
            "Your feedback can make the advice more accurate, timely and useful.",
            "Want to join? Comment BETA below.",
        ],
        "heroes": ["Sven", "Juggernaut", "Terrorblade"],
        "live": "DURING THE MATCH",
        "review": "AFTER THE GAME",
        "interface": "Actual Wardly interface",
        "volunteers": "Volunteer beta testing",
        "feedback": [
            "What helped?",
            "What was late / distracting?",
            "Which advice was wrong?",
        ],
        "goals": ["More accurate", "Better timed", "More useful"],
        "join": "Join the beta test",
    },
}
HEROES = ("sven", "juggernaut", "terrorblade")
ARROW = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M5 19 19 5M5 5h14v14"/></svg>'
ICONS = (
    '<circle cx="12" cy="12" r="9"/><path d="M12 6v6l4 3"/>',
    '<path d="m5 5 14 14M19 5 5 19"/>',
    '<circle cx="12" cy="12" r="9"/><path d="M12 6v8m0 2v2"/>',
)


def uri(path: Path) -> str:
    """Self-contained frames work in cloud browsers without file:// navigation."""
    kind = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return f"data:{kind};base64," + base64.b64encode(path.read_bytes()).decode("ascii")


# Editorial phrase boundaries preserve every spoken word, without dangling
# articles/prepositions or the generic renderer's arbitrary character cuts.
PHRASES = {
    "uk": [
        "Граєш у Доту?|Допоможи зробити|Wardly кращим.",
        "Це безкоштовний|Windows-тренер:|підказки в матчі|та розбір після гри.",
        "Шукаємо добровольців|до чотирьох тисяч MMR.|Особливо на Свені,|Джагернауті й Терорблейді.",
        "Зіграй кілька матчів|і розкажи,|що справді допомогло.",
        "Що запізнилося|чи відволікало?|Де порада|була неправильною?",
        "Разом зробимо поради|точнішими,|вчаснішими й кориснішими.",
        "Хочеш долучитися?|Напиши «БЕТА»|в коментарях.",
    ],
    "en": [
        "Play Dota?|Help us make|Wardly better.",
        "It's a free|Windows coach,|with in-game tips|and post-match reviews.",
        "We're looking for volunteers|around zero to four thousand MMR.|Especially Sven,|Juggernaut and Terrorblade players.",
        "Play a few matches|and tell us|what actually helped.",
        "What came too late|or distracted you?|Which advice was wrong?",
        "Your feedback can make|the advice more accurate,|timely and useful.",
        "Want to join?|Comment BETA below.",
    ],
}


def phrase_captions(language: str, words: list[dict[str, Any]], end: float) -> list[dict[str, Any]]:
    phrases = [p for scene in PHRASES[language] for p in scene.split("|")]
    if " ".join(phrases) != " ".join(w["word"] for w in words):
        raise ValueError("Editorial captions must preserve the complete narration")
    result, at = [], 0
    for phrase in phrases:
        count = len(phrase.split())
        group = words[at : at + count]
        at += count
        stop = words[at]["start"] if at < len(words) else end
        result.append(
            {
                "text": phrase,
                "start": group[0]["start"],
                "end": max(group[-1]["end"], stop),
                "words": [{"w": w["word"], "s": w["start"], "e": w["end"]} for w in group],
            }
        )
    return result


def page(
    language: str,
    timeline: list[dict[str, Any]],
    captions: list[dict[str, Any]],
    motion: dict[str, list[str]] | None = None,
) -> str:
    copy = COPY[language]
    uk = language == "uk"
    esc = html.escape
    assets = SITE / "assets"
    images = {
        "logo": uri(assets / "logo.png"),
        "game": uri(assets / "game" / f"ingame-{language}.jpg"),
        "review": uri(assets / "app" / language / "review.jpg"),
    }
    motion = motion or {}
    posters = {key: uri(assets / "heroes" / (key + ".webp")) for key in HEROES}

    def hero(key: str, cls: str) -> str:
        frames = motion.get(key)
        source = frames[0] if frames else posters[key]
        return (
            f'<img class="{cls} {"animated" if frames else "poster"}" '
            f'data-hero="{key}" src="{source}">'
        )

    cards = "".join(
        f'<div class="hero-card h{i}">{hero(key, "hero-art")}'
        f'<div class="hero-name" data-safe>{esc(name)}</div></div>'
        for i, (key, name) in enumerate(zip(HEROES, copy["heroes"], strict=True))
    )
    questions = (
        ["Запізно?", "Відволікає?", "Помилка?"]
        if uk
        else ["Too late?", "Distracting?", "Wrong advice?"]
    )
    feedback = "".join(
        f'<div class="question q{i}"><span class="question-icon"><svg viewBox="0 0 24 24" '
        f'fill="none" stroke="currentColor" stroke-width="1.5">{symbol}</svg></span>'
        f"<b data-safe>{esc(text)}</b></div>"
        for i, (text, symbol) in enumerate(zip(questions, ICONS, strict=True))
    )
    goals = "".join(
        f'<div class="goal g{i}" data-safe>{esc(text)}<span>{ARROW}</span></div>'
        for i, text in enumerate(copy["goals"])
    )
    tag = "ТВІЙ ДОСВІД ПОТРІБЕН" if uk else "YOUR EXPERIENCE MATTERS"
    player = "ШУКАЄМО ГРАВЦІВ" if uk else "LOOKING FOR PLAYERS"
    steps = ("Зіграй.", "Розкажи.") if uk else ("Play.", "Tell us.")
    improve = "Твій відгук —<br>кращі поради." if uk else "Your feedback.<br>Better advice."
    want = "Хочеш долучитися?" if uk else "Want to join?"
    comment = "Напиши в коментарях" if uk else "Comment below"
    # The in-game image and review crop keep their original pixels. The review
    # crop excludes the sidebar logo, so branding appears only once in a frame.
    sections = f"""
<section class="scene s0">
  <div class="hook-halo"></div>
  <div class="eyebrow" data-safe>{tag}</div>
  <div class="hook-heroes">{hero("sven", "hook-left")}{hero("terrorblade", "hook-right")}{hero("juggernaut", "hook-main")}</div>
  <div class="audience" data-safe>DOTA 2 <span>·</span> 0–4 000 MMR</div>
</section>
<section class="scene s1">
  <div class="eyebrow" data-safe>{esc(copy["free"])}</div>
  <div class="product-title live-title" data-safe>{"Підказки<br><em>у грі.</em>" if uk else "Tips.<br><em>In the game.</em>"}</div>
  <div class="product-title review-title" data-safe>{"Розбір.<br><em>Після матчу.</em>" if uk else "Reviews.<br><em>After the match.</em>"}</div>
  <div class="screen live-screen"><img src="{images["game"]}"><div class="focus-corner"></div></div>
  <div class="screen review-screen"><img src="{images["review"]}"></div>
  <div class="screen-note" data-safe>{esc(copy["interface"])}</div>
</section>
<section class="scene s2">
  <div class="eyebrow" data-safe>{player}</div>
  <div class="rating" data-safe>0–4 000<span>MMR</span></div>
  <div class="hero-deck">{cards}</div>
  <div class="hero-foot" data-safe>{"Особливо на цих героях" if uk else "Especially these heroes"}</div>
</section>
<section class="scene s3">
  <div class="eyebrow" data-safe>{"КІЛЬКА МАТЧІВ. ЧЕСНИЙ ВІДГУК." if uk else "A FEW MATCHES. HONEST FEEDBACK."}</div>
  <div class="steps" data-safe><span>{steps[0]}</span><b>{ARROW}</b><em>{steps[1]}</em></div>
  <div class="review-detail"><img src="{images["review"]}"></div>
  <div class="screen-note" data-safe>{esc(copy["interface"])}</div>
</section>
<section class="scene s4">
  <div class="eyebrow" data-safe>{"ЩО ВАРТО ЗМІНИТИ?" if uk else "WHAT SHOULD CHANGE?"}</div>
  <div class="questions">{feedback}</div>
</section>
<section class="scene s5">
  <div class="eyebrow" data-safe>{"РОБИМО WARDLY КРАЩИМ РАЗОМ" if uk else "MAKE WARDLY BETTER TOGETHER"}</div>
  <h1 class="improve" data-safe>{improve}</h1>
  <div class="goals">{goals}</div>
</section>
<section class="scene s6">
  <div class="end-orbit"></div>
  <div class="invite" data-safe>{want}</div>
  <div class="comment-card"><div class="comment-symbol" aria-hidden="true"></div><b data-safe>{copy["cta"]}</b></div>
  <div class="comment-label" data-safe>{comment}</div>
  <div class="address" data-safe>{copy["site"]}</div>
  <div class="free" data-safe><span class="windows" aria-hidden="true"><i></i><i></i><i></i><i></i></span>{copy["free"]}</div>
</section>"""
    fonts = {
        name: uri(assets / "fonts" / f"{name}-wght-normal.woff2")
        for name in (
            "montserrat-cyrillic",
            "montserrat-latin",
            "inter-cyrillic",
            "inter-latin",
        )
    }
    css = (Path(__file__).with_name("beta_style.css")).read_text(encoding="utf-8")
    js = (Path(__file__).with_name("beta_motion.js")).read_text(encoding="utf-8")
    return f'''<!doctype html><html lang="{language}"><meta charset="utf-8">
<style>
@font-face{{font-family:Montserrat;src:url("{fonts["montserrat-cyrillic"]}");font-weight:100 900;unicode-range:U+0400-045F,U+0490-0491}}
@font-face{{font-family:Montserrat;src:url("{fonts["montserrat-latin"]}");font-weight:100 900}}
@font-face{{font-family:Inter;src:url("{fonts["inter-cyrillic"]}");font-weight:100 900;unicode-range:U+0400-045F,U+0490-0491}}
@font-face{{font-family:Inter;src:url("{fonts["inter-latin"]}");font-weight:100 900}}
{css}
</style><body>
<div class="ambient"></div><div class="edge-light"></div>
{sections}
<header><img src="{images["logo"]}" data-brand><b data-safe>Wardly</b><span data-safe>{copy["label"]}</span></header>
<div class="captions" data-safe></div>
<script>
const timeline={json.dumps(timeline, ensure_ascii=False)}, captions={json.dumps(captions, ensure_ascii=False)};
const motion={json.dumps(motion)}, language={json.dumps(language)};
{js}
</script></body></html>'''
