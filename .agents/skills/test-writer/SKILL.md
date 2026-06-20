---
name: test-writer
description: >
  Писать pytest-тесты для backend Dota AI Coach. Использовать когда нужно покрыть
  тестами модули app/, особенно логику советов, scheduler spacing, decision points,
  safety-гейтинг, UX-политику. Триггерить на словах: тест, test, покрыть, coverage,
  pytest, conftest, fixture, проверка, test case, assertion.
---

# Test writer

## Принципы

Тесты в этом проекте — **функциональные/интеграционные**: они прогоняют реальный
пайплайн через HTTP-эндпоинты FastAPI `TestClient`, а не мокают внутренние слои.
Это обеспечивает высокое покрытие при малом количестве тестов.

LLM-вывод **НЕ тестировать напрямую** — он опционален и gated `USE_LLM`.
Тестировать только детерминированную логику.

## Инфраструктура

- **Фреймворк:** pytest, без конфигурационного файла (дефолтные настройки)
- **Тесты:** `backend/tests/`
- **Фикстуры:** `backend/tests/conftest.py`
- **GSI-сэмплы:** `data/gsi_samples/` (37 JSON-файлов, сценарии для разных героев)
- **Симуляции:** `data/match_simulations/` (2 JSONL-файла по ~600 состояний)
- **Запуск:** `cd backend && pytest -q`

## Fixtures (из conftest.py)

Три фикстуры, все автоматически доступны:

1. **`reset_runtime_state`** (autouse) — сбрасывает 5 глобальных синглтонов
   (`ADVICE_SCHEDULER`, `MATCH_MEMORY`, `COACH_SESSION_HISTORY` и др.)
   до и после каждого теста. Главная изоляция — не нужно руками ресетить.
2. **`client`** — `fastapi.testclient.TestClient(app)`. Почти все тесты идут через него.
3. **`repo_root`** — `Path` к корню репозитория. Для доступа к `data/` файлам.

## Паттерны существующих тестов

### 1. HTTP-smoke (test_api_smoke.py)
GET-запросы к эндпоинтам, проверка status_code и базовой структуры ответа.

```python
def test_health_returns_ok(client: TestClient) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
```

### 2. GSI-сэмплы → проверка советов (test_gsi_samples_and_advice.py)
POST реального JSON из `data/gsi_samples/` в `/gsi`, затем GET `/overlay/recommendation`
и проверка `decision_point`, `advice_mode`, текста.

```python
def _sample(repo_root: Path, name: str) -> dict:
    return json.loads((repo_root / "data" / "gsi_samples" / name).read_text())

def _post_sample(client: TestClient, repo_root: Path, name: str) -> dict:
    resp = client.post("/gsi", json=_sample(repo_root, name))
    assert resp.status_code == 200
    return resp.json()
```

### 3. Scheduler spacing через демо-эндпоинт (test_scheduler_spacing.py)
Синтетические state-дикты POST'ятся в `/demo/replay-state`, проверяется spacing
между не-urgent советами (>= 45s), interrupt при LOW_HP, heartbeat nudge (>= 180s тишины).

```python
def _state(timestamp: int = 0, **overrides: object) -> dict:
    base: dict = {
        "hero": "Phantom Lancer", "hp": 1200, "max_hp": 2200,
        "game_state": "playing", "farm_quality": "good", "last_hits": 50,
        **overrides,
    }
    if timestamp:
        base["game_time"] = timestamp
    return base

def _send_demo_state(client: TestClient, timestamp: int, state: dict) -> dict:
    resp = client.post("/demo/replay-state", json={"timestamp": timestamp, **state})
    assert resp.status_code == 200
    return resp.json()
```

### 4. Replay-симуляции (test_replay_demo_data.py)
Полный проигрыш JSONL-файла (601 состояние) через POST в `/demo/replay-state`,
проверка количества советов и spacing.

### 5. Юнит-тест модуля (test_live_session_recorder.py)
Прямой импорт модуля и проверка file I/O в `tmp_path`.

## Конвенции

- **Именование:** `test_<descriptive_snake_case>` — длинные, самодокументирующиеся имена
- **Хелперы:** префикс `_` (`_state`, `_send_demo_state`, `_sample`)
- **Ассерты на decision_point:** использовать `in {...}` set membership,
  не жёсткое равенство — допускает вариации:
  ```python
  assert rec["decision_point"] in {"LOW_HP", "LOW_HP_WARNING"}
  ```
- **Один файл — одна забота:** smoke, GSI-сэмплы, scheduler spacing, recorder, replay
- **Type annotations:** `from __future__ import annotations` + аннотации на всех функциях
- **Импорты:** `from __future__ import annotations` + стандартные + `pytest` + `app.*`

## Что тестировать (и как)

| Область | Эндпоинт / подход | Что проверять |
|---------|-------------------|----------------|
| Decision points | POST `/gsi` с GSI-сэмплом → GET `/overlay/recommendation` | Правильный decision_point для сценария |
| Scheduler spacing | POST `/demo/replay-state` с синтетическим state | Дубликаты подавлены, spacing >= 45s, urgent interrupt |
| Heartbeat nudge | POST `/demo/replay-state` с timestamp jumps | Nudge после 180s тишины, не заменяет urgent |
| Death pinning | GSI-сэмплы со смертью → совет залипает | Death-совет не сбрасывается раньше времени |
| Safety gating | GSI-сэмплы для разных героев | Hero-specific safety логика |
| UX policy | GET `/overlay/recommendation` | advice_mode правильный, rate-limit bypass работает |
| Laning coach | POST `/gsi` с лайнинг-сэмплом (0-10 мин) | Farm deficit, regen check советы |
| Post-laning coach | POST `/gsi` с post-laning сэмплом (10+ мин) | Route reset, farm recovery советы |

## Новые GSI-сэмплы

Если нужного сценария нет в `data/gsi_samples/` (37 файлов):
1. Посмотреть существующие за образец формата
2. Создать минимальный JSON с нужными полями
3. Положить в `data/gsi_samples/`
4. НЕ редактировать существующие сэмплы вручную

## Чего НЕ делать

- Не мокать внутренние слои (decision_points, scheduler, recommender) — тестируй
  через HTTP-эндпоинты, как остальные тесты
- Не тестировать LLM-ответы — LLM опционален (USE_LLM=false)
- Не добавлять pytest-конфигурацию — проект использует дефолты
- Не писать тесты, зависящие от порядка выполнения — `autouse` fixture гарантирует
  изоляцию через ресет синглтонов
