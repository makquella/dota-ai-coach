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
- `backend/app/player_api.py`, `player_service.py`, `player_store.py`, `steam_ids.py` - linked Steam account (auto from GSI), SQLite match table, background OpenDota sync.
- `backend/app/match_tracker.py` - whole-match timeline of the local player from live GSI (samples, deaths with unspent gold, items, buybacks).
- `backend/app/opendota.py`, `match_facts.py`, `post_match_analysis.py`, `analysis_texts.py`, `career_analysis.py` - OpenDota client, merged match facts, post-match review (ru/en), statistics and advice over many matches.
- `backend/app/hero_meta.py`, `build_analysis.py`, `peer_analysis.py` - cached OpenDota meta (items, item timings, pro builds, win rate per rank), build advice, comparison with same-role players of the player's rank.
- `backend/app/draft_analysis.py`, `self_compare.py` - draft of a match (matchups vs the enemy five, best hero of your pool for it, counter items) and your best games vs your worst on your main hero.
- `backend/app/farm_tracker.py` - live "no farm lately" signal for the post-laning coach.
- `backend/app/buyback_tracker.py` - live "a purchase left less gold than the buyback costs" signal (after 30:00) for the post-laning coach.
- `backend/app/map_analysis.py`, `advice_follow.py` - match map (path, deaths, wards, lane position; deaths on the enemy half) and deaths within 30 s after an urgent advice.
- `backend/app/game_plan.py` - the overlay's plan for the first 1:30: last-hit target at 10:00, key item with its typical timing, the recurring mistake or the chosen focus.
- `backend/app/focus_goal.py` - the one problem the player works on, judged in every match played after it was chosen.
- `backend/app/personal_baseline.py` - a match against the player's usual numbers on the same hero.
- `backend/app/scheduler/frequency.py` - advice frequency preference (calm / normal / active) scaling the coaching gaps.
- `backend/app/diagnostics.py` - recent errors and runtime info for the problem report, with keys redacted.
- `backend/scripts/simulate_live_gsi.py` - raw GSI through the live endpoints on game time, printing every advice card; `backend/scripts/evaluate_system.py` - latency, replay advice, review coverage and fact-check numbers.
- `backend/app/coach_llm.py`, `coach_review.py` - optional AI coach: explains a match or the recent matches in plain words (Google Gemini Flash by default, or Groq / OpenRouter, all on free tiers), with every number, time, hero and item checked against the rule-based facts. `backend/scripts/compare_coach_models.py` compares models on the same match.
- `backend/app/advice_i18n.py` - Russian wording of the visible advice text, applied only at the API edge (`lang=ru` on `/overlay/recommendation` and `/advice/recent`); the pipeline, logs and history stay English.

## Frontend

Launcher:

- `frontend/launcher/main.js` - app lifecycle: single-instance lock, tray, autostart, backend process (free port, health check, graceful stop, crash restart), replay demo, GSI config, IPC.
- `frontend/launcher/preload.js`, `frontend/launcher/renderer/app.js` - control panel window: status line, match / recent advice / overlay settings cards, collapsed developer section; ru/en texts. Shared design tokens in `frontend/launcher/assets/ui/tokens.css`.
- `frontend/launcher/overlay-window.js` - the always-on-top overlay window and its hotkeys.
- `frontend/launcher/overlay-placement.js` - pure geometry: position presets inside Dota's window / on its monitor, reachability of hand-placed positions.
- `frontend/launcher/renderer/matches.js`, `renderer/charts.js` - Matches / match review / Progress tabs and their SVG charts.
- `frontend/launcher/updater.js` - auto-update from GitHub Releases (electron-updater): background download, install on request, on quit or once Dota is closed.
- `frontend/launcher/overlay-preload.js`, `frontend/launcher/overlay/app.js` - overlay renderer.
- `frontend/launcher/dota-watcher.js`, `steam-locator.js`, `overlay-visibility.js` - dota2.exe/foreground tracking (plus Dota's window rect and exclusive-fullscreen detection), Steam library discovery, and the rules for when the overlay is on screen.
- `frontend/launcher/settings.js` - JSON settings in the user data folder (`%APPDATA%\DotaAICoach\settings.json`).

The launcher is the only Electron app. It starts the backend hidden on a free port and hands the port to both windows over IPC (renderers never build backend URLs themselves). The overlay is transparent, frameless, always-on-top, and polls the backend for advice through the main process. It is on screen only while Dota 2 is running, is the active window, and the backend reports fresh GSI from a match (`/gsi/status` → `in_match`); alt-tab, minimizing Dota or leaving the match hides it. Exceptions: replay demo and unlocked (positioning) mode. On quit the launcher writes `shutdown` to the backend's stdin and waits for a clean exit; the backend also exits by itself if the launcher dies (stdin EOF).

## Player History And Post-Match Reviews

```text
live GSI ──> match_tracker (whole-match timeline) ──┐
                                                    ├─> match_facts ─> post_match_analysis ─> SQLite (player_store)
OpenDota (history, parsed replays) ─> opendota ─────┘                                         │
                                                                                               ├─> /player/matches/{id}  (review, ru/en)
                                                         career_analysis <─────────────────────┴─> /player/career
```

The Steam account is taken from GSI (`player.steamid`) the first time the app sees a match, or linked by hand. After a live match the review is available immediately from the app's own recording; when OpenDota has parsed the replay (requested automatically) the review is rebuilt with per-minute data, benchmarks and kill logs.

Build advice compares the player's item timings with the hero's win rate per purchase time in public matches (target: the typical timing, not the luckiest early one) and with the pro build. Rank comparison uses the same-role players of the player's own matches, since matchmaking puts players of similar rank together; over many matches it becomes "you vs players of your rank", and hero win rates are shown for the player's rank bracket. The meta data is cached in SQLite, so all of this also works offline once it has been fetched. All network work runs on one background thread and never touches the live advice path.

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

After the match, where latency does not matter, the optional AI coach turns the rule-based review into a coach's explanation (what decided the game, turning points, main mistakes with fixes, goals for the next game; the same over the recent matches on the Progress tab). The model only receives facts the rules computed and its answer is checked against them before it is shown; without a key, or on any error, the rule-based review is shown as before.

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
