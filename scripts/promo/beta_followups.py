"""Two distinct follow-up films, sharing the reviewed brand and render engine."""

from __future__ import annotations

import copy
import html
from functools import partial
from pathlib import Path
from types import SimpleNamespace

from . import beta_scenes as base

PHRASES = {
    "juggernaut-review": {
        "uk": [
            "Джагернаут.|Де ти втратив темп?",
            "Порівняй добивання,|фарм і смерті|зі своїми іншими матчами.",
            "Приклад розбору Wardly.",
            "Безкоштовний Windows-тренер.",
            "Перевір, чи корисні|висновки саме тобі.",
            "Шукаємо добровольців|до чотирьох тисяч MMR.",
            "Кілька матчів, чесний відгук.|Напиши «БЕТА».",
        ],
        "en": [
            "Juggernaut player?|Losing tempo?",
            "Compare last hits,|farming and deaths|with your other games.",
            "A Wardly review example.",
            "A free Windows coach.",
            "Help test whether|the review is useful.",
            "Looking for volunteers|around zero to four thousand MMR.",
            "A few games, honest feedback.|Comment BETA.",
        ],
    },
    "terrorblade-feedback": {
        "uk": [
            "Порада відволікла|під час гри?",
            "На Терорблейді важливий|і час підказки.",
            "Перевір Wardly:|підказки в матчі|й розбір після гри.",
            "Безкоштовно для Windows.",
            "Що допомогло?|Що запізнилося?|Де помилка?",
            "Шукаємо добровольців|до чотирьох тисяч MMR.",
            "Зіграй кілька матчів.|Напиши «БЕТА».",
        ],
        "en": [
            "Did a tip distract you|mid-game?",
            "On Terrorblade,|timing matters too.",
            "Try Wardly:|in-game tips|and post-match reviews.",
            "Free for Windows.",
            "What helped?|What came late?|What was wrong?",
            "Looking for volunteers|around zero to four thousand MMR.",
            "Play a few matches.|Comment BETA.",
        ],
    },
}


def metadata(creative: str, language: str) -> dict:
    uk = language == "uk"
    jugg = creative == "juggernaut-review"
    hero = "Juggernaut" if jugg else "Terrorblade"
    local = ("Джагернаут" if jugg else "Терорблейд") if uk else hero
    code = "jugg" if jugg else "tb"
    title = (
        "Джагернаут: чи корисний розбір Wardly? | Dota 2"
        if jugg and uk
        else "Juggernaut: losing tempo? Help test Wardly's match reviews"
        if jugg
        else "Терорблейд до 4к MMR: допоможи покращити поради Wardly"
        if uk
        else "Terrorblade under 4K MMR? Help improve Wardly's tips"
    )
    url = f"https://luhovyimvp.dev/{'' if uk else 'en/'}?ref=shorts-{code}-{language}"
    description = (
        f"Граєш на герої {local} приблизно до 4к MMR? Напиши «БЕТА».\n\n"
        "Wardly — безкоштовний Windows-тренер для Dota 2: підказки в матчі та розбір "
        "після гри. Шукаємо добровольців: кілька матчів і чесний відгук про те, що "
        "допомогло, що запізнилося чи відволікало, де порада була хибною.\n\n"
        + (
            "У відео — приклад інтерфейсу розбору, не матч нового тестера.\n\n"
            if jugg
            else ""
        )
        + f"Безкоштовно для Windows: {url}\n\nУчасть добровільна, без обіцянок приросту MMR.\n\n"
        + f"#Dota2 #ДотаУкраїнською #{hero}"
        if uk
        else f"Play {hero} around 0–4K MMR? Comment BETA to help test Wardly.\n\n"
        "Wardly is a free Windows Dota 2 coach with in-game tips and post-match reviews. "
        "Play a few matches and tell us what helped, what came late or distracted you, "
        "and which advice was wrong.\n\n"
        + (
            "The video shows an interface example, not a new tester's match.\n\n"
            if jugg
            else ""
        )
        + f"Free for Windows: {url}\n\nVoluntary testing. No promises of MMR gains.\n\n"
        + f"#Dota2 #{hero} #Dota2Coach"
    )
    return {
        "title": title,
        "description": description,
        "tags": list(
            dict.fromkeys(["Dota 2", hero, local, "Wardly", "low MMR", "beta test"])
        ),
    }


def profile(creative: str) -> SimpleNamespace:
    phrases = PHRASES[creative]
    localized = copy.deepcopy(base.COPY)
    for language in ("uk", "en"):
        localized[language]["voice"] = [s.replace("|", " ") for s in phrases[language]]
    return SimpleNamespace(
        COPY=localized,
        phrase_captions=partial(base.phrase_captions, phrases=phrases),
        page=partial(page, creative=creative),
    )


