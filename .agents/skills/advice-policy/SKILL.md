---
name: advice-policy
description: >
  Логика советов Dota AI Coach — decision points, recommender, anti-spam scheduler,
  safety-гейтинг, приоритеты, тайминги и UX-политика. Использовать при любой работе с
  advice_*.py, decision_points.py, recommender.py, scheduler, hero_safety.py,
  hero_profiles.py, laning_coach.py, post_laning_coach.py, advice_context.py,
  advice_text.py, advice_ux_policy.py, match_memory.py, signal_capabilities.py.
  Триггерить на словах: совет, advice, decision point, decision_point, scheduler,
  spacing, spam, anti-spam, priority, приоритет, safety, герой, hero profile,
  laning coach, post-laning, heartbeat, nudge, rate limit, когнитивная нагрузка,
  cognitive load, UX-политика, duplicate suppression, urgency.
---

# Advice policy

## ГЛАВНЫЙ ПРИНЦИП

Локальные правила авторитетны. LLM только формулирует текст, не меняет
decision_point / priority / time_window / safety-гейтинг. Любой вызов LLM
должен быть за флагом USE_LLM и не ломать работу при USE_LLM=false.

## Архитектура: 3-слойный пайплайн + 2 фазовых коуча + UX-гарды

```
gsi_state.py → decision_points.py → advice_policy.py → recommender.py / llm_provider.py
                                             ↓
                                    advice_scheduler.py (display: spacing, suppression, heartbeat)
                                             ↓
                                    advice_ux_policy.py (cognitive load: rate limits, trimming)
```

Два фазовых коуча подают дополнительный контекст в recommender:
- `laning_coach.py` (минуты 0-10) — 6 категорий laning-советов
- `post_laning_coach.py` (минуты 10+) — 6 категорий post-laning советов

## Где что (файлы)

| Файл | Строки | Ответственность |
|------|--------|-----------------|
| `decision_points.py` | 488 | Детерминированные точки принятия решений (24 decision points) |
| `recommender.py` | 399 | Выбор формулировки совета (fallback текст, когда LLM выключен) |
| `advice_policy.py` | 290 | Приоритеты советов и правила активации |
| `advice_ux_policy.py` | 183 | UX: rate limits, cognitive load, coaching mode rewording |
| `advice_scheduler.py` | **2234** | **Хотспот:** duplicate suppression, game-time spacing, active-card lifetime, urgent interrupts, LOW_HP episodes, death pinning, objective suppression, heartbeat nudges, LLM refinement scheduling, accounting metrics |
| `hero_safety.py` | 143 | Safety-проверки: escape-способности, мана-shield, дефензивные ресурсы |
| `hero_profiles.py` | 323 | Данные архетипов героев и ключевые safety-способности |
| `laning_coach.py` | 290 | Лайнинг-коуч (0-10 мин): farm deficit, regen, risky position |
| `post_laning_coach.py` | 304 | Пост-ланинг коуч (10+ мин): route reset, farm recovery, objective caution |
| `advice_context.py` | 239 | Контекст для советов: сбор сигналов из GSI state |
| `advice_text.py` | 248 | Шаблоны текстов советов |
| `match_memory.py` | 497 | Память матча: death patterns, repeated behavior |
| `signal_capabilities.py` | 210 | Какие сигналы доступны из GSI (для консервативности) |
| `gsi_state.py` | 682 | Парсинг и нормализация GSI |

## Decision Points (канонический список)

Определены как `Literal` в `decision_points.py` и `advice_scheduler.py`:

**HP/выживаемость:**
- `LOW_HP` — критический HP, немедленный отступ
- `LOW_HP_WARNING` — HP падает, отойти и реген
- `RECENT_DAMAGE_WARNING` — недавний тяжёлый урон
- `OVERSTAY_WARNING` — задержка на низком HP
- `HERO_SURVIVABILITY_RISK` — ключевой дефензивный ресурс недоступен
- `DISABLED_STATUS` — под контролем/станом
- `SMOKED_STATUS` — под дымкой

