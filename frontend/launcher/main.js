const {
  app,
  BrowserWindow,
  Menu,
  Tray,
  clipboard,
  dialog,
  ipcMain,
  nativeImage,
  screen,
  shell
} = require("electron");
const { spawn } = require("node:child_process");
const fs = require("node:fs");
const http = require("node:http");
const net = require("node:net");
const os = require("node:os");
const path = require("node:path");

const { createDotaWatcher } = require("./dota-watcher");
const { createOverlayController, OVERLAY_DEFAULTS } = require("./overlay-window");
const { buildReport, reportFileName } = require("./problem-report");
const { DOTA_STATUS, dotaStatus, overlayVisibility } = require("./overlay-visibility");
const { createSettingsStore } = require("./settings");
const { dotaDirFromExecutable, gsiDirForDotaDir, locateDota } = require("./steam-locator");
const { createUpdater, UPDATE_STATUS } = require("./updater");

const APP_ID = "com.dotaai.coach";
const APP_NAME = "Dota AI Coach";
// Shared with the frozen backend (backend/app/config.py -> %APPDATA%\DotaAICoach).
const APP_DATA_DIR_NAME = "DotaAICoach";

app.setName(APP_NAME);
app.setPath("userData", path.join(app.getPath("appData"), APP_DATA_DIR_NAME));
app.setPath("sessionData", path.join(app.getPath("userData"), "electron"));

const REPO_ROOT = path.resolve(__dirname, "..", "..");
const IS_PACKAGED = app.isPackaged;
const RESOURCES_ROOT = IS_PACKAGED ? process.resourcesPath : REPO_ROOT;
const BACKEND_DIR = path.join(REPO_ROOT, "backend");
const USER_DATA_DIR = app.getPath("userData");
// Mirrors WRITABLE_DIR in backend/app/config.py.
const WRITABLE_DIR = IS_PACKAGED ? USER_DATA_DIR : BACKEND_DIR;
const LOGS_DIR = path.join(WRITABLE_DIR, "logs");
const SESSION_RECORDS_DIR = path.join(WRITABLE_DIR, "session_records");
const SIMULATION_RESULTS_DIR = path.join(WRITABLE_DIR, "simulation_results");
const LAUNCHER_LOG_PATH = path.join(USER_DATA_DIR, "logs", "launcher.log");
const README_PATH = path.join(RESOURCES_ROOT, "README.md");
const ICON_DIR = path.join(__dirname, "assets");

const BACKEND_HOST = "127.0.0.1";
const PREFERRED_BACKEND_PORT = 8000;
const BACKEND_HEALTH_TIMEOUT_MS = 45000;
const BACKEND_GRACEFUL_STOP_MS = 8000;
const BACKEND_MAX_RESTARTS = 3;
const BACKEND_RESTART_WINDOW_MS = 2 * 60 * 1000;
const GSI_STATUS_POLL_MS = 1000;
const GSI_CONFIG_NAME = "gamestate_integration_dota_ai_coach.cfg";
// --bg in assets/ui/tokens.css
const WINDOW_BACKGROUND = "#0b0b0c";

const START_HIDDEN = process.argv.includes("--hidden");
const SMOKE_TEST_RESULT = argValue("--smoke-test");
const IS_SMOKE_TEST = SMOKE_TEST_RESULT !== null;

const DEMO_PRESETS = {
  plMacro: {
    label: "Phantom Lancer 20-30 macro",
    fileName: "replay_gsi_like_match_8843382732_pl_20_30.jsonl"
  },
  juggSafety: {
    label: "Juggernaut 10-20 safety",
    fileName: "replay_gsi_like_match_8843471434_jugg_10_20.jsonl"
  }
};

const settings = createSettingsStore(path.join(USER_DATA_DIR, "settings.json"), {
  backendPort: null,
  gsiConfigPath: "",
  gsiAutoInstalled: false,
  trayHintShown: false,
  // "The overlay is visible for me" on the exclusive-fullscreen warning.
  fullscreenWarningDismissed: false,
  // Set before an update installs so the relaunched app returns the way it was.
  startHiddenOnce: false,
  updatedFrom: "",
  // First-run checklist on Home: the first GSI data seen, and "hide" pressed.
  gsiSeenAt: "",
  setupDismissed: false,
  // How often coaching advice may appear: calm | normal | active (backend scheduler).
  adviceFrequency: "normal",
  overlay: { ...OVERLAY_DEFAULTS }
});

let mainWindow = null;
let tray = null;
let isQuitting = false;
let shutdownPromise = null;
let shutdownComplete = false;

const processes = {
  backend: null,
  demo: null
};
const processStatus = {
  backend: "stopped",
  demo: "stopped"
};
const lastExit = {};
const stoppingProcesses = new Set();
const backend = {
  port: null,
  startPromise: null,
  restarts: []
};
let mode = "Live GSI";
let gsiStatus = { status: "unknown", path: "" };
let logs = "";
let logMode = "clean";
let hiddenBackendAccessLogs = 0;
let currentDemoPreset = "";
let recordingStatus = "stopped";
let launcherLogStream = null;
let dotaInstall = { steamRoots: [], libraries: [], dotaDir: "", gsiDir: "", source: "not searched" };
let dotaInstallLogged = false;
let dotaLocatePromise = null;
let autoInstallRunning = false;
const live = {
  inMatch: false,
  pollTimer: null,
  polling: false,
  details: emptyLiveDetails(),
  recentAdvice: [],
  polls: 0,
  player: null
};
// Match id of the last "review ready" balloon; a click on it opens that review.
let pendingReviewOpen = null;
const presence = { status: DOTA_STATUS.NOT_FOUND, visible: false, reason: "", code: "" };
let autostartEnabled = false;
let fullscreenBalloonShown = false;
let fullscreenWarningShown = false;

const BACKEND_NOISE_PATTERNS = [
  /GET\s+\/overlay\/recommendation\b/,
  /POST\s+\/demo\/replay-state\b/,
  /POST\s+\/gsi\b/
];

const overlay = createOverlayController({
  settings,
  getBackend: backendInfo,
  getLocale: () => uiLocale(),
  getDotaRect: () => dotaWatcher.getState().windowRect,
  onChange: () => {
    refreshPresence();
    updateStatus();
    refreshTray();
  },
  log: (message) => appendLog("overlay", message, { force: true })
});

const dotaWatcher = createDotaWatcher({
  log: (message) => appendLog("dota", message, { force: true })
});
dotaWatcher.on("change", (state) => {
  appendLog(
    "dota",
    state.running ? `dota2 running, ${state.focused ? "focused" : "in background"}` : "dota2 not running"
  );
  if (state.running && !dotaInstall.dotaDir && dotaDirFromExecutable(state.exePath)) {
    // The running game tells us where it is installed, even outside known libraries.
    autoInstallGsiOnce().catch((error) => appendLog("gsi", error.message, { force: true }));
  }
  // Follow Dota to its monitor / window (no-op when nothing moved).
  overlay.refreshPlacement();
  noteExclusiveFullscreen(state);
  refreshPresence();
  // The status screen shows the process/focus state itself, so push it even
  // when overlay visibility and the tray status did not change.
  updateStatus();
  if (fullscreenWarningActive() !== fullscreenWarningShown) {
    fullscreenWarningShown = fullscreenWarningActive();
    refreshTray();
  }
});

const updater = createUpdater({
  currentVersion: app.getVersion(),
  // NSIS build only: the portable exe and dev runs are not updated.
  supported: IS_PACKAGED && process.platform === "win32" && !process.env.PORTABLE_EXECUTABLE_DIR && !IS_SMOKE_TEST,
  // Never while Dota runs or a match feeds GSI (manual installs included).
  isGameRunning,
  // The unattended install also waits for the demo and a hidden panel.
  canInstallNow: () =>
    processStatus.demo !== "running" && !(mainWindow && !mainWindow.isDestroyed() && mainWindow.isVisible()),
  beforeInstall: ({ unattended }) => {
    const panelOpen = Boolean(mainWindow && !mainWindow.isDestroyed() && mainWindow.isVisible());
    settings.set("startHiddenOnce", unattended || !panelOpen);
    settings.set("updatedFrom", app.getVersion());
  },
  log: (message) => appendLog("update", message, { force: true })
});
updater.on("change", () => {
  updateStatus();
  refreshTray();
});

// ---------------------------------------------------------------------------
// Tray texts (Russian or English, by system locale)
// ---------------------------------------------------------------------------

