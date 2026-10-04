"""Build the generated parts of the site from the coach's own data.

- the hero lists on site/heroes.html (from data/heroes/hero_profiles.json);
- one page per full-advisor hero: site/heroes/<slug>.html (ru) and
  site/en/heroes/<slug>.html (en) — last-hit pace, when to back off, the saves
  the coach names, the key fight ability and the profile's note: the numbers
  the live coach itself uses (hero_profiles, advice_context, live_tools);
- the static English pages site/en/index.html and site/en/heroes.html, made
  from the Russian HTML and the English texts in site/i18n-en.js;
- site/sitemap.xml.

    python scripts/build_site.py          # write the files
    python scripts/build_site.py --check  # fail when a file is out of date (CI)

Run from anywhere; needs the backend's requirements (it imports backend/app).
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
BASE = "https://luhovyimvp.dev"
sys.path.insert(0, str(ROOT / "backend"))

from app.advice_context import LH_RANGE_POINTS
from app.hero_profiles import POSITION_PACE
from app.live_tools import USABLE_SAFETY

ASSET_VERSION = "9"
POSITIONS = ("carry", "mid", "offlane", "support")
POSITION_NAMES = {
    "ru": {"carry": "Керри", "mid": "Мид", "offlane": "Хардлайн", "support": "Саппорт"},
    "en": {"carry": "Carry", "mid": "Mid", "offlane": "Offlane", "support": "Support"},
}
ARCHETYPES = {
    "hard_scaling_farmer": ("фармящий керри, который раскрывается к поздней игре", "a farming carry who comes online late"),
    "tempo_fighting_carry": ("керри, который рано начинает драться", "a carry who starts fighting early"),
    "ranged_carry": ("керри дальнего боя, которому важна позиция", "a ranged carry who lives by positioning"),
    "durable_tempo_core": ("живучий кор, который задаёт темп", "a durable core who sets the tempo"),
    "mobile_tempo_mid": ("подвижный мидер, который играет от темпа", "a mobile mid who plays for tempo"),
    "ranged_tempo_mid": ("мидер дальнего боя, который играет от темпа", "a ranged mid who plays for tempo"),
    "frontline_initiator": ("хардлайнер, который начинает драки", "an offlaner who starts the fights"),
    "fragile_hard_support": ("хрупкий саппорт пятой позиции, которому важнее всего позиция", "a fragile hard support who lives by positioning"),
    "disable_support": ("саппорт с контролем, который решает, кого поймать", "a support with disables who decides who gets caught"),
    "save_support": ("саппорт, который спасает своих", "a support who saves the team"),
    "fight_support": ("саппорт, который выигрывает драки одним заклинанием", "a support whose one spell wins fights"),
    "durable_support": ("живучий саппорт, который может стоять впереди", "a durable support who can stand in front"),
    "roaming_support": ("саппорт четвёртой позиции, который ходит по карте", "a roaming soft support"),
    "roaming_initiator": ("саппорт четвёртой позиции, который начинает драки", "a soft support who starts the fights"),
    "fragile_nuker": ("хрупкий саппорт, который наносит много урона издалека", "a fragile support who deals damage from range"),
}
# The profile's note in Russian (the profile keeps it in English); a few English
# notes written for the coach are reworded for players here.
NOTES_RU = {
    "Anti-Mage": "Не лезь вперёд, пока Blink на перезарядке.",
    "Juggernaut": "Не навязывай размены, пока Blade Fury на перезарядке.",
    "Lifestealer": "Не прыгай под контроль, пока Rage на перезарядке.",
    "Medusa": "Мана — это твоя живучесть, а не только ресурс на заклинания.",
    "Slark": "Не затягивай размены, когда нечем уйти или сбросить с себя эффекты.",
    "Morphling": "Не рискуй в разменах, пока Waveform на перезарядке или нечем перелить силу (Attribute Shift).",
    "Phantom Assassin": "Не прыгай вперёд, когда уйти почти нечем.",
    "Drow Ranger": "Держи дистанцию, когда нечем защититься.",
    "Luna": "Не заходи далеко без поддержки команды.",
    "Sven": "Не навязывай размены, пока Warcry на перезарядке и нечем уйти.",
    "Kez": "Трать рывки осторожно и не ныряй за невыгодными убийствами.",
    "Ursa": "Не лезь под контроль, пока Enrage не готов.",
    "Monkey King": "Не вступай в драку, если из неё нечем выпрыгнуть.",
    "Spectre": "Фарми безопасно и не трать время на невыгодные ранние драки.",
    "Terrorblade": "Не начинай драки без Metamorphosis и без команды.",
    "Phantom Lancer": "Не вступай в драку, пока Doppelganger на перезарядке.",
    "Naga Siren": "Не фарми опасные места, когда нечем уйти.",
    "Sniper": "Стой дальше, когда нечем защититься.",
    "Muerta": "Не стой впереди без прикрытия команды.",
    "Gyrocopter": "Ровный фарм важнее драк: не ныряй без поддержки.",
    "Ember Spirit": "Не лезь в невыгодные драки: держи Sleight of Fist и Flame Guard, чтобы уйти.",
    "Shadow Fiend": "Своего спасения нет: думай о Blink или Black King Bar и дерись за спинами команды.",
    "Storm Spirit": "Ball Lightning спасает, только пока на него хватает маны.",
    "Queen of Pain": "Не прыгай в драку, пока Blink на перезарядке.",
    "Puck": "Phase Shift спасает от одного удара: береги его от оглушения, а не от мелкого урона.",
    "Templar Assassin": "Без зарядов Refraction она хрупкая: отойди и дождись их.",
    "Void Spirit": "Держи Dissimilate или Astral Step, чтобы уйти.",
    "Outworld Destroyer": "Своего спасения нет: держи дистанцию и Force Staff или Blink.",
    "Dragon Knight": "Живучий, но медленный: не гонись далеко от команды без Elder Dragon Form.",
    "Axe": "Начинай драку, когда команда рядом; не прыгай в одиночку с малым HP.",
    "Mars": "Береги Arena of Blood для драки, в которую команда успеет.",
    "Legion Commander": "Бери Duel, только когда выигрываешь его: сначала проверь HP и Blink.",
    "Bristleback": "Поворачивайся спиной к урону и не стой лицом в проигранной драке.",
    "Centaur Warrunner": "Stampede спасает и команду: оставь его на отход, если драка пошла не так.",
    "Tidehunter": "Ravage выигрывает драки: не умирай, пока команда не подошла.",
    "Slardar": "Guardian Sprint — и зайти, и уйти: с малым HP не трать его на заход.",
    "Timbersaw": "Timber Chain нужны деревья: дерись рядом с ними и держи его на отход.",
    "Pangolier": "Держи Swashbuckle или Rolling Thunder на отход.",
    "Primal Beast": "Onslaught — это заход: не несись в одиночку с малым HP.",
    "Crystal Maiden": "Стой за корами: Freezing Field нужна безопасная точка, а позже — Black King Bar или Glimmer Cape.",
    "Lion": "Держи Hex на рывок врага или его главного героя; с Blink Dagger каждая драка начинается с тебя.",
    "Shadow Shaman": "Shackles держит тебя на месте: кастуй его, только когда враг не может ответить.",
    "Witch Doctor": "Death Ward не даёт двигаться: ставь его из-за деревьев или с готовым Glimmer Cape.",
    "Lich": "Frost Shield — на кора, которого бьют; Chain Frost лучше всего, когда враги стоят рядом.",
    "Dazzle": "Shallow Grave спасёт кора, только если ты рядом: но не будь первым, кого видит враг.",
    "Oracle": "Держи False Promise для кора в беде — или для себя, когда цель ты.",
    "Warlock": "Chaotic Offering выигрывает драки: держи его на момент, когда враг уже вошёл.",
    "Jakiro": "Ice Path и Macropyre выигрывают линию и вышки: дави, когда коры рядом.",
    "Vengeful Spirit": "Nether Swap спасает пойманного кора, но ставит на его место тебя: меняйся, только если переживёшь.",
    "Disruptor": "Glimpse — на героя, который прыгнул; Kinetic Field и Static Storm запирают драку.",
    "Ogre Magi": "Огр может стоять впереди, но Bloodlust на коре стоит больше твоих разменов.",
    "Treant Protector": "Living Armor спасает вышки и коров с любой точки карты; Overgrowth начинает драку.",
    "Rubick": "Не показывайся, пока враг не потратил своё главное заклинание, — и забери его.",
    "Earthshaker": "Echo Slam нужны Blink Dagger и враги рядом друг с другом: дождись, пока они соберутся.",
    "Tusk": "Ice Shards отрезает путь отхода; Snowball берёт союзника с собой на убийство.",
    "Earth Spirit": "Rolling Boulder — ещё и твой отход: держи его, когда уходишь далеко вперёд.",
    "Mirana": "Держи Leap на отход; Moonlight Shadow переворачивает драку или спасает всю команду.",
    "Skywrath Mage": "Тебя убьёт любой, кто дотянется: кастуй сзади и держи Force Staff или Glimmer Cape.",
    "Snapfire": "Firesnap Cookie на себя выпрыгивает из опасности; Mortimer Kisses отрезает место драки.",
    "Hoodwink": "Scurry рядом с деревьями держит тебя в живых; для Bushwhack нужно дерево за врагом.",
    "Spirit Breaker": "Бей Charge по тому, до кого команда успеет; Bulldoze выведет, если пошло не так.",
    "Nyx Assassin": "Vendetta ещё и прячет: держи её или Spiked Carapace на случай, если поймали.",
    "Bounty Hunter": "Track на главного героя врага — это золото и обзор; Shadow Walk — твой отход.",
    "Clockwerk": "Hookshot начинает драку: лети, когда команда достаточно близко, чтобы успеть.",
}
NOTES_EN = {
    "Ember Spirit": "Avoid low-value fights: keep Sleight of Fist and Flame Guard for the way out.",
}
FALLBACK_SAVES = "Force Staff, Blink Dagger, Black King Bar, Ghost Scepter, Magic Wand"


# --- data -------------------------------------------------------------------------


def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def load_profiles() -> list[dict]:
    data = json.loads((ROOT / "data" / "heroes" / "hero_profiles.json").read_text(encoding="utf-8"))
    return data["profiles"]


def portrait_keys() -> dict[str, str]:
    text = (ROOT / "frontend" / "launcher" / "renderer" / "dota-data.js").read_text(encoding="utf-8")
    data = json.loads(text[text.index("=") + 1 : text.rindex(";")])
    return {name: key for name, key in data["heroes"].values()}


def english_texts() -> dict[str, str]:
    text = (SITE / "i18n-en.js").read_text(encoding="utf-8")
    return json.loads(text[text.index("{") : text.rindex("}") + 1])


def saves(profile: dict) -> list[str]:
    names = profile["key_escape_abilities"] + profile["key_defensive_abilities"]
    return [name for name in names if name.lower() in USABLE_SAFETY]


def pace_rows(profile: dict, position: str) -> list[tuple[int, int, int]]:
    """Last hits by minute: the profile's lane targets, then the carry pace scaled by position."""
    rows = [(int(m), low, high) for m, (low, high) in sorted(profile["laning_expected_lh"].items(), key=lambda kv: int(kv[0]))]
    factor = POSITION_PACE.get(position, 1.0)
    rows += [(m, round(low * factor), round(high * factor)) for m, low, high in LH_RANGE_POINTS if m > rows[-1][0]]
    return rows


