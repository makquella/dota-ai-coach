"""News («Новини»): the weekly meta post, its site pages and its Telegram text.

A post is a JSON file in data/news/posts/ written by `scripts/build_news.py meta`
from OpenDota's public hero statistics (the last 7 days of public matches, all
ranks): every hero's picks and wins for that week, day by day. Everything shown —
the highlights, the hero lists, who rose and who fell, the Ukrainian and English
texts — is computed here from those numbers, so a page and its Telegram post
always say the same thing. scripts/build_site.py writes the pages (site/news.html,
site/news/<slug>.html and their /en/ copies); .github/workflows/news.yml makes a
post every Monday and sends it to the Telegram channel.

Who changed: against the previous post when there is one (week over week), else
inside the week — the last three days against the first three.
"""

from __future__ import annotations

import html
import json
import re
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parents[1]
POSTS = ROOT / "data" / "news" / "posts"
HERO_IMAGES = ROOT / "site" / "assets" / "heroes"
BASE = "https://luhovyimvp.dev"
CHANNEL = "https://t.me/wardlydota"
# A hero picked in fewer matches is left out of the lists (a few lucky games).
MIN_PICK_RATE = 0.02
TOP = 5
MOVERS = 3
# A change under this many percentage points is noise, not news.
MIN_MOVE = 0.5
# Inside the week: each half needs this many picks of the hero to compare.
HALF_MIN_PICKS = 2000
# The win-rate bars start here, so that 52 % and 55 % look different.
WIN_BAR_FLOOR = 0.45
# Telegram's limit for one message is 4096 characters.
TELEGRAM_LIMIT = 3800

MONTHS_UK = (
    "січня",
    "лютого",
    "березня",
    "квітня",
    "травня",
    "червня",
    "липня",
    "серпня",
    "вересня",
    "жовтня",
    "листопада",
    "грудня",
)
MONTHS_EN = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)

