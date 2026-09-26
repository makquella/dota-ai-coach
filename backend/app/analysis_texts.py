"""
analysis_texts.py - Russian and English texts for match and career reviews.

post_match_analysis.py and career_analysis.py produce language-neutral
findings ({"id", "params"}); this module turns them into a title, an
explanation with the numbers, and a concrete drill. Keep both languages in
sync: tests/test_post_match_analysis.py checks every finding id has both.
"""

from __future__ import annotations

from typing import Any


def clock(seconds: Any) -> str:
    try:
        value = int(seconds)
    except (TypeError, ValueError):
        return "—"
    sign = "-" if value < 0 else ""
    value = abs(value)
    return f"{sign}{value // 60}:{value % 60:02d}"


def _times(values: Any) -> str:
    return ", ".join(clock(v) for v in values or [])


FINDINGS: dict[str, dict[str, dict[str, str]]] = {
    "lh10_great": {
        "ru": {
            "title": "Сильная линия",
            "text": "{lh10} добиваний к 10-й минуте — выше цели {target}. Вы вышли из лайнинга с хорошим запасом золота.",
        },
        "en": {
            "title": "Strong lane",
            "text": "{lh10} last hits by minute 10, above the {target} target. You left the lane with a solid gold lead.",
        },
    },
    "lh10_low": {
        "ru": {
            "title": "Мало добиваний на линии",
            "text": "{lh10} добиваний к 10-й минуте при цели {target} — это примерно {gold_lost} золота, которых не хватило к первому предмету.",
            "drill": "5–10 минут в «Демо героя» перед игрой: только добивания без соперника, цель — 45+ к 10:00. На линии бейте крипа, когда его HP ниже урона одной атаки.",
        },
        "en": {
            "title": "Few last hits in lane",
            "text": "{lh10} last hits by minute 10 against a {target} target — about {gold_lost} gold missing from your first item.",
            "drill": "5–10 minutes of Hero Demo before playing: last hits only, no enemy, aim for 45+ by 10:00. In lane, attack when the creep's HP is below one hit.",
        },
    },
    "lane_eff_high": {
        "ru": {
            "title": "Эффективная линия",
            "text": "Эффективность линии {efficiency}% — вы забрали почти всё золото, что было доступно.",
        },
        "en": {
            "title": "Efficient lane",
            "text": "Lane efficiency {efficiency}% — you took nearly all the gold available.",
        },
    },
    "lane_eff_low": {
        "ru": {
            "title": "Линия отдана",
            "text": "Эффективность линии {efficiency}%: больше половины доступного золота ушло мимо.",
            "drill": "Если на линии не стоите, уходите в лес или на соседнюю волну, а не стойте под вышкой без крипов.",
        },
        "en": {
            "title": "Lane given away",
            "text": "Lane efficiency {efficiency}%: more than half the available gold slipped away.",
            "drill": "If you cannot hold the lane, farm the jungle or the next wave instead of waiting under the tower.",
        },
    },
    "denies_good": {
        "ru": {
            "title": "Хорошие денаи",
            "text": "{denies} денаев к 10-й минуте — сопернику доставалось меньше опыта и золота.",
        },
        "en": {
            "title": "Good denies",
            "text": "{denies} denies by minute 10 — the enemy got less gold and experience.",
        },
    },
    "lane_deaths": {
        "ru": {
            "title": "Смерти на линии",
            "text": "{count} {count_deaths} до 10-й минуты ({times}). Каждая — это ~300 золота и минута без опыта в самый важный отрезок игры.",
            "drill": "Держитесь за своими крипами, когда у врага готовы способности и рядом нет вашего саппорта; при пропаже врага с карты отходите к вышке.",
        },
        "en": {
            "title": "Lane deaths",
            "text": "{count} deaths before minute 10 ({times}). Each costs ~300 gold and a minute of experience at the most important stage.",
            "drill": "Stay behind your creeps while enemy spells are up and your support is away; step back to the tower when an enemy goes missing.",
        },
    },
    "gpm_high": {
        "ru": {
            "title": "Отличный фарм",
            "text": "{gpm} золота в минуту — лучше, чем у {pct}% игроков на {hero}.",
        },
        "en": {
            "title": "Great farm",
            "text": "{gpm} gold per minute — better than {pct}% of {hero} players.",
        },
    },
    "gpm_high_static": {
        "ru": {
            "title": "Отличный фарм",
            "text": "{gpm} золота в минуту — выше ориентира {target} для этой роли.",
        },
        "en": {
            "title": "Great farm",
            "text": "{gpm} gold per minute — above the {target} benchmark for this role.",
        },
    },
    "gpm_low": {
        "ru": {
            "title": "Фарм ниже нормы",
            "text": "{gpm} золота в минуту — хуже, чем у {pct_rest}% игроков на {hero}.",
            "drill": "Между драками всегда должен быть план фарма: волна → лагерь → следующая волна. Не стойте без дела и не ходите за командой, если драки нет.",
        },
        "en": {
            "title": "Farm below par",
            "text": "{gpm} gold per minute — lower than {pct_rest}% of {hero} players.",
            "drill": "Always have a farm route between fights: wave → camp → next wave. Don't idle or follow the team when there is no fight.",
        },
    },
    "gpm_low_static": {
        "ru": {
            "title": "Фарм ниже нормы",
            "text": "{gpm} золота в минуту при ориентире {target} для этой роли.",
            "drill": "Между драками всегда должен быть план фарма: волна → лагерь → следующая волна. Не стойте без дела и не ходите за командой, если драки нет.",
        },
        "en": {
            "title": "Farm below par",
            "text": "{gpm} gold per minute against a {target} benchmark for this role.",
            "drill": "Always have a farm route between fights: wave → camp → next wave. Don't idle or follow the team when there is no fight.",
        },
    },
    "farm_stall": {
        "ru": {
            "title": "Провал в фарме",
            "text": "С {from_} по {to}-ю минуту всего {last_hits} {last_hits_word}. В это время герой не фармил и не приносил пользы на карте.",
            "drill": "Если не знаете, что делать, — фармите ближайший безопасный лагерь. Раз в минуту смотрите на миникарту: где свободные волны?",
        },
        "en": {
            "title": "Farm stall",
            "text": "Only {last_hits} last hits from minute {from_} to {to}. The hero neither farmed nor made plays in that window.",
            "drill": "When unsure what to do, farm the nearest safe camp. Check the minimap every minute for free waves.",
        },
    },
    "deaths_low": {
        "ru": {
            "title": "Бережёте героя",
            "text": "Всего {deaths} {deaths_word} за {minutes} {minutes_word} — команда почти всегда играла с вами.",
        },
        "en": {
            "title": "Kept your hero alive",
            "text": "Only {deaths} deaths in {minutes} minutes — your team almost always had you.",
        },
    },
    "deaths_high": {
        "ru": {
            "title": "Слишком много смертей",
            "text": "{deaths} {deaths_word} за {minutes} {minutes_word}{dead_suffix}.",
            "drill": "Перед каждым выходом в чужую часть карты задайте себе вопрос: сколько врагов не видно на миникарте? Если трое и больше — фармите ближе к своей стороне.",
        },
        "en": {
            "title": "Too many deaths",
            "text": "{deaths} deaths in {minutes} minutes{dead_suffix}.",
            "drill": "Before going into enemy territory ask: how many enemies are missing from the minimap? Three or more — farm closer to your side.",
        },
    },
    "death_with_gold": {
        "ru": {
            "title": "Смерть с золотом на руках",
            "text": "{count_text} с большим запасом золота; худшая — на {t_text} с {gold} золота. При смерти теряется ненадёжное золото, а предмет ещё не куплен.",
            "drill": "Накопили на предмет — купите его (курьер или лавка) до того, как идти в опасную зону.",
        },
        "en": {
            "title": "Died holding gold",
            "text": "{count_text} with a lot of gold on hand; the worst at {t_text} with {gold} gold. Dying costs unreliable gold and delays the item.",
            "drill": "Once you can afford an item, buy it (courier or shop) before walking into danger.",
        },
    },
    "death_streak": {
        "ru": {
            "title": "Серия смертей",
            "text": "{count} {count_deaths} за 5 минут ({from_text}–{to_text}). После смерти легко повторить ту же ошибку.",
            "drill": "После смерти посмотрите на миникарту и таймеры и выберите безопасную цель — не возвращайтесь сразу туда, где вас поймали.",
        },
        "en": {
            "title": "Death streak",
            "text": "{count} deaths within 5 minutes ({from_text}–{to_text}). It is easy to repeat the same mistake right after dying.",
            "drill": "After dying, look at the minimap and timers and pick a safe target — don't walk straight back to where you were caught.",
        },
    },
    "killed_by_one": {
        "ru": {
            "title": "Главная угроза: {hero}",
            "text": "{hero} убил вас {count} раз из {deaths}.",
            "drill": "Следите, где {hero}, прежде чем выходить вперёд, и заранее продумайте защиту от него: предмет, позицию или способность для побега.",
        },
        "en": {
            "title": "Main threat: {hero}",
            "text": "{hero} killed you {count} times out of {deaths}.",
            "drill": "Know where {hero} is before stepping forward and plan a counter: an item, positioning or an escape spell.",
        },
    },
    "kp_high": {
        "ru": {
            "title": "В каждой драке",
            "text": "Участие в убийствах {kp}% — вы были там, где решалась игра.",
        },
        "en": {
            "title": "In every fight",
            "text": "{kp}% kill participation — you were where the game was decided.",
        },
    },
    "kp_low": {
        "ru": {
            "title": "Команда дралась без вас",
            "text": "Участие в убийствах {kp}% из {team_kills} убийств команды.",
            "drill": "После 20-й минуты перед важными целями (Рошан, вышки, смок) заканчивайте фарм и подходите к команде заранее.",
        },
        "en": {
            "title": "The team fought without you",
            "text": "{kp}% kill participation out of {team_kills} team kills.",
            "drill": "After minute 20, before key objectives (Roshan, towers, smokes) stop farming and join the team early.",
        },
    },
    "damage_high": {
        "ru": {
            "title": "Много урона по героям",
            "text": "Урон по героям лучше, чем у {pct}% игроков на этом герое.",
        },
        "en": {
            "title": "High hero damage",
            "text": "Hero damage better than {pct}% of players on this hero.",
        },
    },
    "damage_low": {
        "ru": {
            "title": "Мало урона в драках",
            "text": "Урон по героям хуже, чем у {pct_rest}% игроков на этом герое.",
            "drill": "В драке бейте цель, до которой безопасно дотянуться, а не ждите конца драки в стороне.",
        },
        "en": {
            "title": "Little damage in fights",
            "text": "Hero damage lower than {pct_rest}% of players on this hero.",
            "drill": "In fights, hit the target you can safely reach instead of waiting out the fight.",
        },
    },
    "towers_high": {
        "ru": {
            "title": "Давили строения",
            "text": "Урон по строениям лучше, чем у {pct}% игроков — вы превращали преимущество в карту.",
        },
        "en": {
            "title": "Pushed buildings",
            "text": "Building damage better than {pct}% of players — you turned advantage into map control.",
        },
    },
    "core_item_fast": {
        "ru": {
            "title": "Быстрый первый предмет",
            "text": "{item} к {t_text} — хороший тайминг, чтобы начинать влиять на игру.",
        },
        "en": {
            "title": "Fast first item",
            "text": "{item} by {t_text} — a good timing to start making an impact.",
        },
    },
    "core_item_slow": {
        "ru": {
            "title": "Поздний первый предмет",
            "text": "Первый крупный предмет ({item}) только к {t_text}. К этому времени соперники обычно уже с 2 предметами.",
            "drill": "Соберите сборку заранее и не тратьте золото на лишнее до первого ключевого предмета; фармите между драками.",
        },
        "en": {
            "title": "Late first item",
            "text": "First big item ({item}) only at {t_text}. By then opponents usually have two.",
            "drill": "Plan the build in advance, skip extras until the first key item, and farm between fights.",
        },
    },
    "no_core_item": {
        "ru": {
            "title": "Нет ни одного крупного предмета",
            "text": "За {minutes} {minutes_word} не собран ни один крупный предмет.",
            "drill": "Поставьте цель: первый ключевой предмет к 15–17 минуте. Проверяйте прогресс по золоту на 10-й минуте.",
        },
        "en": {
            "title": "No big item",
            "text": "No big item completed in {minutes} minutes.",
            "drill": "Set a goal: the first key item by minute 15–17. Check your gold progress at minute 10.",
        },
    },
    "wards_high": {
        "ru": {
            "title": "Хороший обзор",
            "text": "{obs} обсервер-вардов и {sen} сентри — команда видела карту.",
        },
        "en": {
            "title": "Good vision",
            "text": "{obs} observer and {sen} sentry wards — the team could see the map.",
        },
    },
    "wards_low": {
        "ru": {
            "title": "Мало вардов",
            "text": "{obs} обсервер-вардов за {minutes} {minutes_word}.",
            "drill": "Ставьте вард каждый раз, когда он есть в лавке, и перед каждым походом к Рошану или вражеской вышке.",
        },
        "en": {
            "title": "Few wards",
            "text": "{obs} observer wards in {minutes} minutes.",
            "drill": "Place a ward every time the shop has one, and before every Roshan or tower push.",
        },
    },
    "stacks_good": {
        "ru": {
            "title": "Стаки для команды",
            "text": "{stacks} стаков лагерей — дополнительное золото для ваших кор-героев.",
        },
        "en": {
            "title": "Stacks for the team",
            "text": "{stacks} camps stacked — extra gold for your cores.",
        },
    },
}

