# Dota AI Coach — agent instructions

## Что это
Real-time коуч для керри в Dota 2 (курсовая MVP). Принимает live GSI от Dota 2,
нормализует состояние, применяет детерминированные правила, фильтрует советы
через анти-спам scheduler и показывает компактную карточку в Electron-оверлее.

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

## Стек
- Backend: Python, FastAPI, uvicorn, pydantic v2, requests, httpx
- Frontend: Electron (Node) — launcher + desktop-overlay
- Replays: Java (Gradle) clarity-парсер -> события -> GSI-like JSONL
- Тесты: pytest (backend), node --check (frontend)

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
- Установка:  cd backend && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
- Запуск:     USE_LLM=false uvicorn app.main:app --reload   (127.0.0.1:8000)
- Тесты:      pytest -q
- Компиляция: python3 -m compileall -q app scripts packaging tests
- Frontend:   node --check frontend/launcher/main.js  (и остальные js)
- Демо без Dota: python3 scripts/run_overlay_demo.py --simulation-file ... 

## Чего НЕ делать
- Не коммитить в main напрямую без проверки тестов
- Не трогать data/ и simulation_results/ вручную
- Не добавлять тяжёлые зависимости без необходимости (стек намеренно лёгкий)
- Не нарушать SAFETY-границы выше