**Ресурсы:**
- `LOW_MANA` — маны мало для драки
- `ABILITY_SAFETY_COOLDOWN` — дефензивная способность на кулдауне

**Смерть/ревью:**
- `DEATH_REVIEW` — анализ после смерти
- `REPEATED_DEATH_PATTERN` — многократные смерти, один паттерн
- `DEATH_WITH_ESCAPE_ON_COOLDOWN` — смерть при недоступном escape
- `DEATH_LOW_RESOURCE` — смерть при схлопнувшихся HP/мане

**Игра/объективы:**
- `BUYBACK_AVAILABLE` — buyback доступен
- `DEAD_WAIT` — ожидание респавна
- `FARMING_PHASE_PRESSURE` — давление врагов при фарме
- `OBJECTIVE_FIGHT_CHECK` — оценять, вступать ли в файт за объект
- `BAD_FIGHT_RISK` — файт выглядит невыгодным
- `ITEM_TIMING` — достигнут значимый тайминг предмета
- `SAFE_FARMING` — нет угроз, продолжать фарм

**Системные:**
- `NO_ADVICE` — явно нет совета
- `SOFT_STATUS` — без срочного совета, статус только
- `LANING_REGEN_CHECK` — проверка использования реген-предметов на лайне
- `LANING_FARM_CHECK` — проверка farm deficit на лайне

### Группировки

- **Death Review** (`DEATH_REVIEW_DECISIONS`): `DEATH_REVIEW`, `REPEATED_DEATH_PATTERN`, `DEATH_WITH_ESCAPE_ON_COOLDOWN`, `DEATH_LOW_RESOURCE`
- **Rate-limit bypass** (`RATE_LIMIT_BYPASS_DECISIONS`): `LOW_HP`, `DEATH_REVIEW`, `REPEATED_DEATH_PATTERN`, `DEATH_WITH_ESCAPE_ON_COOLDOWN`, `DEATH_LOW_RESOURCE`
- **Advice modes** (UX): `urgent` (LOW_HP, DISABLED_STATUS), `status` (NO_ADVICE, SOFT_STATUS, DEAD_WAIT, DEATH_REVIEW), `coaching` (всё остальное)

## Правила при доработке

### Новое правило → тест
Любую новую логику советов покрывать pytest-тестами в `backend/tests/`.
См. `test_scheduler_spacing.py` за примерами (6 тестов: duplicate suppression,
game-time spacing, urgent interrupts, heartbeat nudges).

### Консервативность
При отсутствии сигнала НЕ выдумывать. GSI не даёт точных позиций врагов,
gold, кулдаунов из реплеев — не предполагать их наличие. Использовать
`signal_capabilities.py` чтобы понимать, что реально доступно.

### Scheduler — горячая зона
`advice_scheduler.py` уже 2234 строки. Новую логику выносить в отдельные модули.
Не ломать: duplicate suppression, game-time spacing, heartbeat nudge timing,
LOW_HP episode handling, death pinning.

### Категории — строки, не enum'ы
Все категории — plain strings в `Literal` типах или set literals.
Новый decision point → добавить в `Literal` в `decision_points.py` И в `advice_scheduler.py`.
Не создавать абстракции (no AdviceCategory enum), следовать существующему стилю.

### Видимый текст → русский перевод
Пайплайн пишет советы только по-английски; русский добавляется на границе API
(`app/advice_i18n.py`, `lang=ru`). Новый или изменённый видимый текст
(`action`, `reason`, `message`) → добавить перевод в `_RU_EXACT` (или шаблон в
`_RU_PATTERNS`, если внутри имя героя/способности). `tests/test_advice_i18n.py`
падает на любом видимом тексте без перевода.

### LLM-гейтинг
- Все вызовы LLM за `USE_LLM` флагом
- LLM формулирует текст, не определяет decision_point/priority/time_window
- При `USE_LLM=false` всё работает через `recommender.py` fallback-тексты
