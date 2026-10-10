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
python ../scripts/check_types.py
python -m mypy --strict ../scripts/check_types.py
python -m pytest --junitxml=/tmp/wardly-backend-tests.xml
python -m compileall -q app scripts packaging tests
python ../scripts/build_changelog.py --check
python ../scripts/build_site.py --check
```

На Windows путь XML заменить на доступный временный файл. Сохранить exit status pytest и проверить текущий XML: tests > 0, failures/errors = 0; skipped сообщать отдельно. Locked mypy gate блокирует новые ошибки и требует удалять resolved allowances; 176 существующих ошибок остаются известным долгом. Команды prune и границы проверки — [TYPE_CHECKING.md](TYPE_CHECKING.md).

Из `frontend/launcher/`: `npm run check`, `npm test`. Из `services/api/`: `npm test` запускает unit tests и integration tests transfer на настоящем local D1/Miniflare. Отдельно доступны `npm run test:unit` и `npm run test:integration`. Backend tests используют TestClient + SQLite и чистые domain modules; другие Worker SQL paths пока используют fake D1/R2, поэтому при изменении их атомарности нужно расширять реальные D1 проверки. Границы harness — [TRANSFER_ATOMICITY.md](TRANSFER_ATOMICITY.md).

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

После проверки: `git diff --check`, просмотр финального diff и untracked files. Логи, SQLite, записи матчей и локальные результаты не коммитить. Отчёт должен отличать passed, failed, skipped и unrun проверки. Portable runner и version gate: [DEV_RUNNER.md](DEV_RUNNER.md); `python scripts/dev.py check --changed --dry-run` показывает текущие пути, profiles, argv и cwd. Actual Electron smoke и local D1 harness уже существуют; их границы описаны выше.

## Проверить исправление на записи (0.53.58)

`backend/scripts/replay_check.py` прогоняет четыре очищенных синтетических матча — керри (Juggernaut), мид (Shadow Fiend), оффлейн (Axe), саппорт (Crystal Maiden) — через весь живой путь (`/gsi` → `/overlay/recommendation`, часы планировщика = часы игры) и сравнивает показанные советы и подсказки карты с принятыми результатами в `backend/tests/replay_golden/<case>.json`. Строка результата — `MM:SS DECISION_POINT mode`: что и когда показано, без формулировки, поэтому правка текста не считается изменением поведения. Перед каждым кейсом состояние приложения сбрасывается как в `tests/conftest.py`, результат не зависит от порядка.

```
cd backend
python scripts/replay_check.py                      # все кейсы, разница с принятыми
python scripts/replay_check.py --case offlane_axe --text   # с текстом карточек
python scripts/replay_check.py --update             # принять новое поведение (дифф — в PR)
```

`tests/test_replay_golden.py` запускает все кейсы (~35 с) и при расхождении печатает добавленные и пропавшие строки и команду для воспроизведения. Изменение live-правил, планировщика, decision points или подсказок карты требует этого теста; намеренное изменение поведения обновляет эталоны в том же PR.