TEXT = {
    "uk": {
        "title": "Мета тижня: {period}",
        "lead": "За останні 7 днів у публічних матчах Dota 2 зіграно близько {matches} ігор (дані OpenDota, усі ранги).",
        "lead_more": "Хто виграє найчастіше, кого беруть найбільше і хто змінився за тиждень.",
        "lead_short": "Хто виграє найчастіше і кого беруть найбільше.",
        "tile_win": "Найсильніший тижня",
        "tile_pick": "Найпопулярніший",
        "tile_up": "Злетів за тиждень",
        "tile_matches": "Ігор за тиждень",
        "tile_win_value": "{v} перемог",
        "tile_pick_value": "у {v} матчів",
        "tile_up_value": "{v} перемог",
        "tile_matches_value": "публічні матчі, усі ранги",
        "win_title": "Найчастіше виграють",
        "pick_title": "Найпопулярніші",
        "up_title": "Ростуть",
        "down_title": "Падають",
        "win_hint": "Відсоток перемог серед героїв, яких брали хоча б у {min} % матчів.",
        "pick_hint": "У скількох матчах тижня був цей герой.",
        "moves_week": "Відсоток перемог порівняно з минулим тижнем.",
        "moves_inside": "Відсоток перемог за останні три дні порівняно з першими трьома днями тижня.",
        "source": "Джерело: OpenDota, публічні матчі за {period}.",
        "cta_title": "Граєте на цих героях?",
        "cta_text": "Wardly підказує просто в матчі: темп добивань проти вашого суперника, предмети проти вражеського драфту, таймери й прокачку. Безкоштовно для Windows.",
        "download": "Завантажити для Windows",
        "share_title": "Поділіться з тіммейтами",
        "share_text": "Скиньте мету друзям перед вечором у Доті: з одного допису видно, кого брати й кого банити.",
        "share_tg": "Надіслати в Telegram",
        "channel": "Канал @wardlydota",
        "list_title": "Новини",
        "list_lead": "Мета тижня щопонеділка: хто виграє, кого беруть і хто змінився. Ті самі дописи й нові версії — у нашому Telegram-каналі.",
        "list_channel": "Підписатися на канал @wardlydota",
        "list_top": "Найсильніший: {hero}, {v}",
        "changelog": "Що нового в застосунку →",
        "tg_more": "Повна таблиця",
        "tg_win": "{v} перемог",
        "tg_pick": "у {v} матчів",
        "tg_app": "Wardly — безкоштовний тренер просто в грі",
        "pp": "п. п.",
        "million": "{n} млн",
        "thousand": "{n} тис.",
    },
    "en": {
        "title": "Meta of the week: {period}",
        "lead": "About {matches} public Dota 2 matches were played over the last 7 days (OpenDota data, all ranks).",
        "lead_more": "Who wins most, who is picked most and who changed this week.",
        "lead_short": "Who wins most and who is picked most.",
        "tile_win": "Strongest this week",
        "tile_pick": "Most picked",
        "tile_up": "Biggest riser",
        "tile_matches": "Games this week",
        "tile_win_value": "{v} win rate",
        "tile_pick_value": "in {v} of matches",
        "tile_up_value": "{v} win rate",
        "tile_matches_value": "public matches, all ranks",
        "win_title": "Highest win rate",
        "pick_title": "Most picked",
        "up_title": "Rising",
        "down_title": "Falling",
        "win_hint": "Win rate of heroes picked in at least {min}% of matches.",
        "pick_hint": "How many of the week's matches had the hero.",
        "moves_week": "Win rate against the previous week.",
        "moves_inside": "Win rate of the last three days against the first three days of the week.",
        "source": "Source: OpenDota, public matches of {period}.",
        "cta_title": "Playing these heroes?",
        "cta_text": "Wardly tells you during the match: your last-hit pace against this opponent, items against the enemy draft, timers and skills. Free for Windows.",
        "download": "Download for Windows",
        "share_title": "Share it with your teammates",
        "share_text": "Send the meta to your friends before tonight's games: one post shows whom to pick and whom to ban.",
        "share_tg": "Send in Telegram",
        "channel": "Channel @wardlydota",
        "list_title": "News",
        "list_lead": "The meta of the week every Monday: who wins, who is picked and who changed. The same posts and new versions go to our Telegram channel.",
        "list_channel": "Follow @wardlydota on Telegram",
        "list_top": "Strongest: {hero}, {v}",
        "changelog": "What's new in the app →",
        "tg_more": "Full table",
        "tg_win": "{v} win rate",
        "tg_pick": "in {v} of matches",
        "tg_app": "Wardly — a free coach right in your game",
        "pp": "pp",
        "million": "{n} million",
        "thousand": "{n} thousand",
    },
}


# --- data ---------------------------------------------------------------------------


def load_posts() -> list[dict[str, Any]]:
    """Every post, newest first."""
    posts = [json.loads(path.read_text(encoding="utf-8")) for path in POSTS.glob("*.json")]
    return sorted(posts, key=lambda post: post["date"], reverse=True)


def slug(post: dict[str, Any]) -> str:
    return f"{post['date']}-meta"


def _days(values: Any) -> list[int] | None:
    if not isinstance(values, list) or len(values) != 7:
        return None
    try:
        days = [int(n or 0) for n in values]
    except (TypeError, ValueError):
        return None
    return days if all(n >= 0 for n in days) else None


