"""News («Новини»): the weekly meta post, its site pages and its Telegram text.

A post is a JSON file in data/news/posts/ written by `scripts/build_news.py meta`
from OpenDota's public hero statistics (the last 7 days of public matches, all
ranks): every hero's picks and wins for that week. Everything shown — the hero
lists, the change against the previous post, the Ukrainian and English texts —
is computed here from those numbers, so a page and its Telegram post always say
the same thing. scripts/build_site.py writes the pages (site/news.html,
site/news/<slug>.html and their /en/ copies); .github/workflows/news.yml makes
a post every Monday and sends it to the Telegram channel.
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
BASE = "https://luhovyimvp.dev"
# A hero picked in fewer matches is left out of the lists (a few lucky games).
MIN_PICK_RATE = 0.02
TOP = 5
MOVERS = 3
# A change under this many percentage points is noise, not news.
MIN_MOVE = 0.5

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
        "lead": "За останні 7 днів у публічних матчах Dota 2 зіграно близько {matches} ігор (дані OpenDota, усі ранги). Хто виграє найчастіше, кого беруть найбільше і хто змінився за тиждень.",
        "win_title": "Найчастіше виграють",
        "pick_title": "Найпопулярніші",
        "up_title": "За тиждень виросли",
        "down_title": "За тиждень впали",
        "col_hero": "Герой",
        "col_win": "Перемоги",
        "col_pick": "У матчах",
        "col_change": "Зміна",
        "note": "Враховано героїв, яких брали щонайменше в {min} % матчів.",
        "source": "Джерело: OpenDota, публічні матчі за {period}.",
        "cta_title": "Граєте на цих героях?",
        "cta_text": "Wardly підказує просто в матчі: темп добивань проти вашого суперника, предмети проти вражеського драфту, таймери й прокачку. Безкоштовно для Windows.",
        "download": "Завантажити для Windows",
        "share_title": "Поділіться з тіммейтами",
        "share_tg": "Надіслати в Telegram",
        "share_text": "Скиньте мету друзям перед вечором у Доті: з одного допису видно, кого брати й кого банити.",
        "list_title": "Новини",
        "list_lead": "Мета тижня щопонеділка: хто виграє, кого беруть і хто змінився. Ті самі дописи — у нашому Telegram-каналі.",
        "list_meta": "Огляд тижня за даними OpenDota.",
        "read": "Читати",
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
        "lead": "About {matches} public Dota 2 matches were played over the last 7 days (OpenDota data, all ranks). Who wins most, who is picked most and who changed this week.",
        "win_title": "Highest win rate",
        "pick_title": "Most picked",
        "up_title": "Up this week",
        "down_title": "Down this week",
        "col_hero": "Hero",
        "col_win": "Win rate",
        "col_pick": "Picked in",
        "col_change": "Change",
        "note": "Only heroes picked in at least {min}% of matches.",
        "source": "Source: OpenDota, public matches of {period}.",
        "cta_title": "Playing these heroes?",
        "cta_text": "Wardly tells you during the match: your last-hit pace against this opponent, items against the enemy draft, timers and skills. Free for Windows.",
        "download": "Download for Windows",
        "share_title": "Share it with your teammates",
        "share_tg": "Send in Telegram",
        "share_text": "Send the meta to your friends before tonight's games: one post shows whom to pick and whom to ban.",
        "list_title": "News",
        "list_lead": "The meta of the week every Monday: who wins, who is picked and who changed. The same posts go to our Telegram channel.",
        "list_meta": "A weekly overview from OpenDota data.",
        "read": "Read",
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


def meta_post(hero_stats: list[dict[str, Any]], today: date) -> dict[str, Any]:
    """A post from OpenDota's /heroStats: each hero's public picks and wins of the
    last 7 days (`pub_pick_trend` / `pub_win_trend`, one value per day)."""
    heroes = []
    for row in hero_stats:
        picks = sum(int(n or 0) for n in row.get("pub_pick_trend") or [])
        wins = sum(int(n or 0) for n in row.get("pub_win_trend") or [])
        name = row.get("localized_name")
        if isinstance(name, str) and picks > 0 and 0 <= wins <= picks:
            heroes.append({"id": int(row["id"]), "name": name, "picks": picks, "wins": wins})
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


def summary(post: dict[str, Any], previous: dict[str, Any] | None) -> dict[str, Any]:
    """The lists a post shows: matches, top win rate, most picked, movers."""
    heroes = post["heroes"]
    matches = sum(hero["picks"] for hero in heroes) / 10
    rows = {
        hero["name"]: {
            "name": hero["name"],
            "win": hero["wins"] / hero["picks"],
            "pick": hero["picks"] / matches,
        }
        for hero in heroes
    }
    eligible = [row for row in rows.values() if row["pick"] >= MIN_PICK_RATE]
    top_win = sorted(eligible, key=lambda row: (-row["win"], row["name"]))[:TOP]
    top_pick = sorted(rows.values(), key=lambda row: (-row["pick"], row["name"]))[:TOP]
    up: list[dict[str, Any]] = []
    down: list[dict[str, Any]] = []
    if previous is not None:
        before_matches = sum(hero["picks"] for hero in previous["heroes"]) / 10
        before = {
            hero["name"]: hero["wins"] / hero["picks"]
            for hero in previous["heroes"]
            if hero["picks"] / before_matches >= MIN_PICK_RATE
        }
        moves = [
            {**row, "change": (row["win"] - before[row["name"]]) * 100}
            for row in eligible
            if row["name"] in before
        ]
        up = sorted(
            (m for m in moves if m["change"] >= MIN_MOVE), key=lambda m: (-m["change"], m["name"])
        )[:MOVERS]
        down = sorted(
            (m for m in moves if m["change"] <= -MIN_MOVE), key=lambda m: (m["change"], m["name"])
        )[:MOVERS]
    return {"matches": matches, "win": top_win, "pick": top_pick, "up": up, "down": down}


def previous_of(post: dict[str, Any], posts: list[dict[str, Any]]) -> dict[str, Any] | None:
    older = [p for p in posts if p["date"] < post["date"]]
    return max(older, key=lambda p: p["date"]) if older else None


# --- words and numbers -----------------------------------------------------------------


def period(post: dict[str, Any], lang: str) -> str:
    start, end = date.fromisoformat(post["from"]), date.fromisoformat(post["to"])
    months = MONTHS_UK if lang == "uk" else MONTHS_EN
    if start.month == end.month:
        return f"{start.day}–{end.day} {months[end.month - 1]}"
    return f"{start.day} {months[start.month - 1]} – {end.day} {months[end.month - 1]}"


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
    return TEXT[lang]["lead"].format(matches=matches_text(data["matches"], lang))


# --- site pages ------------------------------------------------------------------------


def _table(
    rows: list[dict[str, Any]], lang: str, value: str, links: dict[str, str], prefix: str
) -> str:
    t = TEXT[lang]
    e = html.escape
    head = {"win": t["col_win"], "pick": t["col_pick"], "change": t["col_change"]}[value]
    body = []
    for row in rows:
        name = e(row["name"])
        if row["name"] in links:
            name = f'<a href="{prefix}heroes/{links[row["name"]]}.html">{name}</a>'
        shown = points(row["change"], lang) if value == "change" else percent(row[value], lang)
        body.append(f"                  <tr><td>{name}</td><td>{e(shown)}</td></tr>")
    rows_html = "\n".join(body)
    return f"""              <table class="pace">
                <thead><tr><th>{e(t["col_hero"])}</th><th>{e(head)}</th></tr></thead>
                <tbody>
{rows_html}
                </tbody>
              </table>"""


def post_main(
    post: dict[str, Any], data: dict[str, Any], lang: str, links: dict[str, str], home: str
) -> str:
    """The <main> of a post page; `home` leads to this language's home page."""
    t = TEXT[lang]
    e = html.escape
    page_url = f"{BASE}{'' if lang == 'uk' else '/en'}/news/{slug(post)}.html"
    blocks = [("win_title", data["win"], "win"), ("pick_title", data["pick"], "pick")]
    if data["up"]:
        blocks.append(("up_title", data["up"], "change"))
    if data["down"]:
        blocks.append(("down_title", data["down"], "change"))
    articles = "\n".join(
        f"""            <article class="mode">
              <h2>{e(t[key])}</h2>
{_table(rows, lang, value, links, home)}
            </article>"""
        for key, rows, value in blocks
    )
    share = html.escape(
        "https://t.me/share/url?"
        + urlencode({"url": f"{page_url}?ref=tg-share", "text": title(post, lang)})
    )
    min_rate = f"{MIN_PICK_RATE * 100:.0f}"
    return f"""    <main id="main">
      <section class="page-head">
        <div class="wrap">
          <p class="mode-tag"><a href="{home}news.html">{e(t["list_title"])}</a> · <time datetime="{post["date"]}">{e(post["date"])}</time></p>
          <h1>{e(title(post, lang))}</h1>
          <p class="lead">{e(lead(post, data, lang))}</p>
        </div>
      </section>

      <section class="section section-tight">
        <div class="wrap">
          <div class="modes">
{articles}
          </div>
          <p class="mode-note">{e(t["note"].format(min=min_rate))} {e(t["source"].format(period=period(post, lang)))}</p>
        </div>
      </section>

      <section class="section section-alt">
        <div class="wrap hero-more">
          <div>
            <h2>{e(t["share_title"])}</h2>
            <p>{e(t["share_text"])}</p>
            <a class="btn btn-outline btn-lg" href="{share}" rel="noopener">{e(t["share_tg"])}</a>
          </div>
          <div class="hero-cta">
            <h2>{e(t["cta_title"])}</h2>
            <p>{e(t["cta_text"])}</p>
            <a class="btn btn-primary btn-lg js-download" href="https://github.com/makquella/dota-ai-coach/releases/latest">
              <svg class="i" aria-hidden="true"><use href="#i-windows" /></svg>
              <span>{e(t["download"])}</span>
            </a>
          </div>
        </div>
      </section>
    </main>"""


def list_main(posts: list[dict[str, Any]], lang: str, home: str, up: str) -> str:
    t = TEXT[lang]
    e = html.escape
    items = "\n".join(
        f"""            <article class="mode">
              <p class="mode-tag"><time datetime="{post["date"]}">{e(post["date"])}</time></p>
              <h2><a href="news/{slug(post)}.html">{e(title(post, lang))}</a></h2>
              <p class="mode-note">{e(t["list_meta"])}</p>
            </article>"""
        for post in posts
    )
    return f"""    <main id="main">
      <section class="page-head">
        <div class="wrap">
          <h1>{e(t["list_title"])}</h1>
          <p class="lead">{e(t["list_lead"])}</p>
        </div>
      </section>

      <section class="section section-tight">
        <div class="wrap">
          <div class="modes">
{items}
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


# Telegram's limit for one message is 4096 characters.
TELEGRAM_LIMIT = 3800


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