const TRAY_TEXT = {
  en: {
    open: "Open",
    overlay: "Overlay",
    autostartWindows: "Start with Windows",
    autostartLogin: "Start at login",
    quit: "Quit",
    backend: "Backend",
    [DOTA_STATUS.NOT_FOUND]: "Dota not found",
    [DOTA_STATUS.WAITING]: "Waiting for game",
    [DOTA_STATUS.IN_GAME]: "In game",
    gsiInstalled: "Dota 2 GSI config installed.",
    restartDota: "Restart Dota 2 to connect.",
    fullscreenMenu: "Overlay hidden by exclusive fullscreen",
    fullscreenBalloon:
      "Dota runs in exclusive fullscreen, so the overlay cannot be drawn over it. In Dota: Settings → Video → Display mode → Borderless window. Or turn on spoken advice in the app.",
    updateDownloading: (version, percent) => `Downloading update ${version}… ${percent}%`,
    updateReady: (version) => `Restart and update to ${version}`,
    updateAfterGame: (version) => `Update ${version} installs after you close Dota`,
    updated: (version) => `Updated to ${version}.`,
    reviewReady: (score) => `Post-match review is ready${score ? `: score${score}` : ""}. Click to open it.`,
    problemReport: "Save a problem report"
  },
  ru: {
    open: "Открыть",
    overlay: "Оверлей",
    autostartWindows: "Автозапуск с Windows",
    autostartLogin: "Автозапуск при входе",
    quit: "Выход",
    backend: "Бэкенд",
    [DOTA_STATUS.NOT_FOUND]: "Дота не найдена",
    [DOTA_STATUS.WAITING]: "Ждём игру",
    [DOTA_STATUS.IN_GAME]: "В игре",
    gsiInstalled: "Конфиг GSI для Dota 2 установлен.",
    restartDota: "Перезапустите Dota 2.",
    fullscreenMenu: "Оверлей не виден: полноэкранный режим",
    fullscreenBalloon:
      "Дота запущена в эксклюзивном полноэкранном режиме — поверх него оверлей не рисуется. В Доте: Настройки → Видео → режим экрана «Окно без рамки» (Borderless window). Или включите озвучку советов в приложении.",
    updateDownloading: (version, percent) => `Загружается обновление ${version}… ${percent}%`,
    updateReady: (version) => `Перезапустить и обновить до ${version}`,
    updateAfterGame: (version) => `Обновление ${version} установится после выхода из Доты`,
    updated: (version) => `Обновлено до версии ${version}.`,
    reviewReady: (score) => `Разбор матча готов${score ? `: оценка${score}` : ""}. Нажмите, чтобы открыть.`,
    problemReport: "Сохранить отчёт о проблеме"
  }
};

function t(key, ...args) {
  let locale = "en";
  try {
    locale = app.getLocale().toLowerCase().startsWith("ru") ? "ru" : "en";
  } catch {
    // app.getLocale() is only available after "ready".
  }
  const value = TRAY_TEXT[locale][key] || TRAY_TEXT.en[key] || key;
  return typeof value === "function" ? value(...args) : value;
}

function argValue(name) {
  for (const arg of process.argv) {
    if (arg === name) {
      return "";
    }
    if (arg.startsWith(`${name}=`)) {
      return arg.slice(name.length + 1);
    }
  }
  return null;
}

// ---------------------------------------------------------------------------
// Logging
// ---------------------------------------------------------------------------

function openLauncherLog() {
  try {
    fs.mkdirSync(path.dirname(LAUNCHER_LOG_PATH), { recursive: true });
    if (fs.existsSync(LAUNCHER_LOG_PATH) && fs.statSync(LAUNCHER_LOG_PATH).size > 2 * 1024 * 1024) {
      fs.renameSync(LAUNCHER_LOG_PATH, `${LAUNCHER_LOG_PATH}.old`);
    }
    launcherLogStream = fs.createWriteStream(LAUNCHER_LOG_PATH, { flags: "a" });
    launcherLogStream.on("error", () => {
      launcherLogStream = null;
    });
  } catch {
    launcherLogStream = null;
  }
}

function send(channel, payload) {
  if (mainWindow && !mainWindow.isDestroyed()) {
    mainWindow.webContents.send(channel, payload);
  }
}

function appendLog(scope, text, options = {}) {
  const clean = String(text || "").replace(/\r/g, "").trimEnd();
  if (!clean) {
    return;
  }
  const lineParts = [];
  for (const part of clean.split("\n")) {
    const stamped = `[${new Date().toLocaleTimeString()}] [${scope}] ${part}`;
    if (launcherLogStream) {
      launcherLogStream.write(`${new Date().toISOString()} [${scope}] ${part}\n`);
    }
    if (!options.force && isHiddenLogLine(scope, part)) {
      hiddenBackendAccessLogs += 1;
      if (hiddenBackendAccessLogs % 25 === 0) {
        lineParts.push(
          `[${new Date().toLocaleTimeString()}] [launcher] clean logs hidden: backend=${hiddenBackendAccessLogs}`
        );
      }
      continue;
    }
    lineParts.push(stamped);
  }
  if (IS_SMOKE_TEST) {
    process.stdout.write(`${lineParts.join("\n")}\n`);
  }
  if (!lineParts.length) {
    return;
  }
  logs = `${logs}${lineParts.join("\n")}\n`;
  if (logs.length > 80000) {
    logs = logs.slice(-80000);
  }
  send("launcher:logs", logs);
}

function isHiddenLogLine(scope, line) {
  return logMode === "clean" && scope === "backend" && BACKEND_NOISE_PATTERNS.some((pattern) => pattern.test(line));
}

// ---------------------------------------------------------------------------
// Status
// ---------------------------------------------------------------------------

function backendUrl() {
  return backend.port ? `http://${BACKEND_HOST}:${backend.port}` : "";
}

function backendInfo() {
  return { status: processStatus.backend, port: backend.port, url: backendUrl() };
}

function gsiEndpoint() {
  const port = backend.port || Number(settings.get("backendPort")) || PREFERRED_BACKEND_PORT;
  return `http://${BACKEND_HOST}:${port}/gsi`;
}

function emptyLiveDetails() {
  return { connected: false, inMatch: false, hero: null, clockTime: null, secondsSinceLastGsi: null, stage: "unknown" };
}

function uiLocale() {
  try {
    return app.getLocale().toLowerCase().startsWith("ru") ? "ru" : "en";
  } catch {
    return "en";
  }
}

function publicStatus() {
  const dota = dotaWatcher.getState();
  return {
    locale: uiLocale(),
    live: { ...live.details },
    recentAdvice: live.recentAdvice,
    overlayPosition: overlay.position(),
    overlayVoice: overlay.voice(),
    adviceFrequency: adviceFrequency(),
    overlayLocked: !overlay.isUnlocked(),
    dotaRunning: dota.running,
    dotaFocused: dota.focused,
    dotaFullscreen: fullscreenWarningActive(),
    appVersion: app.getVersion(),
    update: { ...updater.getState(), blockedByGame: isGameRunning() },
    player: live.player,
    setup: { gsiSeen: Boolean(settings.get("gsiSeenAt")), dismissed: Boolean(settings.get("setupDismissed")) },
    overlayReasonCode: presence.code,
    backend: processStatus.backend,
    backendPort: backend.port,
    backendUrl: backendUrl(),
    gsiEndpoint: gsiEndpoint(),
    overlay: overlay.isEnabled() ? "running" : "stopped",
    overlayVisible: presence.visible,
    overlayReason: presence.reason,
    dota: presence.status,
    dotaDir: dotaInstall.dotaDir,
    demo: processStatus.demo,
    demoPreset: processStatus.demo !== "stopped" ? currentDemoPreset : "",
    recording: recordingStatus,
    gsiConfig: gsiStatus.status,
    gsiPath: gsiStatus.path,
    mode,
    llm: "off",
    logMode,
    autostart: autostartEnabled,
    autostartSupported: isAutostartSupported()
  };
}

function updateStatus() {
  send("launcher:status", publicStatus());
}

function isGameRunning() {
  return Boolean(dotaWatcher.getState().running || live.inMatch);
}

// Exclusive fullscreen: Windows does not draw other windows over the game, so
// the overlay is "shown" but invisible. Tell the user once per Dota run (tray
// balloon) and keep a warning on the status screen and in the tray menu. The
// user can dismiss it if the overlay is visible for them anyway.
function fullscreenWarningActive() {
  const dota = dotaWatcher.getState();
  return Boolean(
    dota.running && dota.exclusiveFullscreen && overlay.isEnabled() && !settings.get("fullscreenWarningDismissed")
  );
}

function noteExclusiveFullscreen(state) {
  if (!state.running) {
    fullscreenBalloonShown = false;
    return;
  }
  if (!state.exclusiveFullscreen || fullscreenBalloonShown) {
    return;
  }
  fullscreenBalloonShown = true;
  appendLog("overlay", "Dota runs in exclusive fullscreen; the overlay cannot be drawn over it.", { force: true });
  if (fullscreenWarningActive()) {
    showTrayBalloon(t("fullscreenBalloon"));
  }
}

// ---------------------------------------------------------------------------
// Dota presence: overlay visibility + tray status
// ---------------------------------------------------------------------------

function refreshPresence() {
  const dota = dotaWatcher.getState();
  const decision = overlayVisibility({
    enabled: overlay.isEnabled(),
    unlocked: overlay.isUnlocked(),
    demoRunning: processStatus.demo === "running",
    dota,
    inMatch: live.inMatch
  });
  overlay.setVisible(decision.visible);
  const status = dotaStatus({ dota, inMatch: live.inMatch });
  const visibilityChanged = decision.visible !== presence.visible || decision.reason !== presence.reason;
  const statusChanged = status !== presence.status;
  presence.visible = decision.visible;
  presence.reason = decision.reason;
  presence.code = decision.code;
  presence.status = status;
  if (visibilityChanged) {
    appendLog("overlay", `${decision.visible ? "Shown" : "Hidden"}: ${decision.reason}`);
  }
  if (statusChanged) {
    appendLog("dota", `Status: ${TRAY_TEXT.en[status]}`, { force: true });
  }
  if (visibilityChanged || statusChanged) {
    updateStatus();
    refreshTray();
  }
}

// The backend decides whether GSI is fresh and comes from a match
// (/gsi/status -> in_match); poll it so the overlay hides within ~1 s.
function startGsiPolling() {
  if (live.pollTimer) {
    return;
  }
  live.pollTimer = setInterval(pollGsiStatus, GSI_STATUS_POLL_MS);
  live.pollTimer.unref?.();
}

function stopGsiPolling() {
  clearInterval(live.pollTimer);
  live.pollTimer = null;
}