def meta_post(hero_stats: list[dict[str, Any]], today: date) -> dict[str, Any]:
    """A post from OpenDota's /heroStats: each hero's public picks and wins of the
    last 7 days, day by day (`pub_pick_trend` / `pub_win_trend`)."""
    heroes = []
    for row in hero_stats:
        picks_days, wins_days = _days(row.get("pub_pick_trend")), _days(row.get("pub_win_trend"))
        name = row.get("localized_name")
        if not isinstance(name, str) or picks_days is None or wins_days is None:
            continue
        picks, wins = sum(picks_days), sum(wins_days)
        if picks <= 0 or not 0 <= wins <= picks:
            continue
        key = str(row.get("name") or "").removeprefix("npc_dota_hero_")
        heroes.append(
            {
                "id": int(row["id"]),
                "name": name,
                "key": key if re.fullmatch(r"[a-z0-9_]+", key) else "",
                "picks": picks,
                "wins": wins,
                "picks_days": picks_days,
                "wins_days": wins_days,
            }
        )
    if len(heroes) < 50:
        raise ValueError(f"OpenDota returned {len(heroes)} heroes with picks: too few")
    start = date.fromordinal(today.toordinal() - 6)
    return {
        "kind": "meta",
        "date": today.isoformat(),
        "from": start.isoformat(),
        "to": today.isoformat(),
        "source": "OpenDota /api/heroStats (pub_pick_trend, pub_win_trend)",
        "heroes": sorted(heroes, key=lambda hero: hero["id"]),
    }


def _win_rates(post: dict[str, Any]) -> dict[str, float]:
    matches = sum(hero["picks"] for hero in post["heroes"]) / 10
    return {
        hero["name"]: hero["wins"] / hero["picks"]
        for hero in post["heroes"]
        if hero["picks"] / matches >= MIN_PICK_RATE
    }


def _inside_week(post: dict[str, Any]) -> dict[str, tuple[float, float]]:
    """{hero: (win rate of the first three days, of the last three)}."""
    halves = {}
    for hero in post["heroes"]:
        picks, wins = hero.get("picks_days"), hero.get("wins_days")
        if not picks or not wins:
            continue
        early_picks, late_picks = sum(picks[:3]), sum(picks[4:])
        if min(early_picks, late_picks) < HALF_MIN_PICKS:
            continue
        halves[hero["name"]] = (sum(wins[:3]) / early_picks, sum(wins[4:]) / late_picks)
    return halves


def summary(post: dict[str, Any], previous: dict[str, Any] | None) -> dict[str, Any]:
    """What a post shows: matches, top win rate, most picked, who rose and fell,
    and `moves` — "week" (against the previous post), "inside" (inside the week)
    or None when neither can be told."""
    heroes = post["heroes"]
    matches = sum(hero["picks"] for hero in heroes) / 10
    rows = {
        hero["name"]: {
            "name": hero["name"],
            "key": hero.get("key") or "",
            "win": hero["wins"] / hero["picks"],
            "pick": hero["picks"] / matches,
        }
        for hero in heroes
    }
    eligible = [row for row in rows.values() if row["pick"] >= MIN_PICK_RATE]
    top_win = sorted(eligible, key=lambda row: (-row["win"], row["name"]))[:TOP]
    top_pick = sorted(rows.values(), key=lambda row: (-row["pick"], row["name"]))[:TOP]
    moves: list[dict[str, Any]] = []
    basis = None
    if previous is not None:
        before = _win_rates(previous)
        moves = [
            {**row, "change": (row["win"] - before[row["name"]]) * 100}
            for row in eligible
            if row["name"] in before
        ]
        basis = "week" if moves else None
    if basis is None:
        halves = _inside_week(post)
        moves = [
            {**row, "change": (halves[row["name"]][1] - halves[row["name"]][0]) * 100}
            for row in eligible
            if row["name"] in halves
        ]
        basis = "inside" if moves else None
    up = sorted(
        (m for m in moves if m["change"] >= MIN_MOVE), key=lambda m: (-m["change"], m["name"])
    )[:MOVERS]
    down = sorted(
        (m for m in moves if m["change"] <= -MIN_MOVE), key=lambda m: (m["change"], m["name"])
    )[:MOVERS]
    return {
        "matches": matches,
        "win": top_win,
        "pick": top_pick,
        "up": up,
        "down": down,
        "moves": basis if up or down else None,
    }


