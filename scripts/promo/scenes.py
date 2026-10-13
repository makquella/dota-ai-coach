"""The video as one HTML page (1080x1920) drawn frame by frame: render.py
awaits window.renderAt(t) and takes a screenshot per frame, so every frame is
exact and repeatable (no CSS animations racing the screenshots).

Moving pictures are frame sequences (media.py): Valve's idle animation of the
hero (with transparency) and in-game clips of abilities. An <img data-seq>
shows the frame for its scene's local time, so a stun lands on the same frame
in every render. Scenes cut in with a short punch and a flash; a card hits
with a shake; the subtitles light up word by word with the voice.

Look: the site's dark brand (Montserrat / Inter, the red accent), the real
overlay card (frontend/launcher/overlay/styles.css). TikTok, Reels and Shorts
cover the bottom ~420 px and the right ~140 px with their own buttons: the
content stays inside SAFE (top 200 .. bottom 1500, left 72 .. right 940)."""

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
SCENE_PAD = 0.35  # seconds of picture after the voice of a scene ends
MIN_SCENE = 2.2
SUB_WORDS, SUB_CHARS = 3, 22
CARD_AT = 1.0  # the overlay card hits this long into a coach moment
PAY_AFTER = 1.8  # then the advised ability plays, at the latest at half the scene

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


# --- timing ----------------------------------------------------------------------------


def estimated_words(text: str, start: float, end: float) -> list[dict[str, Any]]:
    """Without a voice: each word gets its share of the time by its length."""
    words = text.split()
    total = sum(len(w) + 1 for w in words) or 1
    out, at = [], start
    for word in words:
        span = (end - start) * (len(word) + 1) / total
        out.append({"word": word, "start": round(at, 3), "end": round(at + span, 3)})
        at += span
    return out


def subtitle_lines(words: list[dict[str, Any]], end: float) -> list[dict[str, Any]]:
    """Words (absolute times) in short lines; a line stays until the next one starts."""
    lines: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = []
    for word in words:
        trial = " ".join(w["word"] for w in [*current, word])
        if current and (len(current) >= SUB_WORDS or len(trial) > SUB_CHARS):
            lines.append(current)
            current = [word]
        else:
            current.append(word)
        if re.search(r"[.!?:]$", word["word"]):
            lines.append(current)
            current = []
    if current:
        lines.append(current)
    out = []
    for index, line in enumerate(lines):
        stop = lines[index + 1][0]["start"] if index + 1 < len(lines) else end
        out.append(
            {
                "text": " ".join(w["word"] for w in line),
                "start": round(line[0]["start"], 3),
                "end": round(max(stop, line[-1]["end"]), 3),
                "words": [{"w": w["word"], "s": w["start"], "e": w["end"]} for w in line],
            }
        )
    return out


def subtitle_chunks(text: str, start: float, end: float) -> list[dict[str, Any]]:
    """The scene's voice text in short lines, each on screen for its share of the time."""
    return subtitle_lines(estimated_words(text, start, end), end)


def timeline(
    scenes: list[dict[str, Any]],
    voice_seconds: list[float | None],
    voice_words: list[list[dict[str, Any]] | None] | None = None,
) -> list[dict[str, Any]]:
    """Start and end of each scene: its voice plus a short pause (or a reading
    time by length when silent), never shorter than MIN_SCENE. Word times come
    from the voice when there is one (relative to the scene), else estimated."""
    voice_words = voice_words or [None] * len(scenes)
    out, at = [], 0.0
    for scene, seconds, words in zip(scenes, voice_seconds, voice_words, strict=True):
        spoken = seconds if seconds is not None else max(1.5, len(scene["voice"]) / 15)
        length = max(MIN_SCENE, spoken + SCENE_PAD)
        if scene["kind"] == "cta":
            length += 0.8  # the end card stays a moment
        voice_end = at + spoken
        absolute = (
            [{**w, "start": at + w["start"], "end": at + w["end"]} for w in words]
            if words
            else estimated_words(scene["voice"], at + 0.05, voice_end)
        )
        out.append(
            {
                **scene,
                "start": round(at, 3),
                "end": round(at + length, 3),
                "words": absolute,
                # The hook's headline is its voice: no subtitles over it.
                "subs": []
                if scene["kind"] == "hook"
                else subtitle_lines(absolute, min(at + length, voice_end + 0.3)),
            }
        )
        at += length
    return out