async function pollGsiStatus() {
  if (live.polling) {
    return;
  }
  live.polling = true;
  let details = emptyLiveDetails();
  try {
    if (processStatus.backend === "running") {
      const status = await requestBackendJson("/gsi/status");
      details = {
        connected: Boolean(status.gsi_connected),
        inMatch: Boolean(status.in_match),
        hero: status.hero && status.hero !== "Unknown" ? String(status.hero) : null,
        clockTime: Number.isFinite(status.clock_time) ? status.clock_time : null,
        secondsSinceLastGsi: Number.isFinite(status.seconds_since_last_gsi) ? status.seconds_since_last_gsi : null,
        stage: status.stage || "unknown"
      };
      // Advice is evaluated when someone asks for /overlay/recommendation. The
      // overlay window does that every second; when it is switched off, ask
      // here so advice keeps being produced for the "Recent advice" card.
      if (!overlay.isOpen()) {
        await fetchOverlayRecommendation();
      }
    }
  } catch {
    details = emptyLiveDetails();
  } finally {
    live.polling = false;
  }
  // Recent advice changes rarely; every third poll is enough.
  live.polls += 1;
  if (processStatus.backend === "running" && live.polls % 5 === 2) {
    pollPlayerStatus().catch(() => {});
  }
  let recentChanged = false;
  if (processStatus.backend === "running" && live.polls % 3 === 1) {
    try {
      const recent = await requestBackendJson(`/advice/recent?limit=5&lang=${uiLocale()}`);
      const items = Array.isArray(recent.items) ? recent.items : [];
      recentChanged = JSON.stringify(items) !== JSON.stringify(live.recentAdvice);
      live.recentAdvice = items;
    } catch {
      // Keep the last list; the backend may be restarting.
    }
  }
  if (details.connected && !settings.get("gsiSeenAt")) {
    settings.set("gsiSeenAt", new Date().toISOString());
  }
  const detailsChanged = recentChanged || JSON.stringify(details) !== JSON.stringify(live.details);
  live.details = details;
  if (details.inMatch !== live.inMatch) {
    live.inMatch = details.inMatch;
    refreshPresence();
  }
  if (detailsChanged) {
    // Hero and match clock on the status screen.
    updateStatus();
  }
}

function setBackendStatus(status) {
  processStatus.backend = status;
  if (status !== "running") {
    live.inMatch = false;
    live.details = emptyLiveDetails();
    live.recentAdvice = [];
    refreshPresence();
  }
  updateStatus();
  overlay.notifyBackendChanged();
  refreshTray();
}

// ---------------------------------------------------------------------------
// Child processes
// ---------------------------------------------------------------------------

function pythonExecutable() {
  const candidates = process.platform === "win32"
    ? [
        path.join(BACKEND_DIR, ".venv", "Scripts", "python.exe"),
        path.join(BACKEND_DIR, "venv", "Scripts", "python.exe"),
        "python"
      ]
    : [
        path.join(BACKEND_DIR, ".venv", "bin", "python"),
        path.join(BACKEND_DIR, "venv", "bin", "python"),
        "python3",
        "python"
      ];
  for (const candidate of candidates) {
    if (candidate.includes(path.sep) && !fs.existsSync(candidate)) {
      continue;
    }
    return candidate;
  }
  return "python";
}

function packagedExecutable(baseName) {
  const executable = process.platform === "win32" ? `${baseName}.exe` : baseName;
  return path.join(RESOURCES_ROOT, "backend", executable);
}

function demoFileForPreset(preset) {
  return path.join(RESOURCES_ROOT, "data", "match_simulations", preset.fileName);
}

function ensureExecutableExists(name, executablePath) {
  if (fs.existsSync(executablePath)) {
    return true;
  }
  appendLog("launcher", `${name} executable was not found: ${executablePath}`, { force: true });
  return false;
}

function normalizeEnv(env = {}) {
  const normalized = {};
  for (const [key, value] of Object.entries(env)) {
    if (value === undefined || value === null) {
      continue;
    }
    normalized[key] = String(value);
  }
  return normalized;
}

function spawnManaged(name, command, args, options = {}) {
  if (processes[name]) {
    appendLog("launcher", `${name} is already running.`);
    return null;
  }

  const cwd = options.cwd || REPO_ROOT;
  const safeArgs = (Array.isArray(args) ? args : []).filter((arg) => arg !== undefined && arg !== null).map(String);
  const commandLine = `${command} ${safeArgs.join(" ")}`.trim();
  if (!fs.existsSync(cwd)) {
    appendLog("launcher", `Cannot start ${name}: cwd does not exist: ${cwd}; command=${commandLine}`, { force: true });
    return null;
  }
  appendLog("launcher", `Starting ${name}: ${commandLine} (cwd: ${cwd})`, { force: true });

  let child = null;
  try {
    child = spawn(command, safeArgs, {
      cwd,
      env: normalizeEnv({ ...process.env, ...(options.env || {}) }),
      stdio: [options.stdinControl ? "pipe" : "ignore", "pipe", "pipe"],
      windowsHide: true
    });
  } catch (error) {
    appendLog(name, `Failed to start: ${error.message}; command=${commandLine}; cwd=${cwd}`, { force: true });
    return null;
  }
  processes[name] = child;
  delete lastExit[name];

  child.on("spawn", () => {
    appendLog("launcher", `${name} process started with pid ${child.pid}.`, { force: true });
  });
  child.stdout.on("data", (chunk) => appendLog(name, chunk.toString()));
  child.stderr.on("data", (chunk) => appendLog(name, chunk.toString()));
  if (child.stdin) {
    // The backend may exit before we write to it; a broken pipe is not an error here.
    child.stdin.on("error", () => {});
  }
  const finalize = (code, signal) => {
    if (processes[name] !== child) {
      return;
    }
    const wasStopping = stoppingProcesses.delete(name);
    lastExit[name] = { code, signal };
    processes[name] = null;
    appendLog(name, `Exited with code ${code ?? "null"} signal ${signal ?? "null"}.`, { force: true });
    if (typeof options.onExit === "function") {
      options.onExit({ code, signal, wasStopping });
    }
  };
  child.on("error", (error) => {
    appendLog(name, `Failed to start: ${error.message}; command=${commandLine}; cwd=${cwd}`, { force: true });
    if (!child.pid) {
      // Spawn failed; "exit" will not follow.
      finalize(null, null);
    }
  });
  // Registered before any waitForExit() listener, so bookkeeping runs first.
  child.on("exit", finalize);

  return child;
}

function waitForExit(child, timeoutMs) {
  if (child.exitCode !== null || child.signalCode !== null) {
    return Promise.resolve(true);
  }
  return new Promise((resolve) => {
    const onExit = () => {
      clearTimeout(timer);
      resolve(true);
    };
    const timer = setTimeout(() => {
      child.off("exit", onExit);
      resolve(false);
    }, timeoutMs);
    child.once("exit", onExit);
  });
}

// Returns "graceful", "forced" or "" when nothing was running.
async function stopManaged(name, { timeoutMs = 5000 } = {}) {
  const child = processes[name];
  if (!child) {
    appendLog("launcher", `${name} is not running.`);
    return "";
  }
  appendLog("launcher", `Stopping ${name}...`, { force: true });
  stoppingProcesses.add(name);
  const exited = waitForExit(child, timeoutMs);

  if (child.stdin && child.stdin.writable) {
    // Backend protocol (backend/packaging/backend_server.py): "shutdown" on
    // stdin, then EOF. Uvicorn finishes in-flight requests and exits by itself.
    child.stdin.write("shutdown\n");
    child.stdin.end();
  } else {
    try {
      child.kill("SIGTERM");
    } catch (error) {
      appendLog("launcher", `Stop signal failed for ${name}: ${error.message}`, { force: true });
    }
  }

  if (await exited) {
    return "graceful";
  }
  appendLog("launcher", `${name} did not exit within ${timeoutMs / 1000}s; forcing it to stop.`, { force: true });
  try {
    child.kill("SIGKILL");
  } catch (error) {
    appendLog("launcher", `Force stop failed for ${name}: ${error.message}`, { force: true });
  }
  await waitForExit(child, 3000);
  return "forced";
}

// ---------------------------------------------------------------------------
// Backend
// ---------------------------------------------------------------------------

function isValidPort(value) {
  const port = Number(value);
  return Number.isInteger(port) && port > 0 && port < 65536;
}

function isPortFree(port) {
  return new Promise((resolve) => {
    const server = net.createServer();
    server.unref();
    server.once("error", () => resolve(false));
    server.listen({ port, host: BACKEND_HOST, exclusive: true }, () => {
      server.close(() => resolve(true));
    });
  });
}

function ephemeralPort() {
  return new Promise((resolve, reject) => {
    const server = net.createServer();
    server.unref();
    server.once("error", reject);
    server.listen({ port: 0, host: BACKEND_HOST, exclusive: true }, () => {
      const { port } = server.address();
      server.close(() => resolve(port));
    });
  });
}

// The last used port is preferred so the Dota GSI config stays valid between
// launches; any free port is used when it is taken.
async function pickBackendPort() {
  const override = process.env.DOTA_AI_BACKEND_PORT;
  if (isValidPort(override)) {
    return Number(override);
  }
  const candidates = [settings.get("backendPort"), PREFERRED_BACKEND_PORT].filter(isValidPort).map(Number);
  for (const candidate of new Set(candidates)) {
    if (await isPortFree(candidate)) {
      return candidate;
    }
    appendLog("launcher", `Port ${candidate} is busy; looking for another one.`, { force: true });
  }
  return ephemeralPort();
}

