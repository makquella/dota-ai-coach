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

const { createOverlayController, OVERLAY_DEFAULTS } = require("./overlay-window");
const { createSettingsStore } = require("./settings");

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
const GSI_CONFIG_NAME = "gamestate_integration_dota_ai_coach.cfg";

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
  trayHintShown: false,
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

const BACKEND_NOISE_PATTERNS = [
  /GET\s+\/overlay\/recommendation\b/,
  /POST\s+\/demo\/replay-state\b/,
  /POST\s+\/gsi\b/
];

const overlay = createOverlayController({
  settings,
  getBackend: backendInfo,
  onChange: () => {
    updateStatus();
    refreshTray();
  },
  log: (message) => appendLog("overlay", message, { force: true })
});

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

function publicStatus() {
  return {
    backend: processStatus.backend,
    backendPort: backend.port,
    backendUrl: backendUrl(),
    gsiEndpoint: gsiEndpoint(),
    overlay: overlay.isEnabled() ? "running" : "stopped",
    demo: processStatus.demo,
    demoPreset: processStatus.demo !== "stopped" ? currentDemoPreset : "",
    recording: recordingStatus,
    gsiConfig: gsiStatus.status,
    gsiPath: gsiStatus.path,
    mode,
    llm: "off",
    logMode,
    autostart: isAutostartEnabled(),
    autostartSupported: isAutostartSupported()
  };
}

function updateStatus() {
  send("launcher:status", publicStatus());
}

