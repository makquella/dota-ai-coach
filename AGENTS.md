# AGENTS.md

Onboarding for OpenCode agents. Only non-obvious, repo-specific facts. See `docs/` for full tutorials.

## Layout

Two independent packages, no monorepo tooling:
- `backend/` — Python 3.11 FastAPI app. Package is `app/`, entrypoint `app.main:app`. **Run all backend commands from `backend/`.**
- `frontend/` — one Electron app, `launcher/`: control panel window + always-on-top overlay window + tray; it runs the backend itself. `frontend/overlay.html` + `script.js` are a legacy browser debug overlay.
- `scripts/` — Windows build (`build-windows.ps1`) and smoke test (`smoke-windows.ps1`).
- `data/` — read-only fixtures: `match_simulations/` (replay-derived GSI-like JSONL), `heroes/`, `knowledge_base/`, `gsi_samples/`, `scenarios/`.
- `backend/scripts/` — offline replay/simulation/benchmark scripts, not part of the server runtime.

## Backend tooling (run from `backend/`)

Create the venv once (gitignored at `backend/.venv`):
```bash
python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements-dev.txt
```

Quality gate — this is the order CI (`.github/workflows/ci.yml`) uses:
```bash
ruff check .                 # lint
ruff format --check .        # format check
mypy app                     # NON-BLOCKING (see below)
pytest -q
python -m compileall -q app scripts packaging tests
```
After editing backend code, match the repo's Claude post-edit hook: `ruff check --fix . && ruff format .`.

Run a focused test:
```bash
pytest tests/test_scheduler_spacing.py -q
pytest tests/test_evaluate_low_hp_gate.py::test_name -q
```

- Env flags live in `backend/.env` (see `.env.example`). `app/config.py` loads `backend/.env` then repo-root `.env`, both `override=False`.
- Dev server: `USE_LLM=false uvicorn app.main:app --reload` (from `backend/`).

### ruff: do NOT "fix" the ignored rules
`pyproject.toml` intentionally ignores `E501, SIM102, SIM103, F841`. These are tracked "Phase 0" soft-start debt that would need logic refactors in `advice_scheduler.py` / `post_laning_coach.py`. Don't collapse those nested ifs or remove the unused local in `evaluate()` unless you are doing the surrounding refactor. Line length is 100.

### mypy is non-blocking
Soft-start config: `check_untyped_defs=true`, `disallow_untyped_defs=false`, and CI runs `mypy app || true`. Don't treat mypy warnings as failures or gate on them; do annotate new code when reasonable.

## Backend runtime state is module-global (important for tests)

The app keeps live state in module-level singletons, not a DB:
- `ADVICE_SCHEDULER` (`app.advice_scheduler`)
- `MATCH_MEMORY` (`app.match_memory`)
- `COACH_SESSION_HISTORY` (`app.coach_summary`)
- `LIVE_SESSION_RECORDER` (`app.live_session_recorder`)
- `gsi_state` module globals (`_latest_raw_payload`, `_latest_normalized_state`, ...)

`tests/conftest.py` has an **autouse** `reset_runtime_state` fixture that clears all of these before and after every test, and inserts `backend/` onto `sys.path` so `from app...` imports resolve. When writing tests, rely on this fixture. When reasoning about server behavior, remember these carry cross-request state. The `client` fixture returns a FastAPI `TestClient`.

`app/scheduler/` is a subpackage factored out of the large `advice_scheduler.py` (hashing, heartbeat, safety_predicates, state, types). Load the **advice-policy** skill before changing advice/scheduler/safety logic.

## Local policy is authoritative; LLM is optional

Default `USE_LLM=false`. LLM providers only reword advice or run offline review. The backend always owns `decision_point`, `priority`, `time_window`, safety gating, and anti-spam scheduling — never let LLM output override these, and don't add hard LLM dependencies to the live path.

## Frontend tooling

No lint/typecheck. Verification is `node --check` on these ten files (CI runs exactly this; `npm run check` in `frontend/launcher/` does the same) plus dependency-free unit tests for the Electron-free modules (`npm test` = `node --test test/*.test.js`, also in CI):
```bash
node --check frontend/launcher/main.js
node --check frontend/launcher/preload.js
node --check frontend/launcher/settings.js
node --check frontend/launcher/overlay-window.js
node --check frontend/launcher/overlay-preload.js
node --check frontend/launcher/overlay-visibility.js
node --check frontend/launcher/dota-watcher.js
node --check frontend/launcher/steam-locator.js
node --check frontend/launcher/renderer/app.js
node --check frontend/launcher/overlay/app.js
```
Dev: `npm install && npm run dev` inside `frontend/launcher/`. On Wayland/GNOME use `npm run dev:x11` for the overlay to stay always-on-top. Electron is pinned at 42.4.0.

Runtime check without a display server: `xvfb-run -a npx electron . --no-sandbox --smoke-test=/tmp/smoke.json` (from `frontend/launcher/`) starts the backend, loads both windows, checks `/health`, stops the backend gracefully and exits 0/1.