function startBackend() {
  if (processes.backend) {
    return Promise.resolve(true);
  }
  if (!backend.startPromise) {
    backend.startPromise = launchBackend().finally(() => {
      backend.startPromise = null;
    });
  }
  return backend.startPromise;
}

async function launchBackend() {
  setBackendStatus("starting");
  const port = await pickBackendPort();
  backend.port = port;
  if (!isValidPort(process.env.DOTA_AI_BACKEND_PORT)) {
    settings.set("backendPort", port);
  }
  if (!IS_SMOKE_TEST) {
    autoInstallGsiOnce().catch((error) => appendLog("gsi", error.message, { force: true }));
  }

  const env = {
    USE_LLM: "false",
    SIMULATION_USE_LLM: "false",
    LIVE_CONSERVATIVE_MODE: "true",
    DOTA_AI_ADVICE_FREQUENCY: adviceFrequency(),
    PYTHONUNBUFFERED: "1",
    DOTA_AI_BACKEND_HOST: BACKEND_HOST,
    DOTA_AI_BACKEND_PORT: String(port),
    DOTA_AI_BACKEND_LOG_LEVEL: "info",
    DOTA_AI_BACKEND_STDIN_CONTROL: "1",
    SESSION_RECORDS_DIR
  };
  let command = pythonExecutable();
  let args = ["-u", path.join("packaging", "backend_server.py")];
  let cwd = BACKEND_DIR;
  if (IS_PACKAGED) {
    command = packagedExecutable("dota-ai-coach-backend");
    args = [];
    cwd = path.dirname(command);
    if (!ensureExecutableExists("Backend", command)) {
      setBackendStatus("stopped");
      return false;
    }
  }

  const child = spawnManaged("backend", command, args, {
    cwd,
    env,
    stdinControl: true,
    onExit: handleBackendExit
  });
  if (!child) {
    setBackendStatus("stopped");
    return false;
  }

  const healthy = await waitForBackendHealth(child, BACKEND_HEALTH_TIMEOUT_MS);
  if (processes.backend !== child) {
    return false;
  }
  if (!healthy) {
    appendLog(
      "launcher",
      `Backend did not answer ${backendUrl()}/health within ${BACKEND_HEALTH_TIMEOUT_MS / 1000}s; stopping it. Check the backend log lines above.`,
      { force: true }
    );
    // Do not leave an unhealthy process holding the port and blocking Start/Restart.
    await stopBackend();
    return false;
  }
  appendLog("launcher", `Backend is ready: ${backendUrl()}`, { force: true });
  setBackendStatus("running");
  return true;
}

function handleBackendExit({ code, wasStopping }) {
  // Recording lives in the backend process; a new backend starts with it off.
  recordingStatus = "stopped";
  setBackendStatus("stopped");
  if (wasStopping || isQuitting || IS_SMOKE_TEST) {
    return;
  }
  appendLog("launcher", `Backend stopped unexpectedly (code ${code ?? "null"}).`, { force: true });
  const now = Date.now();
  backend.restarts = backend.restarts.filter((timestamp) => now - timestamp < BACKEND_RESTART_WINDOW_MS);
  if (backend.restarts.length >= BACKEND_MAX_RESTARTS) {
    appendLog("launcher", "Backend keeps crashing; automatic restart is paused. Use Start Backend to retry.", {
      force: true
    });
    return;
  }
  backend.restarts.push(now);
  const timer = setTimeout(() => {
    if (!isQuitting && !processes.backend) {
      appendLog("launcher", "Restarting backend...", { force: true });
      startBackend();
    }
  }, 2000);
  timer.unref?.();
}

async function stopBackend() {
  const outcome = await stopManaged("backend", { timeoutMs: BACKEND_GRACEFUL_STOP_MS });
  setBackendStatus("stopped");
  return outcome;
}

async function restartBackend() {
  await stopBackend();
  backend.restarts = [];
  return startBackend();
}

async function waitForBackendHealth(child, timeoutMs) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    if (processes.backend !== child) {
      return false;
    }
    if (await isBackendReady()) {
      return true;
    }
    await delay(400);
  }
  return false;
}

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function isBackendReady() {
  if (!backend.port) {
    return Promise.resolve(false);
  }
  return new Promise((resolve) => {
    const request = http.get(`${backendUrl()}/health`, { timeout: 1200 }, (response) => {
      response.resume();
      resolve(response.statusCode >= 200 && response.statusCode < 300);
    });
    request.on("timeout", () => {
      request.destroy();
      resolve(false);
    });
    request.on("error", () => resolve(false));
  });
}

function requestBackendJson(endpointPath, method = "GET", body = undefined, timeoutMs = 2500) {
  return new Promise((resolve, reject) => {
    if (processStatus.backend !== "running") {
      reject(new Error("Backend is not running."));
      return;
    }
    const url = new URL(endpointPath, backendUrl());
    const request = http.request(
      url,
      {
        method,
        timeout: timeoutMs,
        headers: { "Content-Type": "application/json" }
      },
      (response) => {
        let responseBody = "";
        response.setEncoding("utf8");
        response.on("data", (chunk) => {
          responseBody += chunk;
        });
        response.on("end", () => {
          if (response.statusCode < 200 || response.statusCode >= 300) {
            const error = new Error(`Backend returned HTTP ${response.statusCode}: ${responseBody}`);
            error.status = response.statusCode;
            try {
              error.payload = JSON.parse(responseBody);
            } catch {
              error.payload = null;
            }
            reject(error);
            return;
          }
          try {
            resolve(responseBody ? JSON.parse(responseBody) : {});
          } catch (error) {
            reject(new Error(`Backend returned invalid JSON: ${error.message}`));
          }
        });
      }
    );
    request.on("timeout", () => {
      request.destroy(new Error("Backend request timed out."));
    });
    request.on("error", reject);
    request.end(body === undefined ? undefined : JSON.stringify(body));
  });
}

// ---------------------------------------------------------------------------
// Player: linked Steam account, match history, post-match reviews
// ---------------------------------------------------------------------------

// The renderer asks by operation name; only these paths are ever requested.
const PLAYER_OPS = {
  status: () => ["GET", "/player"],
  link: (args) => ["POST", "/player/link", { steam: String(args.steam || "").slice(0, 200) }],
  linkDetected: () => ["POST", "/player/link-detected"],
  unlink: () => ["DELETE", "/player"],
  sync: () => ["POST", "/player/sync"],
  matches: (args) => [
    "GET",
    `/player/matches?limit=${clampInt(args.limit, 1, 200, 30)}&offset=${clampInt(args.offset, 0, 100000, 0)}` +
      (/^\d{1,4}$/.test(String(args.heroId ?? "")) ? `&hero_id=${args.heroId}` : "") +
      (["win", "loss"].includes(args.result) ? `&result=${args.result}` : "")
  ],
  match: (args) => ["GET", `/player/matches/${matchIdArg(args)}?lang=${uiLocale()}`],
  refreshMatch: (args) => ["POST", `/player/matches/${matchIdArg(args)}/refresh`],
  career: () => ["GET", `/player/career?lang=${uiLocale()}`],
  // AI coach (optional; the key is kept by the backend and never sent back).
  coachMatch: (args) => ["POST", `/player/matches/${matchIdArg(args)}/coach?lang=${uiLocale()}`],
  coachCareer: () => ["POST", `/player/career/coach?lang=${uiLocale()}`],
  aiStatus: () => ["GET", "/player/ai"],
  aiSave: (args) => [
    "POST",
    "/player/ai",
    {
      provider: aiProviderArg(args),
      api_key: String(args.apiKey || "").trim().slice(0, 300),
      // Optional model id (e.g. stealth/space-bunny-alpha); empty = the service default.
      model: /^[\w./:-]{1,100}$/.test(String(args.model || "")) ? String(args.model) : null
    }
  ],
  aiClear: () => ["DELETE", "/player/ai"],
  // Optional OpenDota key (faster sync, higher limits); never sent back either.
  odStatus: () => ["GET", "/player/opendota"],
  odSave: (args) => ["POST", "/player/opendota", { api_key: String(args.apiKey || "").trim().slice(0, 100) }],
  odClear: () => ["DELETE", "/player/opendota"],
  // One real request to the provider: allow it time.
  aiCheck: () => ["POST", "/player/ai/check", undefined, 45000]
};

// Where a player gets a free key (opened in the browser).
const AI_KEY_PAGES = {
  gemini: "https://aistudio.google.com/apikey",
  groq: "https://console.groq.com/keys",
  openrouter: "https://openrouter.ai/settings/keys"
};

function aiProviderArg(args) {
  const provider = String(args.provider || "");
  if (!Object.hasOwn(AI_KEY_PAGES, provider)) {
    throw new Error("Unknown AI provider.");
  }
  return provider;
}

function clampInt(value, min, max, fallback) {
  const number = Number.parseInt(value, 10);
  return Number.isFinite(number) ? Math.min(max, Math.max(min, number)) : fallback;
}

function matchIdArg(args) {
  const id = String(args.matchId || "");
  if (!/^\d{1,20}$/.test(id)) {
    throw new Error("Invalid match id.");
  }
  return id;
}

async function playerRequest(op, args = {}) {
  const build = PLAYER_OPS[op];
  if (!build) {
    return { ok: false, code: "unknown_op" };
  }
  try {
    const [method, endpoint, body, timeoutMs] = build(args || {});
    return { ok: true, data: await requestBackendJson(endpoint, method, body, timeoutMs) };
  } catch (error) {
    const payload = error.payload || {};
    return {
      ok: false,
      status: error.status || 0,
      code: payload.code || (processStatus.backend !== "running" ? "backend_down" : "request_failed"),
      detail: payload.detail || error.message
    };
  }
}

