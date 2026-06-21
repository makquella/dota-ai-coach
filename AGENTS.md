# Dota AI Coach — agent instructions

## Что это
Real-time коуч для керри в Dota 2. Принимает live GSI от Dota 2,
нормализует состояние, применяет детерминированные правила, фильтрует советы
через анти-спам scheduler и показывает компактную карточку в Electron-оверлее.
Проект начат как курсовой MVP и продолжается как личный проект.

## ГЛАВНЫЙ ПРИНЦИП (не нарушать)
- Локальная rule-based политика — единственный источник правды для live-советов.
- LLM используется ТОЛЬКО для формулировок текста и оффлайн-ревью.
- LLM НИКОГДА не переопределяет: decision_point, priority, time_window,
  safety-гейтинг, анти-спам scheduling.
- Любой вызов LLM должен быть за флагом USE_LLM и не ломать работу при USE_LLM=false.

## SAFETY (жёсткие границы — не предлагать и не писать такое)
Проект НЕ делает и не должен делать:
- чтение памяти процесса Dota 2
- захват/анализ экрана
- автоматизацию клавиатуры/мыши
- инжект/хук в игровой процесс
- зависимость от STRATZ в live-режиме
Live-режим потребляет только локальные HTTP GSI-пейлоады.

## Границы фаз (Phase 0: сетка безопасности)
Текущая фаза добавляет guardrails без изменения логики:
- Линт/формат: ruff (pyproject.toml, line-length 100, target py311)
- Тайп-чек: mypy (мягкий старт, check_untyped_defs, non-blocking)
- Тесты: pytest (testpaths=tests, addopts=-q)
- CI: .github/workflows/ci.yml — backend (ruff/mypy/pytest/compileall)
  и frontend (node --check) jobs на push/PR в main
- Локальные хуки: .claude/settings.json — PostToolUse (Edit|Write|MultiEdit)
  -> ruff check --fix + ruff format; Stop -> pytest -q
Главное правило фазы: НИКАКОГО рефакторинга логики, только сетка безопасности.

## Стек
- Backend: Python 3.11, FastAPI, uvicorn, pydantic v2, requests, httpx
- Frontend: Electron (Node 20) — launcher + desktop-overlay
- Replays: Java (Gradle) clarity-парсер -> события -> GSI-like JSONL
- Тесты/линт: pytest, ruff, mypy (backend); node --check (frontend)

## Структура
- backend/app/        — FastAPI приложение и логика коуча
- backend/scripts/    — импорт OpenDota, симуляции, конвертация реплеев
- backend/tests/      — pytest
- backend/replay_tools/clarity/ — Java-парсер .dem
- frontend/launcher/  — Electron-лаунчер
- frontend/desktop-overlay/ — Electron-оверлей
- data/               — GSI-сэмплы и симуляции (НЕ редактировать вручную)
- docs/               — документация

## Правила кода
- Python: PEP8, type hints везде, pydantic-модели для схем (см. app/schemas.py)
- Не раздувать модули: advice_scheduler.py уже большой — новую логику выносить
- Любую новую логику советов покрывать pytest-тестами в backend/tests/
- Все секреты только через .env (см. .env.example), в код не хардкодить
- Сохранять обратную совместимость GSI-парсинга (gsi_state.py)

## Команды
- Установка:  cd backend && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements-dev.txt
- Запуск:     USE_LLM=false uvicorn app.main:app --reload   (127.0.0.1:8000)
- Тесты:      pytest -q
- Линт:       ruff check .       (cd backend)
- Формат:     ruff format .      (cd backend)
- Тайп-чек:   mypy app           (cd backend, non-blocking)
- Компиляция: python3 -m compileall -q app scripts packaging tests
- Frontend:   node --check frontend/launcher/main.js  (и остальные js)
- Демо без Dota: python3 scripts/run_overlay_demo.py --simulation-file ... 

## Чего НЕ делать
- Не коммитить в main напрямую без проверки тестов
- Не трогать data/ и simulation_results/ вручную
- Не добавлять тяжёлые зависимости без необходимости (стек намеренно лёгкий)
- Не нарушать SAFETY-границы выше

## Осознанные trade-off'ы (НЕ «исправлять» — это намеренный консерватизм)
Следующие решения выглядят как недосмотры, но сделаны осознанно. Будущий агент
не должен «чинить» их как регрессии. Фаза 3 только фиксирует их здесь.

- #1 defensive-ability cooldown не считается риском при полном HP
  (hero_safety.py, блок key_abilities["defensive"]). Defensive-способность на
  кулдауне флагуется как риск только когда hp_percent <= low_hp_warning_threshold.
  При полном HP пропуск считается нешумным: герой ещё не в punish-окне, лучше
  недосигналить риск, чем спамить. Менять — только с обсуждением.

- #3 live-conservative слой гасит OBJECTIVE_FIGHT_CHECK -> SOFT_STATUS даже при
  full_team_alive, если не хватает сигналов (main.py,
  _live_conservative_decision_point). В live_gsi мы принципиально не можем
  подтвердить готовность команды, поэтому без nearby_allies_enemies /
  enemy_positions / exact_teamfight_context или при context_confidence != "high"
  objective-вызов даунгрейдится. Это намеренный консерватизм: лучше не дать
  совет, чем толкнуть к неверному objective. Не менять.
