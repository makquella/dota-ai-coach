"""
advice_why.py - «Чому ця порада?»: one plain sentence per decision point
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
        "uk": "Здоров'я лишилося зовсім мало: одна атака або закляття — і смерть.",
        "en": "Your health was very low: one more hit or spell could kill you.",
    },
    "LOW_HP_WARNING": {
        "uk": "Здоров'я опустилося до небезпечної для вашого героя позначки — ще не смертельно, але краще підлікуватися заздалегідь.",
        "en": "Your health dropped to a risky level for your hero: not deadly yet, but better to heal before it is.",
    },
    "RECENT_DAMAGE_WARNING": {
        "uk": "За останні 10 секунд ви втратили п'яту частину здоров'я й більше — схоже, на вас напали.",
        "en": "You lost a fifth of your health or more in the last 10 seconds: someone is hitting you.",
    },
    "OVERSTAY_WARNING": {
        "uk": "Ви нещодавно отримали шкоду й лишилися на місці з половиною здоров'я — саме так найчастіше й помирають.",
        "en": "You took damage recently and stayed where you were with half health: that is how most deaths start.",
    },
    "DISABLED_STATUS": {
        "uk": "На вас контроль — оглушення, перетворення, безмовність, німота, роззброєння або вимкнення здібностей: важливо знати, що можна натиснути зараз, а що — одразу після.",
        "en": "You were under a disable — stun, hex, silence, mute, disarm or break: it matters what you can press now and what the moment it ends.",
    },
    "HERO_SURVIVABILITY_RISK": {
        "uk": "Ваш герой легко гине, а здоров'я чи мани мало або поруч бійка.",
        "en": "Your hero dies easily, and health or mana was low or a fight was near.",
    },
    "ABILITY_SAFETY_COOLDOWN": {
        "uk": "Ваше вміння для втечі чи захисту ще перезаряджається — без нього ризикувати не можна.",
        "en": "Your escape or defensive ability was on cooldown: without it, risks cost more.",
    },
    "BAD_FIGHT_RISK": {
        "uk": "Поруч іде або щойно була бійка — у такий момент легко віддати зайву смерть, якщо лізти без вигоди.",
        "en": "A fight was going on or had just happened near you: an easy moment to give away a death if you join without an edge.",
    },
    "OBJECTIVE_FIGHT_CHECK": {
        "uk": "Поруч вежа, Рошан або інша ціль — важливо вирішити, іти за нею разом із командою чи ні.",
        "en": "A tower, Roshan or another objective was near: time to decide whether to go for it with your team.",
    },
    "ITEM_TIMING": {
        "uk": "Ви щойно зібрали важливий предмет — з ним у героя з'являється вікно сили.",
        "en": "You just finished a key item: your hero has a window of power with it.",
    },
    "LOW_MANA": {
        "uk": "Мани менше п'ятої частини — у бійці не вистачить на закляття.",
        "en": "Your mana was under a fifth: not enough for your spells in a fight.",
    },
    "LANING_FARM_CHECK": {
        "uk": "Добивань на лінії менше, ніж зазвичай у вашого героя до цієї хвилини.",
        "en": "You had fewer last hits in lane than usual for your hero at this minute.",
    },
    "LANING_REGEN_CHECK": {
        "uk": "На лінії здоров'я помітно просіло — час підлікуватися, поки вороги цим не скористалися.",
        "en": "Your health dropped in lane: time to heal before the enemies use it.",
    },
    "SMOKED_STATUS": {
        "uk": "Ви під Smoke of Deceit: вас не видно, доки ви не підійдете до ворога близько.",
        "en": "You were under Smoke of Deceit: enemies cannot see you until you get close.",
    },
    "FARMING_PHASE_PRESSURE": {
        "uk": "Золота й добивань менше, ніж потрібно до цієї хвилини, — фарм відстає.",
        "en": "Your gold and last hits were behind the pace for this minute.",
    },
    "SOFT_STATUS": {
        "uk": "Нічого термінового — спокійна підказка під час лінії.",
        "en": "Nothing urgent: a calm tip for the laning stage.",
    },
    "SAFE_FARMING": {
        "uk": "Нічого термінового — підказка, як фармити безпечніше.",
        "en": "Nothing urgent: a tip on farming more safely.",
    },
    "BUYBACK_AVAILABLE": {
        "uk": "Ви мертві, поруч важлива бійка або ціль, і на викуп вистачає золота.",
        "en": "You were dead, a key fight or objective was near, and you had gold for a buyback.",
    },
    "DEATH_REVIEW": {
        "uk": "Ви померли — поки чекаєте відродження, саме час зрозуміти чому.",
        "en": "You died: waiting to respawn is the time to see why.",
    },
    "DEATH_WITH_ESCAPE_ON_COOLDOWN": {
        "uk": "Ви померли, коли вміння для втечі ще перезаряджалося.",
        "en": "You died while your escape ability was on cooldown.",
    },
    "DEATH_LOW_RESOURCE": {
        "uk": "Ви померли з малим запасом здоров'я чи мани ще до бійки.",
        "en": "You died after going into the fight with little health or mana.",
    },
    "REPEATED_DEATH_PATTERN": {
        "uk": "Ви помираєте вже не вперше за короткий час — варто змінити підхід.",
        "en": "You died more than once in a short time: time to change the approach.",
    },
    "DEAD_WAIT": {
        "uk": "Ви мертві: час до відродження можна витратити з користю.",
        "en": "You were dead: the time until respawn can still be used.",
    },
}


def why(decision_point: object, lang: str) -> str | None:
    """The sentence for a decision point in `lang` (uk or en), or None."""
    texts = WHY.get(str(decision_point or ""))
    if not texts:
        return None
    return texts["uk" if lang == "uk" else "en"]