// Every ~5 s: account + "a new post-match review is ready" (tray balloon).
async function pollPlayerStatus() {
  const result = await playerRequest("status");
  if (!result.ok) {
    return;
  }
  const status = result.data || {};
  const review = status.last_review || null;
  const reviewKey = review ? `${review.match_id}|${review.at}` : "";
  const first = live.player === null;
  const previousKey = live.player ? live.player.reviewKey : "";
  live.player = {
    linked: Boolean(status.linked),
    name: status.player ? status.player.persona_name || null : null,
    accountId: status.account_id || null,
    lastReview: review,
    reviewKey,
    aiConfigured: Boolean(status.ai && status.ai.configured),
    opendotaKey: Boolean(status.opendota_key),
    liveMatch: status.live_match || null
  };
  if (!first && reviewKey && reviewKey !== previousKey) {
    const score = review.score !== null && review.score !== undefined ? ` ${review.score}/100` : "";
    appendLog("player", `Post-match review ready for match ${review.match_id}${score}.`, { force: true });
    pendingReviewOpen = review.match_id;
    showTrayBalloon(t("reviewReady", score));
    send("launcher:player-event", { type: "review-ready", matchId: review.match_id, score: review.score });
  }
  updateStatus();
}

async function fetchOverlayRecommendation() {
  try {
    return { ok: true, data: await requestBackendJson(`/overlay/recommendation?lang=${uiLocale()}`) };
  } catch (error) {
    return { ok: false, error: error.message };
  }
}

// ---------------------------------------------------------------------------
// Replay demo
// ---------------------------------------------------------------------------

async function runDemo(presetName = "plMacro", includeDeepReview = false) {
  if (processes.demo) {
    appendLog("launcher", "Demo is already running. Stop Demo before starting another preset.", { force: true });
    return false;
  }
  if (processStatus.backend !== "running" || !(await isBackendReady())) {
    appendLog("launcher", "Backend is not ready yet. Wait for Backend: running, then retry.", { force: true });
    return false;
  }

  const preset = DEMO_PRESETS[presetName] || DEMO_PRESETS.plMacro;
  const args = [
    "--simulation-file",
    demoFileForPreset(preset),
    "--backend-url",
    backendUrl(),
    "--speed",
    "5",
    "--advice-hold-seconds",
    "8"
  ];
  if (includeDeepReview) {
    const slug = presetName === "juggSafety" ? "jugg_10_20" : "pl_20_30";
    args.push(
      "--export-deep-review",
      path.join(SIMULATION_RESULTS_DIR, `deep_review_${slug}.md`),
      "--export-deep-review-json",
      path.join(SIMULATION_RESULTS_DIR, `deep_review_${slug}.json`)
    );
  }

  const command = IS_PACKAGED ? packagedExecutable("dota-ai-coach-demo-playback") : pythonExecutable();
  const commandArgs = IS_PACKAGED ? args : ["-u", path.join("scripts", "run_overlay_demo.py"), ...args];
  if (IS_PACKAGED && !ensureExecutableExists("Demo playback", command)) {
    return false;
  }
  if (!overlay.isEnabled()) {
    overlay.setEnabled(true);
  }
  const child = spawnManaged("demo", command, commandArgs, {
    cwd: IS_PACKAGED ? WRITABLE_DIR : BACKEND_DIR,
    env: {
      PYTHONUNBUFFERED: "1",
      SIMULATION_USE_LLM: "false",
      USE_LLM: "false"
    },
    onExit: () => {
      processStatus.demo = "stopped";
      mode = "Live GSI";
      currentDemoPreset = "";
      appendLog("launcher", "Demo stopped.", { force: true });
      refreshPresence();
      updateStatus();
    }
  });
  if (!child) {
    return false;
  }
  processStatus.demo = "running";
  currentDemoPreset = preset.label;
  mode = "Replay Demo";
  refreshPresence();
  appendLog("launcher", `Demo started: ${preset.label}`, { force: true });
  updateStatus();
  return true;
}

// ---------------------------------------------------------------------------
// Live GSI helpers
// ---------------------------------------------------------------------------

async function checkLiveGsiStatus() {
  try {
    const status = await requestBackendJson("/gsi/status");
    appendLog("live", formatLiveGsiStatus(status), { force: true });
    return status;
  } catch (error) {
    appendLog("live", `Could not check live GSI: ${error.message}`, { force: true });
    return { error: error.message };
  }
}

async function setLiveRecording(active) {
  const verb = active ? "start" : "stop";
  try {
    const status = await requestBackendJson(`/session-recording/${verb}`, "POST");
    recordingStatus = status.active ? "running" : "stopped";
    appendLog("recording", `Recording ${verb === "start" ? "started" : "stopped"}: ${status.session_dir || SESSION_RECORDS_DIR}`, {
      force: true
    });
    updateStatus();
    return status;
  } catch (error) {
    appendLog("recording", `Could not ${verb} recording: ${error.message}`, { force: true });
    updateStatus();
    return { error: error.message };
  }
}

function formatLiveGsiStatus(status) {
  if (status.error) {
    return status.error;
  }
  const connection = status.gsi_connected ? "connected" : "waiting/stale";
  const seconds = status.seconds_since_last_gsi ?? "n/a";
  const hero = status.hero || "unknown hero";
  const time = status.game_time ?? "unknown time";
  const stage = status.stage || "unknown";
  const missing = Array.isArray(status.missing_important_fields) && status.missing_important_fields.length
    ? ` missing=${status.missing_important_fields.join(", ")}`
    : " missing=none";
  return `GSI ${connection}; last=${seconds}s; hero=${hero}; game_time=${time}; stage=${stage}; mode=${status.current_mode};${missing}`;
}

// "heartbeat" keeps a paused match fresh for the backend's staleness check
// (GSI_STALE_SECONDS=5); otherwise the overlay would hide during pauses.
function gsiConfigText() {
  return `"Dota AI Coach GSI"
{
  "uri"           "${gsiEndpoint()}"
  "timeout"       "5.0"
  "buffer"        "0.1"
  "throttle"      "0.1"
  "heartbeat"     "2.0"
  "data"
  {
    "provider"    "1"
    "map"         "1"
    "player"      "1"
    "hero"        "1"
    "abilities"   "1"
    "items"       "1"
    "buildings"   "1"
  }
}
`;
}

// Steam registry -> libraryfolders.vdf -> every library; the running
// dota2.exe path (from the watcher) is used as an extra hint.
function refreshDotaInstall() {
  if (!dotaLocatePromise) {
    const extraDotaDirs = [dotaDirFromExecutable(dotaWatcher.getState().exePath)].filter(Boolean);
    dotaLocatePromise = locateDota({ extraDotaDirs })
      .then((result) => {
        const changed = result.dotaDir !== dotaInstall.dotaDir;
        dotaInstall = result;
        if (changed) {
          updateStatus();
        }
        if (changed || !dotaInstallLogged) {
          dotaInstallLogged = true;
          appendLog(
            "gsi",
            result.dotaDir
              ? `Dota 2 found: ${result.dotaDir}`
              : `Dota 2 not found. Steam libraries checked: ${result.libraries.join(", ") || "none"}`,
            { force: true }
          );
        }
        return result;
      })
      .catch((error) => {
        appendLog("gsi", `Dota 2 search failed: ${error.message}`, { force: true });
        return dotaInstall;
      })
      .finally(() => {
        dotaLocatePromise = null;
      });
  }
  return dotaLocatePromise;
}

function resolveGsiDir(customPath = "") {
  const trimmed = String(customPath || "").trim();
  if (trimmed) {
    return trimmed;
  }
  // A detected install wins over the saved path, which may point at a
  // folder Dota was moved away from.
  if (dotaInstall.gsiDir) {
    return dotaInstall.gsiDir;
  }
  const saved = String(settings.get("gsiConfigPath") || "");
  if (saved && fs.existsSync(path.dirname(saved))) {
    return path.dirname(saved);
  }
  return "";
}

function checkGsiConfig(customPath = "") {
  const dir = resolveGsiDir(customPath);
  if (!dir) {
    gsiStatus = { status: "not found", path: "" };
    updateStatus();
    return gsiStatus;
  }
  const filePath = path.join(dir, GSI_CONFIG_NAME);
  const installed = fs.existsSync(filePath);
  gsiStatus = { status: installed ? "installed" : "not found", path: filePath };
  appendLog("gsi", installed ? `Config found: ${filePath}` : `Config not found in: ${dir}`);
  updateStatus();
  return gsiStatus;
}

function installGsiConfig(customPath = "") {
  const dir = resolveGsiDir(customPath);
  if (!dir) {
    gsiStatus = { status: "not found", path: "" };
    appendLog("gsi", "Dota GSI folder was not found. Enter a custom gamestate_integration path.", { force: true });
    updateStatus();
    return gsiStatus;
  }
  try {
    fs.mkdirSync(dir, { recursive: true });
    const filePath = path.join(dir, GSI_CONFIG_NAME);
    fs.writeFileSync(filePath, gsiConfigText(), "utf8");
    settings.set("gsiConfigPath", filePath);
    gsiStatus = { status: "installed", path: filePath };
    appendLog("gsi", `Installed config: ${filePath} -> ${gsiEndpoint()}`, { force: true });
  } catch (error) {
    gsiStatus = { status: "error", path: dir };
    appendLog("gsi", `Could not write GSI config: ${error.message}`, { force: true });
  }
  updateStatus();
  return gsiStatus;
}

