"""Source-backed preparation variants; exact target-dependent research stays off."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GameplayRule:
    id: str
    hero: str
    ability: str
    gate: str
    evidence: tuple[str, ...]
    action: str
    reason: str
    action_uk: str
    reason_uk: str


RULES = (
    GameplayRule(
        "sven.hammer_flight_mode.prepare",
        "Sven",
        "sven_storm_bolt",
        "scepter",
        ("S-flight",),
        "Check Storm Hammer alt-cast: with Scepter, that mode makes you travel to the target.",
        "Your Scepter is observed. Choose the mode for your intended landing; the selected target is unknown to the app.",
        "Перевірте alt-cast Storm Hammer: зі Scepter саме цей режим переносить вас до цілі.",
        "Scepter підтверджено. Оберіть режим під потрібну кінцеву позицію; застосунок не бачить обрану ціль.",
    ),
    GameplayRule(
        "sven.barrier_variant.prepare",
        "Sven",
        "sven_warcry",
        "shard",
        ("S-barrier",),
        "Check Warcry's physical barrier against physical damage; it does not cover every damage type.",
        "Your Shard is observed. Match the barrier to the threat instead of treating Warcry as universal protection.",
        "Врахуйте фізичний бар'єр Warcry проти фізичної шкоди: він не захищає від усіх її типів.",
        "Shard підтверджено. Зіставте бар'єр із загрозою, а не сприймайте Warcry як універсальний захист.",
    ),
    GameplayRule(
        "sven.strength_start.prepare",
        "Sven",
        "sven_gods_strength",
        "ready",
        ("S-strength", "S-strength-time"),
        "Check your approach before God's Strength; save its window for useful attacks.",
        "God's Strength is available. Account for travel time before activating it; slow resistance does not stop stuns.",
        "Оцініть підхід перед God's Strength: збережіть її час для корисних атак.",
        "God's Strength доступна. Врахуйте час зближення перед активацією; опір сповільненню не зупиняє оглушення.",
    ),
    GameplayRule(
        "sven.hammer_dispel.prepare",
        "Sven",
        "sven_storm_bolt",
        "scepter",
        ("S-dispel",),
        "Consider upgraded Hammer's basic dispel when choosing a target; it is not a strong dispel.",
        "Scepter is observed. Check whether the target's effect can be removed; the app cannot see target modifiers.",
        "Врахуйте базове розвіювання покращеного Hammer при виборі цілі: це не сильне розвіювання.",
        "Scepter підтверджено. Перевірте, чи можна зняти ефект цілі; застосунок не бачить її модифікатори.",
    ),
    GameplayRule(
        "sven.warcry_approach.prepare",
        "Sven",
        "sven_warcry",
        "ready",
        ("S-warcry",),
        "Consider Warcry for the approach or expected physical damage, before that damage lands.",
        "Warcry is available. Its armor and movement can help the approach; neither guarantees protection from disables.",
        "Розгляньте Warcry для зближення або очікуваної фізичної шкоди, перш ніж її отримати.",
        "Warcry доступна. Броня й швидкість можуть допомогти при зближенні; вони не гарантують захист від контролю.",
    ),
    GameplayRule(
        "juggernaut.ward_reset.self",
        "Juggernaut",
        "juggernaut_healing_ward",
        "recovery",
        ("J-ward",),
        "Consider Healing Ward for your missing HP if you have a protected recovery window.",
        "Your HP is reduced and Ward is available. Keep it out of reach; check mana for your next spell.",
        "Розгляньте Healing Ward для відновлення свого HP, якщо є захищене вікно для лікування.",
        "Ваш HP знижений, Ward доступний. Тримайте його поза досяжністю ворога й перевірте ману на наступну здібність.",
    ),
    GameplayRule(
        "juggernaut.swift_scope.prepare",
        "Juggernaut",
        "juggernaut_swift_slash",
        "ready",
        ("J-swift",),
        "Consider Swiftslash for a brief task only if its shorter window is enough.",
        "Your actual Swiftslash is available. Check the target and follow-up before choosing it over Omnislash.",
        "Розгляньте Swiftslash для короткої задачі, лише якщо її коротшого вікна достатньо.",
        "Ваша Swiftslash доступна. Перевірте ціль і продовження, перш ніж обирати її замість Omnislash.",
    ),
    GameplayRule(
        "juggernaut.omni_isolation.prepare",
        "Juggernaut",
        "juggernaut_omni_slash",
        "ready",
        ("J-omni",),
        "Check the units around your intended Omnislash target before committing.",
        "Omnislash is available, but nearby creeps can share the slashes. Wait only if doing so does not lose the target.",
        "Перевірте оточення запланованої цілі Omnislash перед застосуванням.",
        "Omnislash доступна, але сусідні кріпи можуть розділити удари. Чекайте лише якщо це не втратить потрібну ціль.",
    ),
    GameplayRule(
        "juggernaut.spin_tp.prepare",
        "Juggernaut",
        "juggernaut_blade_fury",
        "teleport",
        ("J-spin",),
        "Check enemy control before relying on Blade Fury + TP.",
        "Blade Fury is available and you carry teleport. Debuff immunity does not prevent every TP cancel; check TP readiness too.",
        "Перевірте ворожий контроль, перш ніж покладатися на Blade Fury + TP.",
        "Blade Fury доступна, телепорт є. Імунітет до ефектів не запобігає кожному зриву TP; перевірте й готовність телепорту.",
    ),
    GameplayRule(
        "juggernaut.slash_items.prepare",
        "Juggernaut",
        "juggernaut_omni_slash",
        "slash_item",
        ("J-omni-items",),
        "Consider the useful item action before Omnislash; items can be used during the slashes.",
        "BKB or Manta is available. Decide whether it helps this task; having the item is not a reason to spend it.",
        "Продумайте застосування предмета для Omnislash: він доступний і під час її ударів.",
        "BKB або Manta доступні. Вирішіть, чи допоможуть вони цій задачі: наявність предмета не є причиною витрачати його.",
    ),
    GameplayRule(
        "terrorblade.sunder_target.prepare",
        "Terrorblade",
        "terrorblade_sunder",
        "ready",
        ("T-sunder",),
        "Check the target's HP percentage before relying on Sunder to recover.",
        "Sunder is available. A low-HP target may not improve yours; swapping with an ally transfers the HP cost to them.",
        "Перевірте відсоток HP цілі, перш ніж покладатися на відновлення через Sunder.",
        "Sunder доступна. Ціль із низьким HP може не покращити ваш стан; обмін із союзником перекладає на нього втрату HP.",
    ),
    GameplayRule(
        "terrorblade.zeal_meta.prepare",
        "Terrorblade",
        "terrorblade_demon_zeal",
        "meta_pair",
        ("T-zeal", "T-zeal-cost"),
        "Check Zeal's HP cost before using it; Metamorphosis removes the Zeal effect.",
        "Both abilities are available. Choose for the intended task; a cooldown alone cannot confirm an active effect.",
        "Врахуйте витрату HP на Zeal перед застосуванням: Metamorphosis знімає її ефект.",
        "Обидві здібності доступні. Обирайте під заплановану задачу; перезарядка сама по собі не підтверджує активний ефект.",
    ),
    GameplayRule(
        "terrorblade.wave_meta_distinction.prepare",
        "Terrorblade",
        "terrorblade_terror_wave",
        "ready",
        ("T-wave",),
        "Check Terror Wave's separate form when planning around Metamorphosis.",
        "Terror Wave is available. Its transformation does not prove normal Metamorphosis is ready; your current form is unknown to the app.",
        "Врахуйте окрему форму Terror Wave, коли плануєте гру навколо Metamorphosis.",
        "Terror Wave доступна. Її перетворення не підтверджує готовність звичайної Metamorphosis; застосунок не бачить вашу поточну форму.",
    ),
    GameplayRule(
        "terrorblade.meta_arrival.prepare",
        "Terrorblade",
        "terrorblade_metamorphosis",
        "ready",
        ("T-meta", "T-meta-time"),
        "Check travel time before Metamorphosis; begin the form closer to useful attacks.",
        "Metamorphosis is available. Early activation can spend the window walking; earlier use can still be right for your current task.",
        "Врахуйте час руху перед Metamorphosis: починайте форму ближче до корисних атак.",
        "Metamorphosis доступна. Рання активація може витратити вікно на рух; але поточна задача може виправдовувати раннє застосування.",
    ),
    GameplayRule(
        "terrorblade.image_route.prepare",
        "Terrorblade",
        "terrorblade_conjure_image",
        "ready",
        ("T-image",),
        "Consider an illusion for a separate wave if keeping the hero elsewhere fits your plan.",
        "Conjure Image is available. Split only if that wave has value; the app cannot see your illusions or the wave.",
        "Розгляньте ілюзію для окремої хвилі, якщо за вашим планом герой потрібен в іншому місці.",
        "Conjure Image доступна. Розділяйтеся лише якщо хвиля корисна; застосунок не бачить ваших ілюзій чи цю хвилю.",
    ),
)

RULE_BY_ID = {rule.id: rule for rule in RULES}
GAMEPLAY_VERSION = 1
GAMEPLAY_RISK = "Target, enemy control and active effects still need your own check."
GAMEPLAY_TRANSLATIONS = {
    **{rule.action: rule.action_uk for rule in RULES},
    **{rule.reason: rule.reason_uk for rule in RULES},
    GAMEPLAY_RISK: "Ціль, ворожий контроль і активні ефекти ще потрібно перевірити самостійно.",
    "before your next planned action": "перед наступною запланованою дією",
}