def heroes() -> list[dict]:
    keys = portrait_keys()
    out = []
    for profile in load_profiles():
        name = profile["hero"]
        position = profile.get("position", "carry")
        if name not in keys:
            raise SystemExit(f"no portrait key for {name} in dota-data.js")
        if name not in NOTES_RU:
            raise SystemExit(f"no Russian note for {name} in scripts/build_site.py")
        out.append(
            {
                "name": name,
                "slug": slug(name),
                "key": keys[name],
                "position": position,
                "profile": profile,
                "saves": saves(profile),
                "pace": pace_rows(profile, position),
            }
        )
    return sorted(out, key=lambda h: (POSITIONS.index(h["position"]), h["name"]))


# --- the hero lists on heroes.html -------------------------------------------------


def hero_card(hero: dict) -> str:
    small = f"<small>{html.escape(', '.join(hero['saves']))}</small>" if hero["saves"] else ""
    return (
        f'              <li><a href="heroes/{hero["slug"]}.html"><img src="assets/heroes/{hero["key"]}.webp" alt="" '
        f'width="256" height="144" loading="lazy" /><span><b>{html.escape(hero["name"])}</b>{small}</span></a></li>'
    )


def with_hero_lists(page: str, all_heroes: list[dict]) -> str:
    for position in POSITIONS:
        group = [h for h in all_heroes if h["position"] == position]
        cards = "\n".join(hero_card(h) for h in group)
        page, count = re.subn(
            rf'(<ul class="heroes" aria-labelledby="heroes-{position}">\n).*?(\n\s*</ul>)',
            lambda m, cards=cards: m.group(1) + cards + m.group(2),
            page,
            count=1,
            flags=re.DOTALL,
        )
        if not count:
            raise SystemExit(f"heroes.html: no list for {position}")
        page = re.sub(
            rf'(id="heroes-{position}">.*?</span> · )\d+(</h3>)', rf"\g<1>{len(group)}\2", page, count=1, flags=re.DOTALL
        )
    return page


