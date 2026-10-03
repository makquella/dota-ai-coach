"""
map_hints.py - the overlay's one-line map hint: timers and role tips.

A second channel next to the advice card: it never replaces advice, never
goes through the scheduler and never speaks over it (the overlay reads timers
marked "speak" only when the voice reads every advice).

1. Timers (data/meta/map_timers.json, checked against a patch): runes, wisdom
   shrines, lotuses, the Tormentor, neutral item tiers. Each event is shown from
   `lead_seconds` before it until `grace_seconds` after, and only to the
   positions it matters for (app/live_role.py).
2. Role tips: "no TP scroll" for any hero the carry advisor does not follow
   (it has its own); mid: the level-6 rotation window, the last-hit pace at
   5:00 and 8:00, no Bottle in the first minutes, and with level 6 the power
   rune reads "take it and go to a side lane"; offlane: the level-6 pressure
   window and a lost lane (two deaths, or level 4 at 6:00) → pull the big camp
   and survive for experience; supports: leave the last hits to the carry,
   stack a camp in given minutes, pull the small camp at :15 / :45 in the safe
   lane, "no observer ward on you" at most every 5 minutes, and 1500+ gold
   kept after 8:00 → spend it. A tip wins over a minor timer (runes, lotus:
   the stack window always comes before a power rune).

Texts are built in the request language here (like game_plan.py); the file's
events carry both languages.
"""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from app.config import DATA_DIR
from app.last_moments import RUNES_RU
from app.live_tools import POWER_RUNES

TIMERS_PATH = DATA_DIR / "meta" / "map_timers.json"

# Support tip: stack a camp in these minutes (pull at :53-:55).
STACK_MINUTES = (4, 7, 10, 13, 16)
STACK_FROM_SECOND = 38
STACK_UNTIL_SECOND = 53
# Support tip: no observer ward in the inventory.
WARD_FROM_CLOCK = 150
WARD_EVERY = 5 * 60
WARD_SHOW = 20

WARD_ITEMS = {"item_ward_observer", "item_ward_dispenser"}
# Support tip: the same observer ward carried this long (nothing placed).
WARD_HELD = 2 * 60
WARD_HELD_EVERY = 3 * 60
# Support tip: an invisible enemy hero seen (enemy_heroes.py) and no Dust of
# Appearance or sentry ward carried.
INVIS_FROM = 6 * 60
INVIS_EVERY = 6 * 60
INVIS_SHOW = 20
DETECTION_ITEMS = {"item_dust", "item_ward_sentry", "item_ward_dispenser", "item_gem"}
# Where the ward goes: the lane's river until 10:00, then by the kill score
# (8+ kills apart, as the farm advice) or Roshan's pit while he can be up.
WARD_LANING_END = 10 * 60
WARD_SCORE_FROM = 12 * 60
WARD_SCORE_GAP = 8
# Support tip: no save item after this clock with this much gold.
SAVE_ITEMS = {
    "item_glimmer_cape",
    "item_force_staff",
    "item_hurricane_pike",
    "item_ghost",
    "item_ethereal_blade",
    "item_lotus_orb",
    "item_solar_crest",
    "item_pavise",
    "item_guardian_greaves",
}
SAVE_FROM = 12 * 60
# «Missing» calls (enemy_lanes.py): shown this long, at most one per MISSING_GAP.
MISSING_SHOW = 15
MISSING_GAP = 45
SAVE_GOLD = 1200
SAVE_EVERY = 5 * 60
SAVE_SHOW = 20
# Any role without the carry advisor (which has its own TP advice): no TP scroll.
TP_EVERY = 4 * 60
TP_SHOW = 20
# Support tip: a support farming the lane like a core leaves its carry poor.
LAST_HITS_FROM = 3 * 60
LAST_HITS_UNTIL = 10 * 60
SUPPORT_LH_PER_MIN = 2.5
LAST_HITS_EVERY = 3 * 60
# Level 6 before this clock: the mid's rotation window, the offlaner's pressure.
POWER_SPIKE_LEVEL = 6
POWER_SPIKE_UNTIL = 12 * 60
POWER_SPIKE_SHOW = 25
# Mid: last hits at these clocks against a good pace (a core's 55 at 10:00).
MID_LAST_HIT_CHECKS = {5 * 60: 25, 8 * 60: 44}
MID_LAST_HIT_SHOW = 20
# Mid: no Bottle in these minutes (most mids live on it and the runes).
BOTTLE_FROM = 3 * 60 + 30
BOTTLE_UNTIL = 6 * 60
BOTTLE_SHOW = 20
BOTTLE_ITEMS = {"item_bottle"}
# Lane tips for cores (0.36): what players forget in the first ten minutes.
# Regen on the way to lane: none of these in the inventory by 1:30.
LANE_REGEN_ITEMS = {
    "item_tango",
    "item_tango_single",
    "item_flask",
    "item_faerie_fire",
    "item_enchanted_mango",
    "item_bottle",
}
LANE_REGEN_UNTIL = 90
LANE_REGEN_SHOW = 20
# HP half gone in lane with nothing to heal and gold for a Healing Salve.
LANE_HP_FROM, LANE_HP_UNTIL = 120, 10 * 60
LANE_HP_LIMIT = 50
LANE_HP_GOLD = 110
LANE_HP_EVERY, LANE_HP_SHOW = 180, 15
# A Magic Stick by mid-lane: the cheapest save of the game.
STICK_ITEMS = {"item_magic_stick", "item_magic_wand"}
STICK_FROM, STICK_UNTIL = 3 * 60, 8 * 60
STICK_GOLD = 200
STICK_SHOW = 20
# Denies at 4:00 for a carry or a mid who is last-hitting.
DENY_AT = 4 * 60
DENY_SHOW = 20
DENY_MIN = 3
DENY_MIN_LAST_HITS = 8
# A power rune kept in the Bottle this long (clock seconds, alive) → use it.
BOTTLE_RUNE_HELD = 30
BOTTLE_RUNE_SHOW = 20
# Offlane: a lost lane — this many deaths, or below this level at 6:00.
HARD_LANE_FROM = 4 * 60
HARD_LANE_UNTIL = 9 * 60
HARD_LANE_DEATHS = 2
HARD_LANE_LEVEL_AT = 6 * 60
HARD_LANE_LEVEL = 5
HARD_LANE_SHOW = 25
# Safe-lane support: pull the small camp so the wave meets at the own tower.
PULL_FROM = 2 * 60
PULL_UNTIL = 8 * 60
PULL_WINDOWS = ((5, 15), (35, 45))  # (from second, pull at second)
PULL_EVERY = 2 * 60
PULL_SHOW = 10
# Cores: the hero's key item (OpenDota's most bought, with its typical finish
# time) — late by this much, or finished this much before the typical time.
KEY_ITEM_LATE = 2 * 60
KEY_ITEM_EARLY = 2 * 60
KEY_ITEM_SHOW = 25
CORE_ROLES = {"carry", "mid", "offlane"}
# Support: gold kept instead of wards, dust, smoke and a save item.
SPEND_FROM = 8 * 60
SPEND_GOLD = 1500
SPEND_EVERY = 4 * 60
SPEND_SHOW = 20