def previous_of(post: dict[str, Any], posts: list[dict[str, Any]]) -> dict[str, Any] | None:
    older = [p for p in posts if p["date"] < post["date"]]
    return max(older, key=lambda p: p["date"]) if older else None


def image_keys(data: dict[str, Any]) -> set[str]:
    """The heroes whose pictures a post's page shows."""
    rows = data["win"] + data["pick"] + data["up"] + data["down"]
    return {row["key"] for row in rows if row.get("key")}


# --- words and numbers -----------------------------------------------------------------


def period(post: dict[str, Any], lang: str) -> str:
    start, end = date.fromisoformat(post["from"]), date.fromisoformat(post["to"])
    months = MONTHS_UK if lang == "uk" else MONTHS_EN
    if start.month == end.month:
        return f"{start.day}–{end.day} {months[end.month - 1]}"
    return f"{start.day} {months[start.month - 1]} – {end.day} {months[end.month - 1]}"


def long_date(value: str, lang: str) -> str:
    day = date.fromisoformat(value)
    months = MONTHS_UK if lang == "uk" else MONTHS_EN
    return f"{day.day} {months[day.month - 1]} {day.year}"


def percent(value: float, lang: str, digits: int = 1) -> str:
    text = f"{value * 100:.{digits}f}"
    return f"{text.replace('.', ',')} %" if lang == "uk" else f"{text}%"


def points(value: float, lang: str) -> str:
    text = f"{value:+.1f}".replace("-", "−")
    return (
        f"{text.replace('.', ',')} {TEXT[lang]['pp']}"
        if lang == "uk"
        else f"{text} {TEXT[lang]['pp']}"
    )


def matches_text(matches: float, lang: str) -> str:
    t = TEXT[lang]
    if matches >= 1_000_000:
        n = f"{matches / 1_000_000:.1f}"
        return t["million"].format(n=n.replace(".", ",") if lang == "uk" else n)
    return t["thousand"].format(n=round(matches / 1000))


def title(post: dict[str, Any], lang: str) -> str:
    return TEXT[lang]["title"].format(period=period(post, lang))


def lead(post: dict[str, Any], data: dict[str, Any], lang: str) -> str:
    t = TEXT[lang]
    more = t["lead_more"] if data.get("moves") else t["lead_short"]
    return f"{t['lead'].format(matches=matches_text(data['matches'], lang))} {more}"


# --- site pages ------------------------------------------------------------------------

_ICON = {
    "trophy": '<path d="M6 9H4.5a2.5 2.5 0 0 1 0-5H6M18 9h1.5a2.5 2.5 0 0 0 0-5H18M4 22h16M10 14.66V17c0 .55-.47.98-.97 1.21C7.85 18.75 7 20.24 7 22M14 14.66V17c0 .55.47.98.97 1.21C16.15 18.75 17 20.24 17 22M18 2H6v7a6 6 0 0 0 12 0V2Z" />',
    "flame": '<path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.07-2.14-.22-4.05 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.15.43-2.29 1-3a2.5 2.5 0 0 0 2.5 2.5Z" />',
    "up": '<path d="m22 7-8.5 8.5-5-5L2 17" /><path d="M16 7h6v6" />',
    "down": '<path d="m22 17-8.5-8.5-5 5L2 7" /><path d="M16 17h6v-6" />',
    "swords": '<path d="M14.5 17.5 3 6V3h3l11.5 11.5M13 19l6-6M16 16l4 4M19 21l2-2M9.5 6.5 21 18M14.5 6.5 18 3h3v3l-3.5 3.5M5 14l4 4M7 17l-3 3M3 19l2 2" />',
    "send": '<path d="m22 2-7 20-4-9-9-4Z" /><path d="M22 2 11 13" />',
}


def _icon(name: str) -> str:
    return (
        '<svg class="news-icon" viewBox="0 0 24 24" aria-hidden="true" fill="none" '
        'stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        f"{_ICON[name]}</svg>"
    )


