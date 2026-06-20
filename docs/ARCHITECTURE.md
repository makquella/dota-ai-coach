# Architecture

Dota AI Coach is a local-first coursework MVP. It combines live Dota 2 GSI, deterministic advice rules, an anti-spam scheduler, and a small Electron overlay.

## Main Components

```text
Dota 2 GSI / replay demo
  -> FastAPI backend
  -> normalizer
  -> decision points
  -> fallback recommender
  -> advice scheduler
  -> overlay / launcher / recorder
```

## Backend

Key files:

- `backend/app/main.py` - FastAPI app and HTTP endpoints.
- `backend/app/gsi_state.py` - live GSI normalization.
- `backend/app/decision_points.py` - decision point selection.
- `backend/app/recommender.py` - deterministic fallback advice wording.
- `backend/app/advice_scheduler.py` - anti-spam, active advice, game-time spacing.
- `backend/app/advice_policy.py` - local priority and time-window policy.
- `backend/app/advice_context.py` - farm, HP, and position context.
- `backend/app/laning_coach.py` - laning-phase context categories.
- `backend/app/post_laning_coach.py` - post-laning farming and macro categories.
- `backend/app/hero_profiles.py` - data-driven hero profile loading.
- `backend/app/hero_safety.py` - hero survivability checks.
- `backend/app/signal_capabilities.py` - signal availability by source.
- `backend/app/live_session_recorder.py` - local live GSI session recorder.
- `backend/app/coach_summary.py` - post-session summary builder.
- `backend/app/llm_provider.py` - optional wording/review providers.

## Frontend

Launcher:

- `frontend/launcher/main.js`
- `frontend/launcher/preload.js`
- `frontend/launcher/renderer/app.js`

The launcher starts and stops the backend, overlay, and replay demo presets. It also provides clean logs for coursework defense.

Desktop overlay:

- `frontend/desktop-overlay/main.js`
- `frontend/desktop-overlay/preload.js`
- `frontend/desktop-overlay/renderer/app.js`

The overlay is transparent, frameless, always-on-top, and polls the backend for advice.

## Replay And Simulation

Important scripts:

- `backend/scripts/parse_dota_demo_to_replay_events.py`
- `backend/scripts/convert_replay_events_to_gsi_like.py`
- `backend/scripts/run_overlay_demo.py`
- `backend/scripts/simulate_match_advice.py`
- `backend/scripts/compare_simulation_reports.py`

Replay-derived states are called **GSI-like replay states**. They are useful for offline evaluation, but they are not identical to live GSI.

## LLM Role

LLM support is optional. It can improve wording during offline evaluation or controlled demos, but it does not own live safety decisions.

The backend keeps local authority over:

- decision point;
- priority;
- time window;
- cooldown and duplicate suppression;
- urgent safety handling.

## Signal Limits

Live GSI provides useful player-centric signals such as HP, mana, level, items, last hits, gold, position, alive/respawn, and ability cooldowns when present.

Signals not available from current live GSI/replay pipeline include:

- exact enemy positions;
- nearby ally/enemy counts;
- exact team readiness;
- exact teamfight context;
- exact Roshan/objective context.

When required signals are missing, advice stays cautious.

## Diagrams

- [Architecture](diagrams/architecture.mmd)
- [GSI Pipeline](diagrams/gsi_pipeline.mmd)
- [Scheduler Flow](diagrams/scheduler_flow.mmd)