TIPS = {
    "stack": {
        "en": ("Stack a camp", "Pull the camp at :53 so the next spawn stacks on top."),
        "ru": ("Застакайте лагерь", "Отведите крипов на :53 — сверху появится новый лагерь."),
    },
    "tp": {
        "en": ("No TP scroll", "Buy one now: without it you cannot join a fight or save a tower."),
        "ru": (
            "Нет свитка телепортации",
            "Купите его сейчас: без ТП не успеть на драку и к вышке.",
        ),
    },
    "last_hits": {
        "en": (
            "Leave the last hits to your carry",
            "A support's gold comes from runes, stacks and kills.",
        ),
        "ru": ("Оставьте добивания керри", "Золото саппорта — руны, стаки и убийства."),
    },
    "wards": {
        "en": ("No observer wards on you", "Take wards from the shop and light up the next fight."),
        "ru": ("Нет вардов", "Возьмите варды в лавке и подсветите место следующей драки."),
    },
    "ward_bag": {
        "en": (
            "Place your observer ward",
            "A ward in the bag shows nothing: put it where the next fight or gank will come from.",
        ),
        "ru": (
            "Поставьте вард",
            "Вард в сумке ничего не показывает: поставьте его там, откуда придёт драка или ганк.",
        ),
    },
    "invis_dust": {
        "en": (
            "{enemy} goes invisible",
            "Carry Dust of Appearance or a sentry ward into fights: without them nobody can hit {enemy}.",
        ),
        "ru": (
            "{enemy} уходит в невидимость",
            "Носите в драки Dust of Appearance или сентри: без них {enemy} никто не ударит.",
        ),
    },
    # Where to put it: by the phase of the game, the kill score and Roshan.
    "ward_bag_lane": {
        "en": (
            "Place your observer ward",
            "Put it by the river next to your lane: a gank shows up before it reaches you.",
        ),
        "ru": (
            "Поставьте вард",
            "Поставьте его у реки рядом с вашей линией: ганк будет виден заранее.",
        ),
    },
    "ward_bag_behind": {
        "en": (
            "Place your observer ward",
            "Your team is {gap} kills behind: ward the entrances to your own jungle, "
            "where the enemy comes to catch your cores.",
        ),
        "ru": (
            "Поставьте вард",
            "Команда отстаёт на {gap} убийств: поставьте его у входа в свой лес — "
            "там враг ловит ваших коров.",
        ),
    },
    "ward_bag_ahead": {
        "en": (
            "Place your observer ward",
            "Your team is {gap} kills ahead: ward the enemy jungle so your team can "
            "catch their cores and take towers safely.",
        ),
        "ru": (
            "Поставьте вард",
            "Команда впереди на {gap} убийств: поставьте его в лесу врага — "
            "так команда поймает их коров и безопасно снесёт вышки.",
        ),
    },
    "ward_bag_roshan": {
        "en": (
            "Place your observer ward",
            "Roshan can be up now: put it by the Roshan pit so the enemy cannot take it unseen.",
        ),
        "ru": (
            "Поставьте вард",
            "Рошан может уже появиться: поставьте его у логова — враг не заберёт его незаметно.",
        ),
    },
    "save_item": {
        "en": (
            "No save item yet",
            "Glimmer Cape or Force Staff saves a core in a fight: buy one of them next.",
        ),
        "ru": (
            "Нет спасающего предмета",
            "Glimmer Cape или Force Staff спасают кора в драке: купите один из них следующим.",
        ),
    },
    # The save item most bought on the hero (cached OpenDota build).
    "save_item_hero": {
        "en": (
            "No save item yet: {item}",
            "{item} is the save item most bought on this hero: {left} gold to go.",
        ),
        "ru": (
            "Нет спасающего предмета: {item}",
            "{item} чаще всего берут на этом герое, чтобы спасать союзников: "
            "осталось {left} золота.",
        ),
    },
    "save_item_now": {
        "en": (
            "Buy {item} now",
            "{item} is the save item most bought on this hero, and you have the gold for it.",
        ),
        "ru": (
            "Купите {item} сейчас",
            "{item} чаще всего берут на этом герое, чтобы спасать союзников, "
            "и золота на него хватает.",
        ),
    },
    # The save item against the enemy lineup (situational_items.lineup_save_item).
    "save_item_now_lineup": {
        "en": (
            "Buy {item} now",
            "{item} fits against this enemy lineup, and you have the gold for it.",
        ),
        "ru": (
            "Купите {item} сейчас",
            "{item} лучше всего против этого состава врага, и золота на него хватает.",
        ),
    },
    "save_item_magic": {
        "en": (
            "{item} against their magic",
            "{count} enemy heroes deal magic damage, and {item} saves an ally from it.",
        ),
        "ru": (
            "{item} против магии",
            "Героев врага с магическим уроном: {count}, а {item} спасает от него союзника.",
        ),
    },
    "save_item_physical": {
        "en": (
            "{item} against their carries",
            "{enemy} and other right-click carries: {item} stops their attacks for a few seconds.",
        ),
        "ru": (
            "{item} против их керри",
            "У врага {enemy} и другие керри с ударами с руки: {item} на несколько секунд "
            "спасает от их атак.",
        ),
    },
    # An enemy gone from the minimap in the laning stage (enemy_lanes.py).
    "missing_mid": {
        "en": (
            "Enemy mid missing: {hero}",
            "{hero} has not been seen for {seconds} s and may be coming to your lane. "
            "Stay closer to your tower.",
        ),
        "ru": (
            "Не видно мида: {hero}",
            "{hero} не видно уже {seconds} с — может идти на вашу линию. "
            "Держитесь ближе к своей башне.",
        ),
    },
    "missing_lane": {
        "en": (
            "Your lane opponent is missing: {hero}",
            "{hero} has not been seen for {seconds} s: maybe coming around through the "
            "trees or off to another lane. Don't push up too far.",
        ),
        "ru": (
            "Соперник пропал с линии: {hero}",
            "{hero} не видно уже {seconds} с — может обходить через лес или идти на "
            "другую линию. Не заходите далеко вперёд.",
        ),
    },
    "mid_six": {
        "en": (
            "Level 6: look for a rotation",
            "Push the wave first, then check the side lanes with the next rune.",
        ),
        "ru": (
            "6-й уровень: время ротации",
            "Сначала запушьте волну, потом с руной посмотрите на боковые линии.",
        ),
    },
    "mid_last_hits": {
        "en": (
            "{last_hits} last hits by {time}",
            "A good mid has {target}+: last-hit and deny under your tower, trade only with the wave on your side.",
        ),
        "ru": (
            "{last_hits} {last_hits_word} к {time}",
            "Хороший мид — {target}+: добивайте и денайте под своей вышкой, размены — когда волна на вашей стороне.",
        ),
    },
    "mid_bottle": {
        "en": (
            "No Bottle yet",
            "Most mids live on it: every rune refills it, and it keeps you in the lane without going to base.",
        ),
        "ru": (
            "Нет бутылки",
            "Большинство мидеров живёт на ней: руна заполняет её, и не нужно ходить на базу.",
        ),
    },
    "lane_regen": {
        "en": (
            "No regen for the lane",
            "Take Tango or a Healing Salve: the first trades cost HP, and walking to base costs the lane.",
        ),
        "ru": (
            "Нет регена на линию",
            "Возьмите Tango или Healing Salve: первые размены стоят HP, а уход на базу стоит линии.",
        ),
    },
    "lane_hp": {
        "en": (
            "{hp}% HP and nothing to heal",
            "Buy a Healing Salve and send it with the courier: with half HP you cannot stand in for last hits.",
        ),
        "ru": (
            "{hp}% HP и нечем лечиться",
            "Купите Healing Salve и отправьте курьером: с половиной HP не постоишь за добиванием.",
        ),
    },
    "lane_stick": {
        "en": (
            "No Magic Stick yet",
            "200 gold: it charges from enemy spells and heals you in one press — the cheapest save of the lane.",
        ),
        "ru": (
            "Ещё нет Magic Stick",
            "200 золота: он заряжается от вражеских заклинаний и лечит одним нажатием — самое дешёвое спасение на линии.",
        ),
    },
    "lane_denies": {
        "en": (
            "{denies} denies by 4:00",
            "Finish your own creeps when they are low: a deny takes gold and half the experience from the enemy.",
        ),
        "ru": (
            "Добито своих крипов к 4:00: {denies}",
            "Добивайте своих крипов на низком HP: денай забирает у врага золото и половину опыта.",
        ),
    },
    "bottle_rune": {
        "en": (
            "{rune} rune in your Bottle",
            "Use it for a kill on a side lane: the Bottle holds one rune, and the next one comes soon.",
        ),
        "ru": (
            "Руна {rune_ru} в бутылке",
            "Используйте её для убийства на боковой линии: в бутылке помещается одна руна, "
            "а следующая появится скоро.",
        ),
    },
    "mid_rune": {
        "en": ("", "Take it and go straight to a side lane: the best moment to rotate."),
        "ru": ("", "Заберите её и сразу идите на боковую линию: лучший момент для ротации."),
    },
    "mid_rune_bottle": {
        "en": ("", "Bottle it if you do not need it now: keep it for a kill after the next wave."),
        "ru": (
            "",
            "Если сейчас не нужна — положите её в Bottle и приберегите для убийства после следующей волны.",
        ),
    },
    "offlane_hard_lane": {
        "en": (
            "A hard lane",
            "Stop feeding under their tower: pull the big camp into your wave and take the experience safely.",
        ),
        "ru": (
            "Тяжёлая линия",
            "Не умирайте под их вышкой: подтяните большой лагерь в свою волну и берите опыт без риска.",
        ),
    },
    "pull": {
        "en": (
            "Pull at {at_label}",
            "Pull the small camp into your wave so it meets at your tower.",
        ),
        "ru": (
            "Пул на {at_label}",
            "Отведите малый лагерь в свою волну: линия встанет у вашей вышки.",
        ),
    },
    "item_late": {
        "en": (
            "{item} is late",
            "Most players finish it by {time}. Farm camps between waves and skip fights until you have it.",
        ),
        "ru": (
            "{item} опаздывает",
            "Обычно его собирают к {time}. Фармите лагеря между волнами и не лезьте в драки без него.",
        ),
    },
    "item_early": {
        "en": (
            "{item} ahead of time",
            "Most players have it by {time}: this is your window — push and look for fights.",
        ),
        "ru": (
            "{item} раньше обычного",
            "Обычно его собирают к {time}: сейчас ваше окно — давите и ищите драки.",
        ),
    },
    "spend_gold": {
        "en": (
            "{gold} gold unspent",
            "Spend it now: wards, dust, a smoke or a save item such as Force Staff or Glimmer Cape.",
        ),
        "ru": (
            "{gold} золота не потрачено",
            "Потратьте сейчас: варды, дасты, смок или спасающий предмет — Force Staff, Glimmer Cape.",
        ),
    },
    "offlane_six": {
        "en": (
            "Level 6: pressure the lane",
            "With your support, go for the enemy carry or their tower while the wave is close.",
        ),
        "ru": (
            "6-й уровень: давите линию",
            "Вместе с саппортом идите на вражеского керри или вышку, пока волна рядом.",
        ),
    },
}