def _picture(row: dict[str, Any], up: str, images: set[str], size: str) -> str:
    """The hero's picture from site/assets/heroes, else their initials."""
    key = row.get("key") or ""
    if key in images:
        return (
            f'<img class="hero-pic hero-pic-{size}" src="{up}assets/heroes/{key}.webp" '
            f'alt="" width="256" height="144" loading="lazy" />'
        )
    initials = "".join(word[0] for word in row["name"].split()[:2])
    return f'<span class="hero-pic hero-pic-{size} hero-pic-none" aria-hidden="true">{html.escape(initials)}</span>'


def _name(row: dict[str, Any], links: dict[str, str], home: str) -> str:
    name = html.escape(row["name"])
    if row["name"] in links:
        return f'<a href="{home}heroes/{links[row["name"]]}.html">{name}</a>'
    return name


def _bar(value: str, width: float, tone: str = "") -> str:
    width = max(4.0, min(100.0, width))
    return (
        f'<span class="bar{(" bar-" + tone) if tone else ""}" aria-hidden="true">'
        f'<span style="width: {width:.0f}%"></span></span>'
        f'<span class="row-value">{html.escape(value)}</span>'
    )


def _rows(
    rows: list[dict[str, Any]],
    lang: str,
    kind: str,
    links: dict[str, str],
    home: str,
    up: str,
    images: set[str],
) -> str:
    if kind == "win":
        floor, top = WIN_BAR_FLOOR, max(row["win"] for row in rows)
        measured = [
            ((row["win"] - floor) / max(top - floor, 1e-9), percent(row["win"], lang))
            for row in rows
        ]
    elif kind == "pick":
        top = max(row["pick"] for row in rows)
        measured = [(row["pick"] / top, percent(row["pick"], lang)) for row in rows]
    else:
        top = max(abs(row["change"]) for row in rows)
        measured = [(abs(row["change"]) / top, points(row["change"], lang)) for row in rows]
    tone = kind if kind in ("up", "down") else ""
    items = "\n".join(
        f"""                <li class="hero-row">
                  <span class="row-rank">{index}</span>
                  {_picture(row, up, images, "sm")}
                  <span class="row-name">{_name(row, links, home)}</span>
                  {_bar(value, share * 100, tone)}
                </li>"""
        for index, (row, (share, value)) in enumerate(zip(rows, measured, strict=True), 1)
    )
    return f'              <ol class="hero-rows">\n{items}\n              </ol>'


def _card(icon: str, heading: str, hint: str, body: str, extra: str = "") -> str:
    e = html.escape
    return f"""            <article class="mode news-card{extra}">
              <h2 class="news-card-title">{_icon(icon)}<span>{e(heading)}</span></h2>
              <p class="mode-note news-hint">{e(hint)}</p>
{body}
            </article>"""


def _tile(icon: str, label: str, picture: str, name: str, value: str, tone: str = "") -> str:
    e = html.escape
    return f"""            <div class="news-tile{(" news-tile-" + tone) if tone else ""}">
              {picture}
              <div class="news-tile-text">
                <p class="news-tile-label">{_icon(icon)}{e(label)}</p>
                <p class="news-tile-name">{name}</p>
                <p class="news-tile-value">{e(value)}</p>
              </div>
            </div>"""


