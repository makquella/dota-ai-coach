---
name: advice-policy
description: >
  Логіка порад Dota AI Coach — decision points, recommender, anti-spam scheduler,
  safety-гейтинг, пріоритети, таймінги й UX-політика. Використовувати під час будь-якої роботи з
  advice_*.py, decision_points.py, recommender.py, scheduler, hero_safety.py,
  hero_profiles.py, laning_coach.py, post_laning_coach.py, advice_context.py,
  advice_text.py, advice_ux_policy.py, match_memory.py, signal_capabilities.py.
  Тригерити на словах: порада, advice, decision point, decision_point, scheduler,
  spacing, spam, anti-spam, priority, пріоритет, safety, герой, hero profile,
  laning coach, post-laning, heartbeat, nudge, rate limit, когнітивне навантаження,
  cognitive load, UX-політика, duplicate suppression, urgency.
---

# Advice policy

## ГОЛОВНИЙ ПРИНЦИП

Локальні правила авторитетні. LLM лише формулює текст, не змінює
decision_point / priority / time_window / safety-гейтинг. Live-формулювання LLM
мають бути за прапорцем USE_LLM і не ламати роботу при USE_LLM=false.
Post-match AI (`coach_llm.py`, `coach_review.py`) вмикається окремо й не залежить
від USE_LLM; його факти постачає детермінований розбір.

## Архітектура: 3-шаровий пайплайн + 2 фазові коучі + UX-гарди

```
gsi_state.py → decision_points.py → advice_policy.py → recommender.py / llm_provider.py
                                             ↓
                                    advice_scheduler.py (display: spacing, suppression, heartbeat)
                                             ↓
                                    advice_ux_policy.py (cognitive load: rate limits, trimming)
```

Два фазові коучі подають додатковий контекст у recommender:
- `laning_coach.py` (хвилини 0-10) — 6 категорій laning-порад
- `post_laning_coach.py` (хвилини 10+) — 6 категорій post-laning порад

## Де що (файли)

| Файл | Рядки | Відповідальність |
|------|--------|-----------------|
| `decision_points.py` | 488 | Детерміновані точки ухвалення рішень (24 decision points) |
| `recommender.py` | 399 | Вибір формулювання поради (fallback-текст, коли LLM вимкнено) |
| `advice_policy.py` | 290 | Пріоритети порад і правила активації |
| `advice_ux_policy.py` | 183 | UX: rate limits, cognitive load, coaching mode rewording |
| `advice_scheduler.py` | **2234** | **Хотспот:** duplicate suppression, game-time spacing, active-card lifetime, urgent interrupts, LOW_HP episodes, death pinning, objective suppression, heartbeat nudges, LLM refinement scheduling, accounting metrics |
| `hero_safety.py` | 143 | Safety-перевірки: escape-здібності, мана-shield, захисні ресурси |
| `hero_profiles.py` | 323 | Дані архетипів героїв і ключові safety-здібності |
| `laning_coach.py` | 290 | Лайнінг-коуч (0-10 хв): farm deficit, regen, risky position |
| `post_laning_coach.py` | 304 | Пост-лайнінг коуч (10+ хв): route reset, farm recovery, objective caution |
| `advice_context.py` | 239 | Контекст для порад: збір сигналів із GSI state |
| `advice_text.py` | 248 | Шаблони текстів порад |
| `match_memory.py` | 497 | Пам'ять матчу: death patterns, repeated behavior |
| `signal_capabilities.py` | 210 | Які сигнали доступні з GSI (для консервативності) |
| `gsi_state.py` | 682 | Парсинг і нормалізація GSI |

## Decision Points (канонічний список)

Визначені як `Literal` у `decision_points.py` та `advice_scheduler.py`:

**HP/виживання:**
- `LOW_HP` — критичне HP, негайний відступ
- `LOW_HP_WARNING` — HP падає, відійти й регенеруватися
- `RECENT_DAMAGE_WARNING` — нещодавня важка шкода
- `OVERSTAY_WARNING` — затримка на низькому HP
- `HERO_SURVIVABILITY_RISK` — ключовий захисний ресурс недоступний
- `DISABLED_STATUS` — під контролем/станом
- `SMOKED_STATUS` — під смоуком

