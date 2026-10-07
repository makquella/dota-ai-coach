# Проверки по области изменения

Backend-команды выполняются из `backend/` с активированным существующим venv:

```bash
# Linux/macOS
source .venv/bin/activate
# Windows PowerShell
# .\.venv\Scripts\Activate.ps1
python -m ruff check app/<changed_file>.py tests/test_<feature>.py
python -m ruff format --check app/<changed_file>.py tests/test_<feature>.py
python -m pytest tests/test_<feature>.py tests/test_<consumer>.py
```

Заменять `<...>` реальными путями. `python` должен принадлежать venv; без активации использовать `.venv/bin/python` или `.venv/Scripts/python.exe`. Форматирование — отдельная явная операция только над изменёнными файлами. Claude hooks не запускают backend-wide auto-fix или полный pytest автоматически.

Матрица задаёт стартовый набор; добавить consumers изменённой границы. Все backend test paths ниже относятся к `backend/tests/`.

| Изменение | Проверки |
|---|---|
| GSI / сигналы | `test_gsi_samples_and_advice.py`, `test_gsi_in_match.py`, `test_spectator_gsi.py`, `test_fuzz_live_gsi.py`; skill/position tests при касании |
| Decision / policy / coaches | `test_decision_points_recommender.py`, `test_hero_safety.py`, `test_laning_post_laning_coaches.py`; hero/support cases; `test_advice_i18n.py` при изменении видимого текста |
| Scheduler / frequency / shared state | Все `test_evaluate_*_gate.py`, `test_scheduler_spacing.py`, `test_scheduler_state_snapshot.py`, `test_advice_frequency.py`, `test_replay_demo_data.py`; широкий state refactor → весь backend |
| Tracker / store / persistence | `test_player_history.py`, `test_history_backup.py`, `test_backup_atomicity.py`, `test_cache_corruption.py`, `test_match_notes.py`, `test_match_advice_log.py`; новые failure/restart/thread cases; `test_packaging_runtime.py` при paths/lifecycle |
| Analysis / facts | `test_player_history.py`, связанные role/lane/build/death tests, `test_personal_baseline.py`, `test_focus_goal.py`; проверить review/cache versions |
| AI client / facts / questions | `test_coach_ai.py`, `test_diagnostics.py`; fake providers, metric swaps, total deadline/idempotency; без live AI вызовов |
| Profile / cosmetics / friends | `test_player_profile.py`, `test_cosmetics.py`, `test_friend_compare.py`; launcher `test/friends.test.js`, Worker profile tests при public contract |
| HTTP / logging / IPC | `test_api_smoke.py`, `test_diagnostics.py`, соответствующий feature suite; launcher syntax + matching Node test; Electron smoke для main/preload/backend boundary |
| Launcher helper | Из `frontend/launcher/`: `node --test test/<feature>.test.js`, `npm run check`; весь `npm test` допустим перед сдачей |
| Renderer / locales / CSS | Launcher `test/i18n.test.js` + relevant helpers; реальные DOM-сценарии и RU/EN на поддерживаемых масштабах для layout/interaction |
| Worker | Из `services/api/`: `npm test`; SQL/retention/concurrency дополнительно требуют local D1 + migrations |
| Hero / meta data | `test_hero_coverage.py`, `test_core_heroes.py`, `test_supports.py`, `test_stratz_builds.py` и соответствующая live-логика; site generator check |
| Packaging / dependencies | `test_packaging_runtime.py`, launcher `test/package-files.test.js`, full affected suites, clean install и Windows build/smoke |
| Release notes / generated site | `build_changelog.py --check`, `build_site.py --check`; обычная prose-правка не требует полного backend или NSIS |

Shell glob передаётся native pytest по-разному в bash и PowerShell. Для scheduler-проверок разворачивать пути переносимо из `backend/`:

```bash
python -c "import pathlib,subprocess,sys; paths=sorted(str(p) for p in pathlib.Path('tests').glob('test_evaluate_*_gate.py')); paths += ['tests/test_scheduler_spacing.py','tests/test_scheduler_state_snapshot.py','tests/test_advice_frequency.py','tests/test_replay_demo_data.py']; sys.exit(subprocess.call([sys.executable,'-m','pytest',*paths]))"
```

Неизвестный путь, shared schema/config/store/main/preload, зависимости или межслойный refactor требуют более широких проверок затронутой подсистемы. Проверить staged, unstaged и untracked изменения. Новый data-workflow PR может не запустить CI, потому что создан workflow token: до слияния проверить diff и выполнить backend tests локально.

## Полная проверка

Из `backend/` с активным venv:

```bash
python -m ruff check .
python -m ruff format --check .
python -m pytest --junitxml=/tmp/wardly-backend-tests.xml
python -m compileall -q app scripts packaging tests
python ../scripts/build_changelog.py --check
python ../scripts/build_site.py --check
```

На Windows путь XML заменить на доступный временный файл. Сохранить exit status pytest и проверить текущий XML: tests > 0, failures/errors = 0; skipped сообщать отдельно. `python -m mypy app` пока nonblocking по CI: ошибки типизации не равны runtime defects, но результат необходимо сообщать. Locked baseline и clean-module gate ещё не внедрены.

Из `frontend/launcher/`: `npm run check`, `npm test`. Из `services/api/`: `npm test`. Backend tests используют TestClient + SQLite и чистые domain modules; Worker tests используют fake D1/R2, поэтому passing mocks не доказывают SQL syntax/atomicity настоящего D1.

`backend/tests/conftest.py` сбрасывает shared state, отключает OpenDota и обычно не запускает фоновые threads. Изменения queue/lifespan проверять настоящими threads + Events и context-managed TestClient. Fault tests проверяют recovery/rollback/ответ пользователю; не ослаблять assertions и не заменять проверку zero-test запуском.

## Runtime и сборка

Launcher сам запускает backend. Standalone dev-сервер: из `backend/` `USE_LLM=false OPENDOTA_ENABLED=false python -m uvicorn app.main:app --reload`; не запускать его параллельно для отладки launcher. Проверить `/health` и функциональный запрос, а не только PID/порт.

На Linux без дисплея, из `frontend/launcher/` с установленным Electron и Xvfb:

```bash
xvfb-run -a ./node_modules/.bin/electron . --no-sandbox --smoke-test=/tmp/wardly-smoke.json
```

Использовать новый result path либо убрать собственный предыдущий результат перед запуском. Проверить exit status и JSON текущего запуска: `ok=true`, все steps успешны, включая отрисовку обоих окон, player API, recommendation и graceful shutdown. В подготовленной cloud-среде сначала `source /workspace/.local/share/dota-ai-coach/headless-env.sh`. Localhost-запросы служат внутренней проверкой.

Для Ctrl+K проверить на настоящем Electron: открытие палитры, поиск Settings, Enter, пустой результат и Escape. Сохранённого regression harness пока нет. `scripts/site-shots/` содержит real-renderer screenshot helpers, которые можно использовать при его добавлении.

Windows packaging: из корня `scripts/build-windows.ps1`, затем `scripts/smoke-windows.ps1`. `-SkipBackend` подходит только frontend-изменениям при наличии валидного backend build; release требует полного build. Linux Electron smoke не заменяет Windows installer, watcher и реальную Dota GSI проверку.

После проверки: `git diff --check`, просмотр финального diff и untracked files. Логи, SQLite, записи матчей и локальные результаты не коммитить. Отчёт должен отличать passed, failed, skipped и unrun проверки. Отдельный portable runner и D1/UI harness — задачи roadmap, команды к ним пока не предлагать как готовые.
