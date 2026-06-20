# Replay Demo

Replay demo mode lets the coursework defense show the overlay without launching Dota 2.

The demo reads an existing GSI-like JSONL file, sends states to the backend through the normal demo endpoint, and lets the backend produce real advice through the recommender and scheduler.

## Demo Files

Primary demo inputs:

```text
data/match_simulations/replay_gsi_like_match_8843382732_pl_20_30.jsonl
data/match_simulations/replay_gsi_like_match_8843471434_jugg_10_20.jsonl
```

Recommended defense demo:

- Phantom Lancer 20-30 macro/farming.
- Speed `5`.
- Advice hold `8` seconds.
- Fallback-only for stability.

## Run Demo Playback

```bash
cd ~/Study/CourseWork/dota-ai-coach/backend
source .venv/bin/activate
SIMULATION_USE_LLM=false \
python3 scripts/run_overlay_demo.py \
  --simulation-file ../data/match_simulations/replay_gsi_like_match_8843382732_pl_20_30.jsonl \
  --speed 5 \
  --advice-hold-seconds 8
```

The script prints only newly shown advice events by default. Use `--verbose` for every state.

## Export Session Summary

```bash
SIMULATION_USE_LLM=false \
python3 scripts/run_overlay_demo.py \
  --simulation-file ../data/match_simulations/replay_gsi_like_match_8843382732_pl_20_30.jsonl \
  --speed 5 \
  --advice-hold-seconds 8 \
  --export-summary simulation_results/demo_session_summary_pl_20_30.md \
  --export-summary-json simulation_results/demo_session_summary_pl_20_30.json
```

Summary endpoint during/after a demo:

```text
GET http://127.0.0.1:8000/demo/session-summary
```

## What The Overlay Should Show

- `DEMO REPLAY MODE`
- hero
- simulated time
- stage
- advice action
- reason
- priority
- source/confidence

## Launcher Presets

The Electron launcher includes demo buttons for:

- Phantom Lancer 20-30 macro
- Juggernaut 10-20 safety

Clean logs are intended for defense. Verbose logs are for debugging.

## Evaluation Artifacts

The final replay evaluation summary is stored at:

```text
backend/simulation_results/replay_evaluation_summary_20260608.md
backend/simulation_results/replay_evaluation_summary_20260608.csv
```

## Limits

Replay-derived GSI-like states may include missing or inferred fields. The current minimal replay parser does not reconstruct every live GSI signal. Advice therefore avoids claims that require exact enemy positions, exact team readiness, or exact objective context.