# --- pictures --------------------------------------------------------------------------


def seq(name: str | None, cls: str, at: float = 0.0, rate: float = 1.0, loop: bool = True) -> str:
    """A frame sequence (assets["seqs"][name]) played from `at` seconds into the scene."""
    if not name:
        return ""
    return (
        f'<img class="seq {cls}" data-seq="{e(name)}" data-from="{at:.3f}" '
        f'data-rate="{rate}" data-loop="{1 if loop else 0}" alt="">'
    )


def media(scene: dict[str, Any]) -> dict[str, Any]:
    return scene.get("media") or {}


def hero_art(assets: dict[str, str], key: str | None, cls: str = "art") -> str:
    if not key:
        return ""
    src = assets.get(f"render:{key}") or assets.get(f"small:{key}")
    return f'<img class="{cls}" src="{e(src)}" alt="">' if src else ""


def hero_moving(scene: dict[str, Any], assets: dict[str, Any], cls: str) -> str:
    """The hero's idle animation, or the still render without one."""
    idle = media(scene).get("idle")
    if idle and idle in (assets.get("seqs") or {}):
        return seq(idle, f"hero-anim {cls}")
    return hero_art(assets, (scene.get("data") or {}).get("hero"), f"art {cls}")


def backdrop(scene: dict[str, Any], assets: dict[str, Any], cls: str = "bgclip") -> str:
    """A moving game clip behind the scene (blurred and dark), else a still."""
    bg = media(scene).get("bg")
    if bg and bg in (assets.get("seqs") or {}):
        return seq(bg, cls)
    still = assets.get("background") or uri(
        SITE / "assets" / "game" / BACKGROUNDS[scene.get("index", 0) % len(BACKGROUNDS)]
    )
    return f'<img class="bgstill" src="{e(still)}" alt="">'


# --- scene bodies -----------------------------------------------------------------------


def body_hook(scene: dict[str, Any], assets: dict[str, Any]) -> str:
    d = scene["data"]
    sub = (
        f'<div class="kicker" data-at="0.1" data-anim="up">{e(d["sub"])}</div>'
        if d.get("sub")
        else ""
    )
    words = " ".join(
        f'<span data-at="{max(0.0, w["start"] - scene["start"] - 0.04):.2f}" data-anim="word">{e(w["word"])}</span>'
        for w in scene.get("words") or []
    )
    length = len(scene["voice"])
    size = 96 if length <= 40 else 82 if length <= 64 else 70
    return f"""{backdrop(scene, assets)}<div class="halo"></div>
{hero_moving(scene, assets, "big punch")}
<div class="hook-text">{sub}<h1 style="font-size:{size}px">{words}</h1></div>"""


