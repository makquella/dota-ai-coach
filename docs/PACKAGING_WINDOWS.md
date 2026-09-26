# Windows Packaging

Dota AI Coach ships on Windows as **one desktop app** that works on an "open and forget" basis:

- one Electron process with two windows: the control panel and the always-on-top advice overlay;
- the bundled PyInstaller backend is started automatically and hidden (no console window);
- the backend listens on a free local port (the last used one, 8000 on first run when free, otherwise any free port); the port is handed to both windows and written into the Dota 2 GSI config;
- single instance: starting the app again just brings the existing window to the front;
- closing the window hides it to the tray. Tray menu: **Open**, **Overlay** (on/off), **Start with Windows**, **Quit**;
- **Quit** stops the backend gracefully (`shutdown` on its stdin, uvicorn finishes and exits with code 0); force-kill is only a fallback after 8 s. If the app itself crashes, the backend notices stdin EOF and exits on its own;
- a backend that crashes is restarted automatically (up to 3 times in 2 minutes).

The app does not read game memory, read the screen, automate input, or inject into Dota 2. Dota 2 talks to it only through Game State Integration.

## Build With One Command

Prerequisites (build on Windows; PyInstaller and Electron produce platform-specific binaries):

- Windows 10/11
- Python 3.11+ on `PATH` (or pass `-Python C:\path\to\python.exe`)
- Node.js 20+ with npm