Windows packaging: `scripts/build-windows.ps1` (PyInstaller backend + electron-builder NSIS installer) and `scripts/smoke-windows.ps1`; CI job `windows-package` runs both on `windows-latest`. Details: `docs/PACKAGING_WINDOWS.md`.

## Do not commit generated/local artifacts

Gitignored but may appear locally: `backend/logs/`, `backend/session_records/`, `backend/runtime_logs/`, `backend/gsi_debug_samples/`, `backend/build|dist/`, `*.dem` / `*.dem.bz2`, model weights, and `.env`. Two generated paths have **committed exceptions** — don't be surprised they're tracked: only `replay_gsi_like_match_8843382732_pl_20_30.jsonl` and `replay_gsi_like_match_8843471434_jugg_10_20.jsonl` in `data/match_simulations/`, and only `replay_evaluation_summary_20260608.{md,csv}` in `backend/simulation_results/`.

## OpenCode skills (load via the skill tool)

- **advice-policy** — for any work in `advice_*.py`, `decision_points.py`, `recommender.py`, `hero_safety.py`, `hero_profiles.py`, `laning_coach.py`, `post_laning_coach.py`, the scheduler, `match_memory.py`, UX policy.
- **test-writer** — for writing pytest covering backend modules.

## Reference

- Full commands: `docs/REFERENCE_COMMANDS.md`
- File map / data flow: `docs/ARCHITECTURE.md`
- Scheduler detail: `docs/ADVICE_SCHEDULER.md`
- Replay/demo flow: `docs/REPLAY_DEMO.md`, `docs/QUICKSTART.md`

Commands in docs are repo-relative (`cd backend`, `cd frontend/launcher`). Where an absolute path is unavoidable, docs use a `<repo-root>` placeholder.

## Running the project

**Backend (dev)** — run from `backend/`:
```bash
USE_LLM=false uvicorn app.main:app --reload          # http://127.0.0.1:8000
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload --no-access-log   # quieter variant
```
Port defaults to **8000**. With manual uvicorn it is a CLI flag; `backend/packaging/backend_server.py` (used by the launcher and the frozen exe) reads it from env via `app/config.py`: `DOTA_AI_BACKEND_HOST` (=`127.0.0.1`), `DOTA_AI_BACKEND_PORT` (=`8000`), `DOTA_AI_BACKEND_LOG_LEVEL` (=`info`). With `DOTA_AI_BACKEND_STDIN_CONTROL=1` it shuts down gracefully on a `shutdown` line or EOF on stdin — that is how the launcher stops it (no taskkill).

**GSI has no separate listener.** Dota 2 GSI is received by the `POST /gsi` endpoint on the **same** FastAPI server. The launcher writes `gamestate_integration_dota_ai_coach.cfg` into Dota 2's `gamestate_integration/` folder with `uri "http://127.0.0.1:<backend port>/gsi"` and rewrites it if the port changes (`gsiConfigText` / `syncGsiConfigPort` in `frontend/launcher/main.js`). Health check: `GET /health`.

**The launcher runs its own backend.** On start it picks a port (env `DOTA_AI_BACKEND_PORT` → last used port saved in settings → 8000 → any free port), spawns `backend/packaging/backend_server.py` (dev, `backend/.venv` Python, no `--reload`) or the bundled `dota-ai-coach-backend.exe` (packaged) hidden, forces `USE_LLM=false`, `LIVE_CONSERVATIVE_MODE=true`, and passes the port to both windows over IPC. A manual uvicorn on 8000 no longer conflicts (the launcher moves to another port), but you then have two independent backends — pick one entry point when debugging.

**Electron apps:**
```bash
cd frontend/launcher && npm install && npm run dev            # whole app: backend + overlay window + tray; Wayland/GNOME: `npm run dev:x11`
```

## Environment variables and secrets

Config is loaded by `python-dotenv` + `os.getenv` in `app/config.py` — **not** pydantic `BaseSettings`. Loading order: `backend/.env` then repo-root `.env`, both with `override=False` (frozen exe: `%APPDATA%\DotaAICoach\.env` instead). Consequence: **shell env vars always win**, and `backend/.env` takes priority over the root `.env` (root only fills gaps). When debugging "my key isn't picked up", check shell exports first, then `backend/.env`.

**No variable is required** — every `os.getenv` has a default; the backend boots with no `.env` at all.

| Variable | Default | Purpose |
|---|---|---|
| `USE_LLM` | `false` | **LLM on/off toggle** — set `true` to enable |
| `LLM_PROVIDER` | `disabled` | `disabled\|groq\|openrouter\|llamacpp` |
| `LLM_TIMEOUT` / `LLM_MAX_TOKENS` | `6` / `350` | clamped to 1–30s and 1–2000 |
| `GROQ_API_KEY` / `GROQ_MODEL` | `""` / `openai/gpt-oss-120b` | Groq provider |
| `OPENROUTER_API_KEY` / `OPENROUTER_MODEL` | `""` / `openai/gpt-oss-120b:free` | OpenRouter provider |
| `LLAMACPP_BASE_URL` / `LLAMACPP_MODEL` | `http://127.0.0.1:8080` / `local-gpt-oss-20b` | local llama.cpp server (no key) |
| `GSI_DEBUG_LOG` | `false` | dump raw GSI samples locally |
| `LIVE_CONSERVATIVE_MODE` | `true` | conservative live gating |
| `GSI_STALE_SECONDS` | `5` | GSI freshness threshold |
| `SESSION_RECORDS_DIR` | `backend/session_records` | session record output dir |
| `DOTA_AI_BACKEND_HOST` / `DOTA_AI_BACKEND_PORT` | `127.0.0.1` / `8000` | server address for `backend_server.py` / frozen exe |
| `DOTA_AI_BACKEND_STDIN_CONTROL` | unset | `1` = stop gracefully on stdin `shutdown`/EOF (set by the launcher) |

