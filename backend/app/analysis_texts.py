"""
analysis_texts.py - Russian and English texts for match and career reviews.

post_match_analysis.py and career_analysis.py produce language-neutral
findings ({"id", "params"}); this module turns them into a title, an
explanation with the numbers, and a concrete drill. Keep both languages in
sync: tests/test_post_match_analysis.py checks every finding id has both.
"""

from __future__ import annotations

from typing import Any

from app.advice_i18n import translate_ru
from app.advice_why import why
from app.last_moments import SAVERS, saver_label


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
            "text": "{lh10} добиваний к 10-й минуте при цели {target}. Линию вы закончили с хорошим запасом золота.",
        },
        "en": {
            "title": "Strong lane",
            "text": "{lh10} last hits by minute 10 with a {target} target. You left the lane with a solid gold lead.",
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
            "text": "{gpm} золота в минуту при ориентире {target} для этой роли.",
        },
        "en": {
            "title": "Great farm",
            "text": "{gpm} gold per minute with a {target} benchmark for this role.",
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
    "died_after_warning": {
        "ru": {
            "title": "Смерть после предупреждения",
            "text": "{count} {count_times} вы погибли в течение {window} с после срочной подсказки (первый раз — {t_text}). Тренер предупредил вовремя, но отойти не успели.",
            "drill": "Срочная подсказка — сигнал сразу развернуться к своим: сначала шаг назад, потом думать. Потренируйте это в следующей игре.",
        },
        "en": {
            "title": "Died after a warning",
            "text": "{count} times you died within {window} s of urgent advice (first at {t_text}). The warning came in time, but the retreat did not.",
            "drill": "Treat urgent advice as a signal to turn back at once: step away first, think second. Practise it next game.",
        },
    },
    "died_with_saver_ready": {
        "ru": {
            "title": "Спасающий предмет не нажат",
            "text": "{count} {count_times} вы погибли, когда {item_label} был готов, а у героя было время его нажать ({times}).",
            "drill": "Держите {item_label} на удобной клавише и решайте заранее: ниже половины здоровья в драке — нажимаю сразу, не жду.",
        },
        "en": {
            "title": "Saving item not pressed",
            "text": "{count} times you died with {item_label} ready and time to press it ({times}).",
            "drill": "Keep {item_label} on a key you reach easily and decide in advance: below half HP in a fight, press it at once, don't wait.",
        },
    },
    "skill_first_max": {
        "ru": {
            "title": "Другой порядок прокачки",
            "text": "Первым вы вкачали до конца {yours}, а про-игроки на этом герое — {pro} ({agree} из {games} недавних про-матчей).",
            "drill": "В следующей игре на этом герое вкладывайте очки сначала в {pro}: подсказка в игре назовёт, куда вложить очко.",
        },
        "en": {
            "title": "A different skill order",
            "text": "You maxed {yours} first; pro players on this hero max {pro} ({agree} of {games} recent pro games).",
            "drill": "Next game on this hero, put your points into {pro} first: the in-game tip names where each point goes.",
        },
    },
    "burst_deaths": {
        "ru": {
            "title": "Быстрые смерти",
            "text": "{count} из {of} смертей случились меньше чем за 3 с с 70% здоровья и выше: вас ловили раньше, чем можно было ответить.",
            "drill": "Такие смерти решаются до драки: не стойте один там, где врагов не видно на карте, держитесь ближе к союзникам и вардам.",
        },
        "en": {
            "title": "Burst deaths",
            "text": "{count} of {of} deaths came in under 3 s from 70% HP or more: you were caught before you could answer.",
            "drill": "These deaths are decided before the fight: don't stand alone where the enemies are not on the map, stay near your allies and wards.",
        },
    },
    "deaths_enemy_half": {
        "ru": {
            "title": "Смерти на половине противника",
            "text": "{count} из {total} смертей после 10-й минуты — на половине карты противника. Туда заходили, не зная, где враги.{spot_suffix}",
            "drill": "Прежде чем фармить за рекой, найдите на карте хотя бы трёх героев противника. Не видно — фармите на своей половине.",
        },
        "en": {
            "title": "Deaths on the enemy half",
            "text": "{count} of {total} deaths after minute 10 were on the enemy half of the map, walked into without knowing where the enemies were.{spot_suffix}",
            "drill": "Before farming across the river, find at least three enemy heroes on the map. If you can't, farm on your half.",
        },
    },
    "deaths_same_place": {
        "ru": {
            "title": "Смерти в одном месте: {place_title}",
            "text": "{count} из {of} смертей — {place} ({times}). Здесь вас ловят раз за разом.",
            "drill": "{route}",
        },
        "en": {
            "title": "Deaths in one place: {place_title}",
            "text": "{count} of {of} deaths were in the {place} ({times}): you get caught there again and again.",
            "drill": "{route}",
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
    "save_item_fast": {
        "ru": {
            "title": "Спасающий предмет вовремя",
            "text": "{item} уже к {t_text}: с ним вы спасаете кора в драке, а не смотрите, как он умирает.",
        },
        "en": {
            "title": "A save item on time",
            "text": "{item} by {t_text}: with it you save a core in a fight instead of watching them die.",
        },
    },
    "save_item_slow": {
        "ru": {
            "title": "Поздний спасающий предмет",
            "text": "Первый спасающий предмет ({item}) только к {t_text}. Самые важные драки середины игры прошли без него.",
            "drill": "Копите на Glimmer Cape или Force Staff сразу после сапог и вардов: к 15-й минуте он должен быть.",
        },
        "en": {
            "title": "A late save item",
            "text": "First save item ({item}) only at {t_text}. The key mid-game fights went without it.",
            "drill": "Save for Glimmer Cape or Force Staff right after boots and wards: have it by minute 15.",
        },
    },
    "save_item_missing": {
        "ru": {
            "title": "Нет спасающего предмета",
            "text": "За {minutes} {minutes_word} — ни Glimmer Cape, ни Force Staff, ни другого предмета, которым можно спасти кора.",
            "drill": "После сапог и вардов первое золото — на Glimmer Cape или Force Staff.",
        },
        "en": {
            "title": "No save item",
            "text": "In {minutes} minutes: no Glimmer Cape, Force Staff or any other item to save a core with.",
            "drill": "After boots and wards, your first gold goes to Glimmer Cape or Force Staff.",
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
    "runes_good": {
        "ru": {
            "title": "Руны под контролем",
            "text": "Вы подняли {runes} {runes_word} — больше, чем вражеский мид. Руны дают темп для ротаций.",
        },
        "en": {
            "title": "Runes under control",
            "text": "You picked up {runes} runes — more than the enemy mid. Runes give tempo for rotations.",
        },
    },
    "runes_low": {
        "ru": {
            "title": "Мало рун",
            "text": "{runes} {runes_word} за {minutes} {minutes_word}. Мид без рун теряет темп и бутылку.",
            "drill": "Каждые 2 минуты с 6:00 подходите к руне за 10–15 секунд, даже если на линии идёт волна.",
        },
        "en": {
            "title": "Few runes",
            "text": "{runes} runes in {minutes} minutes. A mid without runes loses tempo and bottle charges.",
            "drill": "Every 2 minutes from 6:00, walk to the rune 10–15 seconds early, even with a wave in lane.",
        },
    },
    "runes_behind": {
        "ru": {
            "title": "Руны забирал соперник",
            "text": "{runes} {runes_word} у вас против {enemy_runes} у {hero}. Каждая его руна — ротация на ваши линии.",
            "drill": "Руну, которую не успеваете взять, хотя бы отгоняйте: вард на реку и контроль за 15 секунд до неё.",
        },
        "en": {
            "title": "The enemy mid took the runes",
            "text": "{runes} runes for you against {enemy_runes} for {hero}. Each of his runes is a rotation onto your lanes.",
            "drill": "When you cannot take a rune, contest it: a river ward and control 15 seconds before it spawns.",
        },
    },
    "stacks_low": {
        "ru": {
            "title": "Почти нет стаков",
            "text": "{stacks} {stacks_word} за {minutes} {minutes_word}. Стак — дешёвое золото для вашего керри.",
            "drill": "Минуты 4, 7, 10, 13, 16: в x:53 отводите лагерь рядом с керри. Приложение напомнит.",
        },
        "en": {
            "title": "Almost no stacks",
            "text": "{stacks} camps stacked in {minutes} minutes. A stack is cheap gold for your carry.",
            "drill": "Minutes 4, 7, 10, 13, 16: pull the camp next to your carry at x:53. The app reminds you.",
        },
    },
    "sentries_none": {
        "ru": {
            "title": "Ни одного сентри",
            "text": "За {minutes} {minutes_word} не поставлено ни одного сентри-варда: невидимых героев и вражеские варды нечем открыть.",
            "drill": "Держите 1–2 сентри в инвентаре с 10-й минуты: у своих вардов, у Рошана, против невидимых героев.",
        },
        "en": {
            "title": "No sentry wards",
            "text": "Not one sentry ward in {minutes} minutes: nothing to reveal invisible heroes or enemy wards.",
            "drill": "Keep 1–2 sentries from minute 10: at your wards, at Roshan and against invisible heroes.",
        },
    },
    "stuns_behind": {
        "ru": {
            "title": "Мало контроля в драках",
            "text": "{stuns} с оглушений у вас против {enemy_stuns} с у {hero}. Контроль — главная работа хардлайнера в драке.",
            "drill": "Начинайте драку своим контролем: оглушение по керри или по тому, кто первым вошёл, — до того как тратить остальные способности.",
        },
        "en": {
            "title": "Little control in fights",
            "text": "{stuns} s of stuns for you against {enemy_stuns} s for {hero}. Control is the offlaner's main job in a fight.",
            "drill": "Start fights with your control: stun the carry or whoever comes in first, before spending the rest of your spells.",
        },
    },
    "stuns_good": {
        "ru": {
            "title": "Контроль в драках",
            "text": "{stuns} с оглушений против {enemy_stuns} с у вражеского хардлайнера — вы задавали драки.",
        },
        "en": {
            "title": "Control in fights",
            "text": "{stuns} s of stuns against {enemy_stuns} s for the enemy offlaner — you set up the fights.",
        },
    },
    "towers_behind": {
        "ru": {
            "title": "Мало давления на строения",
            "text": "{damage} урона по строениям у вас против {enemy_damage} у {hero}. Хардлайнер, который не давит вышки, отдаёт карту.",
            "drill": "После выигранной драки или когда враги показались на другой линии — сразу бейте ближайшую вышку, а не уходите в лес.",
        },
        "en": {
            "title": "Little pressure on buildings",
            "text": "{damage} building damage for you against {enemy_damage} for {hero}. An offlaner who does not hit towers gives up the map.",
            "drill": "After a won fight, or when the enemies show on another lane, hit the nearest tower right away instead of going back to the jungle.",
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
        "draft_better_pick": {
            "ru": {
                "title": "Против этого состава лучше подходил {best}",
                "text": "Из ваших частых героев против этой вражеской пятёрки лучше всего выглядит {best}: {best_edge_text} к винрейту против {edge_text} у {hero} (статистика матчапов OpenDota).",
                "drill": "Перед пиком посмотрите на уже выбранных врагов: если ваш основной герой им проигрывает, возьмите героя из своего пула, у которого против них плюс.",
            },
            "en": {
                "title": "{best} fit this lineup better",
                "text": "Of your regular heroes, {best} looks best against this enemy five: {best_edge_text} win rate edge against {edge_text} for {hero} (OpenDota matchup statistics).",
                "drill": "Before picking, look at the enemies already picked: if your main hero loses to them, take a hero from your pool that has an edge against them.",
            },
        },
        "counter_item_missing": {
            "ru": {
                "title": "Нет предмета против {enemy}",
                "text": "У врагов был {enemy} ({reason_label}). Против этого обычно покупают {items}, а в этом матче ни одного из них не было.",
                "drill": "Когда видите в драфте {enemy}, заранее включите в сборку один из предметов: {items}.",
            },
            "en": {
                "title": "No answer to {enemy}",
                "text": "The enemy had {enemy} ({reason_label}). The usual answer is {items}, and none of them was bought this match.",
                "drill": "When you see {enemy} in the draft, plan one of these into your build early: {items}.",
            },
        },
        "counter_item_bought": {
            "ru": {
                "title": "Ответ на {enemy}: {item}",
                "text": "{item} против {enemy} ({reason_label}) — правильный выбор под вражеский состав.",
            },
            "en": {
                "title": "Answer to {enemy}: {item}",
                "text": "{item} against {enemy} ({reason_label}) — the right call for the enemy lineup.",
            },
        },
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
    "offlane": {"ru": "хардлайнера", "en": "offlaner"},
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
    "draft": {"ru": "Драфт", "en": "Draft"},
}

# Best vs worst own matches (self_compare.py): one line per metric.
SELF_COMPARE = {
    "ru": {
        "lh_10": "К 10:00 в лучших матчах у вас {best} добиваний, в худших — {worst}.",
        "gpm": "Золото в минуту: {best} в лучших матчах против {worst} в худших.",
        "deaths": "Смертей за матч: {best} в лучших против {worst} в худших.",
        "lane_deaths": "Смертей на линии: {best} в лучших матчах против {worst} в худших.",
        "kill_participation": "Участие в убийствах: {best} в лучших матчах против {worst} в худших.",
        "first_item_t": "Первый большой предмет: {item_best} к {best} в лучших матчах, {item_worst} к {worst} в худших.",
    },
    "en": {
        "lh_10": "By 10:00 you have {best} last hits in your best games and {worst} in your worst.",
        "gpm": "Gold per minute: {best} in your best games against {worst} in your worst.",
        "deaths": "Deaths per game: {best} in your best games against {worst} in your worst.",
        "lane_deaths": "Lane deaths: {best} in your best games against {worst} in your worst.",
        "kill_participation": "Kill participation: {best} in your best games against {worst} in your worst.",
        "first_item_t": "First big item: {item_best} by {best} in your best games, {item_worst} by {worst} in your worst.",
    },
}

# The player's own build on a hero (hero_build.py): one line per clear gap.
HERO_BUILD = {
    "ru": {
        "timing": "{item} в победах у вас к {win}, в поражениях — к {loss}.",
        "with_better": "С {item} вы выигрываете {winrate}% ({games_text}), без него — {without}% ({without_text}).",
        "without_better": "С {item} у вас {winrate}% побед ({games_text}), без него — {without}% ({without_text}): проверьте, когда он нужен.",
        "first": "Первый большой предмет в победах — чаще {win}, в поражениях — {loss}.",
    },
    "en": {
        "timing": "{item} comes by {win} in your wins and by {loss} in your losses.",
        "with_better": "With {item} you win {winrate}% ({games_text}), without it {without}% ({without_text}).",
        "without_better": "With {item} you win {winrate}% ({games_text}), without it {without}% ({without_text}): check when you need it.",
        "first": "Your first big item in wins is most often {win}, in losses {loss}.",
    },
}

# Why an enemy hero needs a counter item (draft_analysis.COUNTERS).
COUNTER_REASONS = {
    "evasion": {"ru": "уклонение", "en": "evasion"},
    "illusions": {"ru": "иллюзии", "en": "illusions"},
    "invisibility": {"ru": "невидимость", "en": "invisibility"},
    "healing": {"ru": "лечение", "en": "healing"},
}

ROLES = {
    "core": {"ru": "кор", "en": "core"},
    "offlane": {"ru": "хардлайн", "en": "offlane"},
    "support": {"ru": "саппорт", "en": "support"},
}


def _plural_ru(n: int, one: str, few: str, many: str) -> str:
    n = abs(int(n))
    if n % 10 == 1 and n % 100 != 11:
        return one
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return few
    return many


# Death places (map_analysis.zone / map_side) in words.
PLACE_ZONES = {
    "ru": {
        "in": {
            "top": "на верхней линии",
            "mid": "на центральной линии",
            "bot": "на нижней линии",
            "jungle": "в лесу",
            "base": "на базе",
        },
        "name": {
            "top": "верхняя линия",
            "mid": "центральная линия",
            "bot": "нижняя линия",
            "jungle": "лес",
            "base": "база",
        },
    },
    "en": {
        "name": {
            "top": "top lane",
            "mid": "mid lane",
            "bot": "bottom lane",
            "jungle": "jungle",
            "base": "base",
        },
    },
}
PLACE_SIDES = {
    "ru": {"own": "на своей половине", "river": "у реки", "enemy": "на половине врага"},
    "en": {"own": "on your side", "river": "by the river", "enemy": "on the enemy side"},
}
# The route drill of deaths_same_place: crossing the river, or your own half.
PLACE_ROUTES = {
    "ru": {
        "river": "Реку переходите, только когда на карте видно хотя бы троих врагов; иначе фармите лес ближе к своим башням. Вард на подходе к этому месту покажет, кто идёт.",
        "own": "Это ваша половина, но сюда за вами приходят: поставьте вард на подходе и, пока врагов не видно на карте, фармите лагеря ближе к башне.",
    },
    "en": {
        "river": "Cross the river only when at least three enemies are on the map; otherwise farm the jungle near your towers. A ward on the way into this spot shows who is coming.",
        "own": "It is your half, but enemies come here for you: ward the way in and farm the camps near your tower while the enemies are not on the map.",
    },
}


def place_label(zone_id: Any, side: Any, lang: str) -> str | None:
    """ "центральная линия у реки" / "mid lane by the river"; None for unknown ids."""
    lang = "ru" if lang == "ru" else "en"
    name = PLACE_ZONES[lang]["name"].get(zone_id)
    side_text = PLACE_SIDES[lang].get(side)
    return f"{name} {side_text}" if name and side_text else None


def _place_params(params: dict[str, Any], lang: str) -> None:
    zone_id, side = params.get("zone"), params.get("side")
    title = place_label(zone_id, side, lang)
    if title:
        params["place_title"] = title
        params["place"] = (
            f"{PLACE_ZONES['ru']['in'][zone_id]} {PLACE_SIDES['ru'][side]}"
            if lang == "ru"
            else title
        )
        params["route"] = PLACE_ROUTES[lang]["river" if side == "river" else "own"]
    spot = params.get("spot_zone")
    if spot in PLACE_ZONES["en"]["name"]:
        params["spot_suffix"] = (
            f" Чаще всего — {PLACE_ZONES['ru']['in'][spot]}."
            if lang == "ru"
            else f" Most often in the {PLACE_ZONES['en']['name'][spot]}."
        )
    else:
        params["spot_suffix"] = ""


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
    if params.get("reason") in COUNTER_REASONS:
        params["reason_label"] = COUNTER_REASONS[params["reason"]]["ru" if lang == "ru" else "en"]
    for key in ("edge", "best_edge"):
        if isinstance(params.get(key), (int, float)):
            params[f"{key}_text"] = f"{params[key]:+.1f}%".replace(
                ".", "," if lang == "ru" else "."
            )
    if "pct" in params and params["pct"] is not None:
        params["pct_rest"] = 100 - int(params["pct"])
    if params.get("item") in SAVERS:
        params["item_label"] = saver_label(params["item"], lang)
    if finding["id"] in {"deaths_same_place", "deaths_enemy_half"}:
        _place_params(params, lang)
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
            params["count_times"] = _plural_ru(params["count"], "раз", "раза", "раз")
        if params.get("deaths") is not None:
            params["deaths_word"] = _plural_ru(params["deaths"], "смерть", "смерти", "смертей")
        if params.get("last_hits") is not None:
            params["last_hits_word"] = _plural_ru(
                params["last_hits"], "добивание", "добивания", "добиваний"
            )
        if params.get("minutes") is not None:
            params["minutes_word"] = _plural_ru(params["minutes"], "минуту", "минуты", "минут")
        if params.get("runes") is not None:
            params["runes_word"] = _plural_ru(params["runes"], "руну", "руны", "рун")
        if params.get("stacks") is not None:
            params["stacks_word"] = _plural_ru(params["stacks"], "стак", "стака", "стаков")
    return params


class _SafeDict(dict):
    def __missing__(self, key: str) -> str:
        return "—"


def _advice_text(text: Any, lang: str) -> str:
    value = str(text or "")
    if lang != "ru" or not value:
        return value
    return translate_ru(value) or value


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
    spots = (analysis.get("map") or {}).get("spots")
    if spots:
        # Places where the deaths repeat, named for the map card.
        rendered["map"] = {
            **analysis["map"],
            "spots": [
                {**spot, "label": place_label(spot.get("zone"), spot.get("side"), lang)}
                for spot in spots
            ],
        }
    if analysis.get("advice"):
        # Live advice is stored in English; translate it like the overlay does.
        rendered["advice"] = [
            {
                **item,
                "action": _advice_text(item.get("action"), lang),
                "reason": _advice_text(item.get("reason"), lang),
                "why": why(item.get("dp"), lang),
            }
            for item in analysis["advice"]
        ]
    deaths = analysis.get("death_review")
    if deaths:
        rendered["death_review"] = {
            **deaths,
            "deaths": [
                {
                    **row,
                    **(
                        {
                            "last": {
                                **row["last"],
                                "ready_names": [
                                    saver_label(name, lang)
                                    for name in row["last"].get("ready") or []
                                ],
                                "usable_names": [
                                    saver_label(name, lang)
                                    for name in row["last"].get("usable") or []
                                ],
                            }
                        }
                        if row.get("last")
                        else {}
                    ),
                    **(
                        {
                            "warning": {
                                **row["warning"],
                                "action": _advice_text(row["warning"].get("action"), lang),
                            }
                        }
                        if row.get("warning")
                        else {}
                    ),
                }
                for row in deaths.get("deaths") or []
            ],
        }
    rendered["sections"] = {
        name: {**section, "label": SECTIONS.get(name, {}).get(lang, name)}
        for name, section in (analysis.get("sections") or {}).items()
    }
    return rendered