# --- Russian HTML → static English page --------------------------------------------

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}


def _english_url(url: str, depth: int) -> str:
    """A relative URL of a Russian page as seen from its English copy `depth` levels down."""
    if not url or re.match(r"^(#|/|[a-z]+:|//)", url):
        return url
    # Pages with an English copy stay inside /en/; everything else is shared.
    if url in ("./",) or url.startswith(("./#", "heroes.html", "heroes/")):
        return url
    return "../" * depth + url


class _Translator(HTMLParser):
    def __init__(self, en: dict[str, str], page: dict) -> None:
        super().__init__(convert_charrefs=False)
        self.en = en
        self.page = page
        self.out: list[str] = []
        self.skip: list = []  # [tag, depth] while an element's Russian content is replaced
        self.in_title = False
        self.in_ld = False
        self.missing: list[str] = []

    def text(self, key: str) -> str:
        if key not in self.en:
            self.missing.append(key)
            return ""
        return self.en[key]

    def _tag(self, tag: str, attrs: list[tuple[str, str | None]], close: bool) -> str:
        parts = [tag]
        for name, value in attrs:
            parts.append(name if value is None else f'{name}="{html.escape(value, quote=True)}"')
        return "<" + " ".join(parts) + (" />" if close else ">")

    def _rewrite(self, tag: str, attrs: list[tuple[str, str | None]]) -> tuple[list, str | None, bool]:
        """(attributes, replacement content, is html) for one start tag."""
        a = dict(attrs)
        depth = self.page["depth"]
        content = None
        is_html = False
        new: list[tuple[str, str | None]] = []
        for name, value in attrs:
            if name in ("src", "href") and value is not None:
                value = _english_url(value, depth)
            elif name == "style" and value:
                value = re.sub(r"url\((?!['\"]?(?:[a-z]+:|/|#))", "url(" + "../" * depth, value)
            new.append((name, value))
        if tag == "html":
            new = [(n, v) for n, v in new if n not in ("lang", "data-static", "data-alt-en")]
            new = [("lang", "en"), ("data-static", "en"), ("data-alt-ru", self.page["alt_ru"])] + new
        if tag == "meta":
            if a.get("name") == "description" or a.get("property") in ("og:description",):
                key = self.page["description"] if a.get("name") == "description" else self.page["og_description"]
                new = [(n, self.text(key) if n == "content" else v) for n, v in new]
            elif a.get("property") == "og:title":
                new = [(n, self.text(self.page["title"]) if n == "content" else v) for n, v in new]
            elif a.get("property") == "og:url":
                new = [(n, self.page["url"] if n == "content" else v) for n, v in new]
        if tag == "link" and a.get("rel") == "canonical":
            new = [(n, self.page["url"] if n == "href" else v) for n, v in new]
        if "data-i18n-aria" in a:
            new = [(n, self.text(a["data-i18n-aria"]) if n == "aria-label" else v) for n, v in new]
        if "data-i18n-alt" in a:
            new = [(n, self.text(a["data-i18n-alt"]) if n == "alt" else v) for n, v in new]
        pictures = {
            "data-img": "assets/app/en/{}.jpg?v={v}",
            "data-ov": "assets/overlay/en/{}.webp?v={v}",
            "data-game": "assets/game/{}-en.jpg?v={v}",
            "data-shot": "assets/shots/en/{}.jpg?v={v}",
        }
        for attr, pattern in pictures.items():
            if attr in a:
                src = "../" * depth + pattern.format(a[attr], v=self.page["shots"])
                new = [(n, src if n == "src" else v) for n, v in new]
        if "data-i18n" in a:
            content = html.escape(self.text(a["data-i18n"]), quote=False)
        elif "data-i18n-html" in a:
            content, is_html = self.text(a["data-i18n-html"]), True
        return new, content, is_html

    def handle_starttag(self, tag, attrs):
        if self.skip:
            if tag == self.skip[0]:
                self.skip[1] += 1
            return
        new, content, _ = self._rewrite(tag, attrs)
        self.out.append(self._tag(tag, new, False))
        if tag == "title":
            self.in_title = True
            self.out.append(html.escape(self.text(self.page["title"]), quote=False))
        if tag == "script" and dict(attrs).get("type") == "application/ld+json":
            self.in_ld = True
        if content is not None and tag not in VOID:
            self.out.append(content)
            self.skip = [tag, 1]

    def handle_startendtag(self, tag, attrs):
        if self.skip:
            return
        new, _, _ = self._rewrite(tag, attrs)
        self.out.append(self._tag(tag, new, True))

    def handle_endtag(self, tag):
        if self.skip:
            if tag == self.skip[0]:
                self.skip[1] -= 1
                if self.skip[1] == 0:
                    self.skip = []
                    self.out.append(f"</{tag}>")
            return
        if tag == "title":
            self.in_title = False
        if tag == "script":
            self.in_ld = False
        self.out.append(f"</{tag}>")

    def handle_data(self, data):
        if self.skip or self.in_title:
            return
        if self.in_ld and data.strip():
            ld = json.loads(data)
            ld["description"] = self.text(self.page["description"])
            ld["url"] = self.page["url"]
            ld["inLanguage"] = "en"
            ld["alternateName"] = "Wardly — a Dota 2 coach"
            data = "\n    " + json.dumps(ld, ensure_ascii=False, indent=2).replace("\n", "\n    ") + "\n    "
        self.out.append(data)

    def handle_entityref(self, name):
        if not (self.skip or self.in_title):
            self.out.append(f"&{name};")

    def handle_charref(self, name):
        if not (self.skip or self.in_title):
            self.out.append(f"&#{name};")

    def handle_comment(self, data):
        if not self.skip:
            self.out.append(f"<!--{data}-->")

    def handle_decl(self, decl):
        self.out.append(f"<!{decl}>")