def post_main(
    post: dict[str, Any],
    data: dict[str, Any],
    lang: str,
    links: dict[str, str],
    home: str,
    up: str = "../",
    images: set[str] | None = None,
) -> str:
    """The <main> of a post page; `home` leads to this language's home page and
    `up` to the site root; `images` are the hero pictures the site has."""
    t = TEXT[lang]
    e = html.escape
    images = images or set()
    page_url = f"{BASE}{'' if lang == 'uk' else '/en'}/news/{slug(post)}.html"
    best, popular = data["win"][0], data["pick"][0]
    tiles = [
        _tile(
            "trophy",
            t["tile_win"],
            _picture(best, up, images, "lg"),
            _name(best, links, home),
            t["tile_win_value"].format(v=percent(best["win"], lang)),
        ),
        _tile(
            "flame",
            t["tile_pick"],
            _picture(popular, up, images, "lg"),
            _name(popular, links, home),
            t["tile_pick_value"].format(v=percent(popular["pick"], lang)),
        ),
    ]
    if data["up"]:
        riser = data["up"][0]
        tiles.append(
            _tile(
                "up",
                t["tile_up"],
                _picture(riser, up, images, "lg"),
                _name(riser, links, home),
                f"{points(riser['change'], lang)} · {t['tile_up_value'].format(v=percent(riser['win'], lang))}",
                "up",
            )
        )
    else:
        tiles.append(
            _tile(
                "swords",
                t["tile_matches"],
                "",
                e(matches_text(data["matches"], lang)),
                t["tile_matches_value"],
            )
        )
    min_rate = f"{MIN_PICK_RATE * 100:.0f}"
    cards = [
        _card(
            "trophy",
            t["win_title"],
            t["win_hint"].format(min=min_rate),
            _rows(data["win"], lang, "win", links, home, up, images),
        ),
        _card(
            "flame",
            t["pick_title"],
            t["pick_hint"],
            _rows(data["pick"], lang, "pick", links, home, up, images),
        ),
    ]
    moves_hint = t["moves_week"] if data.get("moves") == "week" else t["moves_inside"]
    if data["up"]:
        cards.append(
            _card(
                "up",
                t["up_title"],
                moves_hint,
                _rows(data["up"], lang, "up", links, home, up, images),
                " news-card-up",
            )
        )
    if data["down"]:
        cards.append(
            _card(
                "down",
                t["down_title"],
                moves_hint,
                _rows(data["down"], lang, "down", links, home, up, images),
                " news-card-down",
            )
        )
    share = html.escape(
        "https://t.me/share/url?"
        + urlencode({"url": f"{page_url}?ref=tg-share", "text": title(post, lang)})
    )
    tiles_html = "\n".join(tiles)
    cards_html = "\n".join(cards)
    return f"""    <main id="main">
      <section class="page-head">
        <div class="wrap">
          <p class="mode-tag"><a href="{home}news.html">{e(t["list_title"])}</a> · <time datetime="{post["date"]}">{e(long_date(post["date"], lang))}</time></p>
          <h1>{e(title(post, lang))}</h1>
          <p class="lead">{e(lead(post, data, lang))}</p>
          <div class="news-tiles">
{tiles_html}
          </div>
        </div>
      </section>

      <section class="section section-tight">
        <div class="wrap">
          <div class="news-cards">
{cards_html}
          </div>
          <p class="mode-note news-source">{e(t["source"].format(period=period(post, lang)))}</p>
        </div>
      </section>

      <section class="section section-alt">
        <div class="wrap news-actions">
          <div class="hero-cta">
            <h2>{e(t["share_title"])}</h2>
            <p>{e(t["share_text"])}</p>
            <div class="cta-row">
              <a class="btn btn-primary btn-lg" href="{share}" rel="noopener">{_icon("send")}<span>{e(t["share_tg"])}</span></a>
              <a class="btn btn-outline btn-lg" href="{CHANNEL}" rel="noopener">{e(t["channel"])}</a>
            </div>
          </div>
          <div class="hero-cta">
            <h2>{e(t["cta_title"])}</h2>
            <p>{e(t["cta_text"])}</p>
            <div class="cta-row">
              <a class="btn btn-primary btn-lg js-download" href="https://github.com/makquella/dota-ai-coach/releases/latest">
                <svg class="i" aria-hidden="true"><use href="#i-windows" /></svg>
                <span>{e(t["download"])}</span>
              </a>
            </div>
          </div>
        </div>
      </section>
    </main>"""