// The backend port can change between launches (e.g. 8000 taken by another
// program), and the config template can change between versions. Keep an
// installed Dota GSI config identical to what this version would write.
function syncGsiConfig() {
  const status = checkGsiConfig();
  if (status.status !== "installed") {
    return;
  }
  try {
    if (fs.readFileSync(status.path, "utf8") === gsiConfigText()) {
      return;
    }
    fs.writeFileSync(status.path, gsiConfigText(), "utf8");
    appendLog("gsi", `Updated GSI config (${gsiEndpoint()}). Restart Dota 2 if it is already running.`, {
      force: true
    });
  } catch (error) {
    appendLog("gsi", `Could not update GSI config: ${error.message}`, { force: true });
  }
}

// First run: install the GSI config as soon as Dota 2 is found. Once it has
// been installed (or found installed) the app only keeps it in sync, so a
// user who deletes it on purpose is not overridden.
async function autoInstallGsiOnce() {
  if (autoInstallRunning) {
    return;
  }
  autoInstallRunning = true;
  try {
    await refreshDotaInstall();
    if (settings.get("gsiAutoInstalled")) {
      syncGsiConfig();
      return;
    }
    if (checkGsiConfig().status === "installed") {
      settings.set("gsiAutoInstalled", true);
      syncGsiConfig();
      return;
    }
    if (!resolveGsiDir()) {
      appendLog("gsi", "Dota 2 not found yet; the GSI config will be installed as soon as it is.", {
        force: true
      });
      return;
    }
    if (installGsiConfig().status === "installed") {
      settings.set("gsiAutoInstalled", true);
      const restartHint = dotaWatcher.getState().running ? " Restart Dota 2 to start receiving game data." : "";
      appendLog("gsi", `GSI config installed automatically.${restartHint}`, { force: true });
      showTrayBalloon(t("gsiInstalled") + (restartHint ? ` ${t("restartDota")}` : ""));
    }
  } finally {
    autoInstallRunning = false;
  }
}

async function chooseGsiFolder() {
  const result = await dialog.showOpenDialog(mainWindow, {
    title: "Choose Dota gamestate_integration folder",
    properties: ["openDirectory", "createDirectory"]
  });
  if (result.canceled || !result.filePaths.length) {
    return "";
  }
  return result.filePaths[0];
}

// "Dota not found" action: let the user point at the Dota 2 folder itself
// (…\dota 2 beta) and install the GSI config inside it.
async function chooseDotaFolderAndInstall() {
  const result = await dialog.showOpenDialog(mainWindow, {
    title: "Choose the Dota 2 folder (dota 2 beta)",
    properties: ["openDirectory"]
  });
  if (result.canceled || !result.filePaths.length) {
    return { status: gsiStatus.status, path: gsiStatus.path, canceled: true };
  }
  const chosen = result.filePaths[0];
  const candidates = [chosen, path.join(chosen, "steamapps", "common", "dota 2 beta")];
  const dotaDir = candidates.find((dir) => fs.existsSync(path.join(dir, "game", "dota")));
  if (!dotaDir) {
    appendLog("gsi", `No Dota 2 install in ${chosen} (expected a "game\\dota" folder inside).`, { force: true });
    return { status: "not found", path: "", error: "not_dota_folder" };
  }
  dotaInstall = { ...dotaInstall, dotaDir, gsiDir: gsiDirForDotaDir(dotaDir), source: "chosen" };
  const status = installGsiConfig();
  if (status.status === "installed") {
    settings.set("gsiAutoInstalled", true);
  }
  updateStatus();
  return status;
}

function openPath(targetPath) {
  try {
    fs.mkdirSync(targetPath, { recursive: true });
  } catch {
    // openPath below reports the problem.
  }
  shell.openPath(targetPath).then((error) => {
    if (error) {
      appendLog("launcher", `Could not open ${targetPath}: ${error}`, { force: true });
    }
  });
}

// ---------------------------------------------------------------------------
// Problem report: one text file for the developer (keys removed)
// ---------------------------------------------------------------------------

function readLauncherLog() {
  let text = "";
  for (const file of [`${LAUNCHER_LOG_PATH}.old`, LAUNCHER_LOG_PATH]) {
    try {
      text += fs.readFileSync(file, "utf8");
    } catch {
      // Missing log file: nothing to add.
    }
  }
  return text || logs;
}

function reportFolder() {
  for (const name of ["downloads", "desktop", "documents"]) {
    try {
      const folder = app.getPath(name);
      if (folder && fs.existsSync(folder)) {
        return folder;
      }
    } catch {
      // Try the next folder.
    }
  }
  return USER_DATA_DIR;
}

async function saveProblemReport() {
  let diagnostics = null;
  let diagnosticsError = "";
  try {
    diagnostics = await requestBackendJson("/diagnostics", "GET", undefined, 5000);
  } catch (error) {
    diagnosticsError = error.message;
  }
  const { recentAdvice, ...status } = publicStatus();
  const text = buildReport({
    app: {
      version: app.getVersion(),
      packaged: IS_PACKAGED,
      electron: process.versions.electron,
      os: `${process.platform} ${os.release()} ${process.arch}`,
      locale: app.getLocale(),
      userData: USER_DATA_DIR
    },
    status: { ...status, recentAdviceCount: Array.isArray(recentAdvice) ? recentAdvice.length : 0 },
    settings: settings.all(),
    watcher: dotaWatcher.getState(),
    diagnostics,
    diagnosticsError,
    launcherLog: readLauncherLog()
  });
  const filePath = path.join(reportFolder(), reportFileName());
  try {
    fs.writeFileSync(filePath, text, "utf8");
  } catch (error) {
    appendLog("launcher", `Could not save the problem report: ${error.message}`, { force: true });
    return { ok: false, error: error.message };
  }
  appendLog("launcher", `Problem report saved: ${filePath}`, { force: true });
  shell.showItemInFolder(filePath);
  return { ok: true, path: filePath };
}

// ---------------------------------------------------------------------------
// PDF export of the match review / progress page (light print theme in CSS)
// ---------------------------------------------------------------------------

const PDF_FOOTER = `<div style="width:100%;padding:0 12mm;display:flex;justify-content:space-between;font:8px sans-serif;color:#71717a">
<span>${APP_NAME}</span><span><span class="pageNumber"></span> / <span class="totalPages"></span></span></div>`;

async function exportPdf(kind, id) {
  if (!mainWindow || mainWindow.isDestroyed()) {
    return { ok: false, error: "no window" };
  }
  const stamp = new Date().toISOString().slice(0, 10);
  const fileName = kind === "match" && /^\d{1,20}$/.test(String(id))
    ? `DotaAICoach-match-${id}.pdf`
    : `DotaAICoach-progress-${stamp}.pdf`;
  const { canceled, filePath } = await dialog.showSaveDialog(mainWindow, {
    defaultPath: path.join(reportFolder(), fileName),
    filters: [{ name: "PDF", extensions: ["pdf"] }]
  });
  if (canceled || !filePath) {
    return { ok: false, canceled: true };
  }
  // The page margins are painted with the window background (dark): white while printing.
  mainWindow.setBackgroundColor("#ffffff");
  try {
    const data = await mainWindow.webContents.printToPDF({
      printBackground: true,
      pageSize: "A4",
      margins: { top: 0.4, bottom: 0.5, left: 0.4, right: 0.4 },
      displayHeaderFooter: true,
      headerTemplate: "<span></span>",
      footerTemplate: PDF_FOOTER
    });
    fs.writeFileSync(filePath, data);
  } catch (error) {
    appendLog("launcher", `Could not save the PDF: ${error.message}`, { force: true });
    return { ok: false, error: error.message };
  } finally {
    mainWindow.setBackgroundColor(WINDOW_BACKGROUND);
  }
  appendLog("launcher", `PDF saved: ${filePath}`, { force: true });
  shell.showItemInFolder(filePath);
  return { ok: true, path: filePath };
}

// ---------------------------------------------------------------------------
// Advice frequency (sent at backend start and on change)
// ---------------------------------------------------------------------------

const ADVICE_FREQUENCIES = ["calm", "normal", "active"];

function adviceFrequency() {
  const value = settings.get("adviceFrequency");
  return ADVICE_FREQUENCIES.includes(value) ? value : "normal";
}

async function setAdviceFrequency(value) {
  if (!ADVICE_FREQUENCIES.includes(value)) {
    return publicStatus();
  }
  settings.set("adviceFrequency", value);
  try {
    await requestBackendJson("/settings/advice", "POST", { frequency: value });
  } catch (error) {
    // The backend reads the setting from its env at the next start.
    appendLog("launcher", `Advice frequency saved; the service applies it on start (${error.message}).`, { force: true });
  }
  updateStatus();
  return publicStatus();
}

function setLogMode(nextMode = "clean") {
  logMode = nextMode === "verbose" ? "verbose" : "clean";
  appendLog(
    "launcher",
    `Log mode set to ${logMode}.${hiddenBackendAccessLogs ? ` Hidden clean logs so far: backend=${hiddenBackendAccessLogs}.` : ""}`,
    { force: true }
  );
  updateStatus();
  return publicStatus();
}

// ---------------------------------------------------------------------------
// Windows, tray, autostart
// ---------------------------------------------------------------------------

function appIcon() {
  return nativeImage.createFromPath(path.join(ICON_DIR, process.platform === "win32" ? "icon.ico" : "icon.png"));
}

