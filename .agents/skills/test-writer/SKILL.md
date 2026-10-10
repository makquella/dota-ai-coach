---
name: test-writer
description: >
  Писати pytest-тести для backend Dota AI Coach. Використовувати, коли потрібно покрити
  тестами модулі app/, особливо логіку порад, scheduler spacing, decision points,
  safety-гейтинг, UX-політику. Тригерити на словах: тест, test, покрити, coverage,
  pytest, conftest, fixture, перевірка, test case, assertion.
---

# Test writer

## Принципи

Тести в цьому проєкті — **функціональні/інтеграційні**: вони проганяють реальний
пайплайн через HTTP-ендпоінти FastAPI `TestClient`, а не мокають внутрішні шари.
Це забезпечує високе покриття за невеликої кількості тестів.

Вивід LLM **НЕ тестувати напряму** — він опційний і gated `USE_LLM`.
Тестувати лише детерміновану логіку.

## Інфраструктура

- **Фреймворк:** pytest, без конфігураційного файлу (типові налаштування)
- **Тести:** `backend/tests/`
- **Фікстури:** `backend/tests/conftest.py`
- **GSI-семпли:** `data/gsi_samples/` (37 JSON-файлів, сценарії для різних героїв)
- **Симуляції:** `data/match_simulations/` (2 JSONL-файли по ~600 станів)
- **Запуск:** `cd backend && pytest -q`

## Fixtures (з conftest.py)

Три фікстури, усі автоматично доступні:

1. **`reset_runtime_state`** (autouse) — скидає 5 глобальних синглтонів
   (`ADVICE_SCHEDULER`, `MATCH_MEMORY`, `COACH_SESSION_HISTORY` та ін.)
   до й після кожного тесту. Головна ізоляція — не треба скидати вручну.
2. **`client`** — `fastapi.testclient.TestClient(app)`. Майже всі тести йдуть через нього.
3. **`repo_root`** — `Path` до кореня репозиторію. Для доступу до файлів `data/`.

## Патерни наявних тестів

### 1. HTTP-smoke (test_api_smoke.py)
GET-запити до ендпоінтів, перевірка status_code і базової структури відповіді.

```python
def test_health_returns_ok(client: TestClient) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
```

### 2. GSI-семпли → перевірка порад (test_gsi_samples_and_advice.py)
POST реального JSON із `data/gsi_samples/` у `/gsi`, потім GET `/overlay/recommendation`
і перевірка `decision_point`, `advice_mode`, тексту.

```python
def _sample(repo_root: Path, name: str) -> dict:
    return json.loads((repo_root / "data" / "gsi_samples" / name).read_text())

def _post_sample(client: TestClient, repo_root: Path, name: str) -> dict:
    resp = client.post("/gsi", json=_sample(repo_root, name))
    assert resp.status_code == 200
    return resp.json()
```

### 3. Scheduler spacing через демо-ендпоінт (test_scheduler_spacing.py)
Синтетичні state-дикти POST'яться в `/demo/replay-state`, перевіряється spacing
між не-urgent порадами (>= 45s), interrupt при LOW_HP, heartbeat nudge (>= 180s тиші).

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

### 4. Replay-симуляції (test_replay_demo_data.py)
Повний програш JSONL-файлу (601 стан) через POST у `/demo/replay-state`,
перевірка кількості порад і spacing.

### 5. Юніт-тест модуля (test_live_session_recorder.py)
Прямий імпорт модуля й перевірка file I/O у `tmp_path`.

## Конвенції

- **Іменування:** `test_<descriptive_snake_case>` — довгі імена, що самі себе документують
- **Хелпери:** префікс `_` (`_state`, `_send_demo_state`, `_sample`)
- **Асерти на decision_point:** використовувати `in {...}` set membership,
  а не жорстку рівність — допускає варіації:
  ```python
  assert rec["decision_point"] in {"LOW_HP", "LOW_HP_WARNING"}
  ```
- **Один файл — одна турбота:** smoke, GSI-семпли, scheduler spacing, recorder, replay
- **Type annotations:** `from __future__ import annotations` + анотації на всіх функціях
- **Імпорти:** `from __future__ import annotations` + стандартні + `pytest` + `app.*`

## Що тестувати (і як)

| Область | Ендпоінт / підхід | Що перевіряти |
|---------|-------------------|----------------|
| Decision points | POST `/gsi` з GSI-семплом → GET `/overlay/recommendation` | Правильний decision_point для сценарію |
| Scheduler spacing | POST `/demo/replay-state` із синтетичним state | Дублікати придушено, spacing >= 45s, urgent interrupt |
| Heartbeat nudge | POST `/demo/replay-state` зі стрибками timestamp | Nudge після 180s тиші, не замінює urgent |
| Death pinning | GSI-семпли зі смертю → порада залипає | Death-порада не скидається завчасно |
| Safety gating | GSI-семпли для різних героїв | Hero-specific safety логіка |
| UX policy | GET `/overlay/recommendation` | advice_mode правильний, rate-limit bypass працює |
| Laning coach | POST `/gsi` з лайнінг-семплом (0-10 хв) | Поради farm deficit, regen check |
| Post-laning coach | POST `/gsi` з post-laning семплом (10+ хв) | Поради route reset, farm recovery |

## Нові GSI-семпли

Якщо потрібного сценарію немає в `data/gsi_samples/` (37 файлів):
1. Подивитися наявні як зразок формату
2. Створити мінімальний JSON із потрібними полями
3. Покласти в `data/gsi_samples/`
4. НЕ редагувати наявні семпли вручну

## Чого НЕ робити

- Не мокати внутрішні шари (decision_points, scheduler, recommender) — тестуй
  через HTTP-ендпоінти, як інші тести
- Не тестувати LLM-відповіді — LLM опційний (USE_LLM=false)
- Не додавати pytest-конфігурацію — проєкт використовує типові значення
- Не писати тестів, що залежать від порядку виконання — `autouse` fixture гарантує
  ізоляцію через скидання синглтонів