def english_page(source: str, en: dict[str, str], page: dict) -> str:
    translator = _Translator(en, page)
    translator.feed(source)
    translator.close()
    if translator.missing:
        raise SystemExit(f"site/i18n-en.js lacks: {', '.join(sorted(set(translator.missing)))}")
    return "".join(translator.out)


# --- hero pages --------------------------------------------------------------------

T = {
    "ru": {
        "skip": "Перейти к содержанию",
        "nav": [("#ingame", "В игре"), ("#how", "Как это работает"), ("#review", "Разбор"), ("#profile", "Профиль")],
        "heroes": "Герои",
        "faq": "Вопросы",
        "download": "Скачать",
        "download_long": "Скачать для Windows",
        "lang": "Язык",
        "title": "{name} в Dota 2: сколько добивать и когда уходить — Wardly",
        "description": "{name} ({position}): темп добиваний по минутам, когда уходить и чем спасаться — цифры, по которым бесплатный тренер Wardly подсказывает прямо в матче.",
        "lead": "{name} — {archetype}. Ниже цифры, по которым Wardly подсказывает на этом герое прямо в матче: сколько добивать, когда уходить и чем спасаться.",
        "pace_title": "Темп добиваний",
        "pace_minute": "Минута",
        "pace_lh": "Добивания",
        "pace_note": "Отстаёшь от нижней цифры — тренер скажет об этом прямо в матче и покажет, какой темп хороший на этой минуте.",
        "pace_note_support": "Саппорту не нужно много добивать: цифры — ориентир, а не цель. Если начнёшь забирать крипов у керри, тренер напомнит.",
        "survive_title": "Когда уходить",
        "hp": "При HP ниже {low} % тренер подскажет уйти, ниже {critical} % — срочно, сразу, без паузы.",
        "saves": "Спасение: {saves} — тренер назовёт его, когда оно готово, и напомнит, если ты умер, не нажав его.",
        "no_saves": "Своего спасения нет: тренер назовёт готовый предмет — {items}.",
        "mana": "Мана здесь — это спасение: тренер предупредит, когда её меньше {mana} %.",
        "fight_title": "В драке",
        "fight": "Главное в драке: {abilities}.",
        "note": "Совет тренера: {note}",
        "more_title": "Что ещё подскажет Wardly",
        "more": {
            "carry": [
                "План на игру с пика: цель по добиваниям к 10:00 и ключевой предмет.",
                "Следующий предмет сборки и сколько золота до него.",
                "Нет ТП больше минуты — напомнит. После 30-й минуты оставит золото на байбэк.",
            ],
            "mid": [
                "Проверки добиваний на 5:00 и 8:00 и напоминание про Bottle.",
                "Руны за 20 секунд, а с 6-го уровня — когда идти на другую линию.",
                "Следующий предмет сборки и сколько золота до него.",
            ],
            "offlane": [
                "Проигранная линия — подскажет стянуть большой лагерь.",
                "Темп фарма хардлайнера, а не керри: цели ниже на 30 %.",
                "Ключевой предмет вовремя или поздно — и когда твоё окно для драки.",
            ],
            "support": [
                "Стаки на :53 и пулы малого лагеря на лёгкой линии — за 10 секунд до времени.",
                "Нет вардов или вард слишком долго лежит в сумке — напомнит поставить.",
                "Нет спасающего предмета к 12-й минуте — подскажет Glimmer Cape или Force Staff.",
            ],
        },
        "after": "После матча — разбор: оценка, карта смертей, сборка против статистики OpenDota.",
        "cta_title": "Попробуй на следующей игре",
        "cta_text": "Бесплатно, для Windows 10 и 11. Официальная интеграция Valve — без риска для аккаунта.",
        "others": "Другие герои · {position}",
        "all": "Все герои",
        "footer_label": "Ссылки",
        "releases": "Версии",
        "issues": "Сообщить о проблеме",
        "changelog": "Что нового",
        "privacy": "Конфиденциальность",
        "legal": "Dota 2 — товарный знак Valve Corporation. Проект не связан с Valve и не одобрен ею. Портреты героев — Valve.",
    },
    "en": {
        "skip": "Skip to content",
        "nav": [("#ingame", "In game"), ("#how", "How it works"), ("#review", "Review"), ("#profile", "Profile")],
        "heroes": "Heroes",
        "faq": "FAQ",
        "download": "Download",
        "download_long": "Download for Windows",
        "lang": "Language",
        "title": "{name} in Dota 2: last hits by minute and when to back off — Wardly",
        "description": "{name} ({position}): last hits by minute, when to back off and what saves you — the numbers the free Wardly coach uses to advise you during the match.",
        "lead": "{name} is {archetype}. These are the numbers Wardly uses on this hero during the match: how many last hits, when to back off and what saves you.",
        "pace_title": "Last-hit pace",
        "pace_minute": "Minute",
        "pace_lh": "Last hits",
        "pace_note": "Below the lower number, the coach tells you during the match and shows a good pace for that minute.",
        "pace_note_support": "A support does not need many last hits: the numbers are a guide, not a goal. If you start taking the carry's creeps, the coach reminds you.",
        "survive_title": "When to back off",
        "hp": "Under {low}% HP the coach tells you to leave; under {critical}% it is urgent and comes at once.",
        "saves": "Your save: {saves}. The coach names it when it is ready and reminds you if you died without pressing it.",
        "no_saves": "No save of your own: the coach names a ready item — {items}.",
        "mana": "Mana is your escape here: the coach warns you under {mana}%.",
        "fight_title": "In a fight",
        "fight": "Your key fight ability: {abilities}.",
        "note": "Coach's tip: {note}",
        "more_title": "What else Wardly tells you",
        "more": {
            "carry": [
                "A plan from the pick: a last-hit target for 10:00 and the key item.",
                "The next item of the build and the gold still needed for it.",
                "No TP for a minute — a reminder. After minute 30 it keeps your buyback gold.",
            ],
            "mid": [
                "Last-hit checks at 5:00 and 8:00 and a Bottle reminder.",
                "Runes 20 seconds ahead, and from level 6 when to go to a side lane.",
                "The next item of the build and the gold still needed for it.",
            ],
            "offlane": [
                "A lost lane — a hint to pull the big camp.",
                "An offlaner's farm pace, not a carry's: targets 30% lower.",
                "Your key item on time or late — and when your window to fight is.",
            ],
            "support": [
                "Stacks at :53 and small-camp pulls in the safe lane, 10 seconds ahead.",
                "No wards, or a ward kept in the bag too long — a reminder to place it.",
                "No save item by minute 12 — a hint for Glimmer Cape or Force Staff.",
            ],
        },
        "after": "After the match — a review: a score, a map of your deaths, the build against OpenDota statistics.",
        "cta_title": "Try it in your next game",
        "cta_text": "Free, for Windows 10 and 11. Valve's official integration — no risk for your account.",
        "others": "Other heroes · {position}",
        "all": "All heroes",
        "footer_label": "Links",
        "releases": "Releases",
        "issues": "Report a problem",
        "changelog": "What's new",
        "privacy": "Privacy",
        "legal": "Dota 2 is a trademark of Valve Corporation. This project is not affiliated with or endorsed by Valve. Hero portraits are Valve's.",
    },
}

