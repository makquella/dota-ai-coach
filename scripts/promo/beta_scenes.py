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
        "feedback": ["Що допомогло?", "Що запізнилось / відволікало?", "Де порада була хибною?"],
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
        "feedback": ["What helped?", "What was late / distracting?", "Which advice was wrong?"],
        "goals": ["More accurate", "Better timed", "More useful"],
        "join": "Join the beta test",
    },
}
HEROES = ("sven", "juggernaut", "terrorblade")


def uri(path: Path) -> str:
    """Self-contained frames work in cloud browsers without file:// navigation."""
    kind = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return f"data:{kind};base64," + base64.b64encode(path.read_bytes()).decode("ascii")


def page(language: str, timeline: list[dict[str, Any]], captions: list[dict[str, Any]]) -> str:
    copy = COPY[language]
    esc = html.escape
    assets = SITE / "assets"
    images = {
        "logo": uri(assets / "logo.png"),
        "game": uri(assets / "game" / f"ingame-{language}.jpg"),
        "review": uri(assets / "app" / language / "review.jpg"),
    }
    hero_cards = "".join(
        f'<div class="hero"><img src="{uri(assets / "heroes" / (key + ".webp"))}">'
        f"<b data-safe>{esc(name)}</b></div>"
        for key, name in zip(HEROES, copy["heroes"], strict=True)
    )
    feedback = "".join(
        f'<div class="feedback" data-reveal="{i * 0.7}"><span>0{i + 1}</span>'
        f"<b data-safe>{esc(text)}</b></div>"
        for i, text in enumerate(copy["feedback"])
    )
    goals = "".join(
        f'<div class="goal" data-reveal="{i * 0.6}" data-safe><span>+</span>{esc(text)}</div>'
        for i, text in enumerate(copy["goals"])
    )
    shot = (
        f'<div class="review-shot"><img src="{images["review"]}"></div>'
        f'<div class="shot-label" data-safe>{esc(copy["interface"])}</div>'
    )
    product = (
        f'<div class="product"><span data-safe>{esc(copy["live"])}</span>'
        f'<div class="game-shot"><img src="{images["game"]}"></div>'
        f"<span data-safe>{esc(copy['review'])}</span>"
        f'<div class="product-review"><img src="{images["review"]}"></div></div>'
    )
    contents = [
        f'<div class="hook-art"><img src="{images["game"]}"></div><div class="hook-rule"></div>',
        product,
        f'<div class="mmr" data-safe>0–4 000 <small>MMR</small></div>'
        f'<div class="heroes">{hero_cards}</div>'
        f'<div class="volunteers" data-safe>{esc(copy["volunteers"])}</div>',
        shot,
        f'<div class="feedback-list">{feedback}</div>',
        f'<div class="goals">{goals}</div>',
        f'<img class="end-logo" src="{images["logo"]}">'
        f'<div class="join" data-safe>{esc(copy["join"])}</div>'
        f'<div class="address" data-safe>{esc(copy["site"])}</div>'
        f'<div class="free end-free" data-safe>{esc(copy["free"])}</div>',
    ]
    sections = "".join(
        f'<section class="scene s{i}"><h1 data-safe>{esc(title).replace(chr(10), "<br>")}</h1>'
        f"{body}</section>"
        for i, (title, body) in enumerate(zip(copy["titles"], contents, strict=True))
    )
    fonts = {
        name: uri(assets / "fonts" / f"{name}-wght-normal.woff2")
        for name in ("montserrat-cyrillic", "montserrat-latin", "inter-cyrillic", "inter-latin")
    }
    return f'''<!doctype html><html lang="{language}"><meta charset="utf-8">
<style>
@font-face{{font-family:Montserrat;src:url("{fonts["montserrat-cyrillic"]}");font-weight:100 900;unicode-range:U+0400-045F,U+0490-0491}}
@font-face{{font-family:Montserrat;src:url("{fonts["montserrat-latin"]}");font-weight:100 900}}
@font-face{{font-family:Inter;src:url("{fonts["inter-cyrillic"]}");font-weight:100 900;unicode-range:U+0400-045F,U+0490-0491}}
@font-face{{font-family:Inter;src:url("{fonts["inter-latin"]}");font-weight:100 900}}
*{{box-sizing:border-box}}body{{margin:0;width:1080px;height:1920px;overflow:hidden;background:#0c0d0f;color:#f3f3f4;font-family:Inter,sans-serif}}
.glow{{position:absolute;inset:0;background:radial-gradient(ellipse at 95% 40%,#d23a4629,transparent 60%),linear-gradient(125deg,transparent 55%,#f0556009 55.2%,transparent 55.4%)}}
.grid{{position:absolute;inset:0;opacity:.13;background-image:linear-gradient(#9992 1px,transparent 1px),linear-gradient(90deg,#9992 1px,transparent 1px);background-size:108px 108px}}
header{{position:absolute;left:84px;top:208px;width:816px;display:flex;align-items:center;gap:18px}}
header img{{width:62px;height:62px}}header b{{font:800 44px Montserrat}}header .free{{margin-left:auto;font-size:24px}}
.free{{border:1px solid #7775;border-radius:12px;padding:12px 16px;background:#141619;color:#efe5d4;font-weight:600}}
.label{{position:absolute;left:84px;top:318px;letter-spacing:4px;color:#f05560;font-size:23px;font-weight:800}}
.scene{{position:absolute;inset:0;visibility:hidden;opacity:0}}
h1{{position:absolute;left:84px;top:400px;width:816px;margin:0;font:800 72px/1.22 Montserrat;letter-spacing:-2.5px}}
.s0 h1{{top:450px;font-size:88px}}.hook-rule{{position:absolute;left:84px;top:704px;width:156px;height:9px;background:#f05560}}
.hook-art{{position:absolute;left:84px;top:790px;width:816px;height:386px;overflow:hidden;border:1px solid #fff3;border-radius:26px;transform:rotate(-3deg)}}
.hook-art img{{width:100%;height:100%;object-fit:cover;object-position:78% 30%}}
.product{{position:absolute;left:84px;top:620px;width:816px;display:grid;grid-template-columns:250px 1fr;align-items:center;gap:22px 26px}}
.product span{{font-weight:800;font-size:26px;letter-spacing:1px;color:#efe5d4}}
.game-shot,.product-review{{height:250px;border:1px solid #fff3;border-radius:18px;overflow:hidden;background:#15171b}}
.game-shot img{{width:100%;height:100%;object-fit:cover;object-position:right top}}
.product-review img{{width:100%;height:100%;object-fit:cover;object-position:right top}}
.s2 h1{{font-size:64px}}.mmr{{position:absolute;left:84px;top:565px;font:800 122px/1.2 Montserrat;color:#efe5d4;letter-spacing:-5px}}
.mmr small{{font:700 44px Montserrat;letter-spacing:0}}
.heroes{{position:absolute;left:84px;top:770px;width:816px;display:flex;gap:18px}}
.hero{{width:260px;overflow:hidden;border:1px solid #fff3;border-radius:20px;background:#17191d}}
.hero img{{width:260px;height:218px;object-fit:cover;object-position:center}}
.hero b{{display:block;font-size:26px;text-align:center;padding:19px 4px;color:#efe5d4}}
.volunteers{{position:absolute;left:84px;top:1130px;font-size:30px;color:#a0a2a9}}
.review-shot{{position:absolute;left:84px;top:700px;width:816px;height:430px;border:1px solid #fff3;border-radius:24px;overflow:hidden;box-shadow:0 32px 80px #0008}}
.review-shot img{{width:100%;height:100%;object-fit:cover;object-position:right top}}
.shot-label{{position:absolute;left:84px;top:1160px;font-size:25px;color:#a0a2a9}}
.feedback-list{{position:absolute;left:84px;top:640px;width:816px;display:flex;flex-direction:column;gap:25px}}
.feedback{{display:flex;gap:22px;align-items:center;background:#17191dd9;border:1px solid #fff2;border-radius:22px;padding:29px 22px}}
.feedback span{{font-size:28px;color:#f05560}}.feedback b{{font-size:36px;line-height:1.2;font-weight:650}}
.goals{{position:absolute;left:84px;top:690px;display:flex;flex-direction:column;gap:32px}}
.goal{{font:700 61px/1.2 Montserrat;letter-spacing:-1.5px}}.goal span{{color:#f05560;margin-right:25px}}
.s6 h1{{top:570px;font-size:76px;color:#efe5d4}}.end-logo{{position:absolute;left:84px;top:405px;width:104px;height:104px}}
.join{{position:absolute;left:84px;top:818px;font-size:30px;color:#a0a2a9}}
.address{{position:absolute;left:84px;top:980px;font:700 45px Montserrat;border-bottom:4px solid #f05560;padding-bottom:20px}}
.end-free{{position:absolute;left:84px;top:1110px;font-size:30px}}
.captions{{position:absolute;left:84px;top:1280px;width:816px;min-height:100px;padding:21px 28px;border-radius:20px;background:#08090beF;border:1px solid #ffffff25;text-align:center;font:750 54px/1.18 Inter;box-shadow:0 10px 30px #0006}}
.captions span{{display:inline}}.captions .said{{color:#f05560}}
.progress{{position:absolute;left:84px;top:1470px;width:816px;height:4px;background:#ffffff13}}.progress i{{display:block;height:100%;background:#f05560;transform-origin:left}}
</style><body><div class="glow"></div><div class="grid"></div>
<header><img src="{images["logo"]}"><b data-safe>Wardly</b><div class="free" data-safe>{esc(copy["free"])}</div></header>
<div class="label" data-safe>{esc(copy["label"])}</div>{sections}
<div class="captions" data-safe></div><div class="progress"><i></i></div>
<script>
const timeline={json.dumps(timeline, ensure_ascii=False)}, captions={json.dumps(captions, ensure_ascii=False)};
const total=timeline.at(-1).end, sections=[...document.querySelectorAll('.scene')];
const escape=s=>s.replace(/[&<>"']/g,c=>({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[c]));
window.renderAt=t=>{{
  const active=Math.max(0,timeline.findIndex(s=>t>=s.start&&t<s.end));
  sections.forEach((el,i)=>{{
    const local=t-timeline[i].start;
    el.style.visibility=i===active?'visible':'hidden';
    el.style.opacity=i===active?Math.min(1,Math.max(0,local/.14)):0;
    el.querySelectorAll('[data-reveal]').forEach(x=>{{
      const a=Math.min(1,Math.max(0,(local-Number(x.dataset.reveal))/.25));
      x.style.opacity=a; x.style.transform=`translateX(${{(1-a)*24}}px)`;
    }});
    el.querySelectorAll('.hook-art img,.review-shot img').forEach(x=>x.style.transform=`scale(${{1+Math.max(0,local)*.004}})`);
  }});
  const cue=captions.find(c=>t>=c.start&&t<c.end), box=document.querySelector('.captions');
  box.style.display=cue?'block':'none';
  box.innerHTML=cue?cue.words.map(w=>`<span class="${{t>=w.s?'said':''}}">${{escape(w.w)}}</span>`).join(' '):'';
  document.querySelector('.progress i').style.transform=`scaleX(${{Math.min(1,t/total)}})`;
}};
window.layoutErrors=()=>[...document.querySelectorAll('[data-safe]')].flatMap(el=>{{
  if(el.closest('.scene')?.style.visibility==='hidden'||getComputedStyle(el).display==='none')return [];
  const r=el.getBoundingClientRect();
  const errors=[];
  if(r.left<78||r.top<196||r.right>910||r.bottom>1450)errors.push({{text:el.textContent,box:[r.left,r.top,r.right,r.bottom]}});
  if(el.scrollWidth>el.clientWidth+2||el.scrollHeight>el.clientHeight+2)errors.push({{text:el.textContent,overflow:true}});
  return errors;
}});
window.renderAt(0);
</script></body></html>'''
