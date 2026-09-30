"""
advice_why.py - «Почему этот совет?»: one plain sentence per decision point
saying what the coach saw in the game when it gave the advice.

The advice card says what to do; this says what triggered it, so a player can
tell a real danger from a routine reminder. Shown under the recent advice on
Home (/advice/recent `why`) and in the review's advice log (render_analysis).
Texts follow the rules in decision_points.detect_decision_point; unknown
decision points get no sentence rather than a guess.
"""

from __future__ import annotations

WHY: dict[str, dict[str, str]] = {
    "LOW_HP": {
        "ru": "Здоровья осталось совсем мало: одна атака или заклинание — и смерть.",
        "en": "Your health was very low: one more hit or spell could kill you.",
    },
    "LOW_HP_WARNING": {
        "ru": "Здоровье опустилось к опасной для вашего героя отметке — ещё не смертельно, но лучше подлечиться заранее.",
        "en": "Your health dropped to a risky level for your hero: not deadly yet, but better to heal before it is.",
    },
    "RECENT_DAMAGE_WARNING": {
        "ru": "За последние 10 секунд вы потеряли пятую часть здоровья и больше — похоже, на вас напали.",
        "en": "You lost a fifth of your health or more in the last 10 seconds: someone is hitting you.",
    },
    "OVERSTAY_WARNING": {
        "ru": "Вы недавно получили урон и остались на месте с половиной здоровья — так чаще всего и умирают.",
        "en": "You took damage recently and stayed where you were with half health: that is how most deaths start.",
    },
    "DISABLED_STATUS": {
        "ru": "На вас контроль — оглушение, превращение, безмолвие, немота, разоружение или отключение способностей: важно знать, что можно нажать сейчас, а что — сразу после.",
        "en": "You were under a disable — stun, hex, silence, mute, disarm or break: it matters what you can press now and what the moment it ends.",
    },
    "HERO_SURVIVABILITY_RISK": {
        "ru": "Ваш герой легко погибает, а здоровья или маны мало либо рядом драка.",
        "en": "Your hero dies easily, and health or mana was low or a fight was near.",
    },
    "ABILITY_SAFETY_COOLDOWN": {
        "ru": "Ваше умение для побега или защиты ещё перезаряжается — без него рисковать нельзя.",
        "en": "Your escape or defensive ability was on cooldown: without it, risks cost more.",
    },
    "BAD_FIGHT_RISK": {
        "ru": "Рядом идёт или только что была драка — в такой момент легко отдать лишнюю смерть, если лезть без выгоды.",
        "en": "A fight was going on or had just happened near you: an easy moment to give away a death if you join without an edge.",
    },
    "OBJECTIVE_FIGHT_CHECK": {
        "ru": "Рядом башня, Рошан или другая цель — важно решить, идти за ней вместе с командой или нет.",
        "en": "A tower, Roshan or another objective was near: time to decide whether to go for it with your team.",
    },
    "ITEM_TIMING": {
        "ru": "Вы только что собрали важный предмет — с ним у героя появляется окно силы.",
        "en": "You just finished a key item: your hero has a window of power with it.",
    },
    "LOW_MANA": {
        "ru": "Маны меньше пятой части — в драке не хватит на заклинания.",
        "en": "Your mana was under a fifth: not enough for your spells in a fight.",
    },
    "LANING_FARM_CHECK": {
        "ru": "Добиваний на линии меньше, чем обычно у вашего героя к этой минуте.",
        "en": "You had fewer last hits in lane than usual for your hero at this minute.",
    },
    "LANING_REGEN_CHECK": {
        "ru": "На линии здоровье заметно просело — пора подлечиться, пока враги этим не воспользовались.",
        "en": "Your health dropped in lane: time to heal before the enemies use it.",
    },
    "SMOKED_STATUS": {
        "ru": "Вы под Smoke of Deceit: вас не видно, пока вы не подойдёте к врагу близко.",
        "en": "You were under Smoke of Deceit: enemies cannot see you until you get close.",
    },
    "FARMING_PHASE_PRESSURE": {
        "ru": "Золота и добиваний меньше, чем нужно к этой минуте, — фарм отстаёт.",
        "en": "Your gold and last hits were behind the pace for this minute.",
    },
    "SOFT_STATUS": {
        "ru": "Ничего срочного — спокойная подсказка по ходу линии.",
        "en": "Nothing urgent: a calm tip for the laning stage.",
    },
    "SAFE_FARMING": {
        "ru": "Ничего срочного — подсказка, как фармить безопаснее.",
        "en": "Nothing urgent: a tip on farming more safely.",
    },
    "BUYBACK_AVAILABLE": {
        "ru": "Вы мертвы, рядом важная драка или цель, и на выкуп хватает золота.",
        "en": "You were dead, a key fight or objective was near, and you had gold for a buyback.",
    },
    "DEATH_REVIEW": {
        "ru": "Вы умерли — пока ждёте возрождения, самое время понять почему.",
        "en": "You died: waiting to respawn is the time to see why.",
    },
    "DEATH_WITH_ESCAPE_ON_COOLDOWN": {
        "ru": "Вы умерли, когда умение для побега ещё перезаряжалось.",
        "en": "You died while your escape ability was on cooldown.",
    },
    "DEATH_LOW_RESOURCE": {
        "ru": "Вы умерли с малым запасом здоровья или маны ещё до драки.",
        "en": "You died after going into the fight with little health or mana.",
    },
    "REPEATED_DEATH_PATTERN": {
        "ru": "Вы умираете уже не первый раз за короткое время — стоит сменить подход.",
        "en": "You died more than once in a short time: time to change the approach.",
    },
    "DEAD_WAIT": {
        "ru": "Вы мертвы: время до возрождения можно потратить с пользой.",
        "en": "You were dead: the time until respawn can still be used.",
    },
}


def why(decision_point: object, lang: str) -> str | None:
    """The sentence for a decision point in `lang` (ru or en), or None."""
    texts = WHY.get(str(decision_point or ""))
    if not texts:
        return None
    return texts["ru" if lang == "ru" else "en"]
