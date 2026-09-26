const { BrowserWindow, globalShortcut, screen } = require("electron");
const path = require("node:path");

// Always-on-top advice card. It used to be a separate Electron app
// (frontend/desktop-overlay); now it is a second window of the launcher so the
// whole coach runs as one process with one tray icon.

const WINDOW_WIDTH = 420;
const WINDOW_HEIGHT = 140;
const ALWAYS_ON_TOP_LEVEL = "screen-saver";
const ENFORCE_ALWAYS_ON_TOP_MS = 2500;
const MUTE_MS = 5 * 60 * 1000;

const OVERLAY_DEFAULTS = {
  enabled: true,
  pollIntervalMs: 1000,
  positionPreset: "right-center",
  locked: true,
  debugVisible: false,
  opacity: 1,
  autoHideMs: 8000,
  urgentAutoHideMs: 12000
};

// The window exists while the overlay is enabled; whether it is on screen is
// decided separately (setVisible) from Dota focus + fresh GSI, see
// overlay-visibility.js. The always-on-top timer only runs while it is shown.
function createOverlayController({ settings, getBackend, getLocale = () => "en", onChange = () => {}, log = () => {} }) {
  let overlayWindow = null;
  let alwaysOnTopTimer = null;
  let moveSaveTimer = null;
  let windowShortcutsRegistered = false;
  let wantVisible = false;

  const windowShortcuts = [
    ["CommandOrControl+Alt+M", muteAdvice],
    ["CommandOrControl+Alt+L", toggleLocked],
    ["CommandOrControl+Alt+D", toggleDebugLine],
    ["CommandOrControl+Alt+1", () => setPosition("left-center")],
    ["CommandOrControl+Alt+2", () => setPosition("right-center")],
    ["CommandOrControl+Alt+3", () => setPosition("bottom-center")]
  ];

  function config() {
    const merged = { ...OVERLAY_DEFAULTS, ...(settings.get("overlay") || {}) };
    // 0.92 was the old default window opacity; the card itself is now 85%
    // opaque, so dimming the whole window on top of that hurts readability.
    if (merged.opacity === 0.92) {
      merged.opacity = 1;
    }
    return merged;
  }

  function updateConfig(patch) {
    settings.update("overlay", patch);
  }

  function isEnabled() {
    return Boolean(config().enabled);
  }

  function isOpen() {
    return Boolean(overlayWindow && !overlayWindow.isDestroyed());
  }

  function isVisible() {
    return isOpen() && overlayWindow.isVisible();
  }

  function isUnlocked() {
    return !config().locked;
  }

  function setVisible(visible) {
    wantVisible = Boolean(visible);
    if (!isOpen()) {
      return;
    }
    if (wantVisible && !overlayWindow.isVisible()) {
      overlayWindow.showInactive();
      enforceAlwaysOnTop();
    } else if (!wantVisible && overlayWindow.isVisible()) {
      overlayWindow.hide();
    }
    updateAlwaysOnTopTimer();
  }

  function setEnabled(enabled) {
    updateConfig({ enabled: Boolean(enabled) });
    if (enabled) {
      open();
    } else {
      close();
    }
    onChange();
  }

  function toggle() {
    setEnabled(!isEnabled());
  }

  function open() {
    if (isOpen()) {
      enforceAlwaysOnTop();
      return overlayWindow;
    }
    const current = config();
    overlayWindow = new BrowserWindow({
      width: WINDOW_WIDTH,
      height: WINDOW_HEIGHT,
      title: "Dota AI Coach Overlay",
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
        preload: path.join(__dirname, "overlay-preload.js"),
        contextIsolation: true,
        nodeIntegration: false
      }
    });

    overlayWindow.setOpacity(Number(current.opacity) || OVERLAY_DEFAULTS.opacity);
    enforceAlwaysOnTop();
    moveToPreset(current.positionPreset || OVERLAY_DEFAULTS.positionPreset, false);
    applyLockedMode();

    overlayWindow.loadFile(path.join(__dirname, "overlay", "index.html"));
    overlayWindow.once("ready-to-show", () => {
      if (!isOpen() || !wantVisible) {
        return;
      }
      overlayWindow.showInactive();
      enforceAlwaysOnTop();
      updateAlwaysOnTopTimer();
    });

    overlayWindow.on("show", enforceAlwaysOnTop);
    overlayWindow.on("closed", () => {
      overlayWindow = null;
      updateAlwaysOnTopTimer();
      unregisterWindowShortcuts();
    });
    overlayWindow.on("move", () => {
      if (!isOpen() || config().locked) {
        return;
      }
      clearTimeout(moveSaveTimer);
      moveSaveTimer = setTimeout(() => {
        if (!isOpen()) {
          return;
        }
        const bounds = overlayWindow.getBounds();
        updateConfig({ positionPreset: "custom", customBounds: { x: bounds.x, y: bounds.y } });
      }, 250);
    });

    registerWindowShortcuts();
    updateAlwaysOnTopTimer();
    return overlayWindow;
  }

  function close() {
    unregisterWindowShortcuts();
    clearTimeout(moveSaveTimer);
    if (isOpen()) {
      overlayWindow.destroy();
    }
    overlayWindow = null;
    updateAlwaysOnTopTimer();
  }

  function enforceAlwaysOnTop() {
    if (!isVisible()) {
      return;
    }
    overlayWindow.setAlwaysOnTop(true, ALWAYS_ON_TOP_LEVEL);
    overlayWindow.setVisibleOnAllWorkspaces(true, { visibleOnFullScreen: true });
    overlayWindow.moveTop();
  }

  function updateAlwaysOnTopTimer() {
    clearInterval(alwaysOnTopTimer);
    alwaysOnTopTimer = null;
    if (!isVisible()) {
      return;
    }
    alwaysOnTopTimer = setInterval(enforceAlwaysOnTop, ENFORCE_ALWAYS_ON_TOP_MS);
    if (typeof alwaysOnTopTimer.unref === "function") {
      alwaysOnTopTimer.unref();
    }
  }

  function applyLockedMode() {
    if (!isOpen()) {
      return;
    }
    const locked = Boolean(config().locked);
    try {
      overlayWindow.setIgnoreMouseEvents(locked, { forward: true });
    } catch {
      overlayWindow.setIgnoreMouseEvents(locked);
    }
    send("overlay-config-updated", publicConfig());
  }

  // Presets keep the card off the Dota HUD: the minimap and the hero panel
  // take roughly the bottom 22% of the screen, the top bar the top ~8%.
  function moveToPreset(preset, persist = true) {
    if (!isOpen()) {
      return;
    }
    preset = normalizePreset(preset);
    const current = config();
    const area = screen.getPrimaryDisplay().workArea;
    const margin = 24;
    const hudHeight = Math.round(area.height * 0.24);
    let x = area.x + area.width - WINDOW_WIDTH - margin;
    let y = area.y + Math.round((area.height - WINDOW_HEIGHT) / 2);

    if (preset === "left-center") {
      x = area.x + margin;
    } else if (preset === "bottom-center") {
      x = area.x + Math.round((area.width - WINDOW_WIDTH) / 2);
      y = area.y + area.height - hudHeight - WINDOW_HEIGHT;
    } else if (preset === "custom" && current.customBounds) {
      x = Number(current.customBounds.x) || x;
      y = Number(current.customBounds.y) || y;
    }

    overlayWindow.setBounds({ x, y, width: WINDOW_WIDTH, height: WINDOW_HEIGHT });
    if (persist) {
      updateConfig({
        positionPreset: preset,
        customBounds: preset === "custom" ? current.customBounds : undefined
      });
    }
  }

  function normalizePreset(preset) {
    // "top-left" was an older preset that sat on Dota's top-left menu.
    return preset === "top-left" ? "left-center" : preset;
  }

  function setPosition(preset) {
    const next = normalizePreset(preset);
    if (!["left-center", "right-center", "bottom-center"].includes(next)) {
      return;
    }
    if (isOpen()) {
      moveToPreset(next);
    } else {
      updateConfig({ positionPreset: next, customBounds: undefined });
    }
    onChange();
  }

  function position() {
    return normalizePreset(config().positionPreset || OVERLAY_DEFAULTS.positionPreset);
  }

  function setLocked(locked) {
    if (Boolean(locked) === Boolean(config().locked)) {
      return;
    }
    toggleLocked();
  }

  function toggleLocked() {
    updateConfig({ locked: !config().locked });
    applyLockedMode();
    log(`Overlay ${config().locked ? "locked (click-through)" : "unlocked (draggable, shown until locked again)"}.`);
    onChange();
  }

  function muteAdvice() {
    send("overlay-muted", Date.now() + MUTE_MS);
  }

  function toggleDebugLine() {
    updateConfig({ debugVisible: !config().debugVisible });
    send("overlay-toggle-debug", Boolean(config().debugVisible));
    send("overlay-config-updated", publicConfig());
  }

  function send(channel, payload) {
    if (isOpen()) {
      overlayWindow.webContents.send(channel, payload);
    }
  }

  function registerShortcut(accelerator, handler) {
    try {
      if (!globalShortcut.register(accelerator, handler)) {
        log(`Shortcut ${accelerator} is used by another application.`);
      }
    } catch (error) {
      log(`Shortcut ${accelerator} could not be registered: ${error.message}`);
    }
  }

  function registerWindowShortcuts() {
    if (windowShortcutsRegistered) {
      return;
    }
    windowShortcutsRegistered = true;
    for (const [accelerator, handler] of windowShortcuts) {
      registerShortcut(accelerator, handler);
    }
  }

  function unregisterWindowShortcuts() {
    if (!windowShortcutsRegistered) {
      return;
    }
    windowShortcutsRegistered = false;
    for (const [accelerator] of windowShortcuts) {
      globalShortcut.unregister(accelerator);
    }
  }

  // Ctrl+Alt+O stays registered while the app runs so the overlay can be
  // turned back on from inside the game.
  function registerGlobalShortcuts() {
    registerShortcut("CommandOrControl+Alt+O", toggle);
  }

  function publicConfig() {
    const current = config();
    const backend = getBackend();
    return {
      locale: getLocale(),
      backendUrl: backend.url,
      backendPort: backend.port,
      backendStatus: backend.status,
      pollIntervalMs: current.pollIntervalMs,
      positionPreset: current.positionPreset,
      locked: current.locked,
      debugVisible: current.debugVisible,
      opacity: current.opacity,
      autoHideMs: current.autoHideMs,
      urgentAutoHideMs: current.urgentAutoHideMs
    };
  }

  function notifyBackendChanged() {
    send("overlay-config-updated", publicConfig());
  }

  function dispose() {
    close();
    globalShortcut.unregisterAll();
  }

  return {
    open,
    close,
    toggle,
    setEnabled,
    isEnabled,
    isOpen,
    isVisible,
    isUnlocked,
    setVisible,
    setPosition,
    position,
    setLocked,
    window: () => (isOpen() ? overlayWindow : null),
    enforceAlwaysOnTop,
    publicConfig,
    notifyBackendChanged,
    registerGlobalShortcuts,
    dispose
  };
}

module.exports = { createOverlayController, OVERLAY_DEFAULTS };