def body_card(scene: dict[str, Any], assets: dict[str, Any]) -> str:
    d, m = scene["data"], media(scene)
    seqs = assets.get("seqs") or {}
    length = scene["end"] - scene["start"]
    pay_at = min(max(CARD_AT + PAY_AFTER, length * 0.5), max(CARD_AT + 0.6, length - 1.2))
    urgent = d.get("mode") == "urgent"
    label = "Терміново" if urgent else "Порада"
    classes = "overlay-shell " + ("urgent priority-high" if urgent else "priority-medium")
    moment = d.get("moment")
    threat = m.get("threat") if m.get("threat") in seqs else None
    pay = m.get("pay") if m.get("pay") in seqs else None
    if threat:
        stage = seq(threat, "full", loop=False)
    else:
        stage = backdrop(scene, assets, "full dim") + hero_moving(scene, assets, "center")
    hud = ""
    until = f' data-until="{pay_at:.2f}"'
    if moment == "fall":
        hud = (
            f'<div class="hud"{until}><div data-at="0" data-anim="up"><b>HP</b>'
            '<div class="hp"><i data-hp="1"></i></div></div></div>'
        )
    elif moment == "stun":
        hud = (
            f'<div class="hud stun"{until}><div data-at="0.25" data-anim="slam"><span>ОГЛУШЕНИЙ</span>'
            '<div class="stunbar"><i data-stun="1"></i></div></div></div>'
        )
    chip = ""
    if m.get("pay_name"):
        pic = f'<img src="{e(m["pay_icon"])}" alt="">' if m.get("pay_icon") else ""
        chip = f'<div class="pay-chip">{pic}<span>{e(m["pay_name"])}</span></div>'
    if pay:
        # the ability the card names, in the game
        fix = seq(pay, "full", at=pay_at, loop=False)
    else:
        # an item (or nothing to show): the hero, alive, with the item's glow
        fix = (
            backdrop(scene, assets)
            + '<div class="aura"></div>'
            + hero_moving(scene, assets, "center")
        )
    payoff = f'<div class="pay" data-pay="{pay_at:.2f}">{fix}{chip}</div>'
    return f"""<div class="stage">{stage}</div>{payoff}
<div class="tint {e(moment or "")}" data-tint="{e(moment or "")}"></div>
{hud}
<div class="card-wrap" data-impact="{CARD_AT}">
  <section class="{classes}">
    <div class="top-row"><span class="dot"></span><span class="label">{label}</span></div>
    <p class="action">{e(d["action"])}</p>
    <p class="reason">{e(d.get("reason", ""))}</p>
  </section>
  <div class="card-note">так виглядає підказка поверх Доти</div>
</div>"""


def body_stat(scene: dict[str, Any], assets: dict[str, Any]) -> str:
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
        big = f'<b class="num" data-at="0.2" data-anim="slam">{e(value)}</b>'
    return f"""{backdrop(scene, assets)}{hero_moving(scene, assets, "side")}
<div class="stat-box">{big}<p data-at="0.5" data-anim="up">{e(d["label"])}</p></div>"""


def body_list(scene: dict[str, Any], assets: dict[str, Any]) -> str:
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
    return f"""{backdrop(scene, assets)}{hero_moving(scene, assets, "corner")}
<div class="list"><h2 data-at="0" data-anim="up">{e(d["title"])}</h2>{"".join(rows)}</div>"""


def body_tips(scene: dict[str, Any], assets: dict[str, Any]) -> str:
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
    return f"""{backdrop(scene, assets)}{hero_moving(scene, assets, "upper")}
<div class="tips">{"".join(rows)}</div>"""


