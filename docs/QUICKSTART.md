# Quickstart

This guide starts Dota AI Coach in development mode.

## Requirements

- Python 3.11+
- Node.js and npm
- Dota 2 only for live GSI mode

The replay demo can run without Dota 2.

## Backend

```bash
cd ~/Study/CourseWork/dota-ai-coach/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
USE_LLM=false uvicorn app.main:app --reload
```

Backend URL:

```text
http://127.0.0.1:8000
```

Useful endpoints:

- `GET /health`
- `POST /gsi`
- `POST /demo/replay-state`
- `GET /overlay/recommendation`
- `GET /gsi/debug/fields`
- `GET /demo/session-summary`

## Launcher

```bash
cd ~/Study/CourseWork/dota-ai-coach/frontend/launcher
npm install
npm run dev
```

The launcher is the preferred defense entry point. It can:

- start/stop the backend;
- start/stop the desktop overlay;
- run bundled replay demo presets;
- install/check the Dota 2 GSI config;
- show clean or verbose logs.

## Desktop Overlay

Manual start:

```bash
cd ~/Study/CourseWork/dota-ai-coach/frontend/desktop-overlay
npm install
npm run dev
```

On Fedora/GNOME Wayland, normal `npm run dev` may not keep the overlay always-on-top. For more reliable overlay testing through X11/XWayland, use:

```bash
cd ~/Study/CourseWork/dota-ai-coach/frontend/desktop-overlay
npm run dev:x11
```

The overlay polls:

```text
http://127.0.0.1:8000/overlay/recommendation
```

## Dota 2 Live GSI

Use Dota 2 display mode:

- Borderless Window
- Windowed Fullscreen

The GSI config should post to:

```text
http://127.0.0.1:8000/gsi
```

In the launcher, use `Install / Check Dota GSI` when available.

## Defense Demo Without Dota 2

Start backend and overlay, then run:

```bash
cd ~/Study/CourseWork/dota-ai-coach/backend
source .venv/bin/activate
SIMULATION_USE_LLM=false \
python3 scripts/run_overlay_demo.py \
  --simulation-file ../data/match_simulations/replay_gsi_like_match_8843382732_pl_20_30.jsonl \
  --speed 5 \
  --advice-hold-seconds 8 \
  --export-summary simulation_results/demo_session_summary_pl_20_30.md \
  --export-summary-json simulation_results/demo_session_summary_pl_20_30.json
```

Use `--speed 5` for live defense. Use `--speed 10` for quick testing.

## Optional LLM

Live mode works without LLM:

```text
USE_LLM=false
SIMULATION_USE_LLM=false
```

Local llama.cpp wording test:

```bash
cd ~/Study/llama.cpp
./build/bin/llama-server \
  -hf ggml-org/gpt-oss-20b-GGUF \
  --host 127.0.0.1 \
  --port 8080 \
  --ctx-size 2048 \
  -ngl 99 \
  --flash-attn auto \
  -b 512 \
  -ub 512 \
  -np 1 \
  --jinja \
  --chat-template-kwargs '{"reasoning_effort":"low"}'
```

Then run an offline simulation with:

```bash
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

Local policy remains authoritative for `priority` and `time_window`.