# The overlay's timer strip: the next events for the position, at most this many,
# within this many seconds (Roshan and the Aegis at any distance).
STRIP_SIZE = 3
STRIP_AHEAD = 3 * 60
STRIP_LABELS = {
    "water_rune": ("Водная руна", "Water rune"),
    "power_rune": ("Руна", "Rune"),
    "bounty_rune": ("Богатство", "Bounty"),
    "wisdom_shrine": ("Мудрость", "Wisdom"),
    "lotus": ("Лотос", "Lotus"),
    "tormentor": ("Торментор", "Tormentor"),
    "neutral_tier_2": ("Нейтралки", "Neutrals"),
    "neutral_tier_3": ("Нейтралки", "Neutrals"),
    "neutral_tier_4": ("Нейтралки", "Neutrals"),
    "neutral_tier_5": ("Нейтралки", "Neutrals"),
    "stack": ("Стак", "Stack"),
    "roshan": ("Рошан", "Roshan"),
    "roshan_maybe": ("Рошан?", "Roshan?"),
    "aegis": ("Аегис", "Aegis"),
}


def strip_item(kind: str, at: int, clock: int, lang: str, **extra: Any) -> dict[str, Any]:
    ru, en = STRIP_LABELS[kind]
    return {
        "id": f"{kind}@{at}",
        "kind": kind,
        "label": ru if lang == "ru" else en,
        "at": at,
        "at_label": clock_label(at),
        "in_seconds": at - clock,
        **extra,
    }