FINDINGS.update(
    {
        "build_timing_late": {
            "ru": {
                "title": "Поздний {item}",
                "text": "{item} к {t_text}: с таким таймингом {hero} выигрывает {winrate}% игр. Обычно этот предмет покупают к {typical_t_text}, и тогда побед {typical_winrate}% (публичные матчи OpenDota).",
                "drill": "Следующий матч на {hero}: цель — {item} к {typical_t_text}. Не отвлекайтесь на лишние предметы до него и фармите между драками.",
            },
            "en": {
                "title": "Late {item}",
                "text": "{item} at {t_text}: with that timing {hero} wins {winrate}% of games. It is usually bought by {typical_t_text}, which wins {typical_winrate}% (OpenDota public matches).",
                "drill": "Next {hero} game: aim for {item} by {typical_t_text}. Skip extras before it and farm between fights.",
            },
        },
        "build_timing_good": {
            "ru": {
                "title": "Хороший тайминг: {item}",
                "text": "{item} к {t_text} — с таким таймингом {hero} выигрывает {winrate}% игр (в среднем {average}%).",
            },
            "en": {
                "title": "Good timing: {item}",
                "text": "{item} at {t_text} — with that timing {hero} wins {winrate}% of games (average {average}%).",
            },
        },
        "build_off_meta": {
            "ru": {
                "title": "Нестандартная сборка",
                "text": "Ни одного из самых частых предметов на {hero} ({popular}). Ваши предметы: {mine}.",
                "drill": "Попробуйте стандартную сборку на {hero}: {popular}. Отступайте от неё, только когда понимаете, против чего собираете.",
            },
            "en": {
                "title": "Unusual build",
                "text": "None of the most common {hero} items ({popular}). Your items: {mine}.",
                "drill": "Try the standard {hero} build: {popular}. Deviate only when you know what you are building against.",
            },
        },
        "build_on_meta": {
            "ru": {
                "title": "Проверенная сборка",
                "text": "Собрали ключевые предметы {hero}: {items}.",
            },
            "en": {"title": "Proven build", "text": "You built the key {hero} items: {items}."},
        },
        "peer_gpm_behind": {
            "ru": {
                "title": "Фарм ниже, чем у соперника",
                "text": "{gpm} золота в минуту против {peer_gpm} у {role_label} в этом матче ({heroes}). Игра подбирает соперников вашего уровня, значит такой фарм вам по силам.",
                "drill": "Сравните маршруты: пока нет драки, у кора всегда должна быть волна или лагерь. Смотрите, где фармит {heroes}, и не отдавайте ему свободные волны.",
            },
            "en": {
                "title": "Farming less than your opponent",
                "text": "{gpm} gold per minute vs {peer_gpm} for the {role_label} of this match ({heroes}). Matchmaking pairs you with players of your level, so that farm is within reach.",
                "drill": "Compare routes: without a fight a core always has a wave or a camp. Watch where {heroes} farms and don't leave free waves to them.",
            },
        },
        "peer_gpm_ahead": {
            "ru": {
                "title": "Перефармили соперника",
                "text": "{gpm} золота в минуту против {peer_gpm} у {role_label} в этом матче ({heroes}).",
            },
            "en": {
                "title": "Outfarmed your opponent",
                "text": "{gpm} gold per minute vs {peer_gpm} for the {role_label} of this match ({heroes}).",
            },
        },
        "peer_lh10_behind": {
            "ru": {
                "title": "Проиграли линию по добиваниям",
                "text": "{lh10} добиваний к 10:00 против {peer_lh10} у {role_label} в этом матче ({heroes}).",
                "drill": "На линии следите за HP крипов и бейте, когда хватит одного удара; держите соперника под давлением, когда он добивает.",
            },
            "en": {
                "title": "Lost the last-hit race",
                "text": "{lh10} last hits by 10:00 vs {peer_lh10} for the {role_label} of this match ({heroes}).",
                "drill": "Watch creep HP and hit when one attack is enough; pressure your opponent when they go for last hits.",
            },
        },
        "peer_deaths_more": {
            "ru": {
                "title": "Умирали чаще соперника",
                "text": "{deaths} {deaths_word} против {peer_deaths} у {role_label} в этом матче ({heroes}).",
                "drill": "Перед каждым рискованным выходом проверьте миникарту: сколько врагов не видно? Если трое и больше — фармите безопаснее.",
            },
            "en": {
                "title": "Died more than your opponent",
                "text": "{deaths} deaths vs {peer_deaths} for the {role_label} of this match ({heroes}).",
                "drill": "Before every risky move check the minimap: how many enemies are missing? Three or more — farm safer.",
            },
        },
    }
)