def list_main(
    posts: list[dict[str, Any]],
    lang: str,
    home: str,
    up: str,
    images: set[str] | None = None,
) -> str:
    t = TEXT[lang]
    e = html.escape
    images = images or set()
    items = []
    for post in posts:
        data = summary(post, previous_of(post, posts))
        best = data["win"][0]
        items.append(
            f"""            <a class="mode news-item" href="news/{slug(post)}.html">
              {_picture(best, up, images, "lg")}
              <span class="news-item-text">
                <span class="mode-tag"><time datetime="{post["date"]}">{e(long_date(post["date"], lang))}</time></span>
                <span class="news-item-title">{e(title(post, lang))}</span>
                <span class="mode-note">{e(t["list_top"].format(hero=best["name"], v=percent(best["win"], lang)))}</span>
              </span>
            </a>"""
        )
    items_html = "\n".join(items)
    return f"""    <main id="main">
      <section class="page-head">
        <div class="wrap">
          <h1>{e(t["list_title"])}</h1>
          <p class="lead">{e(t["list_lead"])}</p>
          <div class="cta-row news-list-cta">
            <a class="btn btn-primary btn-lg" href="{CHANNEL}" rel="noopener">{_icon("send")}<span>{e(t["list_channel"])}</span></a>
          </div>
        </div>
      </section>

      <section class="section section-tight">
        <div class="wrap">
          <div class="news-list">
{items_html}
          </div>
          <p class="note"><a href="{up}changelog.html">{e(t["changelog"])}</a></p>
        </div>
      </section>
    </main>"""


# --- Telegram -------------------------------------------------------------------------------


def telegram_meta(post: dict[str, Any], data: dict[str, Any], lang: str = "uk") -> str:
    """The channel post (Telegram HTML): the same lists, short."""
    t = TEXT[lang]
    e = html.escape
    lines = [f"<b>{e(title(post, lang))}</b>", "", e(lead(post, data, lang))]

    def block(icon: str, key: str, rows: list[dict[str, Any]], value: str) -> None:
        if not rows:
            return
        lines.extend(["", f"{icon} <b>{e(t[key])}</b>"])
        for index, row in enumerate(rows, 1):
            if value == "change":
                shown = points(row["change"], lang)
            else:
                shown = t[f"tg_{value}"].format(v=percent(row[value], lang))
            lines.append(f"{index}. {e(row['name'])} — {e(shown)}")

    block("🏆", "win_title", data["win"], "win")
    block("🔥", "pick_title", data["pick"], "pick")
    block("📈", "up_title", data["up"], "change")
    block("📉", "down_title", data["down"], "change")
    prefix = "" if lang == "uk" else "/en"
    lines.extend(
        [
            "",
            f"{e(t['tg_more'])}: {BASE}{prefix}/news/{slug(post)}.html?ref=tg",
            f"{e(t['tg_app'])}: {BASE}{prefix}/?ref=tg",
        ]
    )
    return "\n".join(lines)


def telegram_release(version: str, notes: str) -> str:
    """A release post from docs/release-notes/v<version>.md (its Ukrainian part),
    cut at a bullet when it would not fit one message."""
    uk = notes.split("\n---", 1)[0]
    lines = [f"<b>Wardly {html.escape(version)}</b>", ""]
    for raw in uk.splitlines():
        line = raw.strip()
        if not line or line.startswith("## "):
            continue
        text = html.escape(line[2:] if line.startswith("- ") else line, quote=False)
        text = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", text)
        text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
        lines.append(f"• {text}" if line.startswith("- ") else text)
    while len("\n".join(lines)) > TELEGRAM_LIMIT and len(lines) > 3:
        lines.pop()
    lines.extend(
        [
            "",
            f"Що нового: {BASE}/changelog.html?ref=tg#v{version}",
            f"Завантажити: {BASE}/?ref=tg",
        ]
    )
    return "\n".join(lines)