**Ресурси:**
- `LOW_MANA` — мани замало для бійки
- `ABILITY_SAFETY_COOLDOWN` — захисна здібність на кулдауні

**Смерть/рев'ю:**
- `DEATH_REVIEW` — аналіз після смерті
- `REPEATED_DEATH_PATTERN` — багаторазові смерті, один патерн
- `DEATH_WITH_ESCAPE_ON_COOLDOWN` — смерть за недоступного escape
- `DEATH_LOW_RESOURCE` — смерть за вичерпаних HP/мани

**Гра/об'єктиви:**
- `BUYBACK_AVAILABLE` — buyback доступний
- `DEAD_WAIT` — очікування респавну
- `FARMING_PHASE_PRESSURE` — тиск ворогів під час фарму
- `OBJECTIVE_FIGHT_CHECK` — оцінити, чи вступати в бійку за об'єкт
- `BAD_FIGHT_RISK` — бійка виглядає невигідною
- `ITEM_TIMING` — досягнуто значущого таймінгу предмета
- `SAFE_FARMING` — загроз немає, фармити далі

**Системні:**
- `NO_ADVICE` — явно немає поради
- `SOFT_STATUS` — без термінової поради, лише статус
- `LANING_REGEN_CHECK` — перевірка використання реген-предметів на лінії
- `LANING_FARM_CHECK` — перевірка farm deficit на лінії

### Групування

- **Death Review** (`DEATH_REVIEW_DECISIONS`): `DEATH_REVIEW`, `REPEATED_DEATH_PATTERN`, `DEATH_WITH_ESCAPE_ON_COOLDOWN`, `DEATH_LOW_RESOURCE`
- **Rate-limit bypass** (`RATE_LIMIT_BYPASS_DECISIONS`): `LOW_HP`, `DEATH_REVIEW`, `REPEATED_DEATH_PATTERN`, `DEATH_WITH_ESCAPE_ON_COOLDOWN`, `DEATH_LOW_RESOURCE`
- **Advice modes** (UX): `urgent` (LOW_HP, DISABLED_STATUS), `status` (NO_ADVICE, SOFT_STATUS, DEAD_WAIT, DEATH_REVIEW), `coaching` (усе інше)

## Правила під час доопрацювання

### Нове правило → тест
Будь-яку нову логіку порад покривати pytest-тестами в `backend/tests/`.
Див. `test_scheduler_spacing.py` як приклади (6 тестів: duplicate suppression,
game-time spacing, urgent interrupts, heartbeat nudges).

### Консервативність
За відсутності сигналу НЕ вигадувати. Live GSI може передавати координати
видимих ворогів у minimap і спостережувані події Roshan/Aegis; це не розкриває
прихованих ворогів, готовність команди чи повну картину бійки. Replay GSI-like
не гарантує HP, gold і кулдаунів. Перевіряти `signal_capabilities.py` і реальні
поля source (`gsi_state.py`, `enemy_heroes.py`, `roshan_timer.py`).

### Scheduler — гаряча зона
`advice_scheduler.py` вже має 2234 рядки. Нову логіку виносити в окремі модулі.
Не ламати: duplicate suppression, game-time spacing, heartbeat nudge timing,
LOW_HP episode handling, death pinning.

### Категорії — рядки, не enum'и
Усі категорії — plain strings у `Literal` типах або set literals.
Новий decision point → додати в `Literal` у `decision_points.py` І в `advice_scheduler.py`.
Не створювати абстракцій (no AdviceCategory enum), дотримуватися наявного стилю.

### Видимий текст → український переклад
Пайплайн пише поради лише англійською; українська додається на межі API
(`app/advice_i18n.py`, `lang=uk`). Новий чи змінений видимий текст
(`action`, `reason`, `message`) → додати переклад у `_UK_EXACT` (або шаблон у
`_UK_PATTERNS`, якщо всередині ім'я героя/здібності). `tests/test_advice_i18n.py`
падає на будь-якому видимому тексті без перекладу.

### LLM-гейтинг
- Live-формулювання LLM за прапорцем `USE_LLM`; post-match AI має окремі налаштування
- LLM формулює текст, не визначає decision_point/priority/time_window
- При `USE_LLM=false` live-поради працюють через fallback-тексти `recommender.py`