ICONS = """    <svg width="0" height="0" style="position: absolute" aria-hidden="true">
      <defs>
        <symbol id="i-windows" viewBox="0 0 24 24"><path d="M3 5.5 10.5 4.4v7.1H3zM11.5 4.3 21 3v8.5h-9.5zM3 12.5h7.5v7.1L3 18.5zM11.5 12.5H21V21l-9.5-1.3z" fill="currentColor" stroke="none" /></symbol>
        <symbol id="i-check" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" /><path d="m9 12 2 2 4-4" /></symbol>
      </defs>
    </svg>"""


def hero_page(hero: dict, all_heroes: list[dict], lang: str) -> str:
    t = T[lang]
    e = html.escape
    name, position, profile = hero["name"], hero["position"], hero["profile"]
    up = "../" if lang == "ru" else "../../"  # to the site root
    home = "../"  # to this language's home page
    ru_url = f"{BASE}/heroes/{hero['slug']}.html"
    en_url = f"{BASE}/en/heroes/{hero['slug']}.html"
    url = ru_url if lang == "ru" else en_url
    alt = f'data-alt-en="../en/heroes/{hero["slug"]}.html"' if lang == "ru" else f'data-alt-ru="../../heroes/{hero["slug"]}.html"'
    position_name = POSITION_NAMES[lang][position]
    archetype = ARCHETYPES[profile["archetype"]][0 if lang == "ru" else 1]
    title = t["title"].format(name=name)
    description = t["description"].format(name=name, position=position_name.lower())
    note = NOTES_RU[name] if lang == "ru" else NOTES_EN.get(name, profile["notes"])
    if lang == "ru" and re.match(r"[А-ЯЁ][а-яё]", note):
        note = note[0].lower() + note[1:]  # after «Совет тренера:», unless it starts with a name

    rows = "\n".join(
        f"                  <tr><td>{minute}:00</td><td>{low}–{high}</td></tr>" for minute, low, high in hero["pace"]
    )
    survive = [t["hp"].format(low=profile["low_hp_warning_threshold"], critical=profile["critical_hp_threshold"])]
    survive.append(
        t["saves"].format(saves=", ".join(hero["saves"])) if hero["saves"] else t["no_saves"].format(items=FALLBACK_SAVES)
    )
    if profile.get("survival_resource") == "mana":
        survive.append(t["mana"].format(mana=profile["mana_warning_threshold"]))
    checks = lambda items: "\n".join(
        f'                  <li><svg class="i" aria-hidden="true"><use href="#i-check" /></svg><span>{e(item)}</span></li>'
        for item in items
    )
    fight = [t["fight"].format(abilities=", ".join(profile["key_fight_abilities"])), t["note"].format(note=note)]
    more = t["more"][position] + [t["after"]]
    others = "\n".join(
        f'            <a class="chip" href="{h["slug"]}.html"><img src="{up}assets/heroes/{h["key"]}.webp" alt="" width="256" height="144" loading="lazy" />{e(h["name"])}</a>'
        for h in all_heroes
        if h["position"] == position and h is not hero
    )
    nav = "\n".join(f'          <a href="{home}{anchor}">{e(label)}</a>' for anchor, label in t["nav"])
    download = "https://github.com/makquella/dota-ai-coach/releases/latest"
    return f"""<!doctype html>
<html lang="{lang}" data-static="{lang}" {alt}>
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{e(title)}</title>
    <meta name="description" content="{e(description)}" />
    <meta name="theme-color" content="#0c0d0f" />
    <meta property="og:type" content="article" />
    <meta property="og:title" content="{e(title)}" />
    <meta property="og:description" content="{e(description)}" />
    <link rel="canonical" href="{url}" />
    <link rel="alternate" hreflang="ru" href="{ru_url}" />
    <link rel="alternate" hreflang="en" href="{en_url}" />
    <link rel="alternate" hreflang="x-default" href="{ru_url}" />
    <meta property="og:url" content="{url}" />
    <meta property="og:image" content="{BASE}/assets/og.jpg?v=6" />
    <meta name="twitter:card" content="summary_large_image" />
    <link rel="icon" href="{up}assets/favicon.png" type="image/png" />
    <link rel="stylesheet" href="{up}styles.css?v={ASSET_VERSION}" />
  </head>
  <body>
    <a class="skip" href="#main">{e(t["skip"])}</a>

    <header class="nav" id="top">
      <div class="wrap nav-inner">
        <a class="brand" href="{home}" aria-label="Wardly">
          <img class="brand-mark" src="{up}assets/logo-mark.png" alt="" width="28" height="28" />
          <span class="brand-name">Wardly</span>
        </a>
        <nav class="nav-links" aria-label="{e(t["footer_label"])}">
{nav}
          <a href="{home}heroes.html">{e(t["heroes"])}</a>
          <a href="{home}#faq">{e(t["faq"])}</a>
        </nav>
        <div class="nav-actions">
          <div class="lang" role="group" aria-label="{e(t["lang"])}">
            <button type="button" data-lang="ru" aria-pressed="{str(lang == "ru").lower()}">RU</button>
            <button type="button" data-lang="en" aria-pressed="{str(lang == "en").lower()}">EN</button>
          </div>
          <a class="btn btn-primary btn-sm js-download" href="{download}">
            <svg class="i" aria-hidden="true"><use href="#i-windows" /></svg>
            <span>{e(t["download"])}</span>
          </a>
        </div>
      </div>
    </header>

    <main id="main">
      <section class="page-head">
        <div class="wrap hero-head">
          <img class="hero-portrait" src="{up}assets/heroes/{hero["key"]}.webp" alt="{e(name)}" width="256" height="144" />
          <div>
            <p class="mode-tag"><a href="{home}heroes.html">{e(position_name)}</a></p>
            <h1>{e(name)}</h1>
            <p class="lead">{e(t["lead"].format(name=name, archetype=archetype))}</p>
          </div>
        </div>
      </section>

      <section class="section section-tight">
        <div class="wrap">
          <div class="modes">
            <article class="mode">
              <h2>{e(t["pace_title"])}</h2>
              <table class="pace">
                <thead><tr><th>{e(t["pace_minute"])}</th><th>{e(t["pace_lh"])}</th></tr></thead>
                <tbody>
{rows}
                </tbody>
              </table>
              <p class="mode-note">{e(t["pace_note_support" if position == "support" else "pace_note"])}</p>
            </article>
            <article class="mode">
              <h2>{e(t["survive_title"])}</h2>
              <ul class="checks">
{checks(survive)}
              </ul>
            </article>
            <article class="mode">
              <h2>{e(t["fight_title"])}</h2>
              <ul class="checks">
{checks(fight)}
              </ul>
            </article>
          </div>
        </div>
      </section>

      <section class="section section-alt">
        <div class="wrap hero-more">
          <div>
            <h2>{e(t["more_title"])}</h2>
            <ul class="checks">
{checks(more)}
            </ul>
          </div>
          <div class="hero-cta">
            <h2>{e(t["cta_title"])}</h2>
            <p>{e(t["cta_text"])}</p>
            <a class="btn btn-primary btn-lg js-download" href="{download}">
              <svg class="i" aria-hidden="true"><use href="#i-windows" /></svg>
              <span>{e(t["download_long"])}</span>
            </a>
          </div>
        </div>
      </section>

      <section class="section section-tight">
        <div class="wrap">
          <h2 class="heroes-group first">{e(t["others"].format(position=position_name))}</h2>
          <nav class="chips" aria-label="{e(t["others"].format(position=position_name))}">
{others}
          </nav>
          <p class="note"><a href="{home}heroes.html">{e(t["all"])} →</a></p>
        </div>
      </section>
    </main>

    <footer class="footer">
      <div class="wrap footer-inner">
        <a class="brand" href="{home}" aria-label="Wardly">
          <img class="brand-mark" src="{up}assets/logo-mark.png" alt="" width="24" height="24" />
          <span class="brand-name">Wardly</span>
        </a>
        <nav class="footer-links" aria-label="{e(t["footer_label"])}">
          <a href="https://github.com/makquella/dota-ai-coach" rel="noopener">GitHub</a>
          <a href="https://github.com/makquella/dota-ai-coach/releases" rel="noopener">{e(t["releases"])}</a>
          <a href="https://github.com/makquella/dota-ai-coach/issues" rel="noopener">{e(t["issues"])}</a>
          <a href="{home}heroes.html">{e(t["heroes"])}</a>
          <a href="{up}changelog.html">{e(t["changelog"])}</a>
          <a href="{up}privacy.html">{e(t["privacy"])}</a>
        </nav>
        <p class="footer-legal">{e(t["legal"])}</p>
      </div>
    </footer>

{ICONS}

    <script src="{up}i18n-en.js?v={ASSET_VERSION}" defer></script>
    <script src="{up}app.js?v={ASSET_VERSION}" defer></script>
  </body>
</html>
"""


