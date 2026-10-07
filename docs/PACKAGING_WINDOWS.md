# Windows Packaging

Wardly ships on Windows as **one desktop app** that works on an "open and forget" basis:

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
- Node.js 22.12+ with npm

From the repository root:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build-windows.ps1
```

or double-click `scripts\build-windows.cmd`.

The script:

1. creates the dedicated `backend\.venv-build` if missing and installs `backend\requirements-build.txt` with hashes and wheels only (locked runtime + PyInstaller), then checks dependency consistency;
2. builds the backend with `backend\packaging\dota_ai_coach_backend.spec`;
3. runs `npm ci` in `frontend\launcher`;
4. runs `electron-builder --win nsis --publish never`.

Options: `-Portable` also builds the optional single-file portable exe; `-SkipBackend` reuses an existing `backend\dist` build.

The build venv is separate from the development venv, so test-only packages do
not enter packaging through a reused dev environment. CI and releases use
Python 3.11 and the same lockfiles; see [Python dependencies](PYTHON_DEPENDENCIES.md)
for installation and lock refresh commands.

Output:

```text
frontend\launcher\dist\Wardly-Setup-0.1.0.exe        <- NSIS installer (give this to users)
frontend\launcher\dist\Wardly-Setup-0.1.0.exe.blockmap
frontend\launcher\dist\latest.yml                         <- auto-update feed (published with a release)
frontend\launcher\dist\win-unpacked\Wardly.exe       <- unpacked app, runs without installing
backend\dist\dota-ai-coach-backend\dota-ai-coach-backend.exe
backend\dist\dota-ai-coach-backend\dota-ai-coach-demo-playback.exe
```

No code-signing certificate is configured, so the build sets `CSC_IDENTITY_AUTO_DISCOVERY=false` unless `CSC_LINK` is set. Unsigned installers may trigger a SmartScreen warning on first run.

## Installer

The NSIS installer is a one-click, per-user install (no admin rights):

- installs to `%LOCALAPPDATA%\Programs\<app>\Wardly.exe`;
- creates Start menu and desktop shortcuts named **Wardly**;
- starts the app when installation finishes;
- keeps `%APPDATA%\DotaAICoach` (settings, logs, recordings) on uninstall.

Silent install: `Wardly-Setup-0.1.0.exe /S`.

## Smoke Test

```powershell
powershell -ExecutionPolicy Bypass -File scripts\smoke-windows.ps1
```

It checks, in order:

1. `dota-ai-coach-backend.exe` alone: starts on a free port via `DOTA_AI_BACKEND_PORT`, answers `/health` and `/overlay/recommendation`, writes session records under `%APPDATA%\DotaAICoach`, and exits with code 0 after `shutdown` on stdin;
2. `win-unpacked\Wardly.exe --smoke-test=<result.json>`: the real app starts its bundled backend hidden, loads both windows, checks `/health`, checks that `resources\app-update.yml` exists and `electron-updater` loads, stops the backend gracefully and exits 0; no backend process may be left behind;
3. the same smoke test with a fake Dota: a plain window compiled as `dota2.exe` (with the `csc.exe` that ships with Windows) is started first; the Dota watcher must report its window rect, no exclusive fullscreen, and the overlay must be placed inside that window;
4. `dist\latest.yml` names the installer and `app-update.yml` points at GitHub Releases;
5. the NSIS installer: silent install, then the same smoke test against the installed exe (`-SkipInstaller` skips this part).

CI runs `scripts\build-windows.ps1` and `scripts\smoke-windows.ps1` on `windows-latest` (job `windows-package` in `.github/workflows/ci.yml`) and uploads the installer as a build artifact.

## Releases And Auto-Update

Installed apps update themselves from GitHub Releases of `makquella/dota-ai-coach` (`electron-updater`, `publish` in `frontend/launcher/package.json`).

To release a version:

1. bump `version` in `frontend/launcher/package.json` (and `package-lock.json`: `npm version <x.y.z> --no-git-tag-version` in `frontend/launcher`), merge to `main`;
2. push a tag `v<x.y.z>` on that commit: `git tag v0.2.0 && git push origin v0.2.0`, or, without git, open Actions -> Release -> Run workflow on `main`: the workflow takes the version from `package.json` and creates the tag `v<x.y.z>` itself when it publishes (it refuses to run if that tag already exists).

Do not create the release with GitHub's "Draft a new release" form: it creates the release itself, and the workflow then fails at the publish step because the release already exists.

The `Release` workflow (`.github/workflows/release.yml`) checks that the tag matches the version, builds and smoke-tests on `windows-latest` exactly like CI, then creates the GitHub Release with `latest.yml`, the installer and its `.blockmap`. All three are needed: the app reads `latest.yml` from the latest (non-draft, non-prerelease) release.

In the app:

- it checks 15 s after start and then every 4 hours, and downloads a new version in the background;
- a downloaded update installs when the user picks **Restart and update** (tray menu or the **Updates** row in the control panel), when the app quits, or by itself once Dota has been closed for 5 minutes and the control panel is not open. Nothing is installed while Dota runs or a match feeds GSI, manual installs included (the button and the tray item wait until Dota is closed);
- the install is silent (same per-user NSIS installer, `/S --updated`), the app starts again afterwards — hidden in the tray if it was hidden before — and shows "Updated to x.y.z";
- dev runs (`npm run dev`), the portable exe and `--smoke-test` runs never update. Logs: `[update]` lines in `launcher.log`.

Without code signing electron-updater does not verify the publisher of the downloaded installer; it checks the SHA-512 from `latest.yml` over HTTPS from GitHub.

## Runtime Layout

Packaged app (`process.resourcesPath` = `resources\`):

```text
Wardly.exe
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
%APPDATA%\DotaAICoach\player_data\coach.sqlite3      <- linked account, match table, post-match reviews
%APPDATA%\DotaAICoach\player_data\live_match.json    <- the match being recorded (deleted when it ends)
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

