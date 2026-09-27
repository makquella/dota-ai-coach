# AGENTS.md

Onboarding for OpenCode agents. Only non-obvious, repo-specific facts. See `docs/` for full tutorials.

## Layout

Two independent packages, no monorepo tooling:
- `backend/` — Python 3.11 FastAPI app. Package is `app/`, entrypoint `app.main:app`. **Run all backend commands from `backend/`.**
- `frontend/` — one Electron app, `launcher/`: control panel window + always-on-top overlay window + tray; it runs the backend itself. `frontend/overlay.html` + `script.js` are a legacy browser debug overlay.
- `site/` — the project website: static landing (`index.html` + `styles.css` + `app.js`, no build), ru in the HTML and en in `app.js`; downloads resolve to the latest GitHub release; every picture is real: app windows (`site/assets/app/{ru,en}/`) and overlay cards (`site/assets/overlay/`) and review cards are shot from the real renderer on a demo backend with `scripts/site-shots/` (see its README); gameplay frames come from the Dota 2 Steam page and portraits from Valve's CDN (`game_frames.py`); no drawn mockups, no fake reviews. Live at `https://luhovyimvp.dev` (GitHub Pages; DNS in Cloudflare, DNS-only records; canonical/og URLs point there). Deploy notes in `site/README.md`; `.github/workflows/pages.yml` publishes it to GitHub Pages (manual run).
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

Live pipeline check: `python scripts/simulate_live_gsi.py [--lang ru --reasons | --session <raw_gsi_states.jsonl>]` feeds raw GSI (synthetic match or a recorded session) through `POST /gsi` → `/overlay/recommendation` with the scheduler clock on game time and prints every advice card — use it after changing live advice logic (replay-state simulations skip GSI normalization, where live-only bugs hide).

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
- `PLAYER_SERVICE` (`app.player_api`): SQLite store, match tracker, job queue (reconfigured per test)

`tests/conftest.py` has an **autouse** `reset_runtime_state` fixture that clears all of these before and after every test, and inserts `backend/` onto `sys.path` so `from app...` imports resolve. When writing tests, rely on this fixture. When reasoning about server behavior, remember these carry cross-request state. The `client` fixture returns a FastAPI `TestClient`.

**Advice language.** The pipeline produces English text only. `app/advice_i18n.py` translates the visible fields (`recommendation.action/reason`, `message`, `last_visible_advice`) at the API edge when the launcher asks with `lang=ru` (`/overlay/recommendation`, `/advice/recent`); history, logs and recordings stay English. When you add or change a visible advice string, add its Russian to `_RU_EXACT` (or `_RU_PATTERNS` for texts with a hero/ability name) — `tests/test_advice_i18n.py` replays the fixtures plus mutated live GSI and fails on any visible text without a translation. Unknown text falls back to English, never half-translated.

Buyback reserve: `app/buyback_tracker.py` (fed by `MatchMemory.observe_state`) sets `extra_context.buyback_spent` for 60 s of game time when, from minute 30, a purchase of 400+ gold takes the gold from at least the buyback cost to below it while buyback is ready and the hero is alive; `post_laning_coach` turns it into `post_laning_buyback_reserve` ("Farm back your buyback gold…" with the gold and cost; pressure advice wins) — texts in `_RU_EXACT` / `_RU_PATTERNS`.

TP scroll: `app/tp_tracker.py` reads the raw GSI items (`teleport0` TP scroll or Boots of Travel in the inventory → `extra_context.has_tp`, None without an items block); after 10:00, 60+ s alive without a TP → `tp_missing` → `post_laning_carry_tp` (lower value; pressure advice and a farm stall win; text starts with «Keep…» so the UX policy leaves it as is). Synthetic fixture streams have no TP slot: `simulate_live_gsi.py` adds one.

Spend while dead: when the post-laning death review fires (`post_laning_death_route_reset`, same category so the scheduler still shows it once per death) and the dead hero has 1000+ gold beyond the buyback cost (after 30:00; no buyback cost known → no advice), the text becomes «buy parts of your next item now» (`_spend_while_dead` in `post_laning_coach.py`, RU in `_RU_PATTERNS`); the other death reviews (before 10:00, repeated deaths, escape on cooldown, low resources) keep their action and take that sentence as their reason (`DEATH_ACTION_TYPES` in `recommender.py`).

