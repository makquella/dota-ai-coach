const { app, BrowserWindow, globalShortcut, ipcMain, screen } = require("electron");
const fs = require("node:fs");
const path = require("node:path");

const WINDOW_WIDTH = 420;
const WINDOW_HEIGHT = 140;
const CONFIG_PATH = path.join(__dirname, "overlay.config.json");
const ALWAYS_ON_TOP_LEVEL = "screen-saver";
const ENFORCE_ALWAYS_ON_TOP_MS = 2500;

const DEFAULT_CONFIG = {
  backendUrl: "http://127.0.0.1:8000",
  pollIntervalMs: 1000,
  positionPreset: "right-center",
  locked: true,
  debugVisible: false,
  opacity: 0.92,
  autoHideMs: 8000,
  urgentAutoHideMs: 12000
};

let overlayWindow = null;
let config = loadConfig();
let overlayVisible = true;
let moveSaveTimer = null;
let alwaysOnTopTimer = null;

function loadConfig() {
  try {
    const raw = fs.readFileSync(CONFIG_PATH, "utf8");
    return { ...DEFAULT_CONFIG, ...JSON.parse(raw) };
  } catch {
    return { ...DEFAULT_CONFIG };
  }
}

function saveConfig() {
  fs.writeFileSync(CONFIG_PATH, `${JSON.stringify(config, null, 2)}\n`, "utf8");
}

function createWindow() {
  overlayWindow = new BrowserWindow({
    width: WINDOW_WIDTH,
    height: WINDOW_HEIGHT,
    frame: false,
    transparent: true,
    backgroundColor: "#00000000",
    alwaysOnTop: true,
    skipTaskbar: true,
    resizable: false,
    maximizable: false,
    minimizable: false,
    fullscreenable: false,
    focusable: false,
    hasShadow: false,
    show: false,
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false
    }
  });

  overlayWindow.setOpacity(Number(config.opacity) || DEFAULT_CONFIG.opacity);
  enforceAlwaysOnTop();
  moveToPreset(config.positionPreset || "right-center", false);
  applyLockedMode();

  overlayWindow.loadFile(path.join(__dirname, "renderer", "index.html"));
  overlayWindow.once("ready-to-show", () => {
    enforceAlwaysOnTop();
    if (overlayVisible) {
      overlayWindow.showInactive();
      enforceAlwaysOnTop();
    }
  });

  overlayWindow.on("show", enforceAlwaysOnTop);
  overlayWindow.on("restore", enforceAlwaysOnTop);
  overlayWindow.on("hide", updateAlwaysOnTopTimer);
  overlayWindow.on("closed", () => {
    overlayWindow = null;
    updateAlwaysOnTopTimer();
  });

  overlayWindow.on("move", () => {
    if (!overlayWindow || config.locked) {
      return;
    }
    clearTimeout(moveSaveTimer);
    moveSaveTimer = setTimeout(() => {
      const bounds = overlayWindow.getBounds();
      config.positionPreset = "custom";
      config.customBounds = { x: bounds.x, y: bounds.y };
      saveConfig();
    }, 250);
  });
  updateAlwaysOnTopTimer();
}

function enforceAlwaysOnTop(options = {}) {
  if (!overlayWindow || overlayWindow.isDestroyed()) {
    return;
  }
  if (!overlayVisible && !options.force) {
    return;
  }
  if (overlayWindow.isMinimized() && overlayVisible) {
    overlayWindow.restore();
  }
  overlayWindow.setAlwaysOnTop(true, ALWAYS_ON_TOP_LEVEL);
  overlayWindow.setVisibleOnAllWorkspaces(true, { visibleOnFullScreen: true });
  overlayWindow.moveTop();
}

function updateAlwaysOnTopTimer() {
  clearInterval(alwaysOnTopTimer);
  alwaysOnTopTimer = null;
  if (!overlayWindow || overlayWindow.isDestroyed() || !overlayVisible) {
    return;
  }
  alwaysOnTopTimer = setInterval(enforceAlwaysOnTop, ENFORCE_ALWAYS_ON_TOP_MS);
  if (typeof alwaysOnTopTimer.unref === "function") {
    alwaysOnTopTimer.unref();
  }
}

function applyLockedMode() {
  if (!overlayWindow) {
    return;
  }
  try {
    overlayWindow.setIgnoreMouseEvents(Boolean(config.locked), { forward: true });
  } catch {
    overlayWindow.setIgnoreMouseEvents(Boolean(config.locked));
  }
  overlayWindow.webContents.send("overlay-config-updated", publicConfig());
}

