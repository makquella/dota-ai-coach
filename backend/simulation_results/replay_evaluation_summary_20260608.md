# Replay Evaluation Summary — 2026-06-08

## 1. Мета експерименту

Мета експерименту — оцінити offline replay-derived GSI-like simulation та поведінку Laning Coach v1 / Post-Laning Farming Coach v1 на реальних replay Dota 2. Оцінка охоплює laning, post-laning та early macro/farming stages і перевіряє, чи система генерує безпечні, короткі та context-aware рекомендації без інформаційного шуму.

Окремо перевіряється, що scheduler та suppression rules утримують advice volume у цільовому діапазоні для 10-хвилинних replay slices, а fallback-first architecture залишається основою для urgent/safety advice.

## 2. Джерело даних

Дані отримані з реальних Dota 2 `.dem.bz2` replay, розібраних через локальний Clarity helper. Replay events були конвертовані у 1-second GSI-like states, після чого ці states були прогнані через існуючий `simulate_match_advice.py`.

Використані сценарії:

- Phantom Lancer, match_id `8843382732`, windows `0-10`, `10-20`, `20-30`.
- Juggernaut, match_id `8843471434`, windows `0-10`, `10-20`, `20-30`.

Medusa match `8843473597` був перевірений, але виключений з фінальної оцінки, бо OpenDota повернув `replay_url=None`, тому offline replay pipeline не мав доступного `.dem.bz2` джерела.

Використані report/review artifacts:

- `simulation_results/match_advice_simulation_20260608_082550.json` -> `simulation_results/advice_review_20260608_082550.md`
- `simulation_results/match_advice_simulation_20260608_093526.json` -> `simulation_results/advice_review_20260608_093526.md`
- `simulation_results/match_advice_simulation_20260608_101030.json` -> `simulation_results/advice_review_20260608_101030.md`
- `simulation_results/match_advice_simulation_20260608_101356.json` -> `simulation_results/advice_review_20260608_101356.md`
- `simulation_results/match_advice_simulation_20260608_102637.json` -> `simulation_results/advice_review_20260608_102637.md`
- `simulation_results/match_advice_simulation_20260608_102648.json` -> `simulation_results/advice_review_20260608_102648.md`

Важливо: ці дані є **GSI-like replay states**, а не повною реконструкцією live GSI або повного стану карти.

## 3. Таблиця метрик

| scenario | hero | match_id | time_window | stage | duration_minutes | states_processed | high_confidence_states | low_confidence_states | advice_shown | advice_per_minute | urgent_advice_count | coaching_advice_count | repeated_laning_suppressed_count | repeated_post_laning_suppressed_count | repeated_objective_suppressed_count | low_hp_episode_count | repeated_low_hp_suppressed_count | low_hp_pattern_advice_count | llm_applied_count | llm_invalid_count | average_latency | p95_latency | fits_duration_target |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Phantom Lancer laning replay | Phantom Lancer | 8843382732 | 0-10 | laning / bad-lane recovery | 10.0 | 601 | 498 | 103 | 8 | 0.8 | 3 | 5 | 57 | 0 | 0 | 3 | 90 | 1 | 4 | 0 | 2.420s | 2.573s | yes |
| Phantom Lancer post-laning replay | Phantom Lancer | 8843382732 | 10-20 | post-laning / early recovery | 10.0 | 601 | 601 | 0 | 8 | 0.8 | 3 | 4 | 0 | 249 | 66 | 3 | 0 | 0 | 0 | 0 | 0.000s | 0.000s | yes |
| Phantom Lancer macro farming replay | Phantom Lancer | 8843382732 | 20-30 | macro / post-laning farming | 10.0 | 601 | 601 | 0 | 8 | 0.8 | 1 | 7 | 0 | 279 | 20 | 1 | 0 | 0 | 0 | 0 | 0.000s | 0.000s | yes |
| Juggernaut laning replay | Juggernaut | 8843471434 | 0-10 | laning / farm deficit and pressure | 10.0 | 601 | 469 | 132 | 5 | 0.5 | 0 | 5 | 98 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0.000s | 0.000s | yes |
| Juggernaut noisy post-laning replay | Juggernaut | 8843471434 | 10-20 | post-laning / noisy safety recovery | 10.0 | 601 | 601 | 0 | 8 | 0.8 | 3 | 5 | 0 | 239 | 55 | 4 | 28 | 1 | 0 | 0 | 0.000s | 0.000s | yes |
| Juggernaut macro farming replay | Juggernaut | 8843471434 | 20-30 | macro / post-laning farming | 10.0 | 601 | 601 | 0 | 6 | 0.6 | 0 | 5 | 0 | 261 | 70 | 0 | 0 | 0 | 0 | 0 | 0.000s | 0.000s | yes |

