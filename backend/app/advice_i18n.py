"""
advice_i18n.py - Russian wording for the advice text the player sees.

The advice pipeline (decision points, recommender, scheduler, UX policy) stays
English: logs, session history, recordings and tests keep the canonical text.
Translation happens only at the API edge, when the overlay or the launcher asks
for ``lang=ru`` (``/overlay/recommendation``, ``/advice/recent``).

Only the visible fields are translated: ``recommendation.action``,
``recommendation.reason``, ``message`` and ``last_visible_advice``. A text with
no known translation is returned unchanged (English), never half-translated.
Ability and hero names stay as the backend sends them.

When you add or change a visible advice string anywhere in the pipeline, add
its Russian here too; ``tests/test_advice_i18n.py`` replays the fixtures and
fails on any visible text without a translation.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any

DEFAULT_LANG = "en"

_RU_EXACT: dict[str, str] = {
    "Your bounty grows with the streak: farm near your team and skip dark, unwarded areas.": (
        "За вас дают всё больше золота: фармите рядом с командой и не ходите в тёмные места "
        "без вардов."
    ),
    "The enemy has items first now; trade risky farm for safe farm until your key item.": (
        "У врагов предметы раньше: меняйте рискованный фарм на безопасный до вашего ключевого "
        "предмета."
    ),
    "A kill lead fades unless it turns into towers and map control.": (
        "Преимущество по убийствам тает, если не превратить его в башни и контроль карты."
    ),
    # --- actions -------------------------------------------------------------
    "After respawn, avoid committing forward until your escape is ready.": (
        "После возрождения не лезьте вперёд, пока не готова способность для побега."
    ),
    "After respawn, reset earlier when HP or key resources get low.": (
        "После возрождения уходите раньше, когда HP или ключевые ресурсы на исходе."
    ),
    "After respawn, reset your route and avoid repeating the same risky path.": (
        "После возрождения смените маршрут и не повторяйте тот же опасный путь."
    ),
    "After this item pickup, reassess whether to farm safely or pressure with your team.": (
        "С новым предметом решите заново: фармить безопасно или давить вместе с командой."
    ),
    "Avoid risky trades until your defensive tool is ready.": (
        "Избегайте рискованных разменов, пока не готова защитная способность."
    ),
    "Avoid the pressured lane and farm a safer wave or nearby camp.": (
        "Уйдите с линии, где давят, и фармите более безопасную волну или ближний лагерь."
    ),
    "Avoid this fight and reset to safer farm.": (
        "Не идите в эту драку, вернитесь к безопасному фарму."
    ),
    "Avoid this fight and move to safer farm.": (
        "Не идите в эту драку, перейдите на более безопасный фарм."
    ),
    "Avoid the fight and keep farming safely.": "Пропустите драку и продолжайте спокойно фармить.",
    "Avoid contesting pressure and move to safer farm.": (
        "Не спорьте с давлением, перейдите на более безопасный фарм."
    ),
    "Back up and stabilize before trading again.": (
        "Отойдите и восстановитесь, прежде чем снова размениваться."
    ),
    "Back up slightly, secure safe last hits, then reset your HP.": (
        "Отойдите немного, заберите безопасные добивания, потом восстановите HP."
    ),
    "Back up, stabilize HP, then return to the wave.": (
        "Отойдите, восстановите HP и возвращайтесь к волне."
    ),
    "Buyback is available. Only consider it for critical defense.": (
        "Байбэк доступен. Используйте его только для критической защиты."
    ),
    "Check buyback value only for base defense or a major objective.": (
        "Байбэк оправдан только для защиты базы или важной цели."
    ),
    "Conserve mana or reset before taking a fight.": (
        "Берегите ману или восстановитесь перед дракой."
    ),
    "Consider joining only if your team is ready and the fight is near the objective.": (
        "Присоединяйтесь, только если команда готова и драка идёт у ключевой цели."
    ),
    "Consider joining only if the fight is near the objective.": (
        "Присоединяйтесь, только если драка идёт у ключевой цели."
    ),
    "Consider joining only if your team is ready around the objective.": (
        "Присоединяйтесь, только если команда уже собралась у ключевой цели."
    ),
    "Consider a safer, lower-risk play.": "Выберите более безопасный вариант с меньшим риском.",
    "Consider playing safely.": "Играйте осторожнее.",
    "Consider monitoring lane — no urgent advice.": "Следим за линией — срочных советов нет.",
    "Do not overstay on low HP; reset or play behind creeps.": (
        "Не задерживайтесь на низком HP: отойдите или играйте за крипами."
    ),
    "Do not show deep until enemy positions are clearer.": (
        "Не заходите вглубь карты, пока не ясно, где враги."
    ),
    "Farm the safer part of the lane and avoid long trades.": (
        "Фармите на безопасной части линии и избегайте долгих разменов."
    ),
    "Farm closer to a safer zone until enemy positions are clearer.": (
        "Фармите ближе к безопасной зоне, пока не ясно, где враги."
    ),
    "Focus on safe last hits before forcing trades.": (
        "Сначала безопасные добивания, размены — потом."
    ),
    "Focus on safe last hits before moving to nearby camps.": (
        "Заберите безопасные добивания, потом идите на ближние лагеря."
    ),
    "Focus on safe last hits in the next wave.": (
        "В следующей волне сосредоточьтесь на безопасных добиваниях."
    ),
    "Focus on safe last hits.": "Сосредоточьтесь на безопасных добиваниях.",
    "Keep farming safely and reassess in 60 seconds.": (
        "Продолжайте спокойно фармить, через минуту оцените ситуацию снова."
    ),
    "Keep farming safely in lane and focus on last hits.": (
        "Спокойно фармите на линии и следите за добиваниями."
    ),
    "Keep farming safely in lane.": "Спокойно фармите на линии.",
    "Keep farming safely until the next wave.": "Спокойно фармите до следующей волны.",
    "Keep farming safely.": "Продолжайте спокойно фармить.",
    "Keep farming the safest wave-and-camp route and reassess soon.": (
        "Фармите по самому безопасному маршруту из волн и лагерей, скоро оцените ситуацию снова."
    ),
    "Keep your farm rhythm and avoid low-value trades.": (
        "Держите темп фарма и избегайте бесполезных разменов."
    ),
    "Leave the wave now and reset HP before rejoining.": (
        "Уходите с волны сейчас и восстановите HP, прежде чем вернуться."
    ),
    "Maintain steady farm.": "Держите ровный темп фарма.",
    "Monitoring lane — no urgent advice.": "Следим за линией — срочных советов нет.",
    "Move closer to a safer farming zone before showing on the wave.": (
        "Перед выходом на волну сместитесь ближе к безопасной зоне фарма."
    ),
    "Move closer to a safer lane area before contesting the next wave.": (
        "Перед следующей волной сместитесь в более безопасную часть линии."
    ),
    "No urgent action.": "Срочных действий не нужно.",
    "No urgent decision is needed.": "Срочных решений не нужно.",
    "Only consider the objective if your team is already grouped nearby.": (
        "Идите к цели, только если команда уже собралась рядом."
    ),
    "Go back to farming: take the nearest safe wave or camp now.": (
        "Вернитесь к фарму: заберите ближайшую безопасную волну или лагерь."
    ),
    "You have taken almost no last hits lately; every minute without farm delays your next item.": (
        "В последнее время почти нет добиваний: каждая минута без фарма отодвигает следующий предмет."
    ),
    "Medium risk if you keep walking around without farming.": (
        "Средний риск, если продолжать ходить по карте без фарма."
    ),
    "Farm back your buyback gold before the next purchase.": (
        "Нафармите золото на байбэк, прежде чем покупать дальше."
    ),
    "After minute 30 one death without buyback can decide the game.": (
        "После 30-й минуты одна смерть без байбэка может решить игру."
    ),
    "High risk if you die before the buyback gold is back.": (
        "Высокий риск, если умрёте раньше, чем вернёте золото на байбэк."
    ),
    "Recover farm through the safest wave-and-camp route.": (
        "Навёрстывайте фарм по самому безопасному маршруту из волн и лагерей."
    ),
    "A silence does not stop items: get rid of it before the next spell lands.": (
        "Немота не мешает предметам: снимите её до следующего заклинания."
    ),
    "Reset HP before showing on another lane.": (
        "Восстановите HP, прежде чем появляться на другой линии."
    ),
    "Reset mana before taking an extended fight.": "Восстановите ману перед затяжной дракой.",
    "Reset resources before showing on another lane.": (
        "Восстановите ресурсы, прежде чем появляться на другой линии."
    ),
    "Respect your hero's safety window before forcing a fight.": (
        "Не навязывайте драку, пока защитные способности героя не готовы."
    ),
    "Retreat and reset before rejoining.": "Отступите и восстановитесь, прежде чем вернуться.",
    "Secure the next wave first and avoid trading unless it protects last hits.": (
        "Сначала заберите следующую волну; размениваться — только чтобы защитить добивания."
    ),
    "Stay hidden until your team is ready to make a move.": (
        "Не показывайтесь, пока команда не готова действовать."
    ),
    "Stop re-contesting the pressured lane until you reset HP.": (
        "Не возвращайтесь на линию, где давят, пока не восстановите HP."
    ),
    "Take only the safe creeps and avoid extending the trade.": (
        "Добивайте только безопасных крипов и не затягивайте размен."
    ),
    "Take safe creeps, then rotate to safer farm if pressure continues.": (
        "Заберите безопасных крипов; если давят дальше — уходите на более безопасный фарм."
    ),
    "Use regen or play back until your HP is safer.": (
        "Используйте реген или отойдите, пока HP не восстановится."
    ),
    "Unspent gold is partly lost on the next death; "
    "then choose a safer route than the one you died on.": (
        "Непотраченное золото частично теряется при следующей смерти. Потом выберите "
        "маршрут безопаснее того, где вас поймали."
    ),
    "Keep a TP scroll in its slot: buy one now, the courier can bring it.": (
        "Держите свиток телепортации в слоте: купите его сейчас, курьер принесёт."
    ),
    "Without a TP scroll you cannot join a fight or save a tower in time.": (
        "Без свитка телепортации не успеете ни в драку, ни спасти башню."
    ),
    "Medium risk if a fight starts across the map while you have no TP.": (
        "Средний риск, если драка начнётся на другом конце карты, а свитка телепортации нет."
    ),
    "Use the respawn time to choose a safer farming route.": (
        "Пока ждёте возрождения, выберите более безопасный маршрут фарма."
    ),
    "Use the respawn time to plan a safer next route.": (
        "Пока ждёте возрождения, продумайте более безопасный маршрут."
    ),
    "Use the respawn time to plan your next safe farming route.": (
        "Пока ждёте возрождения, продумайте следующий безопасный маршрут фарма."
    ),
    "Wait out the disable and avoid forcing actions.": (
        "Переждите контроль и не делайте резких действий."
    ),
    "You reached a timing; reassess whether to pressure or keep farming safely.": (
        "Вы вышли на тайминг: решите заново, давить или спокойно фармить дальше."
    ),
    "You reached a damage timing; consider objective fights, not low-value skirmishes.": (
        "Тайминг по урону: ищите драки за ключевые цели, а не случайные стычки."
    ),
    "You reached a defensive timing; consider fighting only around objectives or with team support.": (
        "Защитный тайминг: деритесь только у ключевых целей или вместе с командой."
    ),
    "You reached a farming timing; increase farm speed and avoid unnecessary deaths.": (
        "Тайминг по фарму: ускорьте фарм и не умирайте зря."
    ),
    "You reached a late-game timing; prioritize high-value objectives and safe positioning.": (
        "Тайминг поздней игры: в приоритете важные цели и безопасная позиция."
    ),
    "You reached a mobility timing; look for safer map movement, not random fights.": (
        "Тайминг мобильности: перемещайтесь по карте безопаснее, не ищите случайных драк."
    ),
    "Your farm pace is behind; move to safer, higher-value farm.": (
        "Вы отстаёте по фарму: переходите на более безопасный и выгодный фарм."
    ),
    # --- reasons -------------------------------------------------------------
    "A short reset keeps the next farming route safer without forcing a fight.": (
        "Короткий отход делает следующий маршрут фарма безопаснее без лишней драки."
    ),
    "A meaningful item can change your next decision, but avoid forcing low-value fights.": (
        "Важный предмет может изменить план, но не навязывайте бесполезные драки."
    ),
    "At this HP, one more spell or rotation can turn into a death.": (
        "С таким HP ещё одна способность или ганг могут закончиться смертью."
    ),
    "At this HP, one more trade or spell can kill you.": (
        "С таким HP ещё один размен или способность могут вас убить."
    ),
    "Avoid returning to the same risky area without vision or team support.": (
        "Не возвращайтесь в ту же опасную зону без обзора или поддержки команды."
    ),
    "Avoid rushing back into the same risky area.": (
        "Не бегите сразу обратно в ту же опасную зону."
    ),
    "Current lane state does not need a full coaching card.": (
        "Ситуация на линии не требует отдельной подсказки."
    ),
    "Enemy pressure is active, and a low-value fight can delay your next timing.": (
        "Враги давят, и бесполезная драка отодвинет ваш следующий тайминг."
    ),
    "Enemy pressure is active. A low-value fight or death delays your next timing.": (
        "Враги давят. Бесполезная драка или смерть отодвинет ваш следующий тайминг."
    ),
    "Enemy locations are not confirmed, so exposed farming is unnecessary risk.": (
        "Где враги — неизвестно, поэтому фарм на открытом месте — лишний риск."
    ),
    "HP is critical; one more trade or spell can kill you.": (
        "HP критически низкое: ещё один размен или способность могут вас убить."
    ),
    "HP is low enough that another trade can become dangerous.": (
        "HP так мало, что следующий размен может быть опасен."
    ),
    "HP is stable and no pressure signal is active.": "HP в норме, признаков давления нет.",
    "Improving farm rate is safer than forcing a low-value fight.": (
        "Ускорить фарм безопаснее, чем навязывать бесполезную драку."
    ),
    "Low health makes extra action too risky.": "С низким HP лишние действия слишком рискованны.",
    "Low lane HP makes trades and last hits risky.": (
        "С низким HP на линии размены и добивания рискованны."
    ),
    "Low mana limits escape, spell usage, and fight impact.": (
        "Мало маны: хуже с побегом, способностями и пользой в драке."
    ),
    "Multiple recent deaths can delay your next timing more than missing one wave or camp.": (
        "Несколько смертей подряд отодвинут тайминг сильнее, чем пропущенная волна или лагерь."
    ),
    "Objective fights can be valuable, but the replay does not confirm team readiness.": (
        "Драки за цели бывают выгодны, но по реплею не видно, готова ли команда."
    ),
    "Objective fights can be valuable, but avoid forcing them without team support.": (
        "Драки за цели бывают выгодны, но не навязывайте их без поддержки команды."
    ),
    "Objectives can be worth joining, but random skirmishes are not.": (
        "За ключевые цели драться стоит, за случайные стычки — нет."
    ),
    "Objectives can be worth joining, but avoid forcing a fight without team support.": (
        "За ключевые цели драться стоит, но не навязывайте драку без поддержки команды."
    ),
    "Pressure is active while HP is not comfortable.": "Враги давят, а запаса HP уже нет.",
    "Pressure is active, but HP is still high enough for conservative farming.": (
        "Враги давят, но HP хватает для осторожного фарма."
    ),
    "Pressure plus reduced HP can turn the next trade into a death.": (
        "Давление и неполное HP: следующий размен может закончиться смертью."
    ),
    "Reduced HP plus lane pressure can turn one more trade into a death.": (
        "Неполное HP и давление на линии: ещё один размен может закончиться смертью."
    ),
    "Repeated low-HP returns can cost more than missing one wave.": (
        "Раз за разом возвращаться с низким HP дороже, чем пропустить одну волну."
    ),
    "Returning to the same pressured area can repeat the same death pattern.": (
        "Вернувшись в ту же опасную зону, можно умереть так же, как в прошлый раз."
    ),
    "Revealing on a wave can waste the smoke timing.": (
        "Если показаться на волне, смок пропадёт зря."
    ),
    "Staying exposed after a bad trade often leads to a preventable death.": (
        "Если остаться на виду после неудачного размена, легко умереть зря."
    ),
    "Staying in pressure can cost HP and slow your recovery.": (
        "Под давлением вы теряете HP и дольше восстанавливаетесь."
    ),
    "Stabilizing farm is safer than taking low-value damage.": (
        "Выровнять фарм безопаснее, чем получать урон впустую."
    ),
    "The fight looks risky and may delay your next timing.": (
        "Драка выглядит рискованной и может отодвинуть ваш тайминг."
    ),
    "The item improves your options, but missing cooldown and team context means the safer choice still depends on nearby pressure.": (
        "Предмет даёт больше вариантов, но без данных о кулдаунах и команде "
        "безопасный выбор зависит от давления рядом."
    ),
    "The previous fight became risky because your survivability resource was low.": (
        "Прошлая драка стала опасной: ресурсы для выживания были на исходе."
    ),
    "There is no clear threat, objective, or timing decision right now.": (
        "Сейчас нет явной угрозы, цели или тайминга."
    ),
    "No urgent threat or objective is forcing action. Build resources safely.": (
        "Ни угроз, ни целей, требующих действий. Спокойно набирайте ресурсы."
    ),
    "This reduces risk while keeping your carry game stable.": (
        "Так меньше риска, а игра остаётся стабильной."
    ),
    "Use it only if your team is defending a critical objective or the game could be decided now.": (
        "Только если команда защищает важную цель или игра решается прямо сейчас."
    ),
    "You are behind on farm and under lane pressure; forcing a trade can cost both HP and last hits.": (
        "Вы отстаёте по фарму и на линии давят: размен может стоить и HP, и добиваний."
    ),
    "You are behind on farm, so forcing fights before stabilizing can delay your next timing.": (
        "Вы отстаёте по фарму: драки до того, как выровняетесь, отодвинут тайминг."
    ),
    "You are still behind on farm, and staying in pressure can cost both HP and timing.": (
        "Вы всё ещё отстаёте по фарму, а под давлением теряете и HP, и тайминг."
    ),
    "You are controlled; surviving the next seconds matters more than dealing damage.": (
        "Вы под контролем: выжить в ближайшие секунды важнее, чем нанести урон."
    ),
    "You are under pressure but still have enough HP to keep farming if you stay conservative.": (
        "На вас давят, но HP хватает, чтобы осторожно фармить дальше."
    ),
    "You died after your key escape or defensive tool was unavailable.": (
        "Вы умерли, когда способность для побега или защиты была недоступна."
    ),
    "You took heavy damage recently, so another trade can turn into a death.": (
        "Вы недавно получили много урона: следующий размен может закончиться смертью."
    ),
    "Your farm pace is behind for this minute, but HP is stable, so the fastest recovery is clean last hitting.": (
        "Для этой минуты фарма мало, но HP в норме — быстрее всего догнать чистыми добиваниями."
    ),
    "Your farm pace is stable now, so keep using safe routes instead of forcing uncertain fights.": (
        "Темп фарма выровнялся: держитесь безопасных маршрутов и не лезьте в сомнительные драки."
    ),
    "Your farm route is the safest low-risk choice while enemy locations are uncertain.": (
        "Пока неизвестно, где враги, ваш маршрут фарма — самый безопасный вариант."
    ),
    "Your position is exposed and the replay does not confirm where enemies are.": (
        "Вы на открытой позиции, а по реплею не видно, где враги."
    ),
    "Your position is exposed and enemy locations are not confirmed.": (
        "Вы на открытой позиции, а где враги — неизвестно."
    ),
    "Your position is risky and enemy locations are not confirmed.": (
        "Позиция опасная, а где враги — неизвестно."
    ),
    "Your hero is easier to punish while this safety tool is unavailable.": (
        "Пока защитная способность недоступна, вашего героя легче наказать."
    ),
    "Your key defensive resource is unavailable, so a bad fight is harder to escape.": (
        "Ключевой защитный ресурс недоступен: из неудачной драки будет трудно уйти."
    ),
    "Your lane progress is stable, so do not break it by taking unnecessary damage.": (
        "На линии всё ровно — не портите это лишним уроном."
    ),
    "Death detected, but context is limited.": "Смерть зафиксирована, но данных мало.",
    "Death followed a low HP or key resource state.": (
        "Смерть случилась при низком HP или нехватке ключевых ресурсов."
    ),
    "Death followed a state where a key escape or defensive tool was unavailable.": (
        "Смерть случилась, когда способность для побега или защиты была недоступна."
    ),
    "Death followed farming with limited team context; avoid repeating the same route.": (
        "Смерть случилась во время фарма вдали от команды; не повторяйте тот же маршрут."
    ),
    "Death happened around an objective context.": "Смерть случилась в драке у ключевой цели.",
    "Multiple recent deaths detected; reset the next route after respawn.": (
        "Несколько смертей подряд: после возрождения смените маршрут."
    ),
    "Position is far from your safe side, and enemy locations are not confirmed.": (
        "Вы далеко от своей безопасной стороны, а где враги — неизвестно."
    ),
    "Position is known, but team side is unknown; avoid assuming the area is safe.": (
        "Позиция известна, но сторона команды — нет; не считайте зону безопасной."
    ),
    "Position is lane-side, but enemy locations are not confirmed.": (
        "Вы у линии, но где враги — неизвестно."
    ),
    "Position is near central map areas; avoid assuming the area is safe.": (
        "Вы в центре карты — не считайте зону безопасной."
    ),
    "Position is on your side of the map; still avoid assuming enemies are absent.": (
        "Вы на своей половине карты, но враги всё равно могут быть рядом."
    ),
    "Position is unavailable.": "Позиция неизвестна.",
    # --- status messages -----------------------------------------------------
    "Monitoring...": "Следим за игрой…",
    "Waiting for live GSI...": "Ждём данные из игры…",
    "Take the safest waves and camps first: fights before that delay your next item.": (
        "Сначала самые безопасные волны и лагеря: драки до этого отложат следующий предмет."
    ),
    "Keep taking the safest waves and camps: this pace grows without risky fights.": (
        "Берите самые безопасные волны и лагеря: темп растёт и без рискованных драк."
    ),
    "Current hero is not supported by carry advisor yet.": (
        "Для этого героя советов пока нет: поддерживаются только керри."
    ),
}

# Texts with a hero or ability name inside. The name is kept as sent.
_RU_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(
            r"^Keep farming: (?P<gpm>\d+) gold per minute, (?P<lh>\d+) last hits at minute "
            r"(?P<m>\d+)\.$"
        ),
        "Фармите дальше: {gpm} золота в минуту, добиваний к {m}-й минуте: {lh}.",
    ),
    (
        re.compile(
            r"^No TP scroll for (?P<minutes>\d+) minutes?: without it you cannot join a fight "
            r"or save a tower in time\.$"
        ),
        "Без свитка телепортации уже {minutes} мин — не успеете ни в драку, ни спасти башню.",
    ),
    (
        re.compile(
            r"^Buy parts of your next item now with your (?P<gold>\d+) gold: "
            r"they wait for you at the fountain\.$"
        ),
        "Купите части следующего предмета на {gold} золота сейчас — заберёте их у фонтана.",
    ),
    (
        re.compile(
            r"^Buy parts of your next item with (?P<spare>\d+) gold "
            r"and keep (?P<cost>\d+) for buyback\.$"
        ),
        "Купите части следующего предмета на {spare} золота, а {cost} оставьте на байбэк.",
    ),
    (
        re.compile(r"^Avoid committing forward until (?P<name>.+) is ready\.$"),
        "Не лезьте вперёд до готовности {name}.",
    ),
    (
        re.compile(r"^Avoid risky trades until (?P<name>.+) is ready\.$"),
        "Избегайте рискованных разменов до готовности {name}.",
    ),
    (
        re.compile(r"^Without (?P<name>.+), disables and slows are harder to avoid\.$"),
        "Без {name} труднее избежать контроля и замедлений.",
    ),
    (
        re.compile(r"^Without (?P<name>.+), escaping a bad trade or fight is harder\.$"),
        "Без {name} сложнее выйти из неудачного размена или драки.",
    ),
    (
        re.compile(r"^(?P<name>.+) is unavailable, so committing forward is risky\.$"),
        "Без {name} идти вперёд рискованно.",
    ),
    (
        re.compile(r"^(?P<name>.+) is unavailable, so your hero is easier to punish\.$"),
        "Без {name} вашего героя легче наказать.",
    ),
    (
        re.compile(
            r"^Only (?P<lh>\d+) last hits? in the last (?P<m>\d+) minutes; "
            r"every minute without farm delays your next item\.$"
        ),
        "Добиваний за последние {m} мин: {lh}. Каждая минута без фарма отодвигает следующий предмет.",
    ),
    (
        re.compile(
            r"^You have (?P<gold>\d+) gold and buyback costs (?P<cost>\d+); "
            r"after minute 30 one death without buyback can decide the game\.$"
        ),
        "Золота {gold}, байбэк стоит {cost}. После 30-й минуты одна смерть без байбэка "
        "может решить игру.",
    ),
    (
        re.compile(
            r"^Recover farm: (?P<lh>\d+) last hits at minute (?P<m>\d+), a good pace is "
            r"(?P<low>\d+)\+\.$"
        ),
        "Навёрстывайте фарм: добиваний к {m}-й минуте — {lh}, хороший темп — {low}+.",
    ),
    # live_tools.py: the hero's own abilities and their cooldowns.
    (
        re.compile(r"^Use (?P<name>.+) now: a mute blocks items, not spells\.$"),
        "Используйте {name} сейчас: немота мешает предметам, а не способностям.",
    ),
    (
        re.compile(r"^Use (?P<name>.+) now and walk out of the fight\.$"),
        "Используйте {name} сейчас и выходите из драки.",
    ),
    (
        re.compile(r"^(?P<name>.+) is ready: it buys you the seconds to get away\.$"),
        "{name} уже можно нажать: это даст секунды, чтобы уйти.",
    ),
    (
        re.compile(
            r"^(?P<name>.+) is back in (?P<n>\d+) s: without it, escaping a bad trade "
            r"or fight is harder\.$"
        ),
        "{name} откатится через {n} с: без него сложнее уйти из неудачного размена или драки.",
    ),
    (
        re.compile(
            r"^(?P<name>.+) is back in (?P<n>\d+) s: until then, disables and slows "
            r"are harder to avoid\.$"
        ),
        "{name} откатится через {n} с: до этого сложнее избежать контроля и замедлений.",
    ),
    # live_tools.py: the tool that is ready right now.
    (
        re.compile(r"^Use (?P<name>.+) now to get out, then reset HP\.$"),
        "Используйте {name} сейчас, чтобы уйти, потом восстановите HP.",
    ),
    (
        re.compile(
            r"^Your HP is low and (?P<name>.+) is ready: use it before the next hit, not after\.$"
        ),
        "HP мало, а {name} готов: нажмите его до следующего удара, а не после.",
    ),
    (
        re.compile(r"^Use (?P<name>.+) now, then step back\.$"),
        "Нажмите {name} сейчас и отойдите.",
    ),
    (
        re.compile(r"^Magic Wand has (?P<n>\d+) charges: that HP is yours right now\.$"),
        "В Magic Wand {n} зарядов: это HP можно получить прямо сейчас.",
    ),
    (
        re.compile(r"^(?P<name>Magic Wand) is charged: that HP is yours right now\.$"),
        "{name} заряжен: это HP можно получить прямо сейчас.",
    ),
    (
        re.compile(r"^(?P<name>.+) is ready and heals you at once\.$"),
        "{name} готов и лечит сразу.",
    ),
    (
        re.compile(r"^(?P<name>.+) heals you at once\.$"),
        "{name} лечит сразу.",
    ),
    (
        re.compile(r"^Step out of enemy range and use (?P<name>.+)\.$"),
        "Отойдите туда, где враг не достанет, и используйте {name}.",
    ),
    (
        re.compile(r"^(?P<name>.+) heals over time: use it where enemies cannot hit you\.$"),
        "{name} лечит постепенно: используйте там, где вас не достанут.",
    ),
    (
        re.compile(r"^Use (?P<name>.+) now: it removes the silence\.$"),
        "Нажмите {name} сейчас: он снимает немоту.",
    ),
    (
        re.compile(r"^The moment the disable ends, use (?P<name>.+)\.$"),
        "Как только контроль закончится, сразу нажмите {name}.",
    ),
    (
        re.compile(
            r"^(?P<name>.+) is ready: the second after a disable is when most kills finish\.$"
        ),
        "{name} готов: чаще всего добивают в первую секунду после контроля.",
    ),
    (
        re.compile(r"^You died with (?P<name>.+) ready: next time use it at the first big hit\.$"),
        "Вы погибли с готовым {name}: в следующий раз нажмите его при первом сильном ударе.",
    ),
    (
        re.compile(r"^Use your gold: (?P<name>.+) can be bought now\.$"),
        "Потратьте золото: {name} уже можно купить.",
    ),
    (
        re.compile(
            r"^Its missing parts cost (?P<left>\d+) gold and you have (?P<spare>\d+) "
            r"beyond your buyback\.$"
        ),
        "Недостающие части стоят {left} золота, у вас {spare} сверх байбэка.",
    ),
    (
        re.compile(r"^Its missing parts cost (?P<left>\d+) gold and you have (?P<spare>\d+)\.$"),
        "Недостающие части стоят {left} золота, у вас {spare}.",
    ),
    (
        re.compile(r"^Keep farming toward (?P<name>.+) on the safest waves and camps\.$"),
        "Фармите на {name} на самых безопасных волнах и лагерях.",
    ),
    (
        re.compile(
            r"^(?P<name>.+) is next in most builds: (?P<need>\d+) gold to go, "
            r"about (?P<m>\d+) minutes? at your (?P<gpm>\d+) gold per minute\.$"
        ),
        "{name} — следующий предмет в большинстве сборок: не хватает {need} золота, "
        "это около {m} мин при {gpm} золота в минуту.",
    ),
    (
        re.compile(r"^(?P<name>.+) is next in most builds: (?P<need>\d+) gold to go\.$"),
        "{name} — следующий предмет в большинстве сборок: не хватает {need} золота.",
    ),
    (
        re.compile(r"^Low mana reduces (?P<name>.+)'s effective survivability\.$"),
        "У {name} мало маны — выживаемость заметно ниже.",
    ),
    (
        re.compile(r"^(?P<name>.+) is low on mana, so effective survivability is reduced\.$"),
        "У {name} мало маны — выживаемость заметно ниже.",
    ),
)

# Death places (live_tools.death_copy): Russian needs the zone in a case, so
# these render with a function instead of a format template.
_ZONE_FROM = {
    "top lane": "от верхней линии",
    "mid lane": "от центральной линии",
    "bottom lane": "от нижней линии",
    "jungle": "от леса",
}
_ZONE_IN = {
    "top lane": "на верхней линии",
    "mid lane": "на центральной линии",
    "bottom lane": "на нижней линии",
    "jungle": "в лесу",
}
_ZONE_TO = {
    "top lane": "на верхнюю линию",
    "mid lane": "на центральную линию",
    "bottom lane": "на нижнюю линию",
    "jungle": "в лес",
}
_SIDE = {
    "on your side": "на своей половине",
    "by the river": "у реки",
    "on the enemy side": "на половине врага",
}
_ZONE_RE = "(?P<zone>top lane|mid lane|bottom lane|jungle)"
_SIDE_RE = "(?P<side>on your side|by the river|on the enemy side)"


def _deaths_word(count: int) -> str:
    if count % 10 == 1 and count % 100 != 11:
        return "смерть"
    if 2 <= count % 10 <= 4 and not 12 <= count % 100 <= 14:
        return "смерти"
    return "смертей"


# The situational item's reason (post_laning_coach._situational_because) and
# the gold tail after it.
_SITUATIONAL_TAILS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"^\.$"), "."),
    (re.compile(r"^: (?P<need>\d+) gold to go\.$"), ": не хватает {need} золота."),
    (
        re.compile(
            r"^: (?P<need>\d+) gold to go, about (?P<m>\d+) minutes? at your (?P<gpm>\d+) "
            r"gold per minute\.$"
        ),
        ": не хватает {need} золота, это около {m} мин при {gpm} золота в минуту.",
    ),
    (
        re.compile(
            r"^; its missing parts cost (?P<left>\d+) gold and you have (?P<spare>\d+) "
            r"beyond your buyback\.$"
        ),
        "; недостающие части стоят {left} золота, у вас {spare} сверх байбэка.",
    ),
    (
        re.compile(r"^; its missing parts cost (?P<left>\d+) gold and you have (?P<spare>\d+)\.$"),
        "; недостающие части стоят {left} золота, у вас {spare}.",
    ),
)


def _kills_word(count: int) -> str:
    if count % 10 == 1 and count % 100 != 11:
        return "убийство"
    if 2 <= count % 10 <= 4 and not 12 <= count % 100 <= 14:
        return "убийства"
    return "убийств"


def _situational_reason(groups: dict[str, str]) -> str:
    count = int(groups["count"])
    if groups["kind"].startswith("under stuns"):
        head = (
            f"{count} {_deaths_word(count)} под контролем без единой свободной секунды — "
            f"{groups['name']} это исправит"
        )
    else:
        head = (
            f"{count} {_deaths_word(count)} за 3 секунды и быстрее с высокого здоровья — "
            f"{groups['name']} даст время это пережить"
        )
    for pattern, tail in _SITUATIONAL_TAILS:
        match = pattern.match(groups["tail"])
        if match:
            return head + tail.format(**match.groupdict())
    return ""


_RU_FUNCTIONS: tuple[tuple[re.Pattern[str], Callable[[dict[str, str]], str]], ...] = (
    (
        re.compile(r"^After respawn, change your route: (?P<n>\d+) deaths this game\.$"),
        lambda g: (
            f"После возрождения смените маршрут: {g['n']} {_deaths_word(int(g['n']))} за игру."
        ),
    ),
    (
        re.compile(
            r"^After respawn, change your route: (?P<n>\d+) deaths in the last (?P<m>\d+) "
            r"minutes?\.$"
        ),
        lambda g: (
            f"После возрождения смените маршрут: {g['n']} {_deaths_word(int(g['n']))} "
            f"за {g['m']} мин."
        ),
    ),
    (
        re.compile(
            r"^Your team is (?P<n>\d+) kills behind: farm your own half and fight near your "
            r"towers\.$"
        ),
        lambda g: (
            f"Команда отстаёт на {g['n']} {_kills_word(int(g['n']))}: фармите на своей половине "
            "и деритесь только у своих башен."
        ),
    ),
    (
        re.compile(
            r"^Your team is (?P<n>\d+) kills ahead: group up and take a tower instead of "
            r"farming alone\.$"
        ),
        lambda g: (
            f"Команда впереди на {g['n']} {_kills_word(int(g['n']))}: соберитесь и снесите "
            "башню, а не фармите в одиночку."
        ),
    ),
    (
        re.compile(r"^Stay alive: you are on a (?P<n>\d+)-kill streak\.$"),
        lambda g: f"Берегите себя: у вас серия из {g['n']} убийств подряд.",
    ),
    (
        re.compile(
            r"^(?P<count>\d+) deaths (?P<kind>under stuns with no free second|in 3 seconds or "
            r"less from high health), and (?P<name>.+?) (?:stops that|gives you time against "
            r"that)(?P<tail>(?:\.|: \d+ gold to go.*|; its missing parts cost.*))$"
        ),
        _situational_reason,
    ),
    (
        re.compile(rf"^After respawn, stay away from the {_ZONE_RE} {_SIDE_RE}\.$"),
        lambda g: (
            f"После возрождения держитесь подальше {_ZONE_FROM[g['zone']]} {_SIDE[g['side']]}."
        ),
    ),
    (
        re.compile(
            rf"^(?P<count>\d+) deaths in the {_ZONE_RE} {_SIDE_RE} in (?P<m>\d+) minutes?: "
            r"farm somewhere safer until your team is there\.$"
        ),
        lambda g: (
            f"{g['count']} {_deaths_word(int(g['count']))} {_ZONE_IN[g['zone']]} "
            f"{_SIDE[g['side']]} за {g['m']} мин: фармите в другом месте, пока там нет вашей команды."
        ),
    ),
    (
        re.compile(
            rf"^You died in the {_ZONE_RE} on the enemy side: "
            r"farm your own half until your team is with you\.$"
        ),
        lambda g: (
            f"Вы погибли {_ZONE_IN[g['zone']]} на половине врага: "
            "фармите на своей половине, пока команда не рядом."
        ),
    ),
    (
        re.compile(
            rf"^After respawn, farm your own half: you died in the {_ZONE_RE} on the enemy side\.$"
        ),
        lambda g: (
            "После возрождения фармите на своей половине: "
            f"вы погибли {_ZONE_IN[g['zone']]} на половине врага."
        ),
    ),
    (
        re.compile(
            r"^After respawn, play the (?P<zone>top lane|mid lane|bottom lane) closer to your "
            r"tower until you see the enemy heroes\.$"
        ),
        lambda g: (
            f"После возрождения играйте {_ZONE_IN[g['zone']]} ближе к своей башне, "
            "пока не увидите вражеских героев."
        ),
    ),
    (
        re.compile(
            rf"^After respawn, avoid the {_ZONE_RE} {_SIDE_RE} without your team: you died there\.$"
        ),
        lambda g: (
            f"После возрождения не ходите {_ZONE_TO[g['zone']]} {_SIDE[g['side']]} без команды: "
            "вы погибли там."
        ),
    ),
    (
        re.compile(
            r"^After respawn, stay near your towers or your team: "
            r"you went down in (?P<s>\d+) seconds? from high HP\.$"
        ),
        lambda g: (
            "После возрождения держитесь у своих башен или рядом с командой: "
            f"вас убили за {g['s']} с с высокого здоровья."
        ),
    ),
)

# advice_ux_policy rewords coaching-mode actions as "Consider: <action>" (older
# logs and history have "Consider <action>").
_CONSIDER_PREFIX = re.compile(r"^Consider:? (?P<rest>.+)$")
_SENTENCE_SPLIT = re.compile(r"(?<=[.;!?])\s+(?=[A-Z])")
_TRUNCATION = "..."


def normalize_lang(value: object) -> str:
    """Map "ru", "ru-RU", "RU" to "ru"; anything else is English."""
    return "ru" if str(value or "").strip().lower().startswith("ru") else DEFAULT_LANG


def _normalize(text: str) -> str:
    text = " ".join(text.split())
    # Two spellings of the same status line exist in the pipeline.
    return text.replace(" - ", " — ")


def _lower_first(text: str) -> str:
    return text[:1].lower() + text[1:] if text else text


def _translate_sentence(text: str) -> str | None:
    exact = _RU_EXACT.get(text)
    if exact is not None:
        return exact
    for pattern, template in _RU_PATTERNS:
        match = pattern.match(text)
        if match:
            return template.format(**match.groupdict())
    for pattern, render in _RU_FUNCTIONS:
        match = pattern.match(text)
        if match:
            return render(match.groupdict())
    return None


def _translate_consider(text: str) -> str | None:
    match = _CONSIDER_PREFIX.match(text)
    if not match:
        return None
    rest = match.group("rest")
    inner = _translate_sentence(rest[:1].upper() + rest[1:])
    return f"Подумайте: {_lower_first(inner)}" if inner else None


def _translate_truncated(text: str) -> str | None:
    # scheduler.text truncates long lines to "<prefix>..."; show the full
    # Russian line instead (the UI clamps long text itself).
    prefix = text[: -len(_TRUNCATION)].rstrip()
    if len(prefix) < 20:
        return None
    candidates = [source for source in _RU_EXACT if source.startswith(prefix)]
    return _RU_EXACT[candidates[0]] if len(candidates) == 1 else None


def translate_ru(text: str) -> str | None:
    """Russian for one visible advice text, or None when it is not known."""
    normalized = _normalize(text)
    if not normalized:
        return None
    result = _translate_sentence(normalized) or _translate_consider(normalized)
    if result is not None:
        return result
    if normalized.endswith(_TRUNCATION) and not normalized.endswith("...."):
        truncated = _translate_truncated(normalized)
        if truncated is not None:
            return truncated
    sentences = _SENTENCE_SPLIT.split(normalized)
    if len(sentences) > 1:
        parts = [
            _translate_sentence(sentence) or _translate_consider(sentence) for sentence in sentences
        ]
        if all(parts):
            return " ".join(part for part in parts if part)
    return None


def translate_text(text: Any, lang: str) -> Any:
    """Translate one visible text; unknown text and non-strings pass through."""
    if lang != "ru" or not isinstance(text, str):
        return text
    return translate_ru(text) or text


def _localize_advice_fields(item: Any, lang: str) -> Any:
    if not isinstance(item, dict):
        return item
    localized = dict(item)
    for key in ("action", "reason"):
        if key in localized:
            localized[key] = translate_text(localized[key], lang)
    return localized


def localize_overlay_response(response: dict[str, Any], lang: str) -> dict[str, Any]:
    """Copy of an /overlay/recommendation payload with visible text localized."""
    if lang != "ru":
        return response
    localized = dict(response)
    for key in ("recommendation", "last_visible_advice"):
        if key in localized:
            localized[key] = _localize_advice_fields(localized[key], lang)
    if "message" in localized:
        localized["message"] = translate_text(localized["message"], lang)
    localized["lang"] = lang
    return localized


def localize_advice_items(items: list[dict[str, Any]], lang: str) -> list[dict[str, Any]]:
    """Localize the action/reason of /advice/recent items."""
    if lang != "ru":
        return items
    return [_localize_advice_fields(item, lang) for item in items]