**Frozen (PyInstaller) paths** are decided in `app/config.py` from `sys.frozen`: read-only data from `sys._MEIPASS/data` (`DATA_DIR`), writable files (`LOGS_DIR`, `SESSION_RECORDS_DIR`, `GSI_DEBUG_SAMPLES_DIR`) under `%APPDATA%\DotaAICoach` (`WRITABLE_DIR`). In a source checkout: `data/` and `backend/`. Use `DATA_DIR`/`WRITABLE_DIR` from config for new paths — never `Path(__file__).parents[...]`, which breaks in the frozen build.

**OpenAI: не найдено.** There is **no `OPENAI_API_KEY` anywhere** in the codebase. Cloud providers are Groq and OpenRouter only; `llamacpp` is a local server with no key. The `openai/gpt-oss-*` model names are served *through* OpenRouter/Groq — do not look for or add a direct OpenAI integration.

Script-only env (not runtime): `SIMULATION_*`, `MATCH_SIMULATION_PATH` (`scripts/simulate_match_advice.py`); `BENCHMARK_*` (`scripts/benchmark_llm_models.py`); `DOTA_DEMO_PARSER_COMMAND` (`scripts/parse_dota_demo_to_replay_events.py`). Full list in `backend/.env.example`.

## Frontend apps

One Electron app, **`frontend/launcher/`** (product name "Dota AI Coach", exe `DotaAICoach.exe`). The former separate `frontend/desktop-overlay/` app was merged into it.
- `main.js` — single-instance lock, tray (Open / Overlay / Start with Windows / Quit), close-to-tray, autostart (`--hidden`), backend process (port pick, health wait, graceful stop, crash restart ×3), replay demo presets, GSI config, IPC, `--smoke-test`.
- `renderer/` + `preload.js` — control panel window.
- `overlay-window.js` + `overlay-preload.js` + `overlay/` — transparent frameless always-on-top window; its renderer asks the main process for `/overlay/recommendation` (1000 ms) and never builds backend URLs. The window exists while the overlay is enabled; `setVisible()` decides whether it is on screen, and the always-on-top timer runs only while shown.
- `overlay-visibility.js` — pure rules: shown only when enabled AND (unlocked for dragging OR replay demo OR (dota2 running AND focused AND backend `/gsi/status` `in_match`)); on platforms without focus tracking it follows the switch. Also the tray status (not found / waiting for game / in game).
- `dota-watcher.js` — Windows: one hidden long-lived PowerShell helper (user32 `GetForegroundWindow`/`GetWindowThreadProcessId`/`IsIconic`) prints JSON on change; exits itself when the launcher dies. Linux dev: `/proc` scan, no focus tracking.
- `steam-locator.js` — Steam root from the registry (`reg.exe query`) → `libraryfolders.vdf` → every library; Dota's uninstall key and the running `dota2.exe` path are extra hints. The GSI config is installed automatically once on first run (`settings.gsiAutoInstalled`) and afterwards kept identical to the template.
- `settings.js` — `%APPDATA%\DotaAICoach\settings.json` (Electron `userData` is set to the same folder the frozen backend writes to).

(Legacy browser debug overlay: `frontend/overlay.html` + `script.js`.)

## Doc checkout paths (resolved — no code change)

Earlier docs hardcoded a locale-specific absolute checkout path. It existed **only in documentation, never in code** — code was always portable:
- `backend/app/config.py:11` → `REPO_ROOT = Path(__file__).resolve().parents[2]`
- `frontend/launcher/main.js:8` → `REPO_ROOT = path.resolve(__dirname, "..", "..")`

So **do not touch code or add a `DOTA_AI_COACH_DIR` env var** — nothing reads it.

Fix applied (option b — repo-relative commands): the doc shell blocks in `README.md`, `docs/QUICKSTART.md`, `docs/REFERENCE_COMMANDS.md`, `docs/REPLAY_DEMO.md`, `frontend/desktop-overlay/README.md` (since removed) now use repo-relative `cd` (`cd backend`, `cd frontend/launcher`, …) instead of an absolute locale-specific path, so they don't depend on folder names like `Документы` vs `Documents`. `docs/PACKAGING_WINDOWS.md` uses repo-relative Windows commands (`scripts\build-windows.ps1`). When adding new docs, prefer repo-relative commands; use a `<repo-root>` placeholder with a one-line note only where an absolute path is genuinely unavoidable.