Finding Dota: the Steam root comes from the registry (`HKCU\Software\Valve\Steam\SteamPath`, then `HKLM\SOFTWARE\WOW6432Node\Valve\Steam\InstallPath`), then every library listed in `steamapps\libraryfolders.vdf` is checked (libraries that list app 570 first), so Dota on `D:`, `E:` … is found. Dota's own uninstall key and the path of a running `dota2.exe` are extra hints.

On first run the app installs `gamestate_integration_dota_ai_coach.cfg` into Dota's `game\dota\cfg\gamestate_integration` folder automatically (`uri "http://127.0.0.1:<port>/gsi"`, `heartbeat 2.0`). If Dota is not installed yet, it keeps trying on later launches and as soon as `dota2.exe` starts. After that it only keeps the file in sync with the current port/template, so deleting it on purpose sticks; `Install / Check Dota GSI` in the control panel installs it manually (also into a custom folder). Dota reads GSI configs only at start, so restart Dota 2 after the file is installed or changed.

## When The Overlay Is On Screen

The overlay window is shown only when all of these hold:

1. the overlay is switched on (tray → **Overlay**, `Ctrl+Alt+O`);
2. `dota2.exe` is running and its window is the active (foreground, not minimized) window;
3. the backend reports fresh GSI from a match (`GET /gsi/status` → `in_match`: data younger than `GSI_STALE_SECONDS`, a hero picked, game state strategy time … game in progress).

Alt-tab or minimizing Dota hides it within ~0.3 s; leaving the match or the main menu hides it within ~5 s. Exceptions: while a replay demo runs, and while the overlay is unlocked for dragging (`Ctrl+Alt+L`), it is shown regardless of Dota.

Tray status (Russian texts on a Russian system): **Dota not found** / «Дота не найдена» (no `dota2.exe`), **Waiting for game** / «Ждём игру» (Dota running, no match data), **In game** / «В игре».

Focus tracking uses one hidden PowerShell helper that calls `user32.dll` (`GetForegroundWindow`, `GetWindowThreadProcessId`, `IsIconic`, `GetWindowRect`) and `shell32.dll` (`SHQueryUserNotificationState`) and prints a line only when something changes; it polls every 0.3 s while Dota runs and every 1.5 s otherwise, and exits when the app exits. If PowerShell is unavailable, the overlay simply follows the on/off switch.

### Monitor And Position

The position presets (left / right / bottom) are computed inside Dota's window, not on the primary monitor: with Dota on a second monitor the card is on that monitor, and in windowed mode it stays inside the game window (above the minimap/hero panel for **Bottom**). The helper reports the window in physical pixels (it is DPI aware); the app converts it with `screen.screenToDipRect`. While Dota is minimized or closed the card stays on the monitor Dota was last seen on. A hand-placed position (**Move**) is kept as is, unless its monitor is gone, then the **Right** preset is used. The card also re-places itself when monitors are added, removed or change resolution.

### Exclusive Fullscreen

Windows does not draw other windows over a game in *exclusive* fullscreen, so the overlay cannot be seen there. The helper reads `SHQueryUserNotificationState` while Dota is focused; `QUNS_RUNNING_D3D_FULL_SCREEN` means exclusive fullscreen. The app then shows a tray balloon once per Dota run, a warning in the tray menu/tooltip and the status line «Оверлей не виден из-за полноэкранного режима» with the fix: Dota → Settings → Video → Display mode → **Borderless window**. The flag is kept until Dota exits (alt-tab does not clear it). The detection covers Direct3D exclusive fullscreen (Dota's default renderer); if it fires although the overlay is visible (e.g. Windows' fullscreen optimizations), **I can see the advice** in the status line turns the warning off for good (`fullscreenWarningDismissed` in `settings.json`).

## Development Mode

`cd frontend/launcher && npm install && npm run dev` runs the same app from sources. The backend is started as `backend/.venv` Python running `backend/packaging/backend_server.py` (no `--reload`), with the same port selection and graceful shutdown. `DOTA_AI_BACKEND_PORT=<port> npm run dev` forces a port.