def page(language, timeline, captions, motion=None, *, creative):
    uk = language == "uk"
    jugg = creative == "juggernaut-review"
    hero_key = "juggernaut" if jugg else "terrorblade"
    hero_name = (
        ("Джагернаут" if jugg else "Терорблейд")
        if uk
        else ("Juggernaut" if jugg else "Terrorblade")
    )
    text = lambda a, b: a if uk else b
    esc = html.escape
    assets = base.SITE / "assets"
    review = base.uri(assets / "app" / language / "review.jpg")
    game = base.uri(assets / "game" / f"ingame-{language}.jpg")
    motion = motion or {}
    source = (
        motion[hero_key][0]
        if motion.get(hero_key)
        else base.uri(assets / "heroes" / f"{hero_key}.webp")
    )
    art = f'<div class="follow-hero"><img data-hero="{hero_key}" src="{source}"></div>'
    label = text("Приклад інтерфейсу", "Interface example")
    sections = []

    def scene(index, kicker, title, content=""):
        sections.append(
            f'<section class="scene s{index}"><div class="eyebrow" data-safe>{kicker}</div><h1 class="follow-title" data-safe>{title}</h1>{content}</section>'
        )

    scene(
        0,
        f"DOTA 2 · {esc(hero_name)}",
        esc(hero_name) + "?" if jugg else text("Відволікло?", "Distracted?"),
        '<div class="follow-rating" data-safe>0–4 000 <span>MMR</span></div>' + art,
    )
    if jugg:
        scene(
            1,
            text("ПОРІВНЯЙ ЗІ СВОЇМИ МАТЧАМИ", "COMPARE WITH YOUR OTHER GAMES"),
            text("Фарм. Смерті.<br>Порівняння.", "Farm. Deaths.<br>Comparison."),
            f'<div class="screen score-pane"><img src="{review}"></div><div class="screen-note" data-safe>{label}</div>',
        )
    else:
        clock = '<svg viewBox="0 0 100 100" fill="none" stroke="currentColor" stroke-width="3"><circle cx="50" cy="50" r="44"/><path d="M50 20v30l22 15"/></svg>'
        scene(
            1,
            text("ЧАС ПІДКАЗКИ МАЄ ЗНАЧЕННЯ", "TIP TIMING MATTERS"),
            text("Вчасно?", "On time?"),
            f'<div class="timing-art">{clock}</div><div class="timing-note" data-safe>{esc(hero_name)}</div>',
        )
    if jugg:
        scene(
            2,
            label,
            text("Розбір<br>після матчу.", "Post-match<br>review."),
            f'<div class="review-detail"><img src="{review}"></div><div class="screen-note" data-safe>{label} · {esc(hero_name)}</div>',
        )
    else:
        scene(
            2,
            label,
            text("Підказки у грі.<br>Розбір після.", "In-game tips.<br>Match reviews."),
            f'<div class="screen"><img class="game-context" src="{game}"><div class="live-closeup"><img src="{game}"></div></div><div class="screen-note" data-safe>{label} · {text("Джагернаут", "Juggernaut")}</div>',
        )
    windows = '<div class="window-art"><i></i><i></i><i></i><i></i></div>'
    scene(
        3,
        "WARDLY",
        text("Безкоштовно.<br>Для Windows.", "Free.<br>For Windows."),
        windows
        + '<div class="free-note" data-safe>'
        + text("Добровільне бета-тестування", "Volunteer beta testing")
        + "</div>",
    )
    questions = (
        [
            text("Корисно?", "Useful?"),
            text("Зрозуміло?", "Clear?"),
            text("Є помилка?", "Something wrong?"),
        ]
        if jugg
        else [
            text("Допомогло?", "Helpful?"),
            text("Запізно?", "Too late?"),
            text("Помилка?", "Wrong advice?"),
        ]
    )
    rows = "".join(
        f'<div class="question q{i}"><span class="question-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">{base.ICONS[i]}</svg></span><b data-safe>{esc(q)}</b></div>'
        for i, q in enumerate(questions)
    )
    scene(
        4,
        text("ТВІЙ ЧЕСНИЙ ВІДГУК", "YOUR HONEST FEEDBACK"),
        "",
        '<div class="questions">' + rows + "</div>",
    )
    scene(5, text("ШУКАЄМО ДОБРОВОЛЬЦІВ", "VOLUNTEERS WANTED"), "0–4 000 MMR", art)
    c = base.COPY[language]
    sections.append(
        f"""<section class="scene s6"><div class="end-orbit"></div><div class="invite" data-safe>{text("Кілька матчів. Чесний відгук.", "A few games. Honest feedback.")}</div><div class="comment-card"><div class="comment-symbol"></div><b data-safe>{c["cta"]}</b></div><div class="comment-label" data-safe>{text("Напиши в коментарях", "Comment below")}</div><div class="address" data-safe>{c["site"]}</div><div class="free" data-safe>{c["free"]}</div></section>"""
    )
    root = Path(__file__).parent
    return base.document(
        language,
        timeline,
        captions,
        motion,
        f'<main data-creative="{creative}">' + "".join(sections) + "</main>",
        c,
        extra_css=(root / "beta_followups.css").read_text(),
        javascript=(root / "beta_followups.js").read_text(),
    )
