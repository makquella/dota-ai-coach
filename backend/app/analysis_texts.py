"""
analysis_texts.py - Ukrainian and English texts for match and career reviews.

post_match_analysis.py and career_analysis.py produce language-neutral
findings ({"id", "params"}); this module turns them into a title, an
explanation with the numbers, and a concrete drill. Keep both languages in
sync: tests/test_post_match_analysis.py checks every finding id has both.
"""

from __future__ import annotations

from typing import Any

from app.advice_i18n import translate_uk
from app.advice_why import why
from app.last_moments import is_saver, saver_label


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
        "uk": {
            "title": "Сильна лінія",
            "text": "{lh10} добивань до 10-ї хвилини, орієнтир — {target}.",
        },
        "en": {
            "title": "Strong lane",
            "text": "{lh10} last hits by minute 10 with a {target} reference target.",
        },
    },
    "lh10_low": {
        "uk": {
            "title": "Мало добивань на лінії",
            "text": "{lh10} добивань до 10-ї хвилини, орієнтир — {target}.",
            "drill": "5–10 хвилин у «Демо героя» перед грою: лише добивання без суперника, мета — 45+ до 10:00. На лінії бийте кріпа, коли його HP нижче шкоди однієї атаки.",
        },
        "en": {
            "title": "Few last hits in lane",
            "text": "{lh10} last hits by minute 10 against a {target} reference target.",
            "drill": "5–10 minutes of Hero Demo before playing: last hits only, no enemy, aim for 45+ by 10:00. In lane, attack when the creep's HP is below one hit.",
        },
    },
    "lane_eff_high": {
        "uk": {
            "title": "Ефективна лінія",
            "text": "Ефективність лінії {efficiency}% — ви забрали майже все золото, що було доступне.",
        },
        "en": {
            "title": "Efficient lane",
            "text": "Lane efficiency {efficiency}% — you took nearly all the gold available.",
        },
    },
    "lane_eff_low": {
        "uk": {
            "title": "Лінію віддано",
            "text": "Ефективність лінії {efficiency}%: понад половину доступного золота пройшло повз.",
            "drill": "Якщо на лінії не стоїте, ідіть у ліс або на сусідню хвилю, а не стійте під вежею без кріпів.",
        },
        "en": {
            "title": "Lane given away",
            "text": "Lane efficiency {efficiency}%: more than half the available gold slipped away.",
            "drill": "If you cannot hold the lane, farm the jungle or the next wave instead of waiting under the tower.",
        },
    },
    "denies_good": {
        "uk": {
            "title": "Добрі денаї",
            "text": "{denies} денаїв до 10-ї хвилини — суперникові діставалося менше досвіду й золота.",
        },
        "en": {
            "title": "Good denies",
            "text": "{denies} denies by minute 10 — the enemy got less gold and experience.",
        },
    },
    "lane_deaths": {
        "uk": {
            "title": "Смерті на лінії",
            "text": "У даних запису: {count} {count_deaths} до 10-ї хвилини ({times}).",
            "drill": "Тримайтеся за своїми кріпами, коли у ворога готові здібності й поруч немає вашого саппорта; коли ворог зникає з мапи, відходьте до вежі.",
        },
        "en": {
            "title": "Lane deaths",
            "text": "Recorded events: {count} deaths before minute 10 ({times}).",
            "drill": "Stay behind your creeps while enemy spells are up and your support is away; step back to the tower when an enemy goes missing.",
        },
    },
    "gpm_high": {
        "uk": {
            "title": "Чудовий фарм",
            "text": "{gpm} золота за хвилину — краще, ніж у {pct}% гравців на {hero}.",
        },
        "en": {
            "title": "Great farm",
            "text": "{gpm} gold per minute — better than {pct}% of {hero} players.",
        },
    },
    "gpm_high_static": {
        "uk": {
            "title": "Чудовий фарм",
            "text": "{gpm} золота за хвилину, орієнтир для цієї ролі — {target}.",
        },
        "en": {
            "title": "Great farm",
            "text": "{gpm} gold per minute with a {target} benchmark for this role.",
        },
    },
    "gpm_low": {
        "uk": {
            "title": "Фарм нижче норми",
            "text": "{gpm} золота за хвилину — гірше, ніж у {pct_rest}% гравців на {hero}.",
            "drill": "Між бійками завжди має бути план фарму: хвиля → табір → наступна хвиля. Не стійте без діла й не ходіть за командою, якщо бійки немає.",
        },
        "en": {
            "title": "Farm below par",
            "text": "{gpm} gold per minute — lower than {pct_rest}% of {hero} players.",
            "drill": "Always have a farm route between fights: wave → camp → next wave. Don't idle or follow the team when there is no fight.",
        },
    },
    "gpm_low_static": {
        "uk": {
            "title": "Фарм нижче норми",
            "text": "{gpm} золота за хвилину, орієнтир для цієї ролі — {target}.",
            "drill": "Між бійками завжди має бути план фарму: хвиля → табір → наступна хвиля. Не стійте без діла й не ходіть за командою, якщо бійки немає.",
        },
        "en": {
            "title": "Farm below par",
            "text": "{gpm} gold per minute against a {target} benchmark for this role.",
            "drill": "Always have a farm route between fights: wave → camp → next wave. Don't idle or follow the team when there is no fight.",
        },
    },
    "farm_stall": {
        "uk": {
            "title": "Провал у фармі",
            "text": "З {from_} по {to}-ту хвилину всього {last_hits} {last_hits_word}. У цей час герой не фармив і не приносив користі на мапі.",
            "drill": "Якщо не знаєте, що робити, — фарміть найближчий безпечний табір. Раз на хвилину дивіться на мінімапу: де вільні хвилі?",
        },
        "en": {
            "title": "Farm stall",
            "text": "Only {last_hits} last hits from minute {from_} to {to}. The hero neither farmed nor made plays in that window.",
            "drill": "When unsure what to do, farm the nearest safe camp. Check the minimap every minute for free waves.",
        },
    },
    "deaths_low": {
        "uk": {
            "title": "Бережете героя",
            "text": "Усього {deaths} {deaths_word} за {minutes} {minutes_word} — команда майже завжди грала з вами.",
        },
        "en": {
            "title": "Kept your hero alive",
            "text": "Only {deaths} deaths in {minutes} minutes — your team almost always had you.",
        },
    },
    "deaths_high": {
        "uk": {
            "title": "Забагато смертей",
            "text": "{deaths} {deaths_word} за {minutes} {minutes_word}{dead_suffix}.",
            "drill": "Перед кожним виходом у чужу частину мапи запитайте себе: скільки ворогів не видно на мінімапі? Якщо троє й більше — фарміть ближче до своєї сторони.",
        },
        "en": {
            "title": "Too many deaths",
            "text": "{deaths} deaths in {minutes} minutes{dead_suffix}.",
            "drill": "Before going into enemy territory ask: how many enemies are missing from the minimap? Three or more — farm closer to your side.",
        },
    },
    "death_with_gold": {
        "uk": {
            "title": "Смерть із золотом на руках",
            "text": "{count_text} з великим запасом золота; найгірша — на {t_text} з {gold} золота. Під час смерті втрачається ненадійне золото, а предмет ще не куплено.",
            "drill": "Накопичили на предмет — купіть його (кур'єр або крамниця) до того, як іти в небезпечну зону.",
        },
        "en": {
            "title": "Died holding gold",
            "text": "{count_text} with a lot of gold on hand; the worst at {t_text} with {gold} gold. Dying costs unreliable gold and delays the item.",
            "drill": "Once you can afford an item, buy it (courier or shop) before walking into danger.",
        },
    },
    "death_streak": {
        "uk": {
            "title": "Серія смертей",
            "text": "{count} {count_deaths} за 5 хвилин ({from_text}–{to_text}). Після смерті легко повторити ту саму помилку.",
            "drill": "Після смерті подивіться на мінімапу й таймери та оберіть безпечну ціль — не повертайтеся одразу туди, де вас спіймали.",
        },
        "en": {
            "title": "Death streak",
            "text": "{count} deaths within 5 minutes ({from_text}–{to_text}). It is easy to repeat the same mistake right after dying.",
            "drill": "After dying, look at the minimap and timers and pick a safe target — don't walk straight back to where you were caught.",
        },
    },
    "died_after_warning": {
        "uk": {
            "title": "Смерть після попередження",
            "text": "{count} {count_times} ви загинули протягом {window} с після термінової підказки (перший раз — {t_text}). Тренер попередив вчасно, але відійти не встигли.",
            "drill": "Термінова підказка — сигнал одразу розвернутися до своїх: спершу крок назад, потім думати. Потренуйте це в наступній грі.",
        },
        "en": {
            "title": "Died after a warning",
            "text": "{count} times you died within {window} s of urgent advice (first at {t_text}). The warning came in time, but the retreat did not.",
            "drill": "Treat urgent advice as a signal to turn back at once: step away first, think second. Practise it next game.",
        },
    },
    "died_with_saver_ready": {
        "uk": {
            "title": "Рятівний предмет не натиснуто",
            "text": "{count} {count_times} ви загинули, хоча встигали натиснути {item_label} ({times}).",
            "drill": "Тримайте {item_label} на зручній клавіші й вирішуйте заздалегідь: нижче половини здоров'я в бійці — натискаю одразу, не чекаю.",
        },
        "en": {
            "title": "Saving item not pressed",
            "text": "{count} times you died with {item_label} ready and time to press it ({times}).",
            "drill": "Keep {item_label} on a key you reach easily and decide in advance: below half HP in a fight, press it at once, don't wait.",
        },
    },
    "skill_first_max": {
        "uk": {
            "title": "Інший порядок прокачки",
            "text": "Першою ви прокачали до кінця {yours}, а про-гравці на цьому герої — {pro} ({agree} з {games} нещодавніх про-матчів).",
            "drill": "У наступній грі на цьому герої вкладайте очки спершу в {pro}: підказка в грі назве, куди вкласти очко.",
        },
        "en": {
            "title": "A different skill order",
            "text": "You maxed {yours} first; pro players on this hero max {pro} ({agree} of {games} recent pro games).",
            "drill": "Next game on this hero, put your points into {pro} first: the in-game tip names where each point goes.",
        },
    },
    "burst_deaths": {
        "uk": {
            "title": "Швидкі смерті",
            "text": "{count} з {of} смертей — менш ніж за 3 секунди, коли здоров'я було 70% і більше: вас ловили раніше, ніж можна було відповісти.",
            "drill": "Такі смерті вирішуються до бійки: не стійте самі там, де ворогів не видно на мапі, тримайтеся ближче до союзників і вардів.",
        },
        "en": {
            "title": "Burst deaths",
            "text": "{count} of {of} deaths came in under 3 s from 70% HP or more: you were caught before you could answer.",
            "drill": "These deaths are decided before the fight: don't stand alone where the enemies are not on the map, stay near your allies and wards.",
        },
    },
    "deaths_enemy_half": {
        "uk": {
            "title": "Смерті на половині суперника",
            "text": "{count} з {total} смертей після 10-ї хвилини — на половині мапи суперника. Туди заходили, не знаючи, де вороги.{spot_suffix}",
            "drill": "Перш ніж фармити за річкою, знайдіть на мапі хоча б трьох героїв суперника. Не видно — фарміть на своїй половині.",
        },
        "en": {
            "title": "Deaths on the enemy half",
            "text": "{count} of {total} deaths after minute 10 were on the enemy half of the map, walked into without knowing where the enemies were.{spot_suffix}",
            "drill": "Before farming across the river, find at least three enemy heroes on the map. If you can't, farm on your half.",
        },
    },
    "deaths_same_place": {
        "uk": {
            "title": "Смерті в одному місці: {place_title}",
            "text": "{count} з {of} смертей — {place} ({times}). Тут вас ловлять раз у раз.",
            "drill": "{route}",
        },
        "en": {
            "title": "Deaths in one place: {place_title}",
            "text": "{count} of {of} deaths were in the {place} ({times}): you get caught there again and again.",
            "drill": "{route}",
        },
    },
    "killed_by_one": {
        "uk": {
            "title": "Головна загроза: {hero}",
            "text": "{count} з {deaths} смертей — від {hero}.",
            "drill": "Стежте, де {hero}, перш ніж виходити вперед, і заздалегідь продумайте захист від нього: предмет, позицію або здібність для втечі.",
        },
        "en": {
            "title": "Main threat: {hero}",
            "text": "{hero} killed you {count} times out of {deaths}.",
            "drill": "Know where {hero} is before stepping forward and plan a counter: an item, positioning or an escape spell.",
        },
    },
    "kp_high": {
        "uk": {
            "title": "У кожній бійці",
            "text": "Участь у вбивствах {kp}% — ви були там, де вирішувалася гра.",
        },
        "en": {
            "title": "In every fight",
            "text": "{kp}% kill participation — you were where the game was decided.",
        },
    },
    "kp_low": {
        "uk": {
            "title": "Команда билася без вас",
            "text": "Участь у вбивствах {kp}% з {team_kills} вбивств команди.",
            "drill": "Після 20-ї хвилини перед важливими цілями (Рошан, вежі, смок) завершуйте фарм і підходьте до команди заздалегідь.",
        },
        "en": {
            "title": "The team fought without you",
            "text": "{kp}% kill participation out of {team_kills} team kills.",
            "drill": "After minute 20, before key objectives (Roshan, towers, smokes) stop farming and join the team early.",
        },
    },
    "damage_high": {
        "uk": {
            "title": "Багато шкоди героям",
            "text": "Шкода героям краща, ніж у {pct}% гравців на цьому герої.",
        },
        "en": {
            "title": "High hero damage",
            "text": "Hero damage better than {pct}% of players on this hero.",
        },
    },
    "damage_low": {
        "uk": {
            "title": "Мало шкоди в бійках",
            "text": "Шкода героям гірша, ніж у {pct_rest}% гравців на цьому герої.",
            "drill": "У бійці бийте ціль, до якої безпечно дотягнутися, а не чекайте кінця бійки осторонь.",
        },
        "en": {
            "title": "Little damage in fights",
            "text": "Hero damage lower than {pct_rest}% of players on this hero.",
            "drill": "In fights, hit the target you can safely reach instead of waiting out the fight.",
        },
    },
    "towers_high": {
        "uk": {
            "title": "Тиснули будівлі",
            "text": "Шкода будівлям краща, ніж у {pct}% гравців — ви перетворювали перевагу на мапу.",
        },
        "en": {
            "title": "Pushed buildings",
            "text": "Building damage better than {pct}% of players — you turned advantage into map control.",
        },
    },
    "core_item_fast": {
        "uk": {
            "title": "Швидкий перший предмет",
            "text": "{item} до {t_text} — добрий таймінг, щоб починати впливати на гру.",
        },
        "en": {
            "title": "Fast first item",
            "text": "{item} by {t_text} — a good timing to start making an impact.",
        },
    },
    "core_item_slow": {
        "uk": {
            "title": "Пізній перший предмет",
            "text": "Перший великий предмет ({item}) лише до {t_text}. На цей час суперники зазвичай уже з 2 предметами.",
            "drill": "Сплануйте збірку заздалегідь і не витрачайте золото на зайве до першого ключового предмета; фарміть між бійками.",
        },
        "en": {
            "title": "Late first item",
            "text": "First big item ({item}) only at {t_text}. By then opponents usually have two.",
            "drill": "Plan the build in advance, skip extras until the first key item, and farm between fights.",
        },
    },
    "save_item_fast": {
        "uk": {
            "title": "Рятівний предмет вчасно",
            "text": "{item} уже до {t_text}: з ним ви рятуєте кора в бійці, а не дивитеся, як він помирає.",
        },
        "en": {
            "title": "A save item on time",
            "text": "{item} by {t_text}: with it you save a core in a fight instead of watching them die.",
        },
    },
    "save_item_slow": {
        "uk": {
            "title": "Пізній рятівний предмет",
            "text": "Перший рятівний предмет ({item}) лише до {t_text}. Найважливіші бійки середини гри минули без нього.",
            "drill": "Збирайте на Glimmer Cape або Force Staff одразу після чобіт і вардів: до 15-ї хвилини він має бути.",
        },
        "en": {
            "title": "A late save item",
            "text": "First save item ({item}) only at {t_text}. The key mid-game fights went without it.",
            "drill": "Save for Glimmer Cape or Force Staff right after boots and wards: have it by minute 15.",
        },
    },
    "save_item_missing": {
        "uk": {
            "title": "Немає рятівного предмета",
            "text": "За {minutes} {minutes_word} — ні Glimmer Cape, ні Force Staff, ні іншого предмета, яким можна врятувати кора.",
            "drill": "Після чобіт і вардів перше золото — на Glimmer Cape або Force Staff.",
        },
        "en": {
            "title": "No save item",
            "text": "In {minutes} minutes: no Glimmer Cape, Force Staff or any other item to save a core with.",
            "drill": "After boots and wards, your first gold goes to Glimmer Cape or Force Staff.",
        },
    },
    "no_core_item": {
        "uk": {
            "title": "Немає жодного великого предмета",
            "text": "За {minutes} {minutes_word} не зібрано жодного великого предмета.",
            "drill": "Поставте мету: перший ключовий предмет до 15–17 хвилини. Перевіряйте прогрес за золотом на 10-й хвилині.",
        },
        "en": {
            "title": "No big item",
            "text": "No big item completed in {minutes} minutes.",
            "drill": "Set a goal: the first key item by minute 15–17. Check your gold progress at minute 10.",
        },
    },
    "wards_high": {
        "uk": {
            "title": "Добрий огляд",
            "text": "У даних: {obs} обсервер-вардів і {sen} сентрі. Спосіб підрахунку вказано в джерелі.",
        },
        "en": {
            "title": "Good vision",
            "text": "Data reports {obs} observer and {sen} sentry wards. See the evidence for the counting method.",
        },
    },
    "wards_low": {
        "uk": {
            "title": "Мало вардів",
            "text": "{obs} обсервер-вардів за {minutes} {minutes_word}.",
            "drill": "Ставте вард щоразу, коли він є в крамниці, і перед кожним походом до Рошана чи ворожої вежі.",
        },
        "en": {
            "title": "Few wards",
            "text": "{obs} observer wards in {minutes} minutes.",
            "drill": "Place a ward every time the shop has one, and before every Roshan or tower push.",
        },
    },
    "runes_good": {
        "uk": {
            "title": "Руни під контролем",
            "text": "Ви підняли {runes} {runes_word} — більше, ніж ворожий мід. Руни дають темп для ротацій.",
        },
        "en": {
            "title": "Runes under control",
            "text": "You picked up {runes} runes — more than the enemy mid. Runes give tempo for rotations.",
        },
    },
    "runes_low": {
        "uk": {
            "title": "Мало рун",
            "text": "{runes} {runes_word} за {minutes} {minutes_word}. Мід без рун втрачає темп і пляшку.",
            "drill": "Кожні 2 хвилини з 6:00 підходьте до руни за 10–15 секунд, навіть якщо на лінії йде хвиля.",
        },
        "en": {
            "title": "Few runes",
            "text": "{runes} runes in {minutes} minutes. A mid without runes loses tempo and bottle charges.",
            "drill": "Every 2 minutes from 6:00, walk to the rune 10–15 seconds early, even with a wave in lane.",
        },
    },
    "runes_behind": {
        "uk": {
            "title": "Руни забирав суперник",
            "text": "{runes} {runes_word} у вас проти {enemy_runes} у {hero}. Кожна його руна — ротація на ваші лінії.",
            "drill": "Руну, яку не встигаєте взяти, хоча б відганяйте: вард на річку й контроль за 15 секунд до неї.",
        },
        "en": {
            "title": "The enemy mid took the runes",
            "text": "{runes} runes for you against {enemy_runes} for {hero}. Each of their runes is a rotation onto your lanes.",
            "drill": "When you cannot take a rune, contest it: a river ward and control 15 seconds before it spawns.",
        },
    },
    "stacks_low": {
        "uk": {
            "title": "Майже немає стаків",
            "text": "{stacks} {stacks_word} за {minutes} {minutes_word}. Стак — дешеве золото для вашого керрі.",
            "drill": "Хвилини 4, 7, 10, 13, 16: у x:53 відводьте табір поруч із керрі. Застосунок нагадає.",
        },
        "en": {
            "title": "Almost no stacks",
            "text": "{stacks} camps stacked in {minutes} minutes. A stack is cheap gold for your carry.",
            "drill": "Minutes 4, 7, 10, 13, 16: pull the camp next to your carry at x:53. The app reminds you.",
        },
    },
    "sentries_none": {
        "uk": {
            "title": "Жодного сентрі",
            "text": "За {minutes} {minutes_word} не поставлено жодного сентрі-варда: невидимих героїв і ворожі варди нічим відкрити.",
            "drill": "Тримайте 1–2 сентрі в інвентарі з 10-ї хвилини: біля своїх вардів, біля Рошана, проти невидимих героїв.",
        },
        "en": {
            "title": "No sentry wards",
            "text": "Not one sentry ward in {minutes} minutes: nothing to reveal invisible heroes or enemy wards.",
            "drill": "Keep 1–2 sentries from minute 10: at your wards, at Roshan and against invisible heroes.",
        },
    },
    "lane_lost": {
        "uk": {
            "title": "Лінію проти {hero} програно",
            "text": "До 10-ї хвилини {lh_mine} {lh_mine_word} у вас проти {lh_theirs} у {hero} і на {gold} золота менше{turn_text}.",
            "drill": "На важкій лінії грайте від досвіду: стійте в радіусі досвіду, добивайте лише безпечних кріпів і кличте саппорта чи ротацію до 5-ї хвилини, а не після.",
        },
        "en": {
            "title": "Lost the lane against {hero}",
            "text": "By minute 10, {lh_mine} last hits for you against {lh_theirs} for {hero}, and {gold} gold behind{turn_text}.",
            "drill": "In a hard lane, play for experience: stay in XP range, take only the safe last hits and call your support or a rotation before minute 5, not after.",
        },
    },
    "lane_won": {
        "uk": {
            "title": "Лінію проти {hero} виграно",
            "text": "До 10-ї хвилини {lh_mine} {lh_mine_word} у вас проти {lh_theirs} у {hero} і на {gold} золота більше{turn_text}.",
            "drill": "Виграну лінію перетворюйте на темп: вежа, ротація до сусідів або ліс суперника, поки він відстає.",
        },
        "en": {
            "title": "Won the lane against {hero}",
            "text": "By minute 10, {lh_mine} last hits for you against {lh_theirs} for {hero}, and {gold} gold ahead{turn_text}.",
            "drill": "Turn a won lane into tempo: a tower, a rotation to the next lane or the enemy jungle while they are behind.",
        },
    },
    "stuns_behind": {
        "uk": {
            "title": "Мало контролю в бійках",
            "text": "{stuns} с оглушень у вас проти {enemy_stuns} с у {hero}. Контроль — головна робота хардлайнера в бійці.",
            "drill": "Починайте бійку своїм контролем: оглушення по керрі або по тому, хто першим зайшов, — до того як витрачати інші здібності.",
        },
        "en": {
            "title": "Little control in fights",
            "text": "{stuns} s of stuns for you against {enemy_stuns} s for {hero}. Control is the offlaner's main job in a fight.",
            "drill": "Start fights with your control: stun the carry or whoever comes in first, before spending the rest of your spells.",
        },
    },
    "stuns_good": {
        "uk": {
            "title": "Контроль у бійках",
            "text": "{stuns} с оглушень проти {enemy_stuns} с у ворожого хардлайнера — ви задавали бійки.",
        },
        "en": {
            "title": "Control in fights",
            "text": "{stuns} s of stuns against {enemy_stuns} s for the enemy offlaner — you set up the fights.",
        },
    },
    "towers_behind": {
        "uk": {
            "title": "Мало тиску на будівлі",
            "text": "{damage} шкоди будівлям у вас проти {enemy_damage} у {hero}. Хардлайнер, який не тисне вежі, віддає мапу.",
            "drill": "Після виграної бійки або коли вороги показалися на іншій лінії — одразу бийте найближчу вежу, а не йдіть у ліс.",
        },
        "en": {
            "title": "Little pressure on buildings",
            "text": "{damage} building damage for you against {enemy_damage} for {hero}. An offlaner who does not hit towers gives up the map.",
            "drill": "After a won fight, or when the enemies show on another lane, hit the nearest tower right away instead of going back to the jungle.",
        },
    },
    "stacks_good": {
        "uk": {
            "title": "Стаки для команди",
            "text": "{stacks} стаків таборів — додаткове золото для ваших кор-героїв.",
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
            "uk": {
                "title": "Проти цього складу краще підходив {best}",
                "text": "З ваших частих героїв проти цієї ворожої п'ятірки найкраще виглядає {best}: {best_edge_text} до вінрейту проти {edge_text} у {hero} (статистика матчапів OpenDota).",
                "drill": "Перед піком подивіться на вже обраних ворогів: якщо ваш основний герой їм програє, візьміть героя зі свого пулу, у якого проти них плюс.",
            },
            "en": {
                "title": "{best} fit this lineup better",
                "text": "Of your regular heroes, {best} looks best against this enemy five: {best_edge_text} win rate edge against {edge_text} for {hero} (OpenDota matchup statistics).",
                "drill": "Before picking, look at the enemies already picked: if your main hero loses to them, take a hero from your pool that has an edge against them.",
            },
        },
        "counter_item_missing": {
            "uk": {
                "title": "Немає предмета проти {enemy}",
                "text": "У складі ворога — {enemy} ({reason_label}). Проти цього зазвичай купують {items}, а в цьому матчі жодного з них не було.",
                "drill": "Коли бачите в драфті {enemy}, заздалегідь додайте до збірки один із предметів: {items}.",
            },
            "en": {
                "title": "No answer to {enemy}",
                "text": "The enemy had {enemy} ({reason_label}). The usual answer is {items}, and none of them was bought this match.",
                "drill": "When you see {enemy} in the draft, plan one of these into your build early: {items}.",
            },
        },
        "counter_item_bought": {
            "uk": {
                "title": "Відповідь на {enemy}: {item}",
                "text": "{item} проти {enemy} ({reason_label}) — правильний вибір під ворожий склад.",
            },
            "en": {
                "title": "Answer to {enemy}: {item}",
                "text": "{item} against {enemy} ({reason_label}) — the right call for the enemy lineup.",
            },
        },
        "build_timing_late": {
            "uk": {
                "title": "Пізній {item}",
                "text": "{item} до {t_text}: з таким таймінгом {hero} виграє {winrate}% ігор. Зазвичай цей предмет купують до {typical_t_text}, і тоді перемог {typical_winrate}% (публічні матчі OpenDota).",
                "drill": "Наступний матч на {hero}: мета — {item} до {typical_t_text}. Не відволікайтеся на зайві предмети до нього й фарміть між бійками.",
            },
            "en": {
                "title": "Late {item}",
                "text": "{item} at {t_text}: with that timing {hero} wins {winrate}% of games. It is usually bought by {typical_t_text}, which wins {typical_winrate}% (OpenDota public matches).",
                "drill": "Next {hero} game: aim for {item} by {typical_t_text}. Skip extras before it and farm between fights.",
            },
        },
        "build_timing_good": {
            "uk": {
                "title": "Добрий таймінг: {item}",
                "text": "{item} до {t_text} — з таким таймінгом {hero} виграє {winrate}% ігор (у середньому {average}%).",
            },
            "en": {
                "title": "Good timing: {item}",
                "text": "{item} at {t_text} — with that timing {hero} wins {winrate}% of games (average {average}%).",
            },
        },
        "build_off_meta": {
            "uk": {
                "title": "Нестандартна збірка",
                "text": "Жодного з найчастіших предметів на {hero} ({popular}). Ваші предмети: {mine}.",
                "drill": "Спробуйте стандартну збірку на {hero}: {popular}. Відступайте від неї, лише коли розумієте, проти чого збираєте.",
            },
            "en": {
                "title": "Unusual build",
                "text": "None of the most common {hero} items ({popular}). Your items: {mine}.",
                "drill": "Try the standard {hero} build: {popular}. Deviate only when you know what you are building against.",
            },
        },
        "build_on_meta": {
            "uk": {
                "title": "Перевірена збірка",
                "text": "Зібрали ключові предмети {hero}: {items}.",
            },
            "en": {"title": "Proven build", "text": "You built the key {hero} items: {items}."},
        },
        "peer_gpm_behind": {
            "uk": {
                "title": "Фарм нижчий, ніж у суперника",
                "text": "{gpm} золота за хвилину проти {peer_gpm} у {role_label} у цьому матчі ({heroes}). Гра підбирає суперників вашого рівня, отже такий фарм вам до снаги.",
                "drill": "Порівняйте маршрути: поки немає бійки, у кора завжди має бути хвиля або табір. Дивіться, де фармить {heroes}, і не віддавайте йому вільних хвиль.",
            },
            "en": {
                "title": "Farming less than your opponent",
                "text": "{gpm} gold per minute vs {peer_gpm} for the {role_label} of this match ({heroes}). Matchmaking pairs you with players of your level, so that farm is within reach.",
                "drill": "Compare routes: without a fight a core always has a wave or a camp. Watch where {heroes} farms and don't leave free waves to them.",
            },
        },
        "peer_gpm_ahead": {
            "uk": {
                "title": "Перефармили суперника",
                "text": "{gpm} золота за хвилину проти {peer_gpm} у {role_label} у цьому матчі ({heroes}).",
            },
            "en": {
                "title": "Outfarmed your opponent",
                "text": "{gpm} gold per minute vs {peer_gpm} for the {role_label} of this match ({heroes}).",
            },
        },
        "peer_lh10_behind": {
            "uk": {
                "title": "Програли лінію за добиваннями",
                "text": "{lh10} добивань до 10:00 проти {peer_lh10} у {role_label} у цьому матчі ({heroes}).",
                "drill": "На лінії стежте за HP кріпів і бийте, коли вистачить одного удару; тримайте суперника під тиском, коли він добиває.",
            },
            "en": {
                "title": "Lost the last-hit race",
                "text": "{lh10} last hits by 10:00 vs {peer_lh10} for the {role_label} of this match ({heroes}).",
                "drill": "Watch creep HP and hit when one attack is enough; pressure your opponent when they go for last hits.",
            },
        },
        "peer_deaths_more": {
            "uk": {
                "title": "Помирали частіше за суперника",
                "text": "{deaths} {deaths_word} проти {peer_deaths} у {role_label} у цьому матчі ({heroes}).",
                "drill": "Перед кожним ризикованим виходом перевірте мінімапу: скільки ворогів не видно? Якщо троє й більше — фарміть безпечніше.",
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
    "carry": {"uk": "керрі", "en": "carry"},
    "mid": {"uk": "мідера", "en": "mid"},
    "offlane": {"uk": "хардлайнера", "en": "offlaner"},
    "support": {"uk": "саппорта", "en": "support"},
}

RANK_MEDALS = {
    1: {"uk": "Рекрут", "en": "Herald"},
    2: {"uk": "Вартовий", "en": "Guardian"},
    3: {"uk": "Лицар", "en": "Crusader"},
    4: {"uk": "Герой", "en": "Archon"},
    5: {"uk": "Легенда", "en": "Legend"},
    6: {"uk": "Володар", "en": "Ancient"},
    7: {"uk": "Божество", "en": "Divine"},
    8: {"uk": "Безсмертний", "en": "Immortal"},
}


def rank_label(rank_tier: Any, lang: str) -> str | None:
    """rank_tier 54 -> "Легенда 4" / "Legend 4"; 80 -> "Безсмертний"."""
    try:
        tier = int(rank_tier)
    except (TypeError, ValueError):
        return None
    medal = RANK_MEDALS.get(tier // 10)
    if not medal:
        return None
    stars = tier % 10
    name = medal["uk" if lang == "uk" else "en"]
    return f"{name} {stars}" if 1 <= stars <= 5 and tier // 10 < 8 else name


SECTIONS = {
    "laning": {"uk": "Лінія", "en": "Laning"},
    "farm": {"uk": "Фарм", "en": "Farm"},
    "survival": {"uk": "Виживання", "en": "Survival"},
    "fights": {"uk": "Бійки", "en": "Fights"},
    "items": {"uk": "Предмети", "en": "Items"},
    "vision": {"uk": "Огляд", "en": "Vision"},
    "draft": {"uk": "Драфт", "en": "Draft"},
}

# Best vs worst own matches (self_compare.py): one line per metric.
SELF_COMPARE = {
    "uk": {
        "lh_10": "До 10:00 у найкращих матчах у вас {best} добивань, у найгірших — {worst}.",
        "gpm": "Золото за хвилину: {best} у найкращих матчах проти {worst} у найгірших.",
        "deaths": "Смертей за матч: {best} у найкращих проти {worst} у найгірших.",
        "lane_deaths": "Смертей на лінії: {best} у найкращих матчах проти {worst} у найгірших.",
        "kill_participation": "Участь у вбивствах: {best} у найкращих матчах проти {worst} у найгірших.",
        "first_item_t": "Перший великий предмет: {item_best} до {best} у найкращих матчах, {item_worst} до {worst} у найгірших.",
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
    "uk": {
        "timing": "{item} у перемогах у вас до {win}, у поразках — до {loss}.",
        "with_better": "З {item} ви виграєте {winrate}% ({games_text}), без нього — {without}% ({without_text}).",
        "without_better": "З {item} у вас {winrate}% перемог ({games_text}), без нього — {without}% ({without_text}): перевірте, коли він потрібен.",
        "first": "Перший великий предмет у перемогах — частіше {win}, у поразках — {loss}.",
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
    "evasion": {"uk": "ухилення", "en": "evasion"},
    "illusions": {"uk": "ілюзії", "en": "illusions"},
    "invisibility": {"uk": "невидимість", "en": "invisibility"},
    "healing": {"uk": "лікування", "en": "healing"},
    "targeted": {"uk": "ви гинули під {spell}", "en": "{spell} killed you"},
}

ROLES = {
    "core": {"uk": "кор", "en": "core"},
    "offlane": {"uk": "хардлайн", "en": "offlane"},
    "support": {"uk": "саппорт", "en": "support"},
}


def _plural_uk(n: int, one: str, few: str, many: str) -> str:
    n = abs(int(n))
    if n % 10 == 1 and n % 100 != 11:
        return one
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return few
    return many


# Death places (map_analysis.zone / map_side) in words.
PLACE_ZONES = {
    "uk": {
        "in": {
            "top": "на верхній лінії",
            "mid": "на центральній лінії",
            "bot": "на нижній лінії",
            "jungle": "у лісі",
            "base": "на базі",
        },
        "name": {
            "top": "верхня лінія",
            "mid": "центральна лінія",
            "bot": "нижня лінія",
            "jungle": "ліс",
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
    "uk": {"own": "на своїй половині", "river": "біля річки", "enemy": "на половині ворога"},
    "en": {"own": "on your side", "river": "by the river", "enemy": "on the enemy side"},
}
# The route drill of deaths_same_place: crossing the river, or your own half.
PLACE_ROUTES = {
    "uk": {
        "river": "Річку переходьте, лише коли на мапі видно хоча б трьох ворогів; інакше фарміть ліс ближче до своїх веж. Вард на підході до цього місця покаже, хто йде.",
        "own": "Це ваша половина, але сюди за вами приходять: поставте вард на підході й, поки ворогів не видно на мапі, фарміть табори ближче до вежі.",
    },
    "en": {
        "river": "Cross the river only when at least three enemies are on the map; otherwise farm the jungle near your towers. A ward on the way into this spot shows who is coming.",
        "own": "It is your half, but enemies come here for you: ward the way in and farm the camps near your tower while the enemies are not on the map.",
    },
}


def place_label(zone_id: Any, side: Any, lang: str) -> str | None:
    """ "центральна лінія біля річки" / "mid lane by the river"; None for unknown ids."""
    lang = "uk" if lang == "uk" else "en"
    name = PLACE_ZONES[lang]["name"].get(zone_id)
    side_text = PLACE_SIDES[lang].get(side)
    return f"{name} {side_text}" if name and side_text else None


def _place_params(params: dict[str, Any], lang: str) -> None:
    zone_id, side = params.get("zone"), params.get("side")
    title = place_label(zone_id, side, lang)
    if title:
        params["place_title"] = title
        params["place"] = (
            f"{PLACE_ZONES['uk']['in'][zone_id]} {PLACE_SIDES['uk'][side]}"
            if lang == "uk"
            else title
        )
        params["route"] = PLACE_ROUTES[lang]["river" if side == "river" else "own"]
    spot = params.get("spot_zone")
    if spot in PLACE_ZONES["en"]["name"]:
        params["spot_suffix"] = (
            f" Найчастіше — {PLACE_ZONES['uk']['in'][spot]}."
            if lang == "uk"
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
        params["role_label"] = PEER_ROLES[params["role"]]["uk" if lang == "uk" else "en"]
    for key in ("t", "from", "to", "typical_t"):
        if key in params:
            params[f"{key}_text"] = clock(params[key])
    if params.get("reason") in COUNTER_REASONS:
        label = COUNTER_REASONS[params["reason"]]["uk" if lang == "uk" else "en"]
        params["reason_label"] = label.format(spell=params.get("spell") or "")
    for key in ("edge", "best_edge"):
        if isinstance(params.get(key), (int, float)):
            params[f"{key}_text"] = f"{params[key]:+.1f}%".replace(
                ".", "," if lang == "uk" else "."
            )
    if "pct" in params and params["pct"] is not None:
        params["pct_rest"] = 100 - int(params["pct"])
    if is_saver(params.get("item")):
        # An item, the hero's ability ("ability:Blade Fury") or a bottled rune.
        params["item_label"] = saver_label(params["item"], lang)
    if finding["id"] in {"deaths_same_place", "deaths_enemy_half"}:
        _place_params(params, lang)
    if finding["id"] == "deaths_high":
        dead = params.get("time_dead")
        pct = params.get("dead_pct")
        if dead and pct is not None:
            params["dead_suffix"] = (
                f", {clock(dead)} у таверні ({pct}% матчу)"
                if lang == "uk"
                else f", {clock(dead)} spent dead ({pct}% of the match)"
            )
        else:
            params["dead_suffix"] = ""
    if finding["id"] == "death_with_gold":
        count = int(params.get("count") or 1)
        params["count_text"] = (
            f"{count} {_plural_uk(count, 'смерть', 'смерті', 'смертей')}"
            if lang == "uk"
            else f"{count} death{'s' if count != 1 else ''}"
        )
    if finding["id"] in ("lane_lost", "lane_won"):
        turn = params.get("turn")
        if isinstance(turn, int):
            params["turn_text"] = (
                f" — розрив з'явився з {turn}-ї хвилини"
                if lang == "uk"
                else f"; the gap opened at minute {turn}"
            )
        else:
            params["turn_text"] = ""
        if lang == "uk" and params.get("lh_mine") is not None:
            params["lh_mine_word"] = _plural_uk(
                params["lh_mine"], "добивання", "добивання", "добивань"
            )
    if lang == "uk":
        if params.get("count") is not None:
            params["count_deaths"] = _plural_uk(params["count"], "смерть", "смерті", "смертей")
            params["count_times"] = _plural_uk(params["count"], "раз", "рази", "разів")
        if params.get("deaths") is not None:
            params["deaths_word"] = _plural_uk(params["deaths"], "смерть", "смерті", "смертей")
        if params.get("last_hits") is not None:
            params["last_hits_word"] = _plural_uk(
                params["last_hits"], "добивання", "добивання", "добивань"
            )
        if params.get("minutes") is not None:
            params["minutes_word"] = _plural_uk(params["minutes"], "хвилину", "хвилини", "хвилин")
        if params.get("runes") is not None:
            params["runes_word"] = _plural_uk(params["runes"], "руну", "руни", "рун")
        if params.get("stacks") is not None:
            params["stacks_word"] = _plural_uk(params["stacks"], "стак", "стаки", "стаків")
        # A fraction in a Ukrainian sentence is «2,5», not «2.5» (the texts only
        # print the values; the finding keeps its numbers).
        for key, value in list(params.items()):
            if isinstance(value, float) and not value.is_integer():
                params[key] = str(value).replace(".", ",")
    return params


class _SafeDict(dict):
    def __getitem__(self, key: str) -> Any:
        value = super().__getitem__(key)
        return "—" if value is None else value

    def __missing__(self, key: str) -> str:
        return "—"


def _advice_text(text: Any, lang: str) -> str:
    value = str(text or "")
    if lang != "uk" or not value:
        return value
    return translate_uk(value) or value


def render_finding(finding: dict[str, Any], lang: str) -> dict[str, Any]:
    lang = "uk" if lang == "uk" else "en"
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
    """Copy of a stored analysis with titles/texts in `lang` (uk or en)."""
    lang = "uk" if lang == "uk" else "en"
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