function setBackendStatus(status) {
  processStatus.backend = status;
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
    syncGsiConfigPort();
  }

  const env = {
    USE_LLM: "false",
    SIMULATION_USE_LLM: "false",
    LIVE_CONSERVATIVE_MODE: "true",
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

function requestBackendJson(endpointPath, method = "GET") {
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
        timeout: 2500,
        headers: { "Content-Type": "application/json" }
      },
      (response) => {
        let body = "";
        response.setEncoding("utf8");
        response.on("data", (chunk) => {
          body += chunk;
        });
        response.on("end", () => {
          if (response.statusCode < 200 || response.statusCode >= 300) {
            reject(new Error(`Backend returned HTTP ${response.statusCode}: ${body}`));
            return;
          }
          try {
            resolve(body ? JSON.parse(body) : {});
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
    request.end();
  });
}

async function fetchOverlayRecommendation() {
  try {
    return { ok: true, data: await requestBackendJson("/overlay/recommendation") };
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
      updateStatus();
    }
  });
  if (!child) {
    return false;
  }
  processStatus.demo = "running";
  currentDemoPreset = preset.label;
  mode = "Replay Demo";
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

function gsiConfigText() {
  return `"Dota AI Coach GSI"
{
  "uri"           "${gsiEndpoint()}"
  "timeout"       "5.0"
  "buffer"        "0.1"
  "throttle"      "0.1"
  "heartbeat"     "30.0"
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

function defaultGsiDirs() {
  if (process.platform === "win32") {
    return [
      "C:\\Program Files (x86)\\Steam\\steamapps\\common\\dota 2 beta\\game\\dota\\cfg\\gamestate_integration",
      "C:\\Program Files\\Steam\\steamapps\\common\\dota 2 beta\\game\\dota\\cfg\\gamestate_integration"
    ];
  }
  return [
    path.join(os.homedir(), ".steam", "steam", "steamapps", "common", "dota 2 beta", "game", "dota", "cfg", "gamestate_integration"),
    path.join(os.homedir(), ".local", "share", "Steam", "steamapps", "common", "dota 2 beta", "game", "dota", "cfg", "gamestate_integration")
  ];
}

function resolveGsiDir(customPath = "") {
  const trimmed = String(customPath || "").trim();
  if (trimmed) {
    return trimmed;
  }
  const saved = String(settings.get("gsiConfigPath") || "");
  if (saved && fs.existsSync(path.dirname(saved))) {
    return path.dirname(saved);
  }
  return defaultGsiDirs().find((candidate) => fs.existsSync(candidate)) || "";
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
// program). Keep an installed Dota GSI config pointing at the current port.
function syncGsiConfigPort() {
  const status = checkGsiConfig();
  if (status.status !== "installed") {
    return;
  }
  try {
    const current = fs.readFileSync(status.path, "utf8");
    if (current.includes(`"${gsiEndpoint()}"`)) {
      return;
    }
    fs.writeFileSync(status.path, gsiConfigText(), "utf8");
    appendLog(
      "gsi",
      `Updated GSI config to ${gsiEndpoint()}. Restart Dota 2 if it is already running.`,
      { force: true }
    );
  } catch (error) {
    appendLog("gsi", `Could not update GSI config port: ${error.message}`, { force: true });
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
    width: 980,
    height: 720,
    minWidth: 860,
    minHeight: 620,
    title: APP_NAME,
    icon: appIcon(),
    backgroundColor: "#10131a",
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
  updateStatus();
  refreshTray();
  return isAutostartEnabled();
}

function createTray() {
  const trayImage = process.platform === "win32"
    ? nativeImage.createFromPath(path.join(ICON_DIR, "icon.ico"))
    : nativeImage.createFromPath(path.join(ICON_DIR, "tray.png"));
  tray = new Tray(trayImage);
  tray.on("click", showMainWindow);
  tray.on("double-click", showMainWindow);
  refreshTray();
}

function refreshTray() {
  if (!tray || tray.isDestroyed()) {
    return;
  }
  const port = backend.port ? ` on :${backend.port}` : "";
  const backendLine = `Backend: ${processStatus.backend}${processStatus.backend === "stopped" ? "" : port}`;
  tray.setToolTip(`${APP_NAME}\n${backendLine}`);
  tray.setContextMenu(
    Menu.buildFromTemplate([
      { label: "Open", click: showMainWindow },
      {
        label: "Overlay",
        type: "checkbox",
        checked: overlay.isEnabled(),
        click: (item) => overlay.setEnabled(item.checked)
      },
      {
        label: process.platform === "win32" ? "Start with Windows" : "Start at login",
        type: "checkbox",
        checked: isAutostartEnabled(),
        enabled: isAutostartSupported(),
        click: (item) => setAutostart(item.checked)
      },
      { type: "separator" },
      { label: backendLine, enabled: false },
      { type: "separator" },
      { label: "Quit", click: () => app.quit() }
    ])
  );
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
  ipcMain.handle("launcher:check-gsi", (_event, customPath) => checkGsiConfig(customPath));
  ipcMain.handle("launcher:install-gsi", (_event, customPath) => installGsiConfig(customPath));
  ipcMain.handle("launcher:choose-gsi-folder", () => chooseGsiFolder());
  ipcMain.handle("launcher:open-logs", () => openPath(LOGS_DIR));
  ipcMain.handle("launcher:open-simulation-results", () => openPath(SIMULATION_RESULTS_DIR));
  ipcMain.handle("launcher:open-session-records", () => openPath(SESSION_RECORDS_DIR));
  ipcMain.handle("launcher:open-readme", () => shell.openPath(README_PATH));

  ipcMain.handle("overlay:get-config", () => overlay.publicConfig());
  ipcMain.handle("overlay:fetch-recommendation", () => fetchOverlayRecommendation());
}

// ---------------------------------------------------------------------------
// Lifecycle
// ---------------------------------------------------------------------------

async function shutdownChildren() {
  overlay.dispose();
  if (processes.demo) {
    await stopManaged("demo");
  }
  if (processes.backend) {
    await stopBackend();
  }
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

    const started = await startBackend();
    step("backend /health", started && (await isBackendReady()), backendUrl());
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
    createTray();
    if (!START_HIDDEN) {
      createMainWindow();
    }
    overlay.registerGlobalShortcuts();
    if (overlay.isEnabled()) {
      overlay.open();
    }
    for (const eventName of ["display-added", "display-removed", "display-metrics-changed"]) {
      screen.on(eventName, overlay.enforceAlwaysOnTop);
    }
    startBackend();
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