def body_cta(scene: dict[str, Any], assets: dict[str, Any]) -> str:
    logo = uri(SITE / "assets" / "logo.png")
    shot = uri(SITE / "assets" / "app" / "uk" / "review.jpg")
    return f"""{backdrop(scene, assets)}<div class="cta"><img class="shot" src="{shot}" alt="" data-at="0.1" data-anim="up">
<img class="logo" src="{logo}" alt="" data-at="0.3" data-anim="slam">
<h2 data-at="0.45" data-anim="up">Безкоштовний тренер для Dota 2</h2>
<p data-at="0.65" data-anim="up">Підказки в матчі · розбір після гри · українською</p>
<div class="site" data-at="0.85" data-anim="slam">{e(scene["data"].get("site", "luhovyimvp.dev"))}</div>
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
.scene { position:absolute; inset:0; opacity:0; overflow:hidden; transform-origin:50% 45%; }
.bgclip, .bgstill { position:absolute; left:-60px; top:-60px; width:1200px; height:2040px; object-fit:cover;
  filter:blur(16px) brightness(.34) saturate(1.25); }
.full { position:absolute; inset:0; width:1080px; height:1920px; object-fit:cover; }
.full.dim { filter:blur(10px) brightness(.4); }
.stage { position:absolute; inset:0; }
.glow { position:absolute; inset:0; pointer-events:none; background:radial-gradient(1100px 900px at 85% 10%, rgba(240,85,96,.22), transparent 60%); }
.vignette { position:absolute; inset:0; pointer-events:none; z-index:20;
  background:radial-gradient(130% 90% at 50% 45%, transparent 55%, rgba(0,0,0,.65)); }
.flash { position:absolute; inset:0; background:#fff; opacity:0; z-index:30; pointer-events:none; }
.top { position:absolute; top:190px; left:72px; right:72px; display:flex; align-items:center; justify-content:space-between; z-index:25; }
.brand { display:flex; align-items:center; gap:18px; font:800 46px/1 Montserrat, sans-serif; text-shadow:0 4px 20px rgba(0,0,0,.8); }
.brand img { width:64px; height:64px; }
.pill { padding:14px 26px; border-radius:999px; background:rgba(12,13,15,.6); border:2px solid rgba(240,85,96,.7);
  color:var(--accent); font:800 26px/1 Montserrat, sans-serif; letter-spacing:.1em; text-transform:uppercase; }
.subs { position:absolute; left:60px; right:140px; top:1300px; z-index:26; text-align:center; }
.subs .line { display:inline-block; padding:10px 22px; border-radius:20px; background:rgba(8,8,10,.62); }
.subs .w { display:inline-block; margin:0 .14em; font:900 64px/1.15 Montserrat, sans-serif; color:#fff; opacity:.55;
  text-shadow:0 4px 0 #000, 0 0 24px rgba(0,0,0,.8); text-transform:uppercase; letter-spacing:-.01em; }
.subs .w.past { opacity:1; }
.subs .w.on { opacity:1; color:#ffd166; }
.subs .w.num { color:var(--accent); opacity:1; }
/* hook */
.halo { position:absolute; left:50%; top:520px; width:1000px; height:1000px; margin-left:-500px; border-radius:50%;
  background:radial-gradient(circle, rgba(240,85,96,.5), transparent 62%); }
.hero-anim, .art { position:absolute; object-fit:contain; filter:drop-shadow(0 30px 60px rgba(0,0,0,.7)); }
.big { left:60px; top:250px; width:960px; height:960px; }
.hook-text { position:absolute; left:72px; right:150px; top:1110px; z-index:5; }
.hook-text h1 { margin:0; font:900 86px/1.06 Montserrat, sans-serif; letter-spacing:-.02em; text-transform:uppercase;
  text-shadow:0 6px 0 #000, 0 10px 40px rgba(0,0,0,.8); }
.hook-text h1 span { display:inline-block; margin-right:.22em; }
.kicker { color:var(--accent); font:800 34px/1 Montserrat, sans-serif; letter-spacing:.12em; text-transform:uppercase; margin-bottom:22px; }
/* card */
.center { left:110px; top:300px; width:860px; height:860px; }
.pay { position:absolute; inset:0; opacity:0; }
.aura { position:absolute; left:50%; top:420px; width:1100px; height:1100px; margin-left:-550px; border-radius:50%;
  background:radial-gradient(circle, rgba(255,209,102,.55), rgba(255,170,60,.18) 45%, transparent 68%); }
.pay-chip { position:absolute; left:72px; top:300px; display:flex; align-items:center; gap:18px; padding:14px 26px 14px 14px;
  border-radius:20px; background:rgba(12,13,15,.82); border:2px solid rgba(255,209,102,.7); font:800 44px/1 Montserrat, sans-serif; color:#ffd166; }
.pay-chip img { width:72px; height:72px; border-radius:12px; }
.tint { position:absolute; inset:0; pointer-events:none; opacity:0; }
.tint.stun { background:radial-gradient(120% 80% at 50% 45%, rgba(130,90,255,.15), rgba(90,40,220,.55)); }
.tint.fall { background:radial-gradient(120% 80% at 50% 45%, transparent 35%, rgba(220,20,40,.75)); }
.scene-card .stage::after { content:""; position:absolute; left:0; right:0; bottom:0; height:1000px;
  background:linear-gradient(180deg, transparent, rgba(12,13,15,.55) 40%, rgba(12,13,15,.9)); }
.card-wrap { position:absolute; left:72px; width:860px; top:820px; z-index:6; transform-origin:50% 50%; opacity:0; }
.card-wrap .overlay-shell { zoom:2.45; width:351px; max-height:none; box-shadow:0 30px 80px rgba(0,0,0,.7); }
.card-wrap .overlay-shell .action { -webkit-line-clamp:4; }
.card-wrap .overlay-shell .reason { -webkit-line-clamp:3; }
.card-note { margin-top:22px; color:var(--cream); font:600 30px/1.2 Inter, sans-serif; opacity:.9; text-shadow:0 2px 10px #000; }
.hud { position:absolute; left:72px; top:330px; display:flex; align-items:center; gap:20px; z-index:5;
  font:900 44px/1 Montserrat, sans-serif; text-shadow:0 3px 0 #000; }
.hud .hp { width:600px; height:44px; border-radius:10px; background:rgba(0,0,0,.65); border:3px solid rgba(255,255,255,.3); overflow:hidden; }
.hud .hp i { display:block; height:100%; width:100%; background:linear-gradient(90deg,#2fbf55,#5ee27c); }
.hud > div { display:flex; align-items:center; gap:20px; }
.hud.stun > div { flex-direction:column; align-items:flex-start; gap:14px; }
.hud.stun span { padding:16px 30px; border-radius:16px; background:rgba(120,80,255,.92); letter-spacing:.12em; }
.stunbar { width:420px; height:16px; border-radius:8px; background:rgba(0,0,0,.6); overflow:hidden; }
.stunbar i { display:block; height:100%; width:100%; background:#b9a2ff; }
/* stat */
.side { left:260px; top:220px; width:900px; height:900px; }
.stat-box { position:absolute; left:72px; right:150px; top:900px; z-index:5; }
.stat-box b { display:block; font:900 230px/1 Montserrat, sans-serif; color:var(--accent); letter-spacing:-.04em; text-shadow:0 8px 0 #000, 0 10px 40px rgba(0,0,0,.6); }
.stat-box p { margin:20px 0 0; font:800 52px/1.2 Montserrat, sans-serif; text-shadow:0 3px 0 #000; }
/* list */
.corner { right:-120px; top:120px; width:640px; height:640px; opacity:.55; }
.list { position:absolute; left:72px; right:150px; top:330px; z-index:5; }
.list h2 { margin:0 0 40px; font:900 74px/1.05 Montserrat, sans-serif; text-transform:uppercase; text-shadow:0 5px 0 #000; }
.row { display:flex; align-items:center; gap:26px; padding:26px; margin-bottom:26px; border-radius:28px;
  background:rgba(18,19,23,.9); border:2px solid var(--line); }
.row .place { font:900 64px/1 Montserrat, sans-serif; color:var(--accent); width:48px; }
.row img { width:200px; height:112px; border-radius:14px; object-fit:cover; }
.row-main { flex:1; }
.row-top { display:flex; justify-content:space-between; align-items:baseline; font:800 44px/1.1 Montserrat, sans-serif; }
.row-top .num { color:var(--cream); }
.bar { margin-top:16px; height:16px; border-radius:8px; background:rgba(255,255,255,.08); overflow:hidden; }
.bar i { display:block; height:100%; width:0; background:linear-gradient(90deg,var(--fill),var(--accent)); }
/* tips */
.upper { left:200px; top:180px; width:760px; height:760px; opacity:.9; }
.tips { position:absolute; left:72px; right:150px; top:760px; z-index:5; }
.tip { position:relative; display:flex; align-items:center; gap:24px; padding:30px 30px; margin-bottom:26px; border-radius:30px;
  background:rgba(18,19,23,.92); border:2px solid var(--line); }
.tip-n { font:900 60px/1 Montserrat, sans-serif; color:var(--accent); width:44px; }
.tip .ic { width:56px; height:56px; color:var(--cream); flex:none; }
.tip p { margin:0; font:700 42px/1.2 Montserrat, sans-serif; }
/* cta */
.cta { position:absolute; left:72px; right:150px; top:300px; text-align:center; z-index:5; }
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

SCRIPT = r"""
const T = window.__TIMELINE__;
const SEQ = window.__SEQS__;
const clamp = (k) => Math.min(1, Math.max(0, k));
const ease = (k) => 1 - Math.pow(1 - clamp(k), 3);
const back = (k) => { k = clamp(k); const c = 1.9; return 1 + (c + 1) * Math.pow(k - 1, 3) + c * Math.pow(k - 1, 2); };
const scenes = [...document.querySelectorAll('.scene')];
const subs = document.querySelector('.subs');
const flash = document.querySelector('.flash');
function fmt(v, d) { return v.toFixed(d).replace('.', ','); }
function shake(lt, at, dur, amp) {
  const k = (lt - at) / dur;
  if (k < 0 || k > 1) return [0, 0];
  const a = amp * (1 - k);
  return [a * Math.sin(lt * 97), a * Math.cos(lt * 83)];
}
function frameOf(img, lt) {
  const s = SEQ[img.dataset.seq];
  if (!s || !s.frames.length) return null;
  const local = (lt - parseFloat(img.dataset.from)) * parseFloat(img.dataset.rate);
  let i = Math.floor(Math.max(0, local) * s.fps + 1e-6);
  i = img.dataset.loop === '1' ? i % s.frames.length : Math.min(i, s.frames.length - 1);
  return s.frames[i];
}
window.renderAt = async function (t) {
  const loads = [];
  let flashLevel = 0;
  T.scenes.forEach((s, i) => {
    const el = scenes[i];
    const on = t >= s.start - 0.001 && t < s.end + 0.001;
    el.style.opacity = on ? 1 : 0;
    if (!on) return;
    const lt = t - s.start, p = lt / (s.end - s.start);
    // the cut: a punch in and a flash
    const cut = i === 0 ? 1 : ease(lt / 0.3);
    let [sx, sy] = [0, 0];
    if (i > 0) flashLevel = Math.max(flashLevel, 0.35 * (1 - clamp(lt / 0.16)));
    el.querySelectorAll('img.seq').forEach((img) => {
      const src = frameOf(img, lt);
      if (src && img.getAttribute('src') !== src) { img.src = src; loads.push(img.decode().catch(() => {})); }
    });
    el.querySelectorAll('[data-at]').forEach((n) => {
      const at = parseFloat(n.dataset.at), k = ease((lt - at) / 0.4);
      const anim = n.dataset.anim;
      if (anim) {
        n.style.opacity = clamp((lt - at) / 0.12);
        if (anim === 'up') n.style.transform = `translateY(${(1 - k) * 70}px)`;
        if (anim === 'left') n.style.transform = `translateX(${(1 - k) * -140}px)`;
        if (anim === 'slam') n.style.transform = `scale(${1.6 - 0.6 * back((lt - at) / 0.35)})`;
        if (anim === 'word') n.style.transform = `translateY(${(1 - ease((lt - at) / 0.18)) * 40}px) scale(${1.25 - 0.25 * ease((lt - at) / 0.18)})`;
      }
      if (n.dataset.bar) n.style.width = (parseFloat(n.dataset.bar) * 100 * ease((lt - at) / 0.9)) + '%';
      if (n.dataset.count) {
        const k2 = ease((lt - at) / 1.1);
        n.textContent = n.dataset.prefix + fmt(parseFloat(n.dataset.count) * k2, +n.dataset.decimals) + n.dataset.suffix;
      }
    });
    el.querySelectorAll('[data-hp]').forEach((n) => {
      const k = ease(lt / 1.2);
      n.style.width = (100 - 62 * k) + '%';
      n.style.background = k > 0.6 ? 'linear-gradient(90deg,#c62f3c,#f05560)' : '';
    });
    el.querySelectorAll('[data-stun]').forEach((n) => { n.style.width = (100 * (1 - clamp((lt - 0.3) / 2.6))) + '%'; });
    el.querySelectorAll('[data-tint]').forEach((n) => {
      if (n.dataset.tint === 'stun') n.style.opacity = 0.9 * (1 - clamp((lt - 0.25) / 1.4)) * clamp((lt - 0.2) / 0.08);
      else if (n.dataset.tint === 'fall') n.style.opacity = (0.35 + 0.35 * Math.abs(Math.sin(lt * 5))) * (1 - clamp((lt - 2.2) / 0.8));
    });
    if (el.querySelector('[data-tint="stun"]')) {
      flashLevel = Math.max(flashLevel, 0.5 * (1 - clamp((lt - 0.25) / 0.15)) * (lt >= 0.25 ? 1 : 0));
      const [a, b] = shake(lt, 0.25, 0.45, 26); sx += a; sy += b;
    }
    el.querySelectorAll('[data-impact]').forEach((n) => {
      const at = parseFloat(n.dataset.impact);
      n.style.opacity = clamp((lt - at) / 0.06);
      n.style.transform = `scale(${1.35 - 0.35 * back((lt - at) / 0.32)})`;
      if (lt >= at) flashLevel = Math.max(flashLevel, 0.45 * (1 - clamp((lt - at) / 0.18)));
      const [a, b] = shake(lt, at, 0.3, 18); sx += a; sy += b;
    });
    el.querySelectorAll('[data-until]').forEach((n) => { n.style.opacity = 1 - clamp((lt - parseFloat(n.dataset.until)) / 0.15); });
    el.querySelectorAll('[data-pay]').forEach((n) => {
      const at = parseFloat(n.dataset.pay);
      n.style.opacity = ease((lt - at) / 0.22);
      if (lt >= at) flashLevel = Math.max(flashLevel, 0.3 * (1 - clamp((lt - at) / 0.15)));
      const aura = n.querySelector('.aura');
      if (aura) aura.style.transform = `scale(${0.6 + 0.4 * back((lt - at) / 0.5) + 0.05 * Math.sin(lt * 6)})`;
      const chip = n.querySelector('.pay-chip');
      if (chip) chip.style.transform = `scale(${1.5 - 0.5 * back((lt - at - 0.1) / 0.35)})`;
    });
    el.querySelectorAll('.big,.side,.center,.corner,.upper,.full:not(.dim)').forEach((n) => {
      const punch = n.classList.contains('punch') ? 0.22 * (1 - ease(lt / 0.5)) : 0;
      n.style.transform = `scale(${1 + punch + 0.07 * p})`;
    });
    el.style.transform = `translate(${sx}px, ${sy}px) scale(${1.08 - 0.08 * cut})`;
  });
  flash.style.opacity = flashLevel;
  const line = T.subs.find((x) => t >= x.start && t < x.end);
  subs.innerHTML = line ? '<span class="line">' + line.words.map((w) => {
    const num = /\d/.test(w.w) ? ' num' : '';
    const state = t >= w.s && t < w.e ? ' on' : t >= w.e ? ' past' : '';
    return `<span class="w${num}${state}">${w.html}</span>`;
  }).join(' ') + '</span>' : '';
  await Promise.all(loads);
};
"""


def page(fmt: str, scenes: list[dict[str, Any]], assets: dict[str, Any], seed: int = 0) -> str:
    total = scenes[-1]["end"] if scenes else 0.0
    subs = [
        {
            "start": s["start"],
            "end": s["end"],
            "words": [{**w, "html": html.escape(w["w"])} for w in s["words"]],
        }
        for scene in scenes
        for s in scene["subs"]
    ]
    data = {
        "scenes": [{"start": s["start"], "end": s["end"]} for s in scenes],
        "subs": subs,
        "total": total,
    }
    if "background" not in assets:
        assets = {
            **assets,
            "background": uri(SITE / "assets" / "game" / BACKGROUNDS[seed % len(BACKGROUNDS)]),
        }
    layers = []
    for index, scene in enumerate(scenes):
        body = BODIES[scene["kind"]]({**scene, "index": index + seed}, assets)
        layers.append(
            f'<div class="scene scene-{scene["kind"]}">{body}<div class="glow"></div></div>'
        )
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
    seqs = assets.get("seqs") or {}
    return f"""<!doctype html><html lang="uk"><head><meta charset="utf-8">{overlay_css}<style>{css}</style></head>
<body>{"".join(layers)}<div class="vignette"></div>
<header class="top"><div class="brand"><img src="{uri(SITE / "assets" / "logo-mark.png")}" alt="">Wardly</div><div class="pill">{e(PILLS.get(fmt, "Wardly"))}</div></header>
<div class="subs"></div><div class="flash"></div>
<script>window.__TIMELINE__ = {json.dumps(data, ensure_ascii=False)};
window.__SEQS__ = {json.dumps(seqs)};</script>
<script>{SCRIPT}</script></body></html>"""
