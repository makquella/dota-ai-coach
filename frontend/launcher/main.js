const { app, BrowserWindow, clipboard, dialog, ipcMain, shell } = require("electron");
const { spawn } = require("node:child_process");
const fs = require("node:fs");
const http = require("node:http");
const os = require("node:os");
const path = require("node:path");

const REPO_ROOT = path.resolve(__dirname, "..", "..");
const IS_PACKAGED = app.isPackaged;
const RESOURCES_ROOT = IS_PACKAGED ? process.resourcesPath : REPO_ROOT;
const BACKEND_DIR = path.join(REPO_ROOT, "backend");
const OVERLAY_DIR = path.join(REPO_ROOT, "frontend", "desktop-overlay");
const README_PATH = IS_PACKAGED ? path.join(RESOURCES_ROOT, "README.md") : path.join(REPO_ROOT, "README.md");
const SIMULATION_RESULTS_DIR = path.join(BACKEND_DIR, "simulation_results");
const SESSION_RECORDS_DIR = IS_PACKAGED
  ? path.join(app.getPath("userData"), "session_records")
  : path.join(BACKEND_DIR, "session_records");
const GSI_CONFIG_NAME = "gamestate_integration_dota_ai_coach.cfg";
const GSI_ENDPOINT = "http://127.0.0.1:8000/gsi";
const BACKEND_BASE_URL = "http://127.0.0.1:8000";

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

let mainWindow = null;
const processes = {
  backend: null,
  overlay: null,
  demo: null
};
const processStatus = {
  backend: "stopped",
  overlay: "stopped",
  demo: "stopped"
};
const stoppingProcesses = new Set();
let mode = "Live GSI";
let llmEnabled = false;
let gsiStatus = { status: "unknown", path: "" };
let logs = "";
let logMode = "clean";
let hiddenBackendAccessLogs = 0;
let hiddenOverlayNoiseLogs = 0;
let currentDemoPreset = "";
let recordingStatus = "stopped";
let backendExternalReady = false;

const BACKEND_NOISE_PATTERNS = [
  /GET\s+\/overlay\/recommendation\b/,
  /POST\s+\/demo\/replay-state\b/,
  /POST\s+\/gsi\b/
];
const OVERLAY_NOISE_PATTERNS = [
  /gl_surface_presentation_helper\.cc/,
  /GetVSyncParametersIfAvailable\(\) failed/,
  /\bGPU\b.*\b(warning|error|failed)\b/i,
  /\bVSync\b.*\b(warning|error|failed)\b/i
];

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 980,
    height: 720,
    minWidth: 860,
    minHeight: 620,
    title: "Dota 2 Coach",
    backgroundColor: "#10131a",
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false
    }
  });

  mainWindow.loadFile(path.join(__dirname, "renderer", "index.html"));
  mainWindow.on("closed", () => {
    mainWindow = null;
  });
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
    const hiddenKind = options.force ? "" : hiddenLogKind(scope, part);
    if (hiddenKind) {
      if (hiddenKind === "backend") {
        hiddenBackendAccessLogs += 1;
      } else if (hiddenKind === "overlay") {
        hiddenOverlayNoiseLogs += 1;
      }
      const hiddenTotal = hiddenBackendAccessLogs + hiddenOverlayNoiseLogs;
      if (hiddenTotal % 25 === 0) {
        lineParts.push(
          `[${new Date().toLocaleTimeString()}] [launcher] clean logs hidden: backend=${hiddenBackendAccessLogs}, overlay=${hiddenOverlayNoiseLogs}`
        );
      }
      continue;
    }
    lineParts.push(`[${new Date().toLocaleTimeString()}] [${scope}] ${part}`);
  }
  if (!lineParts.length) {
    return;
  }
  const line = lineParts.join("\n");
  logs = `${logs}${line}\n`;
  if (logs.length > 80000) {
    logs = logs.slice(-80000);
  }
  send("launcher:logs", logs);
}

function hiddenLogKind(scope, line) {
  if (logMode !== "clean") {
    return "";
  }
  if (scope === "backend" && BACKEND_NOISE_PATTERNS.some((pattern) => pattern.test(line))) {
    return "backend";
  }
  if (scope === "overlay" && OVERLAY_NOISE_PATTERNS.some((pattern) => pattern.test(line))) {
    return "overlay";
  }
  return "";
}

