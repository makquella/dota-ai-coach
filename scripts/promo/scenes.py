"""The video as one HTML page (1080x1920) drawn frame by frame: render.py
calls window.renderAt(t) and takes a screenshot per frame, so every frame is
exact and repeatable (no CSS animations racing the screenshots).

Look: the site's dark brand (Montserrat / Inter, the red accent), Valve's
hero renders, the real overlay card (frontend/launcher/overlay/styles.css),
in-game screenshots behind. TikTok, Reels and Shorts cover the bottom ~420 px
and the right ~140 px with their own buttons: the content stays inside
SAFE (top 200 .. bottom 1500, left 72 .. right 940)."""

from __future__ import annotations

import html
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SITE = ROOT / "site"
LAUNCHER = ROOT / "frontend" / "launcher"
WIDTH, HEIGHT = 1080, 1920
FPS = 30
CROSSFADE = 0.25
SCENE_PAD = 0.45  # seconds of picture after the voice of a scene ends
MIN_SCENE = 2.2
SUB_WORDS, SUB_CHARS = 5, 30

PILLS = {
    "coach": "Wardly у грі",
    "meta": "Мета тижня",
    "hero": "Герой",
    "fact": "Факт тижня",
    "release": "Оновлення",
}
BACKGROUNDS = (
    "fight.jpg",
    "dark.jpg",
    "forest.jpg",
    "chrono.jpg",
    "hook.jpg",
    "base.jpg",
)
ICONS = {
    "heart": '<path d="M12 21s-7.5-4.6-9.6-9.2C.9 8.5 3 5 6.6 5c2 0 3.4 1.1 4.4 2.5C12 6.1 13.4 5 15.4 5 19 5 21.1 8.5 19.6 11.8 17.5 16.4 12 21 12 21z"/>',
    "shield": '<path d="M12 3 4 6v6c0 4.4 3.4 8.5 8 9 4.6-.5 8-4.6 8-9V6z"/>',
    "coins": '<circle cx="9" cy="9" r="6"/><path d="M15.5 9.5a6 6 0 1 1-6 6"/>',
    "spark": '<path d="M12 2v6M12 16v6M2 12h6M16 12h6M5 5l4 4M15 15l4 4M19 5l-4 4M9 15l-4 4"/>',
    "swords": '<path d="M14.5 17.5 3 6V3h3l11.5 11.5M13 19l6-6M16 16l4 4M19 21l2-2"/>',
}


def uri(path: Path) -> str:
    return path.resolve().as_uri()


def e(text: Any) -> str:
    return html.escape(str(text), quote=True)


def icon(name: str) -> str:
    body = ICONS.get(name, ICONS["spark"])
    return (
        '<svg class="ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
        f'stroke-linecap="round" stroke-linejoin="round">{body}</svg>'
    )


def subtitle_chunks(text: str, start: float, end: float) -> list[dict[str, Any]]:
    """The scene's voice text in short lines, each on screen for its share of the time."""
    words = text.split()
    lines: list[str] = []
    current: list[str] = []
    for word in words:
        trial = " ".join([*current, word])
        if current and (len(current) >= SUB_WORDS or len(trial) > SUB_CHARS):
            lines.append(" ".join(current))
            current = [word]
        else:
            current.append(word)
        if re.search(r"[.!?:]$", word) and current:
            lines.append(" ".join(current))
            current = []
    if current:
        lines.append(" ".join(current))
    total = sum(len(line) + 4 for line in lines) or 1
    out, at = [], start
    for line in lines:
        span = (end - start) * (len(line) + 4) / total
        out.append({"text": line, "start": round(at, 3), "end": round(at + span, 3)})
        at += span
    return out