Live farm signals: `app/farm_tracker.py` (fed by `MatchMemory.observe_state`, one sample per 5 s of game clock) sets `extra_context.farm_stall` when, after minute 12, a hero who farmed 2.5+ LH/min took ≤3 last hits in the last 4 minutes while alive; `post_laning_coach` turns it into `post_laning_farm_stall` (lower-value for the scheduler; pressure advice wins), and `post_laning_farm_recovery` (only for a real gap: `farm_quality` "low" counts when 8+ last hits and 8%+ under the pace, `_effective_farm_quality`) names the pace ("38 last hits at minute 18; a good pace is 98+") — both texts have `_RU_PATTERNS`.

Hero coverage (`schemas.hero_coverage`): the 21 `SUPPORTED_HEROES` get the full carry advisor; any other Dota hero (`safety_only_hero`, npc or title-cased live name) gets survival advice only — `main._covered_decision_point` turns every decision outside `SAFETY_ONLY_DECISIONS` (LOW_HP family, deaths, disables, mana, buyback, smoke) into `NO_ADVICE`; `hero_coverage` is in overlay and `/gsi/status` answers, and Home says so. Non-heroes stay `unsupported_hero`.

`app/scheduler/` is a subpackage factored out of the large `advice_scheduler.py` (hashing, heartbeat, safety_predicates, state, types). Load the **advice-policy** skill before changing advice/scheduler/safety logic.

## Player history and post-match reviews