function publicStatus() {
  return {
    backend: backendExternalReady ? "running" : processStatus.backend,
    overlay: processStatus.overlay,
    demo: processStatus.demo,
    demoPreset: processStatus.demo !== "stopped" ? currentDemoPreset : "",
    recording: recordingStatus,
    gsiConfig: gsiStatus.status,
    gsiPath: gsiStatus.path,
    mode,
    llm: llmEnabled ? "on" : "off",
    logMode
  };
}

function updateStatus() {
  send("launcher:status", publicStatus());
}

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

function npmCommand() {
  return process.platform === "win32" ? "npm.cmd" : "npm";
}

function packagedBackendExecutable() {
  const executable = process.platform === "win32" ? "dota-ai-coach-backend.exe" : "dota-ai-coach-backend";
  return path.join(RESOURCES_ROOT, "backend", executable);
}

function packagedDemoExecutable() {
  const executable = process.platform === "win32" ? "dota-ai-coach-demo-playback.exe" : "dota-ai-coach-demo-playback";
  return path.join(RESOURCES_ROOT, "backend", executable);
}

function packagedOverlayExecutable() {
  const executable = process.platform === "win32" ? "Dota AI Coach Overlay.exe" : "Dota AI Coach Overlay";
  return path.join(RESOURCES_ROOT, "desktop-overlay", executable);
}

function demoFileForPreset(preset) {
  if (IS_PACKAGED) {
    return path.join(RESOURCES_ROOT, "data", "match_simulations", preset.fileName);
  }
  return `../data/match_simulations/${preset.fileName}`;
}

function ensureExecutableExists(name, executablePath) {
  if (fs.existsSync(executablePath)) {
    return true;
  }
  appendLog("launcher", `${name} executable was not found: ${executablePath}`, { force: true });
  return false;
}

function normalizeArgs(args = []) {
  if (!Array.isArray(args)) {
    return [];
  }
  return args
    .filter((arg) => arg !== undefined && arg !== null)
    .map((arg) => String(arg));
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
  if (processes[name] || processStatus[name] === "starting") {
    appendLog("launcher", `${name} is already running.`);
    return false;
  }

  const cwd = options.cwd || REPO_ROOT;
  const safeArgs = normalizeArgs(args);
  const commandLine = `${command} ${safeArgs.join(" ")}`.trim();
  if (!command) {
    appendLog("launcher", `Cannot start ${name}: command is empty. cwd=${cwd}`, { force: true });
    return false;
  }
  if (!fs.existsSync(cwd)) {
    appendLog("launcher", `Cannot start ${name}: cwd does not exist: ${cwd}; command=${commandLine}`, { force: true });
    return false;
  }
  appendLog("launcher", `Starting ${name}: ${commandLine} (cwd: ${cwd})`, { force: true });
  processStatus[name] = "starting";
  updateStatus();

  let child = null;
  try {
    child = spawn(command, safeArgs, {
      cwd,
      env: normalizeEnv({ ...process.env, ...(options.env || {}) }),
      shell: Boolean(options.shell),
      detached: process.platform !== "win32",
      windowsHide: true
    });
  } catch (error) {
    processStatus[name] = "stopped";
    appendLog(name, `Failed to start: ${error.message}; command=${commandLine}; cwd=${cwd}`, { force: true });
    updateStatus();
    return false;
  }
  processes[name] = child;

  child.on("spawn", () => {
    processStatus[name] = "running";
    appendLog("launcher", `${name} process started with pid ${child.pid}.`, { force: true });
    updateStatus();
  });
  child.stdout.on("data", (chunk) => appendLog(name, chunk.toString()));
  child.stderr.on("data", (chunk) => appendLog(name, chunk.toString()));
  child.on("error", (error) => {
    processStatus[name] = "stopped";
    appendLog(name, `Failed to start: ${error.message}; command=${commandLine}; cwd=${cwd}`, { force: true });
    processes[name] = null;
    if (name === "demo") {
      mode = "Live GSI";
      currentDemoPreset = "";
    }
    updateStatus();
  });
  child.on("exit", (code, signal) => {
    const wasStopping = stoppingProcesses.has(name);
    stoppingProcesses.delete(name);
    appendLog(name, `Exited with code ${code ?? "null"} signal ${signal ?? "null"}.`);
    if (name === "backend" && code !== null && !wasStopping) {
      appendLog(
        "launcher",
        code === 0
          ? "Backend process stopped cleanly. If this happened immediately after Start Backend, run the bundled backend exe directly from resources/backend to inspect console output."
          : `Backend process failed with code ${code}. Check the backend log lines above and verify port 8000 is free.`,
        { force: true }
      );
    } else if (wasStopping) {
      appendLog("launcher", `${name} stopped by launcher request.`, { force: true });
    }
    processes[name] = null;
    processStatus[name] = "stopped";
    if (name === "backend") {
      backendExternalReady = false;
    }
    if (name === "demo") {
      mode = "Live GSI";
      appendLog("launcher", "Demo stopped.", { force: true });
      currentDemoPreset = "";
    }
    updateStatus();
  });

  if (name === "demo") {
    mode = "Replay Demo";
  }
  updateStatus();
  return true;
}