def timeline(
    scenes: list[dict[str, Any]], voice_seconds: list[float | None]
) -> list[dict[str, Any]]:
    """Start and end of each scene: its voice plus a short pause (or a reading
    time by length when silent), never shorter than MIN_SCENE."""
    out, at = [], 0.0
    for scene, seconds in zip(scenes, voice_seconds, strict=True):
        spoken = seconds if seconds is not None else max(1.5, len(scene["voice"]) / 15)
        length = max(MIN_SCENE, spoken + SCENE_PAD)
        if scene["kind"] == "cta":
            length += 0.8  # the end card stays a moment
        voice_end = at + (seconds if seconds is not None else spoken)
        out.append(
            {
                **scene,
                "start": round(at, 3),
                "end": round(at + length, 3),
                # The hook's headline is its voice: no subtitles over it.
                "subs": []
                if scene["kind"] == "hook"
                else subtitle_chunks(scene["voice"], at + 0.05, voice_end),
            }
        )
        at += length
    return out


# --- scene bodies -----------------------------------------------------------------------


def hero_art(assets: dict[str, str], key: str | None, cls: str = "art") -> str:
    if not key:
        return ""
    src = assets.get(f"render:{key}") or assets.get(f"small:{key}")
    return f'<img class="{cls}" src="{e(src)}" alt="">' if src else ""


def body_hook(scene: dict[str, Any], assets: dict[str, str]) -> str:
    d = scene["data"]
    sub = (
        f'<div class="kicker" data-at="0.15" data-anim="up">{e(d["sub"])}</div>'
        if d.get("sub")
        else ""
    )
    art = hero_art(assets, d.get("hero"), "art big")
    words = " ".join(
        f'<span data-at="{0.25 + i * 0.07:.2f}" data-anim="up">{e(w)}</span>'
        for i, w in enumerate(scene["voice"].split())
    )
    length = len(scene["voice"])
    size = 92 if length <= 40 else 78 if length <= 64 else 66
    return f"""<div class="hook">{art and f'<div class="halo"></div>{art}'}
<div class="hook-text">{sub}<h1 style="font-size:{size}px">{words}</h1></div></div>"""


def body_card(scene: dict[str, Any], assets: dict[str, str]) -> str:
    d = scene["data"]
    urgent = d.get("mode") == "urgent"
    label = "Терміново" if urgent else "Порада"
    classes = "overlay-shell " + ("urgent priority-high" if urgent else "priority-medium")
    moment = d.get("moment")
    hud = ""
    if moment == "fall":
        hud = (
            '<div class="hud" data-at="0"><div class="hp"><i data-hp="1"></i></div><b>HP</b></div>'
        )
    elif moment == "stun":
        hud = '<div class="hud stun" data-at="0" data-anim="pop"><span>ОГЛУШЕННЯ</span></div>'
    portrait = hero_art(assets, d.get("hero"), "portrait")
    return f"""<div class="game"></div>{portrait}
{hud}
<div class="card-wrap" data-at="0.55" data-anim="left">
  <section class="{classes}">
    <div class="top-row"><span class="dot"></span><span class="label">{label}</span></div>
    <p class="action">{e(d["action"])}</p>
    <p class="reason">{e(d.get("reason", ""))}</p>
  </section>
  <div class="card-note">так виглядає підказка поверх Доти</div>
</div>"""


def body_stat(scene: dict[str, Any], assets: dict[str, str]) -> str:
    d = scene["data"]
    value = str(d["value"])
    match = re.match(r"^([+-]?)(\d+(?:,\d+)?)(.*)$", value)
    if match:
        sign, number, rest = match.groups()
        decimals = len(number.split(",")[1]) if "," in number else 0
        target = float(number.replace(",", "."))
        big = (
            f'<b class="num" data-count="{target}" data-decimals="{decimals}" '
            f'data-prefix="{e(sign)}" data-suffix="{e(rest)}" data-at="0.2">{e(value)}</b>'
        )
    else:
        big = f'<b class="num" data-at="0.2" data-anim="pop">{e(value)}</b>'
    art = hero_art(assets, d.get("hero"), "art side")
    return f"""<div class="stat">{art}<div class="stat-box">{big}
<p data-at="0.5" data-anim="up">{e(d["label"])}</p></div></div>"""