# --- sitemap -----------------------------------------------------------------------


def sitemap(all_heroes: list[dict]) -> str:
    pairs = [("/", "/en/"), ("/heroes.html", "/en/heroes.html")]
    pairs += [(f"/heroes/{h['slug']}.html", f"/en/heroes/{h['slug']}.html") for h in all_heroes]
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">',
    ]
    for ru, en in pairs:
        for loc in (ru, en):
            lines.append(
                f"  <url><loc>{BASE}{loc}</loc>"
                f'<xhtml:link rel="alternate" hreflang="ru" href="{BASE}{ru}" />'
                f'<xhtml:link rel="alternate" hreflang="en" href="{BASE}{en}" /></url>'
            )
    for page in ("/changelog.html", "/privacy.html"):
        lines.append(f"  <url><loc>{BASE}{page}</loc></url>")
    lines.append("</urlset>")
    return "\n".join(lines) + "\n"


# --- all files ----------------------------------------------------------------------


def shots_version() -> str:
    match = re.search(r'const SHOTS_VERSION = "(\d+)"', (SITE / "app.js").read_text(encoding="utf-8"))
    return match.group(1) if match else "1"


def build() -> dict[Path, str]:
    all_heroes = heroes()
    en = english_texts()
    files: dict[Path, str] = {}
    heroes_ru = with_hero_lists((SITE / "heroes.html").read_text(encoding="utf-8"), all_heroes)
    files[SITE / "heroes.html"] = heroes_ru
    shots = shots_version()
    files[SITE / "en" / "index.html"] = english_page(
        (SITE / "index.html").read_text(encoding="utf-8"),
        en,
        {"depth": 1, "alt_ru": "../", "url": f"{BASE}/en/", "title": "title", "description": "metaDescription",
         "og_description": "ogDescription", "shots": shots},
    )
    files[SITE / "en" / "heroes.html"] = english_page(
        heroes_ru,
        en,
        {"depth": 1, "alt_ru": "../heroes.html", "url": f"{BASE}/en/heroes.html", "title": "heroesPageTitle",
         "description": "heroesMetaDescription", "og_description": "heroesOgDescription", "shots": shots},
    )
    for hero in all_heroes:
        files[SITE / "heroes" / f"{hero['slug']}.html"] = hero_page(hero, all_heroes, "ru")
        files[SITE / "en" / "heroes" / f"{hero['slug']}.html"] = hero_page(hero, all_heroes, "en")
    files[SITE / "sitemap.xml"] = sitemap(all_heroes)
    return files


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--check", action="store_true", help="fail when a generated file is out of date")
    args = parser.parse_args()
    files = build()
    generated_dirs = [SITE / "heroes", SITE / "en" / "heroes"]
    stray = [p for d in generated_dirs if d.exists() for p in d.glob("*.html") if p not in files]
    if args.check:
        stale = [p for p, text in files.items() if not p.exists() or p.read_text(encoding="utf-8") != text]
        if stale or stray:
            for path in stale:
                print(f"out of date: {path.relative_to(ROOT)}")
            for path in stray:
                print(f"not generated (remove it): {path.relative_to(ROOT)}")
            print("Run: python scripts/build_site.py")
            return 1
        print(f"site up to date ({len(files)} generated files)")
        return 0
    for path in stray:
        path.unlink()
    for path, text in files.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists() or path.read_text(encoding="utf-8") != text:
            path.write_text(text, encoding="utf-8")
    print(f"wrote {len(files)} files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