function moveToPreset(preset, persist = true) {
  if (!overlayWindow) {
    return;
  }

  const display = screen.getPrimaryDisplay();
  const area = display.workArea;
  const margin = 28;
  const hudGap = 92;
  let x = area.x + area.width - WINDOW_WIDTH - margin;
  let y = area.y + Math.round((area.height - WINDOW_HEIGHT) / 2);

  if (preset === "top-left") {
    x = area.x + margin;
    y = area.y + margin;
  } else if (preset === "bottom-center") {
    x = area.x + Math.round((area.width - WINDOW_WIDTH) / 2);
    y = area.y + area.height - WINDOW_HEIGHT - hudGap;
  } else if (preset === "custom" && config.customBounds) {
    x = Number(config.customBounds.x) || x;
    y = Number(config.customBounds.y) || y;
  }

  overlayWindow.setBounds({ x, y, width: WINDOW_WIDTH, height: WINDOW_HEIGHT });
  if (persist) {
    config.positionPreset = preset;
    if (preset !== "custom") {
      delete config.customBounds;
    }
    saveConfig();
  }
}

function toggleVisibility() {
  if (!overlayWindow) {
    return;
  }
  overlayVisible = !overlayVisible;
  if (overlayVisible) {
    enforceAlwaysOnTop();
    overlayWindow.showInactive();
    enforceAlwaysOnTop();
  } else {
    overlayWindow.hide();
  }
  updateAlwaysOnTopTimer();
}

function toggleLocked() {
  config.locked = !config.locked;
  saveConfig();
  applyLockedMode();
}

function muteAdvice() {
  if (!overlayWindow) {
    return;
  }
  const mutedUntil = Date.now() + 5 * 60 * 1000;
  overlayWindow.webContents.send("overlay-muted", mutedUntil);
}

function closeOverlay() {
  if (overlayWindow) {
    overlayWindow.close();
  }
}

function toggleDebugLine() {
  config.debugVisible = !config.debugVisible;
  saveConfig();
  if (overlayWindow) {
    overlayWindow.webContents.send("overlay-toggle-debug", Boolean(config.debugVisible));
    overlayWindow.webContents.send("overlay-config-updated", publicConfig());
  }
}

function registerShortcuts() {
  globalShortcut.register("CommandOrControl+Alt+O", toggleVisibility);
  globalShortcut.register("CommandOrControl+Alt+M", muteAdvice);
  globalShortcut.register("CommandOrControl+Alt+L", toggleLocked);
  globalShortcut.register("CommandOrControl+Alt+1", () => moveToPreset("top-left"));
  globalShortcut.register("CommandOrControl+Alt+2", () => moveToPreset("right-center"));
  globalShortcut.register("CommandOrControl+Alt+3", () => moveToPreset("bottom-center"));
  globalShortcut.register("CommandOrControl+Shift+H", toggleVisibility);
  globalShortcut.register("CommandOrControl+Shift+Q", closeOverlay);
  globalShortcut.register("CommandOrControl+Shift+D", toggleDebugLine);
}

function publicConfig() {
  return {
    backendUrl: config.backendUrl,
    pollIntervalMs: config.pollIntervalMs,
    positionPreset: config.positionPreset,
    locked: config.locked,
    debugVisible: config.debugVisible,
    opacity: config.opacity,
    autoHideMs: config.autoHideMs,
    urgentAutoHideMs: config.urgentAutoHideMs
  };
}

ipcMain.handle("overlay:get-config", () => publicConfig());
ipcMain.handle("overlay:fetch-recommendation", async (_event, backendUrl) => {
  const baseUrl = String(backendUrl || DEFAULT_CONFIG.backendUrl).replace(/\/+$/, "");
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 2500);

  try {
    const response = await fetch(`${baseUrl}/overlay/recommendation`, {
      signal: controller.signal,
      cache: "no-store"
    });
    if (!response.ok) {
      return { ok: false, error: `Backend returned HTTP ${response.status}` };
    }
    return { ok: true, data: await response.json() };
  } catch {
    return { ok: false, error: "Waiting for backend..." };
  } finally {
    clearTimeout(timeout);
  }
});

app.whenReady().then(() => {
  createWindow();
  registerShortcuts();
  screen.on("display-added", enforceAlwaysOnTop);
  screen.on("display-removed", enforceAlwaysOnTop);
  screen.on("display-metrics-changed", enforceAlwaysOnTop);

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    } else {
      enforceAlwaysOnTop();
    }
  });
});

app.on("will-quit", () => {
  clearInterval(alwaysOnTopTimer);
  globalShortcut.unregisterAll();
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit();
  }
});