def body_list(scene: dict[str, Any], assets: dict[str, str]) -> str:
    d = scene["data"]
    rows = []
    for i, row in enumerate(d["rows"]):
        at = 0.3 + i * 0.55
        pic = assets.get(f"small:{row['key']}", "")
        width = max(0.0, min(1.0, (row["bar"] - 0.45) / 0.12))
        rows.append(
            f"""<div class="row" data-at="{at:.2f}" data-anim="left"><span class="place">{i + 1}</span>
<img src="{e(pic)}" alt=""><div class="row-main"><div class="row-top"><b>{e(row["name"])}</b><span class="num">{e(row["value"])}</span></div>
<div class="bar"><i data-bar="{width:.3f}" data-at="{at + 0.2:.2f}"></i></div></div></div>"""
        )
    return f'<div class="list"><h2 data-at="0" data-anim="up">{e(d["title"])}</h2>{"".join(rows)}</div>'


def body_tips(scene: dict[str, Any], assets: dict[str, str]) -> str:
    d = scene["data"]
    tips = d["tips"]
    span = max(0.1, scene["end"] - scene["start"] - SCENE_PAD - 0.3)
    weights = [len(t["voice"]) for t in tips]
    total = sum(weights) or 1
    rows, at = [], 0.2
    for i, tip in enumerate(tips):
        rows.append(
            f"""<div class="tip" data-at="{at:.2f}" data-anim="left"><span class="tip-n">{i + 1}</span>
{icon(tip.get("icon", "spark"))}<p>{e(tip["text"])}</p></div>"""
        )
        at += span * weights[i] / total
    art = hero_art(assets, d.get("hero"), "art faint")
    return f'<div class="tips">{art}{"".join(rows)}</div>'


def body_cta(scene: dict[str, Any], assets: dict[str, str]) -> str:
    logo = uri(SITE / "assets" / "logo.png")
    shot = uri(SITE / "assets" / "app" / "uk" / "review.jpg")
    return f"""<div class="cta"><img class="shot" src="{shot}" alt="" data-at="0.1" data-anim="up">
<img class="logo" src="{logo}" alt="" data-at="0.3" data-anim="pop">
<h2 data-at="0.45" data-anim="up">Безкоштовний тренер для Dota 2</h2>
<p data-at="0.65" data-anim="up">Підказки в матчі · розбір після гри · українською</p>
<div class="site" data-at="0.85" data-anim="pop">{e(scene["data"].get("site", "luhovyimvp.dev"))}</div>
<div class="bio" data-at="1.05" data-anim="up">посилання в профілі ↓</div></div>"""


BODIES = {
    "hook": body_hook,
    "card": body_card,
    "stat": body_stat,
    "list": body_list,
    "tips": body_tips,
    "cta": body_cta,
}

