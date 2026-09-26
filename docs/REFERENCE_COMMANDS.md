# Reference Commands

This file keeps longer commands out of the main README.

## Backend

```bash
cd backend
source .venv/bin/activate
USE_LLM=false uvicorn app.main:app --reload
```

With access logs reduced:

```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload --no-access-log
```

## Tests

```bash
cd backend
source .venv/bin/activate
pytest -q
python3 -m compileall -q app scripts packaging tests
```

```bash
# from repository root
git diff --check
node --check frontend/launcher/main.js
node --check frontend/launcher/preload.js
node --check frontend/launcher/settings.js
node --check frontend/launcher/overlay-window.js
node --check frontend/launcher/overlay-placement.js
node --check frontend/launcher/overlay-preload.js
node --check frontend/launcher/overlay-visibility.js
node --check frontend/launcher/dota-watcher.js
node --check frontend/launcher/steam-locator.js
node --check frontend/launcher/updater.js
node --check frontend/launcher/renderer/app.js
node --check frontend/launcher/renderer/charts.js
node --check frontend/launcher/renderer/matches.js
node --check frontend/launcher/overlay/app.js
node --check frontend/launcher/assets/icons/lucide.js
(cd frontend/launcher && npm test)   # node --test, no dependencies
```

## Launcher

```bash
cd frontend/launcher
npm install
npm run dev
```

The launcher starts its own backend (`backend/packaging/backend_server.py`) on a free port, so do not run `uvicorn` at the same time unless you need a standalone backend. `DOTA_AI_BACKEND_PORT=<port> npm run dev` forces a port.

## Windows Build (one command)

```powershell
# from repository root, on Windows
powershell -ExecutionPolicy Bypass -File scripts\build-windows.ps1
powershell -ExecutionPolicy Bypass -File scripts\smoke-windows.ps1
```

## Replay Demo

```bash
cd backend
source .venv/bin/activate
SIMULATION_USE_LLM=false \
python3 scripts/run_overlay_demo.py \
  --simulation-file ../data/match_simulations/replay_gsi_like_match_8843382732_pl_20_30.jsonl \
  --speed 5 \
  --advice-hold-seconds 8 \
  --export-summary simulation_results/demo_session_summary_pl_20_30.md \
  --export-summary-json simulation_results/demo_session_summary_pl_20_30.json
```

## Offline Simulation

```bash
SIMULATION_EXPORT_REVIEW=true \
SIMULATION_REVIEW_ONLY_SHOWN=true \
SIMULATION_USE_LLM=false \
python3 scripts/simulate_match_advice.py \
  --simulation-file ../data/match_simulations/replay_gsi_like_match_8843382732_pl_20_30.jsonl
```

## Local LLM Blocking Simulation

```bash
SIMULATION_EXPORT_REVIEW=true \
SIMULATION_REVIEW_ONLY_SHOWN=true \
SIMULATION_USE_LLM=true \
SIMULATION_LLM_BLOCKING=true \
USE_LLM=true \
LLM_PROVIDER=llamacpp \
LLAMACPP_BASE_URL=http://127.0.0.1:8080 \
LLAMACPP_MODEL=local-gpt-oss-20b \
LLM_TIMEOUT=6 \
LLM_MAX_TOKENS=700 \
python3 scripts/simulate_match_advice.py \
  --simulation-file ../data/match_simulations/replay_gsi_like_match_8843382732_pl_20_30.jsonl
```

## Compare Reports

```bash
python3 scripts/compare_simulation_reports.py --latest-two
```

## Find Local Dota Replay Files

```bash
find ~/.steam ~/.local/share/Steam ~/Steam ~/Games \
  -type f \( -iname "*.dem" -o -iname "*.dem.bz2" \) \
  -printf '%TY-%Tm-%Td %TH:%TM %s %p\n' 2>/dev/null \
  | sort -r \
  | head -20
```

## Parse Replay To Events

```bash
python3 scripts/parse_dota_demo_to_replay_events.py \
  --demo "<DEMO_PATH>" \
  --hero "Juggernaut" \
  --player-slot 1 \
  --start-minute 0 \
  --end-minute 10 \
  --output ../data/match_simulations/replay_events_real_demo_0_10.jsonl
```

## Convert Replay Events To GSI-Like States

```bash
python3 scripts/convert_replay_events_to_gsi_like.py \
  --events-jsonl ../data/match_simulations/replay_events_real_demo_0_10.jsonl \
  --hero "Juggernaut" \
  --player-slot 1 \
  --start-minute 0 \
  --end-minute 10 \
  --interval-seconds 1 \
  --output ../data/match_simulations/replay_gsi_like_real_demo_0_10.jsonl
```

## Live Session Records

Live session recordings are stored under:

```text
backend/session_records/
```

Generated runtime records are local artifacts and should not be committed unless explicitly needed for a sanitized report.