function stopManaged(name) {
  appendLog("launcher", `stopManaged begins for ${name}.`, { force: true });
  const child = processes[name];
  if (!child) {
    if (name === "backend" && backendExternalReady) {
      appendLog(
        "launcher",
        "Backend is reachable on /health but was not started by this launcher, so it will not be killed.",
        { force: true }
      );
      return false;
    }
    appendLog("launcher", `${name} is not running.`);
    return false;
  }
  appendLog("launcher", `Stopping ${name}...`);
  stoppingProcesses.add(name);
  killProcessTree(name, child);
  return true;
}

function killProcessTree(name, child) {
  if (!child || !child.pid) {
    return;
  }
  if (process.platform === "win32") {
    const killer = spawn("taskkill", ["/pid", String(child.pid), "/T", "/F"], {
      windowsHide: true
    });
    killer.on("error", (error) => {
      appendLog("launcher", `taskkill failed for ${name}: ${error.message}`);
      try {
        child.kill("SIGTERM");
      } catch (killError) {
        appendLog("launcher", `Fallback stop failed for ${name}: ${killError.message}`);
      }
    });
    return;
  }

  try {
    process.kill(-child.pid, "SIGTERM");
  } catch (groupError) {
    try {
      process.kill(child.pid, "SIGTERM");
    } catch (pidError) {
      appendLog("launcher", `Stop signal failed for ${name}: ${pidError.message}`);
    }
  }

  const timer = setTimeout(() => {
    if (processes[name] !== child) {
      return;
    }
    try {
      process.kill(-child.pid, "SIGKILL");
    } catch (groupError) {
      try {
        process.kill(child.pid, "SIGKILL");
      } catch (pidError) {
        appendLog("launcher", `Force stop failed for ${name}: ${pidError.message}`);
      }
    }
  }, 3000);
  if (typeof timer.unref === "function") {
    timer.unref();
  }
}

async function startBackend() {
  appendLog("launcher", "startBackend begins.", { force: true });
  llmEnabled = false;
  if (processes.backend || processStatus.backend === "starting") {
    appendLog("launcher", "Backend is already managed by launcher.", { force: true });
    return true;
  }
  processStatus.backend = "starting";
  updateStatus();
  if (await isBackendReady()) {
    backendExternalReady = true;
    processStatus.backend = "running";
    appendLog("launcher", "Backend is already running and /health is reachable; using existing backend.", { force: true });
    updateStatus();
    return true;
  }
  backendExternalReady = false;
  if (IS_PACKAGED) {
    const executable = packagedBackendExecutable();
    if (!ensureExecutableExists("Backend", executable)) {
      processStatus.backend = "stopped";
      updateStatus();
      return false;
    }
    processStatus.backend = "stopped";
    const started = spawnManaged("backend", executable, [], {
      cwd: path.dirname(executable),
      env: {
        USE_LLM: "false",
        SIMULATION_USE_LLM: "false",
        LIVE_CONSERVATIVE_MODE: "true",
        DOTA_AI_BACKEND_LOG_LEVEL: "info",
        SESSION_RECORDS_DIR
      }
    });
    if (started) {
      verifyBackendHealthAfterStart();
    }
    return started;
  }

  processStatus.backend = "stopped";
  const started = spawnManaged(
    "backend",
    pythonExecutable(),
    [
      "-m",
      "uvicorn",
      "app.main:app",
      "--host",
      "127.0.0.1",
      "--port",
      "8000",
      "--reload",
      "--no-access-log"
    ],
    {
      cwd: BACKEND_DIR,
      env: {
        USE_LLM: "false",
        SIMULATION_USE_LLM: "false",
        LIVE_CONSERVATIVE_MODE: "true",
        SESSION_RECORDS_DIR
      }
    }
  );
  if (started) {
    verifyBackendHealthAfterStart();
  }
  return started;
}