def timer_strip(
    clock: int | None,
    role: str | None,
    lang: str,
    objectives: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """The next events for this position (one per kind, soonest first) and the
    Roshan / Aegis timers (`objectives`, roshan_timer.RoshanTimer.strip)."""
    if clock is None or clock < 0:
        return []
    items: list[dict[str, Any]] = []
    for event in timers().get("events") or []:
        until = (event.get("roles") or {}).get(role or "")
        if until is None:
            continue
        upcoming = [at for at in _times(event, int(until)) if clock <= at <= clock + STRIP_AHEAD]
        if upcoming and event["id"] in STRIP_LABELS:
            items.append(strip_item(event["id"], upcoming[0], clock, lang))
    if role == "support":
        minute, second = divmod(clock, 60)
        stacks = [
            m * 60 + STACK_UNTIL_SECOND
            for m in STACK_MINUTES
            if clock <= m * 60 + STACK_UNTIL_SECOND <= clock + STRIP_AHEAD
        ]
        if stacks:
            items.append(strip_item("stack", stacks[0], clock, lang))
    # Neutral item tiers share a label: only the next one.
    seen: set[str] = set()
    unique = []
    for item in sorted(items, key=lambda row: row["in_seconds"]):
        if item["label"] in seen:
            continue
        seen.add(item["label"])
        unique.append(item)
    fixed = [dict(item) for item in objectives or []]
    return (fixed + unique)[:STRIP_SIZE]


@lru_cache(maxsize=1)
def timers() -> dict[str, Any]:
    try:
        return json.loads(TIMERS_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"events": []}


def item_names(items: Any) -> list[str] | None:
    """Item names in the inventory, backpack and stash of a raw GSI items block
    (None without one; the TP and neutral slots are left out)."""
    if not isinstance(items, dict) or not items:
        return None
    names = []
    for slot, item in items.items():
        name = item.get("name") if isinstance(item, dict) else item
        if str(slot).startswith(("slot", "stash")) and isinstance(name, str) and name != "empty":
            names.append(name)
    return names


def _observers(item: Any) -> int:
    """Observer wards in one inventory item: its `charges` (the combined dispenser
    counts its observers there, sentries in `secondary_charges`, so 0 is a real
    zero); a ward without a usable count is one."""
    name = item.get("name") if isinstance(item, dict) else item
    if str(name or "") not in WARD_ITEMS:
        return 0
    charges = item.get("charges") if isinstance(item, dict) else None
    valid = isinstance(charges, int) and not isinstance(charges, bool)
    return charges if valid and 0 <= charges < 100 else 1


def observer_charges(items: Any) -> int | None:
    """Observer wards carried in the inventory; None without an items block."""
    if not isinstance(items, dict) or not items:
        return None
    return sum(_observers(item) for slot, item in items.items() if str(slot).startswith("slot"))


def has_observer_ward(items: Any) -> bool | None:
    """From a raw GSI items block; None without one (stash and neutral slots skipped)."""
    count = observer_charges(items)
    return None if count is None else count > 0


def _times(event: dict[str, Any], until: int) -> list[int]:
    if "times" in event:
        return [int(t) for t in event["times"] if int(t) <= until]
    first, every = int(event.get("first", 0)), int(event.get("every", 0))
    if every <= 0:
        return [first] if first <= until else []
    return list(range(first, until + 1, every))


def clock_label(seconds: int) -> str:
    return f"{seconds // 60}:{seconds % 60:02d}"


def next_timer(clock: int, role: str | None, lang: str) -> dict[str, Any] | None:
    """The event about to happen (or just happened) for this position."""
    data = timers()
    lead = int(data.get("lead_seconds", 20))
    grace = int(data.get("grace_seconds", 5))
    # The soonest event; at the same second a major one (Tormentor) wins.
    candidates = [
        (at, bool(event.get("minor")), index, event)
        for index, event in enumerate(data.get("events") or [])
        if (until := (event.get("roles") or {}).get(role or "")) is not None
        for at in _times(event, int(until))
        if at - lead <= clock <= at + grace
    ]
    if not candidates:
        return None
    at, _minor, _index, event = min(candidates, key=lambda row: row[:3])
    ru = lang == "ru"
    return {
        "kind": "timer",
        "id": f"{event['id']}@{at}",
        "at": at,
        "at_label": clock_label(at),
        "in_seconds": at - clock,
        "title": event["ru" if ru else "en"],
        "hint": event.get("hint_ru" if ru else "hint_en") or "",
        "speak": bool(event.get("speak")),
        "minor": bool(event.get("minor")),
        "patch": data.get("patch"),
    }


class RoleTips:
    """Per-match memory of the tips shown (reset with MatchMemory)."""

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self._shown: dict[str, int] = {}
        # (observer wards carried, the clock since when none was placed).
        self._ward_held: tuple[int, int] | None = None
        # Level 6 counts as reached only after a level below 6 was seen: a
        # backend started mid-game at level 8 must not call it a new spike.
        self._armed = False
        # (power rune in the Bottle, the clock it was first seen there).
        self._bottled: tuple[str, int] | None = None

    def observe_level(self, level: int | None) -> None:
        """Every hint request (also while a timer shows): arms the level-6 tip."""
        if level is not None and level < POWER_SPIKE_LEVEL:
            self._armed = True

    def observe_bottle(self, rune: str | None, clock: int) -> None:
        """Every hint request: since when the power rune in the Bottle is there."""
        if rune not in POWER_RUNES:
            self._bottled = None
        elif self._bottled is None or self._bottled[0] != rune or clock < self._bottled[1]:
            self._bottled = (rune, clock)

    def _bottle_rune(self, clock: int, lang: str) -> dict[str, Any] | None:
        """Once per bottled rune: a power rune kept BOTTLE_RUNE_HELD seconds."""
        if self._bottled is None:
            return None
        rune, since = self._bottled
        if clock - since < BOTTLE_RUNE_HELD:
            return None
        key = f"bottle_rune@{since}"
        start = self._once(key, clock, BOTTLE_RUNE_SHOW)
        if start is None:
            return None
        return _tip("bottle_rune", key, lang, rune=rune, rune_ru=RUNES_RU.get(rune, rune))

    def _every(self, key: str, clock: int, every: int, show: int) -> int | None:
        """Shown for `show` seconds, then again `every` seconds later: the start."""
        shown = self._shown.get(key)
        if shown is None or clock - shown >= every or clock < shown:
            self._shown[key] = shown = clock
        return shown if clock - shown <= show else None

    def missing(
        self, clock: int, lang: str, missing: dict[str, Any] | None
    ) -> dict[str, Any] | None:
        """The «missing» call for one disappearance of an enemy: shown for
        MISSING_SHOW seconds (with the seconds of its first second), at most
        one call per MISSING_GAP; nothing once the enemy is seen again."""
        if not missing or missing.get("kind") not in ("mid", "lane"):
            return None
        key = f"missing:{missing['hero']}@{missing['since']}"
        if key not in self._shown:
            last = self._shown.get("missing:last")
            if isinstance(last, int) and clock - last < MISSING_GAP:
                return None
            self._shown[key] = clock
            self._shown["missing:last"] = clock
            self._shown[f"{key}:seconds"] = int(missing["seconds"])
        start = self._shown[key]
        if not 0 <= clock - start <= MISSING_SHOW:
            return None
        tip = _tip(
            f"missing_{missing['kind']}",
            key,
            lang,
            hero=missing["hero"],
            seconds=self._shown[f"{key}:seconds"],
        )
        tip["speak"] = True
        return tip

    def tip(
        self,
        clock: int,
        role: str | None,
        *,
        alive: bool,
        has_ward: bool | None,
        lang: str,
        tp_missing: bool = False,
        carry_advisor: bool = False,
        last_hits: int | None = None,
        level: int | None = None,
        deaths: int | None = None,
        gold: int | None = None,
        lane: str | None = None,
        items: list[str] | None = None,
        key_item: dict[str, Any] | None = None,
        ward_charges: int | None = None,
        save_item: dict[str, Any] | None = None,
        score_gap: int | None = None,
        roshan_open: bool = False,
        enemies: list[str] | None = None,
        denies: int | None = None,
        hp: int | None = None,
        regen: list[str] | None = None,
    ) -> dict[str, Any] | None:
        held_for = self._observe_wards(ward_charges, clock)
        if not alive or role is None:
            return None
        if tp_missing and not carry_advisor:
            start = self._every("tp", clock, TP_EVERY, TP_SHOW)
            if start is not None:
                return _tip("tp", f"tp@{start}", lang)
        if role in ("mid", "offlane") and level is not None:
            key = f"{role}_six"
            if level >= POWER_SPIKE_LEVEL and clock <= POWER_SPIKE_UNTIL and self._armed:
                # Once per match, from the moment the level is reached.
                start = self._shown.setdefault(key, clock)
                if 0 <= clock - start <= POWER_SPIKE_SHOW:
                    return _tip(key, f"{key}@{start}", lang)
        bottled = self._bottle_rune(clock, lang)
        if bottled is not None:
            return bottled
        if role in CORE_ROLES:
            lane = self._lane(clock, role, lang, items, gold, last_hits, denies, hp, regen)
            if lane is not None:
                return lane
        if role in CORE_ROLES and key_item and items is not None:
            timing = self._key_item(clock, lang, key_item, items)
            if timing is not None:
                return timing
        if role == "mid":
            return self._mid(clock, lang, last_hits, items)
        if role == "offlane":
            return self._offlane(clock, lang, deaths, level)
        if role != "support":
            return None
        if (
            last_hits is not None
            and LAST_HITS_FROM <= clock <= LAST_HITS_UNTIL
            and last_hits / (clock / 60) >= SUPPORT_LH_PER_MIN
        ):
            start = self._every("last_hits", clock, LAST_HITS_EVERY, TP_SHOW)
            if start is not None:
                return _tip("last_hits", f"last_hits@{start}", lang)
        minute, second = divmod(clock, 60)
        if minute in STACK_MINUTES and STACK_FROM_SECOND <= second <= STACK_UNTIL_SECOND:
            at = minute * 60 + STACK_UNTIL_SECOND
            return _tip("stack", f"stack@{minute}", lang, at=at, clock=clock)
        if lane == "safe" and PULL_FROM <= clock <= PULL_UNTIL:
            for window_from, pull_at in PULL_WINDOWS:
                if window_from <= second <= pull_at:
                    start = self._every("pull", clock, PULL_EVERY, PULL_SHOW)
                    if start is not None:
                        at = minute * 60 + pull_at
                        label = clock_label(at)
                        return _tip("pull", f"pull@{at}", lang, at=at, clock=clock, at_label=label)
        invisible = _invisible_enemy(enemies)
        if (
            invisible
            and items is not None
            and clock >= INVIS_FROM
            and not DETECTION_ITEMS & set(items)
        ):
            start = self._every("invis_dust", clock, INVIS_EVERY, INVIS_SHOW)
            if start is not None:
                return _tip("invis_dust", f"invis_dust@{start}", lang, enemy=invisible)
        if has_ward is False and clock >= WARD_FROM_CLOCK:
            start = self._every("wards", clock, WARD_EVERY, WARD_SHOW)
            if start is not None:
                return _tip("wards", f"wards@{start}", lang)
        if held_for is not None and held_for >= WARD_HELD and clock >= WARD_FROM_CLOCK:
            start = self._every("ward_bag", clock, WARD_HELD_EVERY, WARD_SHOW)
            if start is not None:
                return _ward_bag_tip(f"ward_bag@{start}", lang, clock, score_gap, roshan_open)
        if (
            items is not None
            and clock >= SAVE_FROM
            and not SAVE_ITEMS & set(items)
            and gold is not None
            and gold >= SAVE_GOLD
        ):
            start = self._every("save_item", clock, SAVE_EVERY, SAVE_SHOW)
            if start is not None:
                return _save_item_tip(f"save_item@{start}", lang, save_item, gold)
        if gold is not None and gold >= SPEND_GOLD and clock >= SPEND_FROM:
            start = self._every("spend_gold", clock, SPEND_EVERY, SPEND_SHOW)
            if start is not None:
                # Rounded down to hundreds, as the player reads it on screen.
                return _tip("spend_gold", f"spend_gold@{start}", lang, gold=gold // 100 * 100)
        return None

    def _lane(
        self,
        clock: int,
        role: str,
        lang: str,
        items: list[str] | None,
        gold: int | None,
        last_hits: int | None,
        denies: int | None,
        hp: int | None,
        regen: list[str] | None,
    ) -> dict[str, Any] | None:
        """A core's lane tips in the first ten minutes: regen on the way, HP half
        gone with nothing to heal, a Magic Stick, denies at 4:00."""
        owned = set(items) if items is not None else None
        if owned is not None and clock <= LANE_REGEN_UNTIL and not LANE_REGEN_ITEMS & owned:
            start = self._once("lane_regen", clock, LANE_REGEN_SHOW)
            if start is not None:
                return _tip("lane_regen", f"lane_regen@{start}", lang)
        if (
            LANE_HP_FROM <= clock <= LANE_HP_UNTIL
            and hp is not None
            and hp <= LANE_HP_LIMIT
            and regen == []
            and gold is not None
            and gold >= LANE_HP_GOLD
        ):
            start = self._every("lane_hp", clock, LANE_HP_EVERY, LANE_HP_SHOW)
            if start is not None:
                shown = self._shown.setdefault(f"lane_hp_value@{start}", hp)
                return _tip("lane_hp", f"lane_hp@{start}", lang, hp=shown)
        if (
            owned is not None
            and STICK_FROM <= clock <= STICK_UNTIL
            and not STICK_ITEMS & owned
            and gold is not None
            and gold >= STICK_GOLD
        ):
            start = self._once("lane_stick", clock, STICK_SHOW)
            if start is not None:
                return _tip("lane_stick", f"lane_stick@{start}", lang)
        if (
            role in ("carry", "mid")
            and DENY_AT <= clock <= DENY_AT + DENY_SHOW
            and denies is not None
            and denies < DENY_MIN
            and (last_hits or 0) >= DENY_MIN_LAST_HITS
        ):
            shown = self._shown.setdefault("lane_denies@value", denies)
            return _tip("lane_denies", f"lane_denies@{DENY_AT}", lang, denies=shown)
        return None

    def _observe_wards(self, charges: int | None, clock: int) -> int | None:
        """Seconds the carried observer wards went without one being placed; None
        without a ward. Buying more keeps the time, placing one restarts it."""
        if not charges:
            self._ward_held = None
            return None
        held = self._ward_held
        if held is None or charges < held[0] or clock < held[1]:
            self._ward_held = (charges, clock)
        elif charges > held[0]:
            self._ward_held = (charges, held[1])
        return clock - self._ward_held[1]

    def _once(self, key: str, clock: int, show: int) -> int | None:
        """Once per match: the start while within `show` seconds of it."""
        start = self._shown.setdefault(key, clock)
        return start if 0 <= clock - start <= show else None

    def _key_item(
        self, clock: int, lang: str, item: dict[str, Any], items: list[str]
    ) -> dict[str, Any] | None:
        """Once per match: the key item finished 2+ minutes before its typical
        time, or not finished 2 minutes after it."""
        typical = int(item["typical_t"])
        params = {"item": item["name"], "time": clock_label(typical)}
        for key in ("item_early", "item_late"):
            if key in self._shown:
                start = self._once(key, clock, KEY_ITEM_SHOW)
                return _tip(key, f"{key}@{start}", lang, **params) if start is not None else None
        has_it = f"item_{item['key']}" in items
        if has_it and clock <= typical - KEY_ITEM_EARLY:
            key = "item_early"
        elif not has_it and clock >= typical + KEY_ITEM_LATE:
            key = "item_late"
        else:
            if has_it:
                self._shown["item_on_time"] = clock  # bought: never "late" later on
            return None
        if "item_on_time" in self._shown:
            return None
        start = self._once(key, clock, KEY_ITEM_SHOW)
        return _tip(key, f"{key}@{start}", lang, **params) if start is not None else None

    def _mid(
        self, clock: int, lang: str, last_hits: int | None, items: list[str] | None
    ) -> dict[str, Any] | None:
        if last_hits is not None:
            for at, target in MID_LAST_HIT_CHECKS.items():
                if at <= clock <= at + MID_LAST_HIT_SHOW and last_hits < target:
                    key = f"mid_last_hits@{at}"
                    # The count of the first second shown stays on the card.
                    shown = self._shown.setdefault(key, last_hits)
                    return _tip(
                        "mid_last_hits",
                        key,
                        lang,
                        last_hits=shown,
                        last_hits_word=_ru_plural(shown, "добивание", "добивания", "добиваний"),
                        time=clock_label(at),
                        target=target,
                    )
        if items is not None and BOTTLE_FROM <= clock <= BOTTLE_UNTIL:
            if not BOTTLE_ITEMS & set(items):
                start = self._once("mid_bottle", clock, BOTTLE_SHOW)
                if start is not None:
                    return _tip("mid_bottle", f"mid_bottle@{start}", lang)
        return None

    def _offlane(
        self, clock: int, lang: str, deaths: int | None, level: int | None
    ) -> dict[str, Any] | None:
        key = "offlane_hard_lane"
        if key not in self._shown:
            if not HARD_LANE_FROM <= clock <= HARD_LANE_UNTIL:
                return None
            lost = (deaths is not None and deaths >= HARD_LANE_DEATHS) or (
                clock >= HARD_LANE_LEVEL_AT and level is not None and level < HARD_LANE_LEVEL
            )
            if not lost:
                return None
        start = self._once(key, clock, HARD_LANE_SHOW)
        return _tip(key, f"{key}@{start}", lang) if start is not None else None


def _ru_plural(count: int, one: str, few: str, many: str) -> str:
    if count % 10 == 1 and count % 100 != 11:
        return one
    if 2 <= count % 10 <= 4 and not 12 <= count % 100 <= 14:
        return few
    return many


def _tip(
    key: str,
    hint_id: str,
    lang: str,
    at: int | None = None,
    clock: int | None = None,
    **params: Any,
) -> dict[str, Any]:
    title, hint = TIPS[key]["ru" if lang == "ru" else "en"]
    if params:
        title, hint = title.format(**params), hint.format(**params)
    return {
        "kind": "tip",
        "id": hint_id,
        "at": at,
        "at_label": clock_label(at) if at is not None else None,
        "in_seconds": at - clock if at is not None and clock is not None else None,
        "title": title,
        "hint": hint,
        "speak": False,
    }


def _invisible_enemy(enemies: list[str] | None) -> str | None:
    """The first enemy hero seen that goes invisible (draft_analysis.COUNTERS)."""
    from app.draft_analysis import COUNTERS  # a heavy import, only when enemies are known

    if not enemies:
        return None
    heroes = COUNTERS["invisibility"][0]
    return next((e for e in enemies if isinstance(e, str) and e in heroes), None)


def _ward_bag_tip(
    hint_id: str, lang: str, clock: int, score_gap: int | None, roshan_open: bool
) -> dict[str, Any]:
    """Where the ward in the bag should go: Roshan's pit while he can be up, the
    lane's river in the laning stage, the own or the enemy jungle by the kill score."""
    if roshan_open:
        return _tip("ward_bag_roshan", hint_id, lang)
    if clock < WARD_LANING_END:
        return _tip("ward_bag_lane", hint_id, lang)
    if score_gap is not None and clock >= WARD_SCORE_FROM:
        if score_gap <= -WARD_SCORE_GAP:
            return _tip("ward_bag_behind", hint_id, lang, gap=-score_gap)
        if score_gap >= WARD_SCORE_GAP:
            return _tip("ward_bag_ahead", hint_id, lang, gap=score_gap)
    return _tip("ward_bag", hint_id, lang)


def score_gap(extra: dict[str, Any]) -> int | None:
    """The player's team kills minus the enemy's, from live GSI; None unknown."""
    team = str(extra.get("team_name") or "").strip().lower()
    radiant, dire = extra.get("radiant_score"), extra.get("dire_score")
    if team not in ("radiant", "dire") or not isinstance(radiant, int):
        return None
    if not isinstance(dire, int) or isinstance(radiant, bool) or isinstance(dire, bool):
        return None
    return radiant - dire if team == "radiant" else dire - radiant


def _save_item_tip(
    hint_id: str, lang: str, item: dict[str, Any] | None, gold: int
) -> dict[str, Any]:
    """The save item against the enemy lineup, the hero's usual one with its
    price, else Glimmer Cape or Force Staff."""
    why = (item or {}).get("why")
    if why in ("magic", "physical") and item and item.get("name"):
        left = item.get("gold_left")
        if isinstance(left, int) and left <= gold:
            return _tip("save_item_now_lineup", hint_id, lang, item=item["name"])
        return _tip(
            f"save_item_{why}",
            hint_id,
            lang,
            item=item["name"],
            count=item.get("count"),
            enemy=item.get("enemy"),
        )
    if not item or not item.get("name") or not isinstance(item.get("gold_left"), int):
        return _tip("save_item", hint_id, lang)
    left = item["gold_left"]
    if left <= gold:
        return _tip("save_item_now", hint_id, lang, item=item["name"])
    # The gold carried counts too: only the rest is still to farm.
    return _tip("save_item_hero", hint_id, lang, item=item["name"], left=left - gold)


def map_hint(
    clock: int | None,
    role: str | None,
    tips: RoleTips,
    *,
    alive: bool,
    has_ward: bool | None,
    lang: str,
    tp_missing: bool = False,
    carry_advisor: bool = False,
    last_hits: int | None = None,
    level: int | None = None,
    deaths: int | None = None,
    gold: int | None = None,
    lane: str | None = None,
    items: list[str] | None = None,
    key_item: dict[str, Any] | None = None,
    objective: dict[str, Any] | None = None,
    ward_charges: int | None = None,
    skill: dict[str, Any] | None = None,
    save_item: dict[str, Any] | None = None,
    score_gap: int | None = None,
    roshan_open: bool = False,
    enemies: list[str] | None = None,
    bottle_rune: str | None = None,
    denies: int | None = None,
    hp: int | None = None,
    regen: list[str] | None = None,
    missing: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """A timer, but a role tip over a minor one (runes, lotus); None before the
    horn or without a role. `objective`: a Roshan / Aegis timer (roshan_timer.py),
    which wins over a scheduled timer that is not sooner. `skill`: a skill-point
    tip (skill_tips.py), which wins over any scheduled timer: it takes a second
    and the timers stay on the strip under the card."""
    if clock is None or clock < 0 or role is None:
        return None
    tips.observe_level(level)
    tips.observe_bottle(bottle_rune, clock)
    if skill is not None and objective is None:
        return skill
    # A missing enemy (enemy_lanes.py) is a danger now: over any scheduled timer.
    called = tips.missing(clock, lang, missing if alive else None)
    if called is not None:
        return called
    timer = next_timer(clock, role, lang)
    if objective is not None and (
        timer is None or timer["minor"] or objective["in_seconds"] <= timer["in_seconds"]
    ):
        timer = objective
    if (
        timer is not None
        and role == "mid"
        and timer["id"].startswith("power_rune@")
        and level is not None
    ):
        if level >= POWER_SPIKE_LEVEL:
            # With level 6 a power rune is the mid's rotation.
            timer["hint"] = TIPS["mid_rune"]["ru" if lang == "ru" else "en"][1]
        elif items is not None and BOTTLE_ITEMS & set(items):
            # Before it (a known level only), a Bottle keeps the rune for a kill.
            timer["hint"] = TIPS["mid_rune_bottle"]["ru" if lang == "ru" else "en"][1]
    if timer is not None and not timer["minor"]:
        return timer
    tip = tips.tip(
        clock,
        role,
        alive=alive,
        has_ward=has_ward,
        lang=lang,
        tp_missing=tp_missing,
        carry_advisor=carry_advisor,
        last_hits=last_hits,
        level=level,
        deaths=deaths,
        gold=gold,
        lane=lane,
        items=items,
        key_item=key_item,
        ward_charges=ward_charges,
        save_item=save_item,
        score_gap=score_gap,
        roshan_open=roshan_open,
        enemies=enemies,
        denies=denies,
        hp=hp,
        regen=regen,
    )
    return tip or timer
