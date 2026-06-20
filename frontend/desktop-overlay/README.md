# Dota AI Coach Desktop Overlay

Electron MVP for showing Dota AI Coach advice in a small always-on-top desktop window.

The overlay only reads from the local backend HTTP API:

```text
http://127.0.0.1:8000/overlay/recommendation
```

It does not inject into Dota 2, read memory, read the screen, automate input, or hook the game process.

## Start Backend

From the repo root:

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload
```

## Start Overlay

In a second terminal:

```bash
cd frontend/desktop-overlay
npm install
npm run dev
```

## Coursework Defense Demo

You can run the overlay without Dota 2 by replaying existing GSI-like simulation states into the backend.

Terminal A - backend:

```bash
cd ~/Study/CourseWork/dota-ai-coach/backend
source .venv/bin/activate
USE_LLM=false uvicorn app.main:app --reload
```

Terminal B - this overlay:

```bash
cd ~/Study/CourseWork/dota-ai-coach/frontend/desktop-overlay
npm install
npm run dev
```

Terminal C - Phantom Lancer 20-30 macro/farming demo. Use `--speed 10` during a live defense so the advice is readable; use `--speed 20` only for quick testing.

```bash
cd ~/Study/CourseWork/dota-ai-coach/backend
source .venv/bin/activate
SIMULATION_USE_LLM=false \
python3 scripts/run_overlay_demo.py \
  --simulation-file ../data/match_simulations/replay_gsi_like_match_8843382732_pl_20_30.jsonl \
  --speed 10 \
  --advice-hold-seconds 6
```

The overlay should show `DEMO REPLAY MODE`, hero, simulated time, stage, HP/Mana/LH, priority, source, confidence, one compact action, and the reason.

## Dota 2 Settings

Use one of these display modes:

- Borderless Window
- Windowed Fullscreen

Make sure your Dota 2 GSI config posts to:

```text
http://127.0.0.1:8000/gsi
```

The old browser overlay remains available at:

```text
http://127.0.0.1:8000/frontend/overlay.html
```

## Hotkeys

- `Ctrl+Alt+O` toggles overlay visibility.
- `Ctrl+Alt+M` mutes advice for 5 minutes.
- `Ctrl+Alt+L` toggles locked/click-through mode.
- `Ctrl+Alt+1` moves to top-left safe position.
- `Ctrl+Alt+2` moves to right-center.
- `Ctrl+Alt+3` moves to bottom-center above HUD.

## Click-Through And Dragging

The overlay starts locked by default. Locked mode enables click-through so the window does not steal mouse input from Dota.

When unlocked with `Ctrl+Alt+L`, the overlay can be dragged. Position and lock state are saved in:

```text
frontend/desktop-overlay/overlay.config.json
```

## Config

Default config:

```json
{
  "backendUrl": "http://127.0.0.1:8000",
  "pollIntervalMs": 1000,
  "positionPreset": "right-center",
  "locked": true,
  "opacity": 0.92,
  "autoHideMs": 8000,
  "urgentAutoHideMs": 12000
}
```

The default `right-center` position avoids the center of the screen, minimap, abilities, and inventory on typical Dota layouts. Use hotkeys if your HUD layout needs a different safe position.