PEER_ROLES = {
    "carry": {"ru": "керри", "en": "carry"},
    "mid": {"ru": "мидера", "en": "mid"},
    "offlane": {"ru": "хардлейнера", "en": "offlaner"},
    "support": {"ru": "саппорта", "en": "support"},
}

RANK_MEDALS = {
    1: {"ru": "Рекрут", "en": "Herald"},
    2: {"ru": "Страж", "en": "Guardian"},
    3: {"ru": "Рыцарь", "en": "Crusader"},
    4: {"ru": "Герой", "en": "Archon"},
    5: {"ru": "Легенда", "en": "Legend"},
    6: {"ru": "Властелин", "en": "Ancient"},
    7: {"ru": "Божество", "en": "Divine"},
    8: {"ru": "Титан", "en": "Immortal"},
}


def rank_label(rank_tier: Any, lang: str) -> str | None:
    """rank_tier 54 -> "Легенда 4" / "Legend 4"; 80 -> "Титан"."""
    try:
        tier = int(rank_tier)
    except (TypeError, ValueError):
        return None
    medal = RANK_MEDALS.get(tier // 10)
    if not medal:
        return None
    stars = tier % 10
    name = medal["ru" if lang == "ru" else "en"]
    return f"{name} {stars}" if 1 <= stars <= 5 and tier // 10 < 8 else name


SECTIONS = {
    "laning": {"ru": "Линия", "en": "Laning"},
    "farm": {"ru": "Фарм", "en": "Farm"},
    "survival": {"ru": "Выживание", "en": "Survival"},
    "fights": {"ru": "Драки", "en": "Fights"},
    "items": {"ru": "Предметы", "en": "Items"},
    "vision": {"ru": "Обзор", "en": "Vision"},
}

ROLES = {
    "core": {"ru": "кор", "en": "core"},
    "offlane": {"ru": "хардлейн", "en": "offlane"},
    "support": {"ru": "саппорт", "en": "support"},
}


def _plural_ru(n: int, one: str, few: str, many: str) -> str:
    n = abs(int(n))
    if n % 10 == 1 and n % 100 != 11:
        return one
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return few
    return many


def _prepared_params(finding: dict[str, Any], lang: str) -> dict[str, Any]:
    params = dict(finding.get("params") or {})
    params["from_"] = params.get("from")
    if "times" in params:
        params["times"] = _times(params["times"])
    if params.get("role") in PEER_ROLES:
        params["role_label"] = PEER_ROLES[params["role"]]["ru" if lang == "ru" else "en"]
    for key in ("t", "from", "to", "typical_t"):
        if key in params:
            params[f"{key}_text"] = clock(params[key])
    if "pct" in params and params["pct"] is not None:
        params["pct_rest"] = 100 - int(params["pct"])
    if finding["id"] == "deaths_high":
        dead = params.get("time_dead")
        pct = params.get("dead_pct")
        if dead and pct is not None:
            params["dead_suffix"] = (
                f", {clock(dead)} в таверне ({pct}% матча)"
                if lang == "ru"
                else f", {clock(dead)} spent dead ({pct}% of the match)"
            )
        else:
            params["dead_suffix"] = ""
    if finding["id"] == "death_with_gold":
        count = int(params.get("count") or 1)
        params["count_text"] = (
            f"{count} {_plural_ru(count, 'смерть', 'смерти', 'смертей')}"
            if lang == "ru"
            else f"{count} death{'s' if count != 1 else ''}"
        )
    if lang == "ru":
        if params.get("count") is not None:
            params["count_deaths"] = _plural_ru(params["count"], "смерть", "смерти", "смертей")
        if params.get("deaths") is not None:
            params["deaths_word"] = _plural_ru(params["deaths"], "смерть", "смерти", "смертей")
        if params.get("last_hits") is not None:
            params["last_hits_word"] = _plural_ru(
                params["last_hits"], "добивание", "добивания", "добиваний"
            )
        if params.get("minutes") is not None:
            params["minutes_word"] = _plural_ru(params["minutes"], "минуту", "минуты", "минут")
    return params


class _SafeDict(dict):
    def __missing__(self, key: str) -> str:
        return "—"


def render_finding(finding: dict[str, Any], lang: str) -> dict[str, Any]:
    lang = "ru" if lang == "ru" else "en"
    catalog = FINDINGS.get(finding["id"], {}).get(lang) or FINDINGS.get(finding["id"], {}).get("en")
    rendered = dict(finding)
    if not catalog:
        rendered.update({"title": finding["id"], "text": "", "drill": None})
        return rendered
    params = _SafeDict(_prepared_params(finding, lang))
    rendered["title"] = catalog["title"].format_map(params)
    rendered["text"] = catalog["text"].format_map(params)
    rendered["drill"] = catalog["drill"].format_map(params) if catalog.get("drill") else None
    rendered["section_label"] = SECTIONS.get(finding.get("section", ""), {}).get(lang)
    return rendered


def render_analysis(analysis: dict[str, Any], lang: str) -> dict[str, Any]:
    """Copy of a stored analysis with titles/texts in `lang` (ru or en)."""
    lang = "ru" if lang == "ru" else "en"
    rendered = dict(analysis)
    rendered["lang"] = lang
    rendered["strengths"] = [render_finding(f, lang) for f in analysis.get("strengths") or []]
    rendered["improvements"] = [render_finding(f, lang) for f in analysis.get("improvements") or []]
    rendered["role_label"] = ROLES.get(analysis.get("role", ""), {}).get(lang)
    peers = analysis.get("peers")
    if peers:
        rendered["peers"] = {
            **peers,
            "role_label": PEER_ROLES.get(peers.get("role", ""), {}).get(lang),
            "lobby_rank_label": rank_label(peers.get("lobby_rank_tier"), lang),
        }
    rendered["sections"] = {
        name: {**section, "label": SECTIONS.get(name, {}).get(lang, name)}
        for name, section in (analysis.get("sections") or {}).items()
    }
    return rendered