From the repository root:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build-windows.ps1
```

or double-click `scripts\build-windows.cmd`.

The script:

1. creates `backend\.venv` if missing and installs `backend\requirements-build.txt` (runtime deps + pinned PyInstaller);
2. builds the backend with `backend\packaging\dota_ai_coach_backend.spec`;
3. runs `npm ci` in `frontend\launcher`;
4. runs `electron-builder --win nsis --publish never`.

Options: `-Portable` also builds the optional single-file portable exe; `-SkipBackend` reuses an existing `backend\dist` build.

Output:

```text
frontend\launcher\dist\DotaAICoach-Setup-0.1.0.exe        <- NSIS installer (give this to users)
frontend\launcher\dist\win-unpacked\DotaAICoach.exe       <- unpacked app, runs without installing
backend\dist\dota-ai-coach-backend\dota-ai-coach-backend.exe
backend\dist\dota-ai-coach-backend\dota-ai-coach-demo-playback.exe
```

No code-signing certificate is configured, so the build sets `CSC_IDENTITY_AUTO_DISCOVERY=false` unless `CSC_LINK` is set. Unsigned installers may trigger a SmartScreen warning on first run.

## Installer

The NSIS installer is a one-click, per-user install (no admin rights):

- installs to `%LOCALAPPDATA%\Programs\<app>\DotaAICoach.exe`;
- creates Start menu and desktop shortcuts named **Dota AI Coach**;
- starts the app when installation finishes;
- keeps `%APPDATA%\DotaAICoach` (settings, logs, recordings) on uninstall.

Silent install: `DotaAICoach-Setup-0.1.0.exe /S`.

## Smoke Test

```powershell
powershell -ExecutionPolicy Bypass -File scripts\smoke-windows.ps1
```

It checks, in order:

1. `dota-ai-coach-backend.exe` alone: starts on a free port via `DOTA_AI_BACKEND_PORT`, answers `/health` and `/overlay/recommendation`, writes session records under `%APPDATA%\DotaAICoach`, and exits with code 0 after `shutdown` on stdin;
2. `win-unpacked\DotaAICoach.exe --smoke-test=<result.json>`: the real app starts its bundled backend hidden, loads both windows, checks `/health`, stops the backend gracefully and exits 0; no backend process may be left behind;
3. the NSIS installer: silent install, then the same smoke test against the installed exe (`-SkipInstaller` skips this part).

CI runs `scripts\build-windows.ps1` and `scripts\smoke-windows.ps1` on `windows-latest` (job `windows-package` in `.github/workflows/ci.yml`) and uploads the installer as a build artifact.

## Runtime Layout

Packaged app (`process.resourcesPath` = `resources\`):

```text
DotaAICoach.exe
resources\app.asar                                  <- launcher + overlay windows
resources\backend\dota-ai-coach-backend.exe
resources\backend\dota-ai-coach-demo-playback.exe
resources\backend\_internal\                        <- PyInstaller runtime (sys._MEIPASS)
resources\backend\_internal\data\                   <- heroes, meta, knowledge_base
resources\data\match_simulations\*.jsonl            <- replay demo presets
resources\README.md
```

Writable files never go into the install directory:

```text
%APPDATA%\DotaAICoach\settings.json                 <- port, overlay position/lock, tray hint
%APPDATA%\DotaAICoach\logs\launcher.log             <- launcher + backend output
%APPDATA%\DotaAICoach\logs\*.json                   <- per-recommendation logs (backend)
%APPDATA%\DotaAICoach\session_records\              <- live GSI recordings
%APPDATA%\DotaAICoach\simulation_results\           <- deep replay reviews
%APPDATA%\DotaAICoach\gsi_debug_samples\            <- only with GSI_DEBUG_LOG=true
%APPDATA%\DotaAICoach\.env                          <- optional backend settings (e.g. GSI_DEBUG_LOG=true)
```

`backend/app/config.py` decides this from `sys.frozen`: read-only data comes from `sys._MEIPASS`, writable paths from `%APPDATA%\DotaAICoach`, the port from `DOTA_AI_BACKEND_PORT`. In a source checkout nothing changes: data from `data/`, writable files under `backend/`.

## Backend Process Contract

The app starts `dota-ai-coach-backend.exe` with:

| Variable | Value |
|---|---|
| `DOTA_AI_BACKEND_HOST` | `127.0.0.1` |
| `DOTA_AI_BACKEND_PORT` | the free port picked by the app |
| `DOTA_AI_BACKEND_STDIN_CONTROL` | `1` — stop gracefully on `shutdown` line or stdin EOF |
| `USE_LLM`, `SIMULATION_USE_LLM` | `false` |
| `LIVE_CONSERVATIVE_MODE` | `true` |

Running the backend exe by hand still works; without `DOTA_AI_BACKEND_STDIN_CONTROL` it ignores stdin and stops on Ctrl+C:

```powershell
cd frontend\launcher\dist\win-unpacked\resources\backend
$env:DOTA_AI_BACKEND_PORT = "8000"
.\dota-ai-coach-backend.exe
curl.exe http://127.0.0.1:8000/health
```

## Dota 2 GSI

`Install / Check Dota GSI` in the control panel writes `gamestate_integration_dota_ai_coach.cfg` into Dota's `gamestate_integration` folder with `uri "http://127.0.0.1:<port>/gsi"`. The app reuses the last port between launches, so the config stays valid. If that port is taken by another program, the app picks another one and rewrites the installed config automatically; restart Dota 2 in that case, because Dota reads GSI configs only at start.

## Development Mode

`cd frontend/launcher && npm install && npm run dev` runs the same app from sources. The backend is started as `backend/.venv` Python running `backend/packaging/backend_server.py` (no `--reload`), with the same port selection and graceful shutdown. `DOTA_AI_BACKEND_PORT=<port> npm run dev` forces a port.

## Troubleshooting

### Backend does not start

Open the control panel (tray → Open) and read the log panel, or `%APPDATA%\DotaAICoach\logs\launcher.log`. Then run the bundled backend directly (see *Backend Process Contract*) to see its console output.

### Overlay does not show

Check tray → **Overlay** is ticked, or press `Ctrl+Alt+O`. Dota 2 must run in *Borderless Window* or *Windowed Fullscreen*.

### Autostart does not work

**Start with Windows** is available only in the installed/unpacked build (not `npm run dev`). It registers `DotaAICoach.exe --hidden`, which starts the app straight into the tray.

## Known Limitations

- No code signing.
- The optional portable exe (`-Portable`) unpacks itself on every start and is slower to launch than the installed app.
- Optional LLM runtime is not bundled; the packaged app forces `USE_LLM=false`.
- Replay demo presets use bundled GSI-like replay states, not live Dota 2.