function createMainWindow({ show = true } = {}) {
  mainWindow = new BrowserWindow({
    width: 760,
    height: 760,
    minWidth: 560,
    minHeight: 560,
    title: APP_NAME,
    icon: appIcon(),
    backgroundColor: WINDOW_BACKGROUND,
    show,
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false
    }
  });
  mainWindow.setMenuBarVisibility(false);
  mainWindow.loadFile(path.join(__dirname, "renderer", "index.html"));

  // Closing the window only hides it; the coach keeps running in the tray.
  mainWindow.on("close", (event) => {
    if (isQuitting || IS_SMOKE_TEST) {
      return;
    }
    event.preventDefault();
    mainWindow.hide();
    showTrayHintOnce();
  });
  // Windows logoff/shutdown: let the window close so the session can end.
  mainWindow.on("session-end", () => {
    isQuitting = true;
    app.quit();
  });
  mainWindow.on("closed", () => {
    mainWindow = null;
  });
  return mainWindow;
}

function showMainWindow() {
  if (!mainWindow || mainWindow.isDestroyed()) {
    createMainWindow();
    return;
  }
  if (mainWindow.isMinimized()) {
    mainWindow.restore();
  }
  mainWindow.show();
  mainWindow.focus();
}

function showTrayHintOnce() {
  if (settings.get("trayHintShown") || !tray || process.platform !== "win32") {
    return;
  }
  settings.set("trayHintShown", true);
  tray.displayBalloon({
    iconType: "info",
    title: APP_NAME,
    content: "Still running in the tray. Right-click the icon to toggle the overlay or quit."
  });
}

function isAutostartSupported() {
  return IS_PACKAGED && (process.platform === "win32" || process.platform === "darwin");
}

function loginItemOptions() {
  return { path: process.execPath, args: ["--hidden"] };
}

function isAutostartEnabled() {
  if (!isAutostartSupported()) {
    return false;
  }
  try {
    return Boolean(app.getLoginItemSettings(loginItemOptions()).openAtLogin);
  } catch {
    return false;
  }
}

function setAutostart(enabled) {
  if (!isAutostartSupported()) {
    appendLog("launcher", "Start with Windows is available in the installed build only.", { force: true });
    return false;
  }
  app.setLoginItemSettings({ ...loginItemOptions(), openAtLogin: Boolean(enabled) });
  appendLog("launcher", `Start with Windows: ${enabled ? "on" : "off"}.`, { force: true });
  autostartEnabled = isAutostartEnabled();
  updateStatus();
  refreshTray();
  return autostartEnabled;
}

function createTray() {
  const trayImage = process.platform === "win32"
    ? nativeImage.createFromPath(path.join(ICON_DIR, "icon.ico"))
    : nativeImage.createFromPath(path.join(ICON_DIR, "tray.png"));
  tray = new Tray(trayImage);
  tray.on("click", showMainWindow);
  tray.on("double-click", showMainWindow);
  tray.on("balloon-click", () => {
    showMainWindow();
    if (pendingReviewOpen) {
      send("launcher:player-event", { type: "open-match", matchId: pendingReviewOpen });
      pendingReviewOpen = null;
    }
  });
  refreshTray();
}

function refreshTray() {
  if (!tray || tray.isDestroyed()) {
    return;
  }
  const statusLine = t(presence.status);
  const port = backend.port && processStatus.backend !== "stopped" ? ` :${backend.port}` : "";
  const backendLine = `${t("backend")}: ${processStatus.backend}${port}`;
  const fullscreen = fullscreenWarningActive();
  const update = updater.getState();
  const tooltipLines = [`${APP_NAME} — ${statusLine}`, fullscreen ? t("fullscreenMenu") : "", backendLine];
  tray.setToolTip(tooltipLines.filter(Boolean).join("\n"));
  const topItems = [{ label: statusLine, enabled: false }];
  if (fullscreen) {
    topItems.push({ label: t("fullscreenMenu"), enabled: false });
  }
  if (update.status === UPDATE_STATUS.READY && isGameRunning()) {
    topItems.push({ label: t("updateAfterGame", update.version), enabled: false });
  } else if (update.status === UPDATE_STATUS.READY) {
    topItems.push({ label: t("updateReady", update.version), click: () => updater.install() });
  } else if (update.status === UPDATE_STATUS.DOWNLOADING) {
    topItems.push({ label: t("updateDownloading", update.version, update.percent), enabled: false });
  }
  tray.setContextMenu(
    Menu.buildFromTemplate([
      ...topItems,
      { type: "separator" },
      { label: t("open"), click: showMainWindow },
      {
        label: t("overlay"),
        type: "checkbox",
        checked: overlay.isEnabled(),
        click: (item) => overlay.setEnabled(item.checked)
      },
      {
        label: process.platform === "win32" ? t("autostartWindows") : t("autostartLogin"),
        type: "checkbox",
        checked: autostartEnabled,
        enabled: isAutostartSupported(),
        click: (item) => setAutostart(item.checked)
      },
      { type: "separator" },
      { label: backendLine, enabled: false },
      { label: t("problemReport"), click: () => saveProblemReport() },
      { type: "separator" },
      { label: t("quit"), click: () => app.quit() }
    ])
  );
}

function showTrayBalloon(content) {
  if (!tray || tray.isDestroyed() || process.platform !== "win32") {
    return;
  }
  tray.displayBalloon({ iconType: "info", title: APP_NAME, content });
}

// ---------------------------------------------------------------------------
// IPC
// ---------------------------------------------------------------------------

function registerIpc() {
  ipcMain.handle("launcher:get-status", () => publicStatus());
  ipcMain.handle("launcher:get-logs", () => logs);
  ipcMain.handle("launcher:clear-logs", () => {
    logs = "";
    hiddenBackendAccessLogs = 0;
    send("launcher:logs", logs);
    return true;
  });
  ipcMain.handle("launcher:copy-logs", () => {
    clipboard.writeText(logs);
    return true;
  });
  ipcMain.handle("launcher:start-backend", () => startBackend());
  ipcMain.handle("launcher:stop-backend", () => stopBackend());
  ipcMain.handle("launcher:restart-backend", () => restartBackend());
  ipcMain.handle("launcher:start-overlay", () => overlay.setEnabled(true));
  ipcMain.handle("launcher:stop-overlay", () => overlay.setEnabled(false));
  ipcMain.handle("launcher:set-autostart", (_event, enabled) => setAutostart(enabled));
  ipcMain.handle("launcher:run-demo", (_event, presetName) => runDemo(presetName, false));
  ipcMain.handle("launcher:run-deep-review", (_event, presetName) => runDemo(presetName, true));
  ipcMain.handle("launcher:stop-demo", () => stopManaged("demo"));
  ipcMain.handle("launcher:set-log-mode", (_event, nextMode) => setLogMode(nextMode));
  ipcMain.handle("launcher:check-live-gsi", () => checkLiveGsiStatus());
  ipcMain.handle("launcher:start-live-recording", () => setLiveRecording(true));
  ipcMain.handle("launcher:stop-live-recording", () => setLiveRecording(false));
  ipcMain.handle("launcher:check-gsi", async (_event, customPath) => {
    await refreshDotaInstall();
    return checkGsiConfig(customPath);
  });
  ipcMain.handle("launcher:install-gsi", async (_event, customPath) => {
    await refreshDotaInstall();
    return installGsiConfig(customPath);
  });
  ipcMain.handle("launcher:choose-gsi-folder", () => chooseGsiFolder());
  ipcMain.handle("launcher:choose-dota-folder", () => chooseDotaFolderAndInstall());
  ipcMain.handle("launcher:set-overlay-position", (_event, preset) => {
    overlay.setPosition(String(preset || ""));
    return publicStatus();
  });
  ipcMain.handle("launcher:set-advice-frequency", (_event, value) => setAdviceFrequency(String(value || "")));
  ipcMain.handle("launcher:set-overlay-voice", (_event, mode, volume) => {
    overlay.setVoice(String(mode || ""), volume);
    return publicStatus();
  });
  ipcMain.handle("launcher:set-overlay-locked", (_event, locked) => {
    overlay.setLocked(Boolean(locked));
    return publicStatus();
  });
  ipcMain.handle("launcher:dismiss-fullscreen-warning", () => {
    settings.set("fullscreenWarningDismissed", true);
    updateStatus();
    refreshTray();
    return publicStatus();
  });
  ipcMain.handle("launcher:check-updates", async () => {
    await updater.check();
    return publicStatus();
  });
  ipcMain.handle("launcher:install-update", () => updater.install());
  ipcMain.handle("launcher:player", (_event, op, args) => playerRequest(String(op || ""), args || {}));
  ipcMain.handle("launcher:open-logs", () => openPath(LOGS_DIR));
  ipcMain.handle("launcher:save-problem-report", () => saveProblemReport());
  ipcMain.handle("launcher:dismiss-setup", () => {
    settings.set("setupDismissed", true);
    return publicStatus();
  });
  ipcMain.handle("launcher:export-pdf", (_event, kind, id) =>
    exportPdf(kind === "match" ? "match" : "career", String(id || ""))
  );
  ipcMain.handle("launcher:open-simulation-results", () => openPath(SIMULATION_RESULTS_DIR));
  ipcMain.handle("launcher:open-session-records", () => openPath(SESSION_RECORDS_DIR));
  ipcMain.handle("launcher:open-readme", () => shell.openPath(README_PATH));
  ipcMain.handle("launcher:open-ai-key-page", (_event, provider) => {
    const pages = { ...AI_KEY_PAGES, opendota: "https://www.opendota.com/api-keys" };
    const url = pages[String(provider)];
    return url && Object.hasOwn(pages, String(provider)) ? shell.openExternal(url) : false;
  });

  ipcMain.handle("overlay:get-config", () => overlay.publicConfig());
  ipcMain.handle("overlay:fetch-recommendation", () => fetchOverlayRecommendation());
}