## 4. Приклади рекомендацій

### Phantom Lancer 0-10 — laning / repeated low HP

- Risky position advice: `Move closer to a safer lane area before contesting the next wave.`
  Reason: `Your position is exposed and enemy locations are not confirmed.`
- Farm deficit advice: `Secure the next wave first and avoid trading unless it protects last hits.`
  Reason: `Your carry farm pace is behind for this minute, but HP is stable, so the fastest recovery is clean last hitting.`
- LOW_HP reset advice: `Leave the wave now and reset HP before rejoining.`
  Reason: `At this HP, one more trade or spell can kill you.`
- Pattern-level advice: `Stop re-contesting the pressured lane until you reset HP.`
  Reason: `Repeated low-HP returns can cost more than missing one wave.`

### Phantom Lancer 10-20 — post-laning recovery

- LOW_HP reset advice: `Reset HP before showing on another lane.`
  Reason: `At this HP, one more spell or rotation can turn into a death.`
- Farm recovery advice: `Recover farm through the safest wave-and-camp route.`
  Reason: `You are behind on farm, so forcing fights before stabilizing can delay your next timing.`
- Pressure avoidance advice: `Avoid the pressured lane and farm a safer wave or nearby camp.`
  Reason: `Staying in pressure can cost HP and slow your recovery.`
- Objective caution advice: `Only consider the objective if your team is already grouped nearby.`
  Reason: `Objective fights can be valuable, but the replay does not confirm team readiness.`

### Phantom Lancer 20-30 — macro / item timing

- Farm recovery advice: `Recover farm through the safest wave-and-camp route.`
  Reason: `You are behind on farm, so forcing fights before stabilizing can delay your next timing.`
- Objective caution advice: `Only consider the objective if your team is already grouped nearby.`
  Reason: `Objective fights can be valuable, but the replay does not confirm team readiness.`
- LOW_HP reset advice: `Reset HP before showing on another lane.`
  Reason: `At this HP, one more spell or rotation can turn into a death.`
- Item timing advice: `After this item pickup, reassess whether to farm safely or pressure with your team.`
  Reason: `The item improves your options, but missing cooldown and team context means the safer choice still depends on nearby pressure.`

### Juggernaut 0-10 — second carry laning scenario

- Risky position advice: `Move closer to a safer lane area before contesting the next wave.`
  Reason: `Your position is exposed and enemy locations are not confirmed.`
- Farm deficit advice: `Secure the next wave first and avoid trading unless it protects last hits.`
  Reason: `Your carry farm pace is behind for this minute, but HP is stable, so the fastest recovery is clean last hitting.`
- Pressure advice: `Take only the safe creeps and avoid extending the trade.`
  Reason: `You are behind on farm and under lane pressure; forcing a trade can cost both HP and last hits.`
- HP warning advice: `Use regen or play back until your HP is safer.`
  Reason: `Low lane HP makes trades and last hits risky.`

### Juggernaut 10-20 — noisy post-laning case after suppression fix

- Farm recovery advice: `Recover farm through the safest wave-and-camp route.`
  Reason: `You are behind on farm, so forcing fights before stabilizing can delay your next timing.`
- Pressure avoidance advice: `Avoid the pressured lane and farm a safer wave or nearby camp.`
  Reason: `Staying in pressure can cost HP and slow your recovery.`
- LOW_HP reset advice: `Reset HP before showing on another lane.`
  Reason: `At this HP, one more spell or rotation can turn into a death.`
- Repeated death pattern advice: `After respawn, reset your route and avoid repeating the same risky path.`
  Reason: `Multiple recent deaths can delay your next timing more than missing one wave or camp.`

### Juggernaut 20-30 — stable macro/farming case

- Death route advice: `Use the respawn time to choose a safer farming route.`
  Reason: `Returning to the same pressured area can repeat the same death pattern.`