CSS = """
@font-face { font-family: Montserrat; font-weight: 100 900; src: url("{fonts}/montserrat-cyrillic-wght-normal.woff2") format("woff2"); unicode-range: U+0400-045F, U+0490-0491, U+04B0-04B1, U+2116; }
@font-face { font-family: Montserrat; font-weight: 100 900; src: url("{fonts}/montserrat-latin-wght-normal.woff2") format("woff2"); }
@font-face { font-family: Inter; font-weight: 100 900; src: url("{fonts}/inter-cyrillic-wght-normal.woff2") format("woff2"); unicode-range: U+0400-045F, U+0490-0491, U+04B0-04B1, U+2116; }
@font-face { font-family: Inter; font-weight: 100 900; src: url("{fonts}/inter-latin-wght-normal.woff2") format("woff2"); }
:root { --bg:#0c0d0f; --text:#f3f3f4; --muted:#a0a2a9; --accent:#f05560; --fill:#d23a46; --cream:#efe5d4; --line:rgba(255,255,255,.1); }
html body { margin:0; width:1080px; height:1920px; overflow:hidden; background:var(--bg); color:var(--text);
  font:400 40px/1.3 Inter, sans-serif; -webkit-font-smoothing:antialiased; }
.bg { position:absolute; inset:-60px; background-size:cover; background-position:center; filter:blur(18px) brightness(.38) saturate(1.1); }
.glow { position:absolute; inset:0; background:radial-gradient(1100px 900px at 85% 10%, rgba(240,85,96,.28), transparent 60%),
  radial-gradient(900px 800px at 0% 100%, rgba(239,229,212,.08), transparent 60%); }
.scene { position:absolute; inset:0; opacity:0; }
.top { position:absolute; top:190px; left:72px; right:72px; display:flex; align-items:center; justify-content:space-between; z-index:9; }
.brand { display:flex; align-items:center; gap:18px; font:800 46px/1 Montserrat, sans-serif; }
.brand img { width:64px; height:64px; }
.pill { padding:14px 26px; border-radius:999px; background:rgba(240,85,96,.16); border:2px solid rgba(240,85,96,.5);
  color:var(--accent); font:800 26px/1 Montserrat, sans-serif; letter-spacing:.1em; text-transform:uppercase; }
.subs { position:absolute; left:72px; right:150px; top:1290px; z-index:10; text-align:center; }
.subs span { display:inline-block; padding:14px 24px; border-radius:18px; background:rgba(8,8,10,.78);
  font:800 52px/1.2 Montserrat, sans-serif; color:#fff; box-shadow:0 8px 30px rgba(0,0,0,.5); }
.subs span b { color:var(--accent); font-weight:800; }
/* hook */
.hook .halo { position:absolute; left:50%; top:560px; width:900px; height:900px; margin-left:-450px; border-radius:50%;
  background:radial-gradient(circle, rgba(240,85,96,.45), transparent 62%); }
.art { position:absolute; object-fit:contain; }
.art.big { left:40px; width:1000px; height:1000px; top:240px; filter:drop-shadow(0 30px 60px rgba(0,0,0,.6)); }
.hook-text { position:absolute; left:72px; right:150px; top:1060px; }
.hook h1 { margin:0; font:900 86px/1.08 Montserrat, sans-serif; letter-spacing:-.02em; text-shadow:0 6px 30px rgba(0,0,0,.7); }
.hook h1 span { display:inline-block; margin-right:.22em; }
.kicker { color:var(--accent); font:800 34px/1 Montserrat, sans-serif; letter-spacing:.12em; text-transform:uppercase; margin-bottom:22px; }
/* card */
.game { position:absolute; inset:0; background-size:auto 2300px; background-position:42% 0; filter:brightness(.62) saturate(1.05); }
.scene-card::after { content:""; position:absolute; left:0; right:0; bottom:0; height:900px; z-index:0;
  background:linear-gradient(180deg, transparent, rgba(12,13,15,.92) 45%, var(--bg)); }
.scene-card > * { z-index:1; }
.portrait { position:absolute; right:-80px; top:300px; width:760px; height:760px; object-fit:contain; opacity:.9;
  filter:drop-shadow(0 20px 50px rgba(0,0,0,.7)); }
.card-wrap { position:absolute; left:72px; width:860px; top:820px; }
.card-wrap .overlay-shell { zoom:2.45; width:351px; max-height:none; }
.card-wrap .overlay-shell .action { -webkit-line-clamp:4; }
.card-wrap .overlay-shell .reason { -webkit-line-clamp:3; }
.card-note { margin-top:22px; color:var(--cream); font:600 30px/1.2 Inter, sans-serif; opacity:.85; }
.hud { position:absolute; left:72px; top:330px; display:flex; align-items:center; gap:20px; font:800 40px/1 Montserrat, sans-serif; }
.hud .hp { width:520px; height:40px; border-radius:10px; background:rgba(0,0,0,.6); border:3px solid rgba(255,255,255,.25); overflow:hidden; }
.hud .hp i { display:block; height:100%; width:100%; background:linear-gradient(90deg,#2fbf55,#5ee27c); }
.hud.stun span { padding:18px 30px; border-radius:16px; background:rgba(120,80,255,.85); letter-spacing:.12em; }
/* stat */
.stat .art.side { left:200px; top:240px; width:900px; height:900px; opacity:.95; }
.stat-box { position:absolute; left:72px; right:150px; top:880px; }
.stat-box b { display:block; font:900 220px/1 Montserrat, sans-serif; color:var(--accent); letter-spacing:-.04em; text-shadow:0 10px 40px rgba(0,0,0,.6); }
.stat-box p { margin:20px 0 0; font:700 50px/1.2 Montserrat, sans-serif; }
/* list */
.list { position:absolute; left:72px; right:150px; top:330px; }
.list h2 { margin:0 0 40px; font:900 74px/1.05 Montserrat, sans-serif; }
.row { display:flex; align-items:center; gap:26px; padding:26px; margin-bottom:26px; border-radius:28px;
  background:rgba(23,24,28,.88); border:2px solid var(--line); }
.row .place { font:900 64px/1 Montserrat, sans-serif; color:var(--accent); width:48px; }
.row img { width:200px; height:112px; border-radius:14px; object-fit:cover; }
.row-main { flex:1; }
.row-top { display:flex; justify-content:space-between; align-items:baseline; font:800 44px/1.1 Montserrat, sans-serif; }
.row-top .num { color:var(--cream); }
.bar { margin-top:16px; height:16px; border-radius:8px; background:rgba(255,255,255,.08); overflow:hidden; }
.bar i { display:block; height:100%; width:0; background:linear-gradient(90deg,var(--fill),var(--accent)); }
/* tips */
.tips { position:absolute; left:72px; right:150px; top:340px; }
.tips .art.faint { left:120px; top:-60px; width:900px; height:900px; opacity:.32; }
.tip { position:relative; display:flex; align-items:center; gap:24px; padding:32px 30px; margin-bottom:30px; border-radius:30px;
  background:rgba(23,24,28,.9); border:2px solid var(--line); }
.tip-n { font:900 60px/1 Montserrat, sans-serif; color:var(--accent); width:44px; }
.tip .ic { width:56px; height:56px; color:var(--cream); flex:none; }
.tip p { margin:0; font:700 44px/1.22 Montserrat, sans-serif; }
/* cta */
.cta { position:absolute; left:72px; right:150px; top:300px; text-align:center; }
.cta .shot { max-height:420px; object-fit:cover; object-position:top; }
.cta .shot { width:100%; border-radius:26px; border:2px solid var(--line); box-shadow:0 30px 80px rgba(0,0,0,.6); }
.cta .logo { width:150px; height:150px; margin:-75px auto 0; display:block; position:relative; }
.cta h2 { margin:20px 0 10px; font:900 62px/1.1 Montserrat, sans-serif; }
.cta p { margin:0; color:var(--muted); font:600 36px/1.3 Inter, sans-serif; }
.cta .site { display:inline-block; margin-top:26px; padding:22px 40px; border-radius:999px; background:var(--fill);
  font:800 50px/1 Montserrat, sans-serif; }
.cta .bio { margin-top:26px; color:var(--cream); font:700 38px/1 Montserrat, sans-serif; }
.num { font-variant-numeric:tabular-nums; }
.ic { width:40px; height:40px; }
"""