function verifyBackendHealthAfterStart() {
  setTimeout(async () => {
    if (!processes.backend) {
      return;
    }
    appendLog("launcher", "Backend health check started.", { force: true });
    if (await isBackendReady()) {
      appendLog("launcher", "Backend health check OK: http://127.0.0.1:8000/health", { force: true });
      return;
    }
    appendLog(
      "launcher",
      "Backend process is running, but /health is not reachable yet. Verify no other process owns port 8000 and check backend stderr above.",
      { force: true }
    );
  }, 2500);
}

function startOverlay() {
  appendLog("launcher", "startOverlay begins.", { force: true });
  if (IS_PACKAGED) {
    const executable = packagedOverlayExecutable();
    if (!ensureExecutableExists("Overlay", executable)) {
      return false;
    }
    return spawnManaged("overlay", executable, [], { cwd: path.dirname(executable) });
  }
  if (process.platform === "win32") {
    return spawnManaged("overlay", "cmd.exe", ["/d", "/s", "/c", "npm run dev"], { cwd: OVERLAY_DIR });
  }
  const overlayArgs = process.platform === "linux" ? ["run", "dev:x11"] : ["run", "dev"];
  return spawnManaged("overlay", npmCommand(), overlayArgs, { cwd: OVERLAY_DIR });
}

async function runDemo(presetName = "plMacro", includeDeepReview = false) {
  if (processes.demo) {
    appendLog("launcher", "Demo is already running. Stop Demo before starting another preset.", { force: true });
    return false;
  }

  if (!(await isBackendReady())) {
    appendLog("launcher", "Backend is not running. Start backend first.", { force: true });
    return false;
  }

  const preset = DEMO_PRESETS[presetName] || DEMO_PRESETS.plMacro;
  const demoFile = demoFileForPreset(preset);
  const args = [
    "--simulation-file",
    demoFile,
    "--speed",
    "5",
    "--advice-hold-seconds",
    "8"
  ];
  if (includeDeepReview) {
    const slug = presetName === "juggSafety" ? "jugg_10_20" : "pl_20_30";
    args.push(
      "--export-deep-review",
      `simulation_results/deep_review_${slug}.md`,
      "--export-deep-review-json",
      `simulation_results/deep_review_${slug}.json`
    );
  }

  currentDemoPreset = preset.label;
  const command = IS_PACKAGED ? packagedDemoExecutable() : pythonExecutable();
  const commandArgs = IS_PACKAGED ? args : ["-u", "scripts/run_overlay_demo.py", ...args];
  if (IS_PACKAGED && !ensureExecutableExists("Demo playback", command)) {
    currentDemoPreset = "";
    return false;
  }
  const started = spawnManaged("demo", command, commandArgs, {
    cwd: IS_PACKAGED ? path.dirname(command) : BACKEND_DIR,
    env: {
      PYTHONUNBUFFERED: "1",
      SIMULATION_USE_LLM: "false",
      USE_LLM: "false"
    }
  });
  if (!started) {
    currentDemoPreset = "";
  } else {
    appendLog("launcher", `Demo started: ${preset.label}`, { force: true });
    updateStatus();
  }
  return started;
}