- Farm recovery advice: `Recover farm through the safest wave-and-camp route.`
  Reason: `You are behind on farm, so forcing fights before stabilizing can delay your next timing.`
- Safe route advice: `Keep farming the safest wave-and-camp route and reassess soon.`
  Reason: `Your farm pace is stable now, so keep using safe routes instead of forcing uncertain fights.`
- Objective caution advice: `Only consider the objective if your team is already grouped nearby.`
  Reason: `Objective fights can be valuable, but the replay does not confirm team readiness.`

## 5. Інтерпретація результатів

PL 0-10 використовується як repeated low-HP / bad-lane recovery scenario. У цьому slice система виявила laning farm deficit, risky position та repeated low-HP returns. `low_hp_episode` logic зменшила urgent spam і сформувала pattern-level advice про те, що повторне contest-іння pressured lane без reset HP є дорожчим, ніж пропуск хвилі.

PL 10-20 показує post-laning recovery: система перейшла від laning-only wording до post-laning формулювань про safer route, HP reset перед показом на іншій lane та cautious objective advice. Duration slice bug був виправлений: window `10-20` оцінюється як `10.0` minutes, а не як абсолютна 20-хвилинна тривалість.

PL 20-30 демонструє macro farming, objective caution та item timing. Advice не робить claims про точну готовність команди або безпечність fight, бо replay не містить nearby allies/enemies, enemy positions та exact objective context.

Juggernaut 0-10 є другим carry laning scenario. Він підтверджує, що Laning Coach v1 працює не лише для Phantom Lancer: система реагує на farm deficit, lane pressure, risky position та low HP warning без переходу до build/meta-specific порад.

Juggernaut 10-20 був noisy post-laning case. Після stronger post-laning safety suppression total advice зменшено до `8` messages за 10 хвилин, `fits_duration_target = yes`, urgent advice залишилось на рівні `3`, а objective advice repetition було приглушено через `repeated_objective_suppressed_count = 55`.

Juggernaut 20-30 є stable macro/farming case. Він показує heavy suppression of repeated advice: `repeated_post_laning_suppressed_count = 261`, `repeated_objective_suppressed_count = 70`, і при цьому система залишила 6 змістовних рекомендацій у межах target volume.

У всіх 10-хвилинних slices advice volume залишився в межах target range `5-8` після поточних suppression fixes. Post-laning wording більше не використовує laning-only `next wave` phrasing для windows після 10 хвилини. Objective advice repetition suppress-иться, а post-laning safety suppression не дозволяє нижчопріоритетним macro cards перекривати LOW_HP/death/reset advice.

LLM застосовувався в PL 0-10 для coaching advice (`llm_applied_count = 4`). Для fallback-only scenarios `llm_applied_count = 0`, `average_latency = 0.000s`, `p95_latency = 0.000s`. Fallback залишився authoritative для urgent/safety advice.

## 6. Обмеження

- Replay parser does not extract exact current spendable gold.
- Replay parser does not extract ability cooldowns yet.
- Інформація про nearby allies/enemies, enemy positions, exact teamfight context та exact objective/Roshan context є недоступною.
- Advice avoids claims requiring missing signals: система не стверджує `safe to fight`, `team is ready`, `enemy is not nearby` або точний стан Roshan/objective.
- Replay-derived GSI-like evaluation корисна для offline testing, але не є повністю еквівалентною live GSI.
- Для match `8843473597` Medusa не було доступного `replay_url`, тому сценарій виключено з фінального evaluation set.

## 7. Висновок

Offline replay evaluation підтверджує, що Laning Coach v1 та Post-Laning Farming Coach v1 можуть генерувати безпечні, ненав’язливі та контекстні рекомендації на основі доступних GSI-like replay signals. Система покриває laning, post-laning recovery та macro/farming stages, реагує на farm pace, HP pressure, position risk, repeated low-HP patterns, objective caution та item timing, але не робить тверджень, які потребують відсутніх сигналів.

Фінальний набір сценаріїв показує, що stronger safety/objective/post-laning suppression тримає advice volume у межах target для 10-хвилинних slices, а fallback-first architecture залишається придатною для coursework MVP: rule-based safety контролює `priority` і `time_window`, тоді як LLM може покращувати coaching wording лише там, де це безпечно.