SCRIPT = """
const T = window.__TIMELINE__;
const ease = (k) => 1 - Math.pow(1 - Math.min(1, Math.max(0, k)), 3);
const scenes = [...document.querySelectorAll('.scene')];
const subs = document.querySelector('.subs');
function fmt(v, d) { return v.toFixed(d).replace('.', ','); }
window.renderAt = function (t) {
  T.scenes.forEach((s, i) => {
    const el = scenes[i];
    const fadeIn = i === 0 ? 1 : ease((t - s.start) / %(fade)s);
    const fadeOut = i === T.scenes.length - 1 ? 1 : 1 - ease((t - s.end + %(fade)s) / %(fade)s);
    const on = t >= s.start - 0.001 && t < s.end + 0.001;
    el.style.opacity = on ? Math.min(fadeIn, fadeOut) : 0;
    if (!on) return;
    const lt = t - s.start, p = lt / (s.end - s.start);
    el.querySelectorAll('[data-at]').forEach((n) => {
      const at = parseFloat(n.dataset.at), k = ease((lt - at) / 0.45);
      const anim = n.dataset.anim;
      if (anim) {
        n.style.opacity = k;
        if (anim === 'up') n.style.transform = `translateY(${(1 - k) * 60}px)`;
        if (anim === 'left') n.style.transform = `translateX(${(1 - k) * -120}px)`;
        if (anim === 'pop') n.style.transform = `scale(${0.6 + 0.4 * k})`;
      }
      if (n.dataset.bar) n.style.width = (parseFloat(n.dataset.bar) * 100 * ease((lt - at) / 0.9)) + '%%';
      if (n.dataset.count) {
        const k2 = ease((lt - at) / 1.1);
        n.textContent = n.dataset.prefix + fmt(parseFloat(n.dataset.count) * k2, +n.dataset.decimals) + n.dataset.suffix;
      }
    });
    el.querySelectorAll('[data-hp]').forEach((n) => {
      const k = ease(lt / 1.6);
      n.style.width = (100 - 62 * k) + '%%';
      n.style.background = k > 0.6 ? 'linear-gradient(90deg,#c62f3c,#f05560)' : '';
    });
    el.querySelectorAll('.art.big,.art.side,.portrait,.game').forEach((n) => {
      n.style.transform = `scale(${1.02 + 0.06 * p})`;
    });
  });
  const bg = document.querySelector('.bg');
  bg.style.transform = `scale(${1.05 + 0.08 * (t / T.total)})`;
  const line = T.subs.find((x) => t >= x.start && t < x.end);
  subs.innerHTML = line ? `<span>${line.html}</span>` : '';
};
window.renderAt(0);
"""