## Troubleshooting

### Backend does not start

Open the control panel (tray → Open) and read the log panel, or `%APPDATA%\DotaAICoach\logs\launcher.log`. Then run the bundled backend directly (see *Backend Process Contract*) to see its console output.

### Overlay does not show

Check tray → **Overlay** is ticked, or press `Ctrl+Alt+O`. The tray status must be **In game**: if it says **Waiting for game** while you are in a match, Dota is not sending GSI — check that the config exists (control panel → `Install / Check Dota GSI`) and restart Dota 2. The hint under **Show advice over the game** in the control panel says why it is hidden. Dota 2 must run in *Borderless Window* or *Windowed*; exclusive fullscreen is detected and reported (see *Exclusive Fullscreen*).

### Advice language

Advice follows the system language: on a Russian Windows the app asks the backend for `lang=ru` and shows Russian text; otherwise English. Translations live in `backend/app/advice_i18n.py`; a text without a translation is shown in English.

### Matches tab is empty

The account is linked automatically when the app sees you in a match; otherwise link it on the **Matches** tab (Friend ID from the Dota profile, or a `steamcommunity.com/profiles/…` link). History older than the app comes from OpenDota: it needs internet and **Expose Public Match Data** enabled in Dota (Settings → Social). Matches played with the app running are always reviewed from its own recording, even offline; the full replay review follows a few minutes after the match when OpenDota has parsed it.

### Update does not arrive

Check `[update]` lines in `%APPDATA%\DotaAICoach\logs\launcher.log` and the **Updates** row in the control panel (**Check** runs a check now). The release must be published (not a draft) and contain `latest.yml`.

### Autostart does not work

**Start with Windows** is available only in the installed/unpacked build (not `npm run dev`). It registers `DotaAICoach.exe --hidden`, which starts the app straight into the tray.

## Code Signing

Unsigned installers work, but Windows SmartScreen shows "Windows protected your PC" on the first install (the user clicks **More info → Run anyway**) and some antiviruses are more suspicious of unsigned executables. Signing is wired into the build and turns on as soon as its secrets exist; without them the build and the release stay unsigned.

When signing is configured, electron-builder signs `DotaAICoach.exe`, the bundled `resources\backend\dota-ai-coach-backend.exe` and the installer; `release.yml` then checks all three with `Get-AuthenticodeSignature` and fails the release if any of them is not validly signed. Without signing it only prints a warning.

Since 2023 code signing keys must live on hardware (token or cloud HSM), so a certificate can no longer be exported to a `.pfx` for CI. The practical options:

| Option | Cost | Who can use it | In this pipeline |
|---|---|---|---|
| **SignPath Foundation** | free | open source projects: OSI licence (this repo is MIT), public repository, an already published release, maintained project; the publisher shown by Windows is "SignPath Foundation" | apply at signpath.org after the first release; needs a follow-up change to `release.yml` (SignPath's GitHub action signs the unpacked app and the installer, then `latest.yml` is regenerated for the signed installer) |
| **Azure Artifact Signing** (formerly Trusted Signing) | from $9.99/month, paid Azure subscription | organisations in the US, Canada, EU, UK and some other countries; **individual developers only in the US and Canada** | supported now: set the secrets below |
| Certificate from a CA (OV/EV) on a cloud HSM | roughly $100–400/year | anyone who passes the CA's identity check | via `CSC_LINK` only if the provider can hand a signing certificate to signtool in CI; most cloud HSMs need their own signing tool instead |

Azure Artifact Signing secrets (repository **Settings → Secrets and variables → Actions**):

| Secret | Value |
|---|---|
| `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET` | an Entra ID app registration with the *Artifact Signing Certificate Profile Signer* role on the signing account |
| `AZURE_SIGNING_ENDPOINT` | the account's regional endpoint, e.g. `https://weu.codesigning.azure.net` |
| `AZURE_SIGNING_ACCOUNT` | the Artifact Signing account name |
| `AZURE_SIGNING_PROFILE` | the certificate profile name |
| `SIGN_PUBLISHER_NAME` | the publisher name exactly as in the certificate (electron-updater also checks updates against it) |

Certificate alternative: `CSC_LINK` (base64 or URL of a `.pfx`) and `CSC_KEY_PASSWORD`, used by electron-builder's signtool path.

Once a release is signed, installed apps check the publisher of every update against `SIGN_PUBLISHER_NAME`; keep it stable between releases.

## Known Limitations

- Releases are unsigned until signing secrets are configured (see [Code Signing](#code-signing)): SmartScreen may warn on the first install; updates are verified by checksum only.
- The optional portable exe (`-Portable`) unpacks itself on every start and is slower to launch than the installed app.
- Optional LLM runtime is not bundled; the packaged app forces `USE_LLM=false`.
- Replay demo presets use bundled GSI-like replay states, not live Dota 2.