function isBackendReady() {
  return new Promise((resolve) => {
    const request = http.get(`${BACKEND_BASE_URL}/health`, { timeout: 1200 }, (response) => {
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
    const url = new URL(endpointPath, BACKEND_BASE_URL);
    const request = http.request(
      url,
      {
        method,
        timeout: 2000,
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

async function startLiveRecording() {
  try {
    const status = await requestBackendJson("/session-recording/start", "POST");
    recordingStatus = status.active ? "running" : "stopped";
    appendLog("recording", `Recording started: ${status.session_dir || SESSION_RECORDS_DIR}`, { force: true });
    updateStatus();
    return status;
  } catch (error) {
    appendLog("recording", `Could not start recording: ${error.message}`, { force: true });
    updateStatus();
    return { error: error.message };
  }
}

async function stopLiveRecording() {
  try {
    const status = await requestBackendJson("/session-recording/stop", "POST");
    recordingStatus = status.active ? "running" : "stopped";
    appendLog("recording", `Recording stopped: ${status.session_dir || SESSION_RECORDS_DIR}`, { force: true });
    updateStatus();
    return status;
  } catch (error) {
    appendLog("recording", `Could not stop recording: ${error.message}`, { force: true });
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
  "uri"           "${GSI_ENDPOINT}"
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
    appendLog("gsi", "Dota GSI folder was not found. Enter a custom gamestate_integration path.");
    updateStatus();
    return gsiStatus;
  }
  fs.mkdirSync(dir, { recursive: true });
  const filePath = path.join(dir, GSI_CONFIG_NAME);
  fs.writeFileSync(filePath, gsiConfigText(), "utf8");
  gsiStatus = { status: "installed", path: filePath };
  appendLog("gsi", `Installed config: ${filePath}`);
  updateStatus();
  return gsiStatus;
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
  shell.openPath(targetPath).then((error) => {
    if (error) {
      appendLog("launcher", `Could not open ${targetPath}: ${error}`);
    }
  });
}

function setLogMode(nextMode = "clean") {
  logMode = nextMode === "verbose" ? "verbose" : "clean";
  appendLog(
    "launcher",
    `Log mode set to ${logMode}.${
      hiddenBackendAccessLogs || hiddenOverlayNoiseLogs
        ? ` Hidden clean logs so far: backend=${hiddenBackendAccessLogs}, overlay=${hiddenOverlayNoiseLogs}.`
        : ""
    }`,
    { force: true }
  );
  updateStatus();
  return publicStatus();
}

function cleanup() {
  for (const name of ["demo", "overlay", "backend"]) {
    if (processes[name]) {
      stopManaged(name);
    }
  }
}

ipcMain.handle("launcher:get-status", () => publicStatus());
ipcMain.handle("launcher:get-logs", () => logs);
ipcMain.handle("launcher:clear-logs", () => {
  logs = "";
  hiddenBackendAccessLogs = 0;
  hiddenOverlayNoiseLogs = 0;
  send("launcher:logs", logs);
  return true;
});
ipcMain.handle("launcher:copy-logs", () => {
  clipboard.writeText(logs);
  return true;
});
ipcMain.handle("launcher:start-backend", () => {
  appendLog("launcher", "IPC received: Start Backend.", { force: true });
  return startBackend();
});
ipcMain.handle("launcher:stop-backend", () => {
  appendLog("launcher", "IPC received: Stop Backend.", { force: true });
  return stopManaged("backend");
});
ipcMain.handle("launcher:start-overlay", () => {
  appendLog("launcher", "IPC received: Start Overlay.", { force: true });
  return startOverlay();
});
ipcMain.handle("launcher:stop-overlay", () => {
  appendLog("launcher", "IPC received: Stop Overlay.", { force: true });
  return stopManaged("overlay");
});
ipcMain.handle("launcher:run-demo", (_event, presetName) => runDemo(presetName, false));
ipcMain.handle("launcher:run-deep-review", (_event, presetName) => runDemo(presetName, true));
ipcMain.handle("launcher:stop-demo", () => stopManaged("demo"));
ipcMain.handle("launcher:set-log-mode", (_event, nextMode) => setLogMode(nextMode));
ipcMain.handle("launcher:check-live-gsi", () => checkLiveGsiStatus());
ipcMain.handle("launcher:start-live-recording", () => startLiveRecording());
ipcMain.handle("launcher:stop-live-recording", () => stopLiveRecording());
ipcMain.handle("launcher:check-gsi", (_event, customPath) => checkGsiConfig(customPath));
ipcMain.handle("launcher:install-gsi", (_event, customPath) => installGsiConfig(customPath));
ipcMain.handle("launcher:choose-gsi-folder", () => chooseGsiFolder());
ipcMain.handle("launcher:open-logs", () => openPath(path.join(BACKEND_DIR, "logs")));
ipcMain.handle("launcher:open-simulation-results", () => openPath(SIMULATION_RESULTS_DIR));
ipcMain.handle("launcher:open-session-records", () => {
  fs.mkdirSync(SESSION_RECORDS_DIR, { recursive: true });
  openPath(SESSION_RECORDS_DIR);
});
ipcMain.handle("launcher:open-readme", () => openPath(README_PATH));

app.whenReady().then(() => {
  createWindow();
  checkGsiConfig();
  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on("before-quit", cleanup);

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit();
  }
});