def sub_html(text: str) -> str:
    """Numbers stand out in the subtitles (the accent colour)."""
    return re.sub(r"(\d[\d,.]*\s?%?)", r"<b>\1</b>", html.escape(text))


def page(fmt: str, scenes: list[dict[str, Any]], assets: dict[str, str], seed: int = 0) -> str:
    total = scenes[-1]["end"] if scenes else 0.0
    subs = [{**s, "html": sub_html(s["text"])} for scene in scenes for s in scene["subs"]]
    data = {
        "scenes": [{"start": s["start"], "end": s["end"]} for s in scenes],
        "subs": subs,
        "total": total,
    }
    background = assets.get("background") or uri(
        SITE / "assets" / "game" / BACKGROUNDS[seed % len(BACKGROUNDS)]
    )
    game = assets.get("game") or uri(SITE / "assets" / "game" / "ingame-uk.jpg")
    layers = []
    for scene in scenes:
        body = BODIES[scene["kind"]](scene, assets).replace(
            '<div class="game"></div>',
            f'<div class="game" style="background-image:url({e(game)})"></div>',
        )
        layers.append(f'<div class="scene scene-{scene["kind"]}">{body}</div>')
    fonts = uri(SITE / "assets" / "fonts")
    css = CSS.replace("{fonts}", fonts)
    overlay_css = "".join(
        f'<link rel="stylesheet" href="{uri(path)}">'
        for path in (
            LAUNCHER / "assets" / "fonts" / "fonts.css",
            LAUNCHER / "assets" / "ui" / "tokens.css",
            LAUNCHER / "overlay" / "styles.css",
        )
    )
    script = SCRIPT % {"fade": CROSSFADE}
    return f"""<!doctype html><html lang="uk"><head><meta charset="utf-8">{overlay_css}<style>{css}</style></head>
<body><div class="bg" style="background-image:url({e(background)})"></div><div class="glow"></div>
{"".join(layers)}
<header class="top"><div class="brand"><img src="{uri(SITE / "assets" / "logo-mark.png")}" alt="">Wardly</div><div class="pill">{e(PILLS.get(fmt, "Wardly"))}</div></header>
<div class="subs"></div>
<script>window.__TIMELINE__ = {json.dumps(data, ensure_ascii=False)};</script>
<script>{script}</script></body></html>"""