Separate from the live advice path (it never gates or changes live advice):
- `app/player_service.py` (singleton `PLAYER_SERVICE` in `app/player_api.py`, routes under `/player`) links the Steam account (auto from GSI `player.steamid` the first time; manual via `app/steam_ids.py`: Friend ID, SteamID64, profile/OpenDota/Dotabuff URL, Steam2/3; vanity `/id/` URLs are rejected) and keeps the match table in SQLite (`app/player_store.py`, `PLAYER_DATA_DIR/coach.sqlite3`). A different account seen in GSI later is offered as `detected`, never switched silently.
- `app/match_tracker.py` records the whole local-player match from raw GSI (`POST /gsi` → `PLAYER_SERVICE.observe_gsi`): a sample every 15 s of clock, deaths with unspent gold, buybacks, items by first appearance, team scores. Finishes on `POST_GAME`, a new match id, or 10 min without GSI (`check_stale`, called from `/gsi/status`); matches under 5 min or with no hero are dropped, and spectator GSI (watching a replay or a live game: per-team `player.team2/team3` blocks, `is_spectator_payload`) is ignored; the in-progress timeline is saved to disk and survives a restart.
- Game modes: `is_reviewable_match` (`dota_constants.py`) keeps only `REVIEWABLE_LOBBY_TYPES` × `REVIEWABLE_GAME_MODES` (All Pick, CM, RD, SD, AR, Least Played, CD, Ranked AP; unknown = yes). Turbo, Ability Draft, ARDM, bots etc. are skipped by the sync (count in meta `skipped_modes:<account>` → `/player/matches` `skipped`, shown under the table), dropped from older databases on the next sync, and a GSI-recorded match is deleted when its OpenDota fetch shows such a mode.
- `app/opendota.py` (sync `requests`, 1.1 s between calls — 0.25 s with an API key — 10 s connect / 60 s read timeout with one retry on a timeout, since a player's history can take OpenDota 30 s; `OpenDotaError.code`; the key is masked in error messages). The key is optional: `OPENDOTA_API_KEY` in `.env`, or entered in Settings → «Данные матчей» (`/player/opendota`, stored in the store's `meta`, never returned — only `key_hint`; the launcher key wins over `.env`) + a one-thread `JobQueue` in the service: sync profile + last 50 matches, review the latest 12 (and ask OpenDota to parse the 5 newest unparsed ones of the last week), then rebuild those reviews once all of them ran (`_rebuild_recent`: the draft's role history needs the older matches); after a live match, fetch it after 2 min and request a replay parse, re-polling every 90 s. Offline, everything works from the GSI timeline.
- `app/match_facts.py` merges OpenDota (parsed or basic) and GSI into one facts dict → `app/post_match_analysis.py` (deterministic sections laning/farm/survival/fights/items/vision, 0-100 scores, findings with ids + params, series, moments; OpenDota benchmark percentiles preferred over static role targets) → `app/analysis_texts.py` renders ru/en titles/texts/drills (every finding id must exist in both languages; tested) → `app/career_analysis.py` (win rate, last-10-vs-previous-10 trends, heroes, recurring findings, focus plan).
- Build advice and rank comparison (both inside `analyze_match`, both optional): `app/hero_meta.py` works on OpenDota meta cached in the store's `cache` table (`/constants/items`, `/heroes/{id}/itemPopularity`, `/scenarios/itemTimings`: 7 days; `/heroStats`: 1 day). It is fetched only on the job thread (`_ensure_hero_meta` before a match fetch, `_ensure_hero_stats` on sync); reviews read the cache only, so they rebuild offline from stale data. `app/build_analysis.py`: the player's build items vs the win rate per purchase-time bucket, compared with the **typical (median) bucket**, not the best one (the earliest buckets are mostly games that were already won), plus the pro build. `app/peer_analysis.py`: the same-role player(s) of each match stand in for "your rank" (matchmaking; roles from lanes in a parsed replay, else the farm order inside each team — `player_roles`); peer findings replace their generic twins (`REPLACED_BY_PEER` in `post_match_analysis.py`), and improvements are capped at 2 per section. Career: same-role averages over analysed matches + hero win rate in the player's rank bracket.
- Today line: `/player` status carries `today` (matches since local midnight: games, wins/losses, average score, focus met/total — reviews are read only when a focus is set, since the status is polled every ~5 s); the home screen shows it under the review banner.
- Personal baseline (`app/personal_baseline.py`): `detail.baseline` compares the match's score, GPM, LH@10 and deaths with the player's other matches on the same hero (up to 20, needs 3+); `tone` good/bad/same (small differences read as «как обычно»). Shown as a line of chips in the review header.
- Focus goal (`app/focus_goal.py`): the player picks one recurring problem on Progress (`POST/DELETE /player/focus`, meta `focus:<account>`); every analysed match started after that is judged by `match_result`: the problem's family (`FAMILIES`: generic, static and peer twins) absent from `analysis.problems` (all improve ids before the per-section cap) = done; `None` when the match could not show it (section missing, or `REQUIRES` block such as `advice`/`map`/`build`/`peers` empty). → `career.focus` (last 10 results, met/total/streak), `detail.focus` (also passed to the AI coach as `player_focus`; the personal baseline is not, since it changes with every new match and would invalidate cached reviews), `last_review.focus_met` for the tray notice, and the game plan's last line («Ваш фокус: …»).
- Game plan (`app/game_plan.py`, `PlayerService.game_plan`, cached 60 s): from pick until clock 1:30, while the card is free (`no_advice | monitoring | unsupported_hero`, live GSI only), `/overlay/recommendation` adds `game_plan` {title, hero, role, lines}: LH target at 10:00 for the usual role on the hero (+ own average; none for support, none for a non-carry-advisor hero with no reviews yet), the most popular mid/early build item with its typical (median) timing and win rate from the cached OpenDota meta, and the top recurring mistake (on the hero with 3+ reviews, else overall). Built in the request language directly (not via `advice_i18n`). The overlay shows it as a plan card.
- Advice log: every new live advice (English, with clock, decision point and mode) is noted on the in-progress timeline (`PLAYER_SERVICE.note_live_advice` from `/overlay/recommendation`, capped at 80) → `facts.advice_log` → `analysis.advice` (first 40), translated to Russian at render time with `advice_i18n.translate_ru`; the review shows it as «Подсказки во время матча». `app/advice_follow.py`: a death within 30 s after urgent advice counts as a warning not acted on (`analysis.advice_follow`, marked in that card); 2+ in a match → `died_after_warning` (survival).
- Map (`app/map_analysis.py`, `analysis.map`, «Карта матча» card drawn by `LauncherCharts.map` as a schematic map, no game art): positions are absolute replay units (centre 16384; live GSI world coordinates are shifted at the edge — `gsi_state._map_coordinate`, `match_tracker.map_position`). The GSI timeline stores the hero's position in every 15 s sample and the last alive position at each death; a parsed OpenDota replay adds `obs_log`/`sen_log` wards and `lane_pos` (128-unit cells). Deaths get a side (own/river/enemy by x + y); 3+ deaths after 10:00 with 60 %+ on the enemy half → `deaths_enemy_half` (survival).
- Draft (`app/draft_analysis.py`, needs the enemy lineup, so OpenDota matches only): cached `/heroes/{id}/matchups` (7 days, fetched for the played hero + the player's pool by `_ensure_matchups` on the job thread) → your hero's win rate vs each enemy, the pool hero with the best average edge vs this lineup (`draft_better_pick`; only pool heroes the player plays in this match's role: the most common role of their reviewed games on the hero, else OpenDota's `/heroStats` role tags, `fits_role`), and a small curated `COUNTERS` table (evasion/illusions/invisibility/healing → items, per role) → `counter_item_missing` / `counter_item_bought` (items from the purchase log, else the final inventory — item ids via the cached constants' `by_id`; neither known → no counter advice, `bought_items`). `draft_better_pick` is lineup-specific, so it is excluded from career recurring problems (`NOT_RECURRING`). `app/self_compare.py`: on the most played hero (6+ reviewed matches) the best third of games by score vs the worst third (LH@10, GPM, deaths, lane deaths, KP, first big item per group) → `career.self_compare`. Bump `ANALYSIS_VERSION` in `post_match_analysis.py` (now 5) when rules change: older stored reviews are rebuilt when read.
- Tests: `tests/test_player_history.py` with `tests/match_fixtures.py` (schema-faithful synthetic OpenDota matches, `FakeOpenDota`, whole-match GSI streams). `conftest.py` reconfigures `PLAYER_SERVICE` per test (tmp dir, no client, `auto_start=False`; run jobs with `service.jobs.run_pending(until=float("inf"))`).

## Local policy is authoritative; LLM is optional

Default `USE_LLM=false`. LLM providers only reword advice or run offline review. The backend always owns `decision_point`, `priority`, `time_window`, safety gating, and anti-spam scheduling — never let LLM output override these, and don't add hard LLM dependencies to the live path.

**Post-match AI coach** (separate from the live path and from `USE_LLM`): `app/coach_llm.py` (OpenAI-compatible chat client: **Gemini** (default, free AI Studio Flash tier, `generativelanguage.googleapis.com/v1beta/openai`, Bearer key, default `gemini-3.8-flash`), Groq and OpenRouter (free `openai/gpt-oss-120b`); JSON mode, `reasoning_effort=medium`, 120 s timeout. Free Gemini Flash models are often overloaded: on 503/429/404 it walks `FALLBACK_MODELS` (3.7 → 3.6 → 3.5 → `gemini-flash-latest`; Pro has no free quota), all busy → code `busy`, which the service retries by itself after 1/2/3 min. Google answers a wrong key with HTTP 400 → `invalid_key`) + `app/coach_review.py` (compact facts from the rendered review / career, numbers rounded as a person writes them → prompt → JSON answer → `FactChecker`: every number, `m:ss` time, hero and item in the text must appear in the facts, plus counts ≤12; 5-minute marks only as minutes («к 15-й минуте»), so "50 last hits" must still be a fact; failing sentences are dropped, >25 % dropped → one retry with the offending tokens → else error `unverified`). Compare models on one match: `scripts/compare_coach_models.py --model gemini:gemini-3.8-flash --model openrouter:stealth/space-bunny-alpha` (keys from env; `--data-dir`/`--match` for a real match from a copy of the app's database). The rules stay the source of every number: change facts or rules, not the checker, when a review is wrong. `PlayerService` runs it on its own `ai_jobs` queue, caches per match + language + facts hash (`coach:match:*`, `coach:career:*` in the `cache` table), shows the old review as `stale` while a new one is written, waits for OpenDota parsing (`waiting`) unless forced, and never auto-retries after an error except `busy` (1/2/3 min; 503 costs no quota). The key (and optional model id) is entered in the launcher (`/player/ai`, stored in the store's `meta` table, never returned — only `key_hint`) or taken from `GEMINI_API_KEY` / `GROQ_API_KEY` / `OPENROUTER_API_KEY` in `.env`. States in `detail.coach` / `career.coach`: `off | waiting | pending | ready | error | not_enough | none`. «Спросить тренера»: `POST /player/matches/{id}/ask` (`PlayerService.ask_match` → `coach_review.answer_question`, synchronous, 60 s client timeout; the launcher op allows 90 s) answers a free question from the match facts through the same `_generate` loop and `FactChecker` (one retry, then `unverified`); the question text is never trusted (the prompt tells the model to ignore instructions in it); the last 5 Q&A per match are kept in the cache (`coach:ask:<account>:<match>`) and returned as `detail.questions`. Tests: `tests/test_coach_ai.py` (`FakeLLM`; pass `llm=` to `PLAYER_SERVICE.configure`, run `service.ai_jobs.run_pending(until=float("inf"))`).

## Frontend tooling

No lint/typecheck. Verification is `node --check` on these seventeen files (CI runs exactly this; `npm run check` in `frontend/launcher/` does the same) plus dependency-free unit tests for the Electron-free modules (`npm test` = `node --test test/*.test.js`, also in CI):
```bash
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
node --check frontend/launcher/problem-report.js
node --check frontend/launcher/renderer/app.js
node --check frontend/launcher/renderer/charts.js
node --check frontend/launcher/renderer/matches.js
node --check frontend/launcher/overlay/app.js
node --check frontend/launcher/overlay/voice.js
node --check frontend/launcher/assets/icons/lucide.js
```
Dev: `npm install && npm run dev` inside `frontend/launcher/`. On Wayland/GNOME use `npm run dev:x11` for the overlay to stay always-on-top. Electron is pinned at 42.4.0.

Runtime check without a display server: `xvfb-run -a npx electron . --no-sandbox --smoke-test=/tmp/smoke.json` (from `frontend/launcher/`) starts the backend, loads both windows, checks `/health`, stops the backend gracefully and exits 0/1.

Windows packaging: `scripts/build-windows.ps1` (PyInstaller backend + electron-builder NSIS installer) and `scripts/smoke-windows.ps1`; CI job `windows-package` runs both on `windows-latest` (including a fake `dota2.exe` window compiled with `csc.exe` to exercise the watcher and overlay placement). Releases: bump `version` in `frontend/launcher/package.json` (+ `package-lock.json` and backend `main.py`), optionally add player-facing notes in `docs/release-notes/v<version>.md` (used instead of generated notes), push tag `v<version>` (or run the `Release` workflow by hand on `main`, which creates the tag); `.github/workflows/release.yml` builds, smoke-tests and publishes the GitHub Release (`latest.yml` + installer + blockmap) that installed apps auto-update from. Code signing is optional and secret-driven (Azure Artifact Signing via `azureSignOptions` CLI overrides in `build-windows.ps1`, or `CSC_LINK`); unsigned without secrets, and `release.yml` verifies the three signatures when signing is configured. Details: `docs/PACKAGING_WINDOWS.md`.

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
| `GEMINI_API_KEY` / `GEMINI_MODEL` | `""` / `gemini-3.8-flash` | Google Gemini, post-match AI coach only (dev key; players enter theirs in the launcher) |
| `LLAMACPP_BASE_URL` / `LLAMACPP_MODEL` | `http://127.0.0.1:8080` / `local-gpt-oss-20b` | local llama.cpp server (no key) |
| `GSI_DEBUG_LOG` | `false` | dump raw GSI samples locally |
| `LIVE_CONSERVATIVE_MODE` | `true` | conservative live gating |
| `GSI_STALE_SECONDS` | `5` | GSI freshness threshold |
| `SESSION_RECORDS_DIR` | `backend/session_records` | session record output dir |
| `DOTA_AI_BACKEND_HOST` / `DOTA_AI_BACKEND_PORT` | `127.0.0.1` / `8000` | server address for `backend_server.py` / frozen exe |
| `DOTA_AI_BACKEND_STDIN_CONTROL` | unset | `1` = stop gracefully on stdin `shutdown`/EOF (set by the launcher) |
| `PLAYER_DATA_DIR` | `<WRITABLE_DIR>/player_data` | SQLite player/match store + in-progress match timeline |
| `OPENDOTA_ENABLED` / `OPENDOTA_API_URL` / `OPENDOTA_API_KEY` | `true` / `https://api.opendota.com/api` / `""` | match history + replay parsing; tests force `OPENDOTA_ENABLED=false` |

**Frozen (PyInstaller) paths** are decided in `app/config.py` from `sys.frozen`: read-only data from `sys._MEIPASS/data` (`DATA_DIR`), writable files (`LOGS_DIR`, `SESSION_RECORDS_DIR`, `GSI_DEBUG_SAMPLES_DIR`) under `%APPDATA%\DotaAICoach` (`WRITABLE_DIR`). In a source checkout: `data/` and `backend/`. Use `DATA_DIR`/`WRITABLE_DIR` from config for new paths — never `Path(__file__).parents[...]`, which breaks in the frozen build.

**OpenAI: не найдено.** There is **no `OPENAI_API_KEY` anywhere** in the codebase. Cloud providers are Groq and OpenRouter (plus Google Gemini for the post-match AI coach only); `llamacpp` is a local server with no key. The `openai/gpt-oss-*` model names are served *through* OpenRouter/Groq — do not look for or add a direct OpenAI integration.

Script-only env (not runtime): `SIMULATION_*`, `MATCH_SIMULATION_PATH` (`scripts/simulate_match_advice.py`); `BENCHMARK_*` (`scripts/benchmark_llm_models.py`); `DOTA_DEMO_PARSER_COMMAND` (`scripts/parse_dota_demo_to_replay_events.py`). Full list in `backend/.env.example`.

## Frontend apps

One Electron app, **`frontend/launcher/`** (product name "Dota AI Coach", exe `DotaAICoach.exe`). The former separate `frontend/desktop-overlay/` app was merged into it.
- `main.js` — single-instance lock, tray (Open / Overlay / Start with Windows / Quit), close-to-tray, autostart (`--hidden`), backend process (port pick, health wait, graceful stop, crash restart ×3), replay demo presets, GSI config, IPC, `--smoke-test`.
- `renderer/` + `preload.js` — control panel window, tabs «Главная / Матчи / Прогресс / Настройки». Home: one status line with a single action (e.g. «Дота не найдена» → «Указать папку Доты»), the first-run checklist, current match, recent advice (backend `GET /advice/recent`). Settings: «Оверлей» (on/off, position preset, move by hand), «Советы» (frequency, voice), «Приложение» (autostart, updates, problem report) and the collapsed «For developers» section with every other tool (backend, GSI config, live GSI, recordings, replay demos, Deep Review, logs). Texts live in the `I18N` table in `renderer/app.js` (ru/en: `settings.language` auto | ru | en from Settings → App, auto = system locale; `uiLocale()` in main decides it for the panel, the overlay, the tray and every backend `lang=` request, sent as `status.locale`); keep both languages in sync when adding strings.
- Look: calm, neutral dark UI (no game theming, no neon, glow, gradients, glassmorphism or emoji). Design tokens live in `assets/ui/tokens.css` (colours, type scale 12/13/14/16/20/28, weights 400/500/600, 4px spacing, radii 6–10px, 120–180ms ease-out motion) and are shared by both windows — add tokens there instead of hard-coding values. One accent (`--accent`) for the primary action and active state only; `--ok/--warn/--error` only as small status dots. Font: Inter, bundled in `assets/fonts/` (OFL, no CDN — the app must work offline); numbers/timers use `tabular-nums`. Icons: Lucide subset vendored in `assets/icons/lucide.js` (`<i data-icon="name">` + `LucideIcons.hydrate()`); add an icon by copying its SVG body from `lucide-static`. Loading states are skeletons (no spinners); every control needs hover, focus-visible and disabled styles. Screenshots: `docs/screenshots/ui-v3/`.
- `overlay-window.js` + `overlay-preload.js` + `overlay/` — transparent frameless always-on-top window; its renderer asks the main process for `/overlay/recommendation` (1000 ms) and never builds backend URLs. The window exists while the overlay is enabled; `setVisible()` decides whether it is on screen, and the always-on-top timer runs only while shown.
- `overlay/voice.js` — optional spoken advice (`settings.overlay.voice`: `off | urgent | all`, the «Голос» row on Home): Chromium `speechSynthesis` with the system voices (Windows SAPI, offline), picks a local voice of the UI language, speaks only the action, once per advice; tips keep a 4 s gap and never talk over each other, urgent advice interrupts. It works in exclusive fullscreen, where the card cannot be drawn. Pure rules, tested in `test/voice.test.js`; loaded by the overlay and the control panel (voice check + sample).
- First-run checklist («Первый запуск» card on Home, `renderSetup` in `renderer/app.js`): service → Dota found → GSI config → first GSI data (`settings.gsiSeenAt`, set by `pollGsiStatus`; data also proves the two steps before it) → Steam account linked, plus the optional AI coach (`status.player.aiConfigured`). The first open step gets the primary action; the card hides itself when the required steps are done or on «×» (`settings.setupDismissed`). The career coach reports `off` before `not_enough`, so Progress offers the AI key form even before 3 reviewed matches.
- PDF export: «Сохранить PDF» on a match review and on Progress → `launcher:export-pdf` → `webContents.printToPDF` (A4, page numbers in the footer; the window background is switched to white while printing because Chromium paints the page margins with it). The look is `@media print` in `renderer/styles.css` + print tokens in `assets/ui/tokens.css` (light page, same chart hues); `.no-print` and every button/input are hidden; long cards break between rows, never inside a finding, tile, chart or table row.
- Advice frequency («Частота советов»: Реже / Обычно / Чаще, `settings.adviceFrequency`): passed to the backend as `DOTA_AI_ADVICE_FREQUENCY` at start and via `POST /settings/advice` on change. `app/scheduler/frequency.py` scales only the coaching pauses (wall-clock cooldown, coaching / same-action / post-laning game-time gaps, heartbeat; calm ×2 and no heartbeat, active ×0.6); urgent and safety advice never change (safety decisions in `UNSCALED_DECISIONS` keep the normal cooldown). `ADVICE_SCHEDULER.frequency` survives `reset()`; `conftest.py` restores `normal`.
- `problem-report.js` — the «Отчёт о проблеме» row / tray item: one text file in Downloads with launcher status, settings, watcher state, backend `GET /diagnostics` (runtime, flags, GSI, scheduler, player/jobs, the last 50 background errors recorded by `app/diagnostics.py`) and the launcher log tail; every key is redacted (tested).
- `test/i18n.test.js` cuts the text tables out of `renderer/app.js`, `renderer/matches.js`, `overlay/app.js` and fails when a key is missing in one language or a `data-i18n` key of `index.html` is undefined.
- Card size (`settings.overlay.size`: small / normal / large = zoom 0.85 / 1 / 1.25): the overlay window grows with the zoom and presets are recomputed with the scaled size.
- `overlay-placement.js` — pure geometry: presets are computed inside Dota's window (`watcher.windowRect`, physical px → `screen.screenToDipRect`), so the card follows Dota to its monitor and stays inside a windowed game; hand-placed positions fall back to a preset when their monitor is gone.
- «Что нового»: after an update main sets `settings.whatsNewPending` to the new version; status `whatsNew` shows a card on Home with the bullets from `I18N.<lang>.whatsNew[version]` in `renderer/app.js` (add them for each release; no bullets → no card) until «Понятно».
- `updater.js` — `electron-updater` from GitHub Releases, packaged NSIS build only (never in dev, portable or `--smoke-test`). Downloads in the background; installs on "Restart and update" (tray / Updates row), on quit, or unattended once Dota has been closed for 5 min and the panel is hidden — never while Dota runs. `settings.startHiddenOnce` / `updatedFrom` bring the relaunched app back hidden and show "Updated to x".
- `overlay-visibility.js` — pure rules: shown only when enabled AND (unlocked for dragging OR replay demo OR (dota2 running AND focused AND backend `/gsi/status` `in_match`)); on platforms without focus tracking it follows the switch. Also the tray status (not found / waiting for game / in game).
- `dota-watcher.js` — Windows: one hidden long-lived PowerShell helper (user32 `GetForegroundWindow`/`GetWindowThreadProcessId`/`IsIconic`/`GetWindowRect`, shell32 `SHQueryUserNotificationState`) prints JSON on change: running, focused, exe path, `windowRect` (physical px, DPI-aware helper) and `exclusiveFullscreen` (D3D exclusive fullscreen, where no overlay can be drawn; sticky until Dota exits). Exclusive fullscreen shows a tray balloon once per run, a tray menu line and a status-line warning with a "I can see the advice" dismiss (`settings.fullscreenWarningDismissed`). Exits itself when the launcher dies. Linux dev: `/proc` scan, no focus tracking.
- `steam-locator.js` — Steam root from the registry (`reg.exe query`) → `libraryfolders.vdf` → every library; Dota's uninstall key and the running `dota2.exe` path are extra hints. `checkLaunchOptions` reads `userdata/<account>/config/localconfig.vdf` (linked account, else the Steam user saved last) for Dota's `-gamestateintegration` launch option (required by Dota since 2023): status `launchOption` = ok/missing/unknown, re-checked when Dota starts; «missing» adds a setup step and, while Dota runs without GSI, a status line with «Copy option». The GSI config is installed automatically once on first run (`settings.gsiAutoInstalled`) and afterwards kept identical to the template.
- Hero portraits / item icons: `dota-assets.js` (main) serves `dota-asset://hero|hero-icon|item/<key>` — downloaded once from Valve's CDN (`cdn.cloudflare.steamstatic.com/apps/dota2/images/dota_react/...`, via `net.fetch`) into `<userData>/dota-assets/`, PNG-checked, failures not retried for 10 min. `renderer/dota-data.js` (generated by `backend/scripts/build_dota_data.py`: hero id → [name, key], item name → key; rerun after a patch adds heroes/items) + `renderer/dota-icons.js` (`DotaIcons.hero/itemKey/heroPicture/itemPicture`, UMD, also loaded by the overlay) build the elements; without a picture the initials show (`.dota-pic::before`). Used in the match table, review header, scoreboard, draft, build, heroes table, Home and the overlay plan card.
- `settings.js` — `%APPDATA%\DotaAICoach\settings.json` (Electron `userData` is set to the same folder the frozen backend writes to).
- Tabs «Главная / Матчи / Прогресс» (`renderer/matches.js`, `renderer/charts.js`): link Steam account, match table (filters by result and hero: `/player/matches?hero_id=&result=win|loss`, with `stats` of the filtered games and `heroes` for the list), progress per hero (`/player/career?hero_id=`, choices in `hero_choices` — `heroes` is the career's own hero table; no AI career review for one hero, to spare the player's quota), post-match review («Разбор тренера» AI card on top with inline key setup when off, score, focus for next game with drills, section meters, build with win rate by purchase time + pro build chips, you vs the same-role opponent, last hits/gold/XP chart vs target pace with death markers, strengths/improvements, key moments, scoreboard), progress (tiles with trend vs previous 10, AI coach review of recent games, score-by-match columns, you vs players of your rank, recurring problems + drills, heroes with win rate at your rank). The renderer calls `launcherApi.player(op, args)`; main maps ops to a fixed whitelist of `/player` paths (`PLAYER_OPS`), polls `/player` every ~5 s and shows a tray balloon «Разбор матча готов» (click opens the review). Charts are dependency-free SVG with hover/focus tooltips; chart colours are the `--viz-*` tokens (validated on `--surface-1`).

(Legacy browser debug overlay: `frontend/overlay.html` + `script.js`.)

## Doc checkout paths (resolved — no code change)

Earlier docs hardcoded a locale-specific absolute checkout path. It existed **only in documentation, never in code** — code was always portable:
- `backend/app/config.py:11` → `REPO_ROOT = Path(__file__).resolve().parents[2]`
- `frontend/launcher/main.js:8` → `REPO_ROOT = path.resolve(__dirname, "..", "..")`

So **do not touch code or add a `DOTA_AI_COACH_DIR` env var** — nothing reads it.

Fix applied (option b — repo-relative commands): the doc shell blocks in `README.md`, `docs/QUICKSTART.md`, `docs/REFERENCE_COMMANDS.md`, `docs/REPLAY_DEMO.md`, `frontend/desktop-overlay/README.md` (since removed) now use repo-relative `cd` (`cd backend`, `cd frontend/launcher`, …) instead of an absolute locale-specific path, so they don't depend on folder names like `Документы` vs `Documents`. `docs/PACKAGING_WINDOWS.md` uses repo-relative Windows commands (`scripts\build-windows.ps1`). When adding new docs, prefer repo-relative commands; use a `<repo-root>` placeholder with a one-line note only where an absolute path is genuinely unavoidable.
