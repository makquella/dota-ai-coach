# Windows Packaging Phase 1

This guide builds the Windows coursework-defense version of Dota AI Coach.

The recommended reliable target is:

```text
frontend\launcher\dist\win-unpacked\Dota AI Coach Launcher.exe
```

The single-file portable `.exe` is optional. If `npm run dist` hangs while signing `resources\elevate.exe`, use the `win-unpacked` build for defense and treat portable output as a known Phase 1 limitation.

The packaged launcher does not read game memory, read the screen, automate input, use STRATZ, or inject into Dota 2. It starts local bundled tools only:

- `dota-ai-coach-backend.exe`
- `Dota AI Coach Overlay.exe`
- bundled replay demo JSONL files
- the existing GSI config helper

## Prerequisites

- Windows 11
- Python 3.11+
- Node.js LTS
- npm
- PowerShell

Build on Windows for Windows output. PyInstaller and Electron produce platform-specific binaries.

## 1. Build The Backend Executables

```powershell
cd C:\path\to\dota-ai-coach\backend
.\.venv\Scripts\Activate.ps1

pip install -r requirements.txt
pip install pyinstaller
pyinstaller packaging\dota_ai_coach_backend.spec
```

Expected output:

```text
backend\dist\dota-ai-coach-backend\dota-ai-coach-backend.exe
backend\dist\dota-ai-coach-backend\dota-ai-coach-demo-playback.exe
backend\dist\dota-ai-coach-backend\_internal\
```

The backend executable starts FastAPI on:

```text
http://127.0.0.1:8000
```

It disables access logs by default. `USE_LLM=false` is the default unless the environment overrides it.

### Backend Standalone Smoke Test

Before building the launcher, verify the backend exe stays alive:

```powershell
cd C:\path\to\dota-ai-coach\backend\dist\dota-ai-coach-backend
.\dota-ai-coach-backend.exe
```

In another PowerShell window:

```powershell
curl.exe http://127.0.0.1:8000/health
```

Expected response:

```json
{"status":"ok"}
```

If the exe exits immediately:

- check the console output from `dota-ai-coach-backend.exe`;
- make sure port `8000` is free;
- rebuild the PyInstaller output after removing old `backend\build` and `backend\dist` folders.

## 2. Build The Desktop Overlay

```powershell
cd C:\path\to\dota-ai-coach\frontend\desktop-overlay
npm install
npm run dist:unpacked
```

Expected output:

```text
frontend\desktop-overlay\dist\win-unpacked\Dota AI Coach Overlay.exe
```

The launcher bundles this unpacked app as an extra resource.

## 3. Build The Launcher Win-Unpacked App

```powershell
cd C:\path\to\dota-ai-coach\frontend\launcher
npm install
npm run dist:unpacked
```

Expected output:

```text
frontend\launcher\dist\win-unpacked\Dota AI Coach Launcher.exe
```

The launcher build includes:

- `backend\dist\dota-ai-coach-backend\`
- `frontend\desktop-overlay\dist\win-unpacked\`
- `data\match_simulations\replay_gsi_like_match_8843382732_pl_20_30.jsonl`
- `data\match_simulations\replay_gsi_like_match_8843471434_jugg_10_20.jsonl`
- `README.md`

## 4. Test Win-Unpacked Launcher

Run:

```powershell
cd C:\path\to\dota-ai-coach\frontend\launcher\dist\win-unpacked
.\Dota AI Coach Launcher.exe
```

Then:

1. Click `Start Backend`.
2. Confirm launcher logs show:
   - `Starting backend: ...resources\backend\dota-ai-coach-backend.exe`
   - `Backend health check OK: http://127.0.0.1:8000/health`
3. Run:

   ```powershell
   curl.exe http://127.0.0.1:8000/health
   ```

4. Click `Start Overlay`.
5. Confirm the overlay window opens.
6. Click `Demo: Phantom Lancer 20-30 macro`.
7. Confirm advice cards appear in the overlay.
8. Click `Stop Demo`.
9. Click `Stop Overlay`.
10. Click `Stop Backend`.

For live Dota GSI testing, use `Install / Check Dota GSI`. The generated config still points to:

```text
http://127.0.0.1:8000/gsi
```

## Packaged Runtime Paths

In development mode, the launcher uses:

- `backend\.venv` Python and `uvicorn`
- `frontend\desktop-overlay\npm run dev`
- repo-local `data\match_simulations`

In packaged `win-unpacked` mode, the launcher uses `process.resourcesPath`:

- `resources\backend\dota-ai-coach-backend.exe`
- `resources\backend\dota-ai-coach-demo-playback.exe`
- `resources\backend\_internal\`
- `resources\desktop-overlay\Dota AI Coach Overlay.exe`
- `resources\data\match_simulations\*.jsonl`

The launcher starts:

- backend with `cwd = resources\backend`;
- overlay with `cwd = resources\desktop-overlay`.

## Optional Portable Build

The package config still exposes:

```powershell
cd C:\path\to\dota-ai-coach\frontend\launcher
npm run dist
```

This attempts to create:

```text
frontend\launcher\dist\Dota AI Coach Launcher-0.1.0-portable.exe
```

Known Phase 1 limitation:

- On some Windows setups, Electron Builder may hang while signing or processing `resources\elevate.exe`.
- The portable single-file exe is not required for coursework defense.
- Use `npm run dist:unpacked` and run `dist\win-unpacked\Dota AI Coach Launcher.exe` as the reliable target.

## Troubleshooting

### Backend Exits Immediately From Launcher

Run the bundled backend directly:

```powershell
cd C:\path\to\dota-ai-coach\frontend\launcher\dist\win-unpacked\resources\backend
.\dota-ai-coach-backend.exe
```

Then check:

```powershell
curl.exe http://127.0.0.1:8000/health
```

If the direct exe works but the launcher fails, check launcher logs for:

- executable path;
- cwd;
- backend stdout/stderr;
- port conflicts.

### Overlay Does Not Open

Check that this file exists:

```text
frontend\launcher\dist\win-unpacked\resources\desktop-overlay\Dota AI Coach Overlay.exe
```

Run it directly once to inspect any Electron runtime error.

### Port 8000 Is Busy

Stop other dev backends before launching the packaged version:

```powershell
netstat -ano | findstr :8000
```

Then stop the conflicting process or restart the machine.

## Known Limitations

- Phase 1 is `win-unpacked` packaging, not a signed installer.
- Portable single-file output is optional and may hang on `elevate.exe` signing/processing.
- No code signing is configured.
- NSIS installer packaging is left for a later phase.
- Optional LLM runtime is not bundled; fallback-only demo mode is recommended for defense.
- The packaged demo uses bundled GSI-like replay states, not live Dota 2.
