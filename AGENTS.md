# AGENTS.md

Onboarding for OpenCode agents. Only non-obvious, repo-specific facts. See `docs/` for full tutorials.

## Layout

Two independent packages, no monorepo tooling:
- `backend/` — Python 3.11 FastAPI app. Package is `app/`, entrypoint `app.main:app`. **Run all backend commands from `backend/`.**
- `frontend/` — Electron apps with no shared code: `launcher/` (defense control panel) and `desktop-overlay/` (always-on-top advice card). `frontend/overlay.html` + `script.js` are a legacy browser debug overlay.
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

No build, no test runner, no lint/typecheck. Verification is syntax-only `node --check` on these six files (CI runs exactly this):
```bash
node --check frontend/launcher/main.js
node --check frontend/launcher/preload.js
node --check frontend/launcher/renderer/app.js
node --check frontend/desktop-overlay/main.js
node --check frontend/desktop-overlay/preload.js
node --check frontend/desktop-overlay/renderer/app.js
```
Dev: `npm install && npm run dev` inside `frontend/launcher/` or `frontend/desktop-overlay/`. On Wayland/GNOME use `npm run dev:x11` for the overlay to stay always-on-top. Electron is pinned at 42.4.0; packaging targets Windows portable only.

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
Port defaults to **8000**. In dev it is a CLI flag; in packaged mode (`backend/packaging/backend_server.py:32-34`) it comes from env: `DOTA_AI_BACKEND_HOST` (=`127.0.0.1`), `DOTA_AI_BACKEND_PORT` (=`8000`), `DOTA_AI_BACKEND_LOG_LEVEL` (=`info`).

**GSI has no separate listener.** Dota 2 GSI is received by the `POST /gsi` endpoint on the **same** FastAPI server, port 8000 (`app/main.py:171`). The launcher writes `gamestate_integration_dota_ai_coach.cfg` into Dota 2's `gamestate_integration/` folder with `uri "http://127.0.0.1:8000/gsi"` (`frontend/launcher/main.js:18-19,663-682`). Health check: `GET /health`.

**Do not run uvicorn manually while the launcher is running.** The launcher itself spawns uvicorn (`frontend/launcher/main.js:439-462`, with `--host 127.0.0.1 --port 8000 --reload --no-access-log`) and forces `USE_LLM=false`, `LIVE_CONSERVATIVE_MODE=true`. A manual uvicorn plus the launcher both grabbing port 8000 causes a silent conflict that is painful to debug. Pick one entry point.

**Electron apps:**
```bash
cd frontend/launcher && npm install && npm run dev            # launcher: also starts backend + overlay + demos
cd frontend/desktop-overlay && npm install && npm run dev     # Wayland/GNOME overlay: use `npm run dev:x11`
```

## Environment variables and secrets

Config is loaded by `python-dotenv` + `os.getenv` in `app/config.py` — **not** pydantic `BaseSettings`. Loading order: `backend/.env` then repo-root `.env`, both with `override=False`. Consequence: **shell env vars always win**, and `backend/.env` takes priority over the root `.env` (root only fills gaps). When debugging "my key isn't picked up", check shell exports first, then `backend/.env`.

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

**OpenAI: не найдено.** There is **no `OPENAI_API_KEY` anywhere** in the codebase. Cloud providers are Groq and OpenRouter only; `llamacpp` is a local server with no key. The `openai/gpt-oss-*` model names are served *through* OpenRouter/Groq — do not look for or add a direct OpenAI integration.

Script-only env (not runtime): `SIMULATION_*`, `MATCH_SIMULATION_PATH` (`scripts/simulate_match_advice.py`); `BENCHMARK_*` (`scripts/benchmark_llm_models.py`); `DOTA_DEMO_PARSER_COMMAND` (`scripts/parse_dota_demo_to_replay_events.py`). Full list in `backend/.env.example`.

## Frontend apps

Two independent Electron apps (separate `package.json`, no shared code):
- **`frontend/launcher/`** (`dota-ai-coach-launcher`) — defense control panel: start/stop backend + overlay + replay demo presets, install/check the Dota 2 GSI config, clean/verbose logs. Spawns uvicorn itself.
- **`frontend/desktop-overlay/`** (`dota-ai-coach-desktop-overlay`) — transparent frameless always-on-top window polling `/overlay/recommendation` (1000 ms) to show one advice card.

(Legacy browser debug overlay: `frontend/overlay.html` + `script.js`.)

## Doc checkout paths (resolved — no code change)

Earlier docs hardcoded a locale-specific absolute checkout path. It existed **only in documentation, never in code** — code was always portable:
- `backend/app/config.py:11` → `REPO_ROOT = Path(__file__).resolve().parents[2]`
- `frontend/launcher/main.js:8` → `REPO_ROOT = path.resolve(__dirname, "..", "..")`

So **do not touch code or add a `DOTA_AI_COACH_DIR` env var** — nothing reads it.

Fix applied (option b — repo-relative commands): the doc shell blocks in `README.md`, `docs/QUICKSTART.md`, `docs/REFERENCE_COMMANDS.md`, `docs/REPLAY_DEMO.md`, `frontend/desktop-overlay/README.md` now use repo-relative `cd` (`cd backend`, `cd frontend/launcher`, …) instead of an absolute locale-specific path, so they don't depend on folder names like `Документы` vs `Documents`. `docs/PACKAGING_WINDOWS.md` keeps its `C:\path\to\dota-ai-coach` placeholder (Windows-specific). When adding new docs, prefer repo-relative commands; use a `<repo-root>` placeholder with a one-line note only where an absolute path is genuinely unavoidable.