// ---------------------------------------------------------------------------
// Lifecycle
// ---------------------------------------------------------------------------

async function shutdownChildren() {
  stopGsiPolling();
  dotaWatcher.stop();
  updater.stop();
  overlay.dispose();
  if (processes.demo) {
    await stopManaged("demo");
  }
  if (processes.backend) {
    await stopBackend();
  }
}

function waitForEvent(emitter, eventName, timeoutMs) {
  return new Promise((resolve) => {
    const onEvent = (value) => {
      clearTimeout(timer);
      resolve(value);
    };
    const timer = setTimeout(() => {
      emitter.off(eventName, onEvent);
      resolve(null);
    }, timeoutMs);
    emitter.once(eventName, onEvent);
  });
}

function waitForWatcherState(predicate, timeoutMs) {
  return new Promise((resolve) => {
    if (predicate(dotaWatcher.getState())) {
      resolve(dotaWatcher.getState());
      return;
    }
    const onReport = (state) => {
      if (predicate(state)) {
        clearTimeout(timer);
        dotaWatcher.off("report", onReport);
        resolve(state);
      }
    };
    const timer = setTimeout(() => {
      dotaWatcher.off("report", onReport);
      resolve(null);
    }, timeoutMs);
    dotaWatcher.on("report", onReport);
  });
}

function waitForLoad(webContents, timeoutMs = 20000) {
  if (!webContents.isLoading() && webContents.getURL()) {
    return Promise.resolve(true);
  }
  return new Promise((resolve) => {
    const timer = setTimeout(() => resolve(false), timeoutMs);
    webContents.once("did-finish-load", () => {
      clearTimeout(timer);
      resolve(true);
    });
    webContents.once("did-fail-load", () => {
      clearTimeout(timer);
      resolve(false);
    });
  });
}

// `--smoke-test=<result.json>`: start the bundled backend exactly like a user
// launch would, check /health, stop it gracefully and exit. Used by CI.
async function runSmokeTest(resultPath) {
  const steps = [];
  const step = (name, ok, detail = "") => {
    steps.push({ name, ok: Boolean(ok), detail: String(detail) });
    appendLog("smoke", `${ok ? "PASS" : "FAIL"} ${name}${detail ? `: ${detail}` : ""}`, { force: true });
  };
  try {
    createMainWindow({ show: false });
    step("main window loaded", await waitForLoad(mainWindow.webContents));
    const overlayWindow = overlay.open();
    step("overlay window loaded", await waitForLoad(overlayWindow.webContents));

    const install = await locateDota();
    step("steam/dota locator", true, install.dotaDir || `Dota 2 not installed; libraries: ${install.libraries.join(", ") || "none"}`);

    if (process.platform === "win32" && process.env.DOTA_AI_SMOKE_FAKE_DOTA === "1") {
      // scripts/smoke-windows.ps1 runs a plain window named dota2.exe: the
      // helper must find its window rect and the overlay must move into it.
      dotaWatcher.start();
      const state = await waitForWatcherState((item) => item.running && item.windowRect, 30000);
      step("dota watcher finds the dota2.exe window", Boolean(state), JSON.stringify(dotaWatcher.getState()));
      step(
        "no exclusive fullscreen for a normal window",
        Boolean(state) && !state.exclusiveFullscreen,
        JSON.stringify(dotaWatcher.getState())
      );
      overlay.refreshPlacement();
      const bounds = overlayWindow.getBounds();
      const rect = state ? state.windowRect : null;
      step(
        "overlay placed inside the Dota window",
        Boolean(rect) &&
          bounds.x >= rect.x &&
          bounds.y >= rect.y &&
          bounds.x + bounds.width <= rect.x + rect.width &&
          bounds.y + bounds.height <= rect.y + rect.height,
        JSON.stringify({ overlay: bounds, dota: rect })
      );
      dotaWatcher.stop();
    } else if (process.platform === "win32") {
      // The real watcher (hidden PowerShell + user32) must report, and with no
      // dota2.exe running the overlay must stay hidden.
      const report = waitForEvent(dotaWatcher, "report", 30000);
      dotaWatcher.start();
      const state = await report;
      step("dota watcher reports", Boolean(state && state.supported), JSON.stringify(state));
      refreshPresence();
      step("overlay hidden without Dota", !overlay.isVisible(), presence.reason);
      dotaWatcher.stop();
    }

    if (IS_PACKAGED && process.platform === "win32") {
      // electron-builder writes app-update.yml only when "publish" is set.
      let updaterDetail = path.join(process.resourcesPath, "app-update.yml");
      let updaterOk = fs.existsSync(updaterDetail);
      try {
        require("electron-updater");
      } catch (error) {
        updaterOk = false;
        updaterDetail = error.message;
      }
      step("auto-update configured", updaterOk, updaterDetail);
    }

    const started = await startBackend();
    step("backend /health", started && (await isBackendReady()), backendUrl());
    // Both renderers must have drawn their UI from live data (catches script
    // errors that a plain "page loaded" check would miss). Only app.js sets
    // these values: the static HTML has data-state="starting", "—" and an empty action.
    await delay(1500);
    const panel = await mainWindow.webContents.executeJavaScript(
      "({ state: document.querySelector('#service')?.dataset.state || '', text: document.querySelector('#service-text')?.textContent || '' })"
    );
    step(
      "control panel rendered",
      panel.state === "running" && panel.text.includes(String(backend.port)),
      `${panel.state}: ${panel.text}`
    );
    const overlayAction = await overlayWindow.webContents.executeJavaScript(
      "document.querySelector('#action')?.textContent || ''"
    );
    step("overlay card rendered", Boolean(overlayAction.trim()), overlayAction);

    // Player history (SQLite store, match reviews) must work in the bundled backend.
    const player = await playerRequest("status");
    step("player API", player.ok && typeof player.data.linked === "boolean", JSON.stringify(player.ok ? player.data.sync : player));

    const recommendation = await fetchOverlayRecommendation();
    step(
      "overlay recommendation",
      recommendation.ok,
      recommendation.ok ? recommendation.data.status : recommendation.error
    );

    const outcome = await stopBackend();
    const exit = lastExit.backend || {};
    step("backend graceful shutdown", outcome === "graceful" && exit.code === 0, `${outcome}, code=${exit.code}`);
  } catch (error) {
    step("unexpected error", false, error.stack || error.message);
  }
  const ok = steps.length > 0 && steps.every((item) => item.ok);
  const result = { ok, port: backend.port, packaged: IS_PACKAGED, steps, logs: logs.slice(-20000) };
  if (resultPath) {
    fs.mkdirSync(path.dirname(path.resolve(resultPath)), { recursive: true });
    fs.writeFileSync(resultPath, `${JSON.stringify(result, null, 2)}\n`, "utf8");
  }
  dotaWatcher.stop();
  overlay.dispose();
  app.exit(ok ? 0 : 1);
}

function bootstrap() {
  if (process.platform === "win32") {
    app.setAppUserModelId(APP_ID);
  }
  openLauncherLog();
  registerIpc();

  if (IS_SMOKE_TEST) {
    app.whenReady().then(() => runSmokeTest(SMOKE_TEST_RESULT));
    return;
  }

  if (!app.requestSingleInstanceLock()) {
    app.quit();
    return;
  }
  app.on("second-instance", showMainWindow);

  app.whenReady().then(() => {
    appendLog("launcher", `${APP_NAME} ${app.getVersion()} started (${IS_PACKAGED ? "packaged" : "dev"}).`, {
      force: true
    });
    autostartEnabled = isAutostartEnabled();
    createTray();
    // After an update the app comes back the way it was: hidden in the tray
    // when the update installed by itself or the window was closed. If the
    // install did not happen (same version), start normally.
    const updatedFrom = settings.get("updatedFrom");
    const justUpdated = Boolean(updatedFrom) && updatedFrom !== app.getVersion();
    const startHidden = START_HIDDEN || (justUpdated && Boolean(settings.get("startHiddenOnce")));
    if (updatedFrom || settings.get("startHiddenOnce")) {
      settings.set("updatedFrom", "");
      settings.set("startHiddenOnce", false);
    }
    if (!startHidden) {
      createMainWindow();
    }
    if (justUpdated) {
      appendLog("update", `Updated from ${updatedFrom} to ${app.getVersion()}.`, { force: true });
      showTrayBalloon(t("updated", app.getVersion()));
    }
    overlay.registerGlobalShortcuts();
    if (overlay.isEnabled()) {
      overlay.open();
    }
    dotaWatcher.start();
    refreshPresence();
    startGsiPolling();
    for (const eventName of ["display-added", "display-removed", "display-metrics-changed"]) {
      screen.on(eventName, () => {
        overlay.refreshPlacement();
        overlay.enforceAlwaysOnTop();
      });
    }
    startBackend();
    updater.start();
    app.on("activate", showMainWindow);
  });

  // Keep running in the tray when every window is closed.
  app.on("window-all-closed", () => {});

  // Stop the backend gracefully before Electron exits.
  app.on("before-quit", (event) => {
    isQuitting = true;
    if (shutdownComplete) {
      return;
    }
    event.preventDefault();
    if (!shutdownPromise) {
      shutdownPromise = shutdownChildren()
        .catch((error) => appendLog("launcher", `Shutdown error: ${error.message}`, { force: true }))
        .finally(() => {
          shutdownComplete = true;
          if (tray && !tray.isDestroyed()) {
            tray.destroy();
          }
          app.quit();
        });
    }
  });

  for (const signal of ["SIGINT", "SIGTERM"]) {
    process.on(signal, () => app.quit());
  }
}

bootstrap();
