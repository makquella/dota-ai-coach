const { BrowserWindow, ipcMain, screen } = require("electron");
const path = require("node:path");

const {
  DEFAULT_FRAME,
  MAX_SLOTS,
  arrowLayout,
  arrowTarget,
  barRect,
  frameFractions,
  validFrame
} = require("./skill-arrow-placement");
const { sameBounds } = require("./overlay-placement");

// Skill arrows (0.43): while the overlay names the ability to level («Learn
// your ultimate: Omnislash»), an arrow over that icon of Dota's ability bar.
// Two windows: the arrow itself (transparent, click-through, never focused)
// and, once, the calibration screen where the player lays a frame over the
// ability icons. Without a calibration there is no arrow: the card says it all.

const ALWAYS_ON_TOP_LEVEL = "screen-saver";
// The calibration screen covers the bottom of Dota's window, where the HUD is.
const CALIBRATION_SHARE = 0.42;

function createSkillArrowController({ settings, getDotaRect = () => null, getLocale = () => "en", log = () => {} }) {
  let arrowWindow = null;
  let calibrationWindow = null;
  let calibrationArea = null;
  let target = null;
  let overlayShown = false;
  let barSize = null;
  let lastPayload = "";

  function config() {
    return settings.get("overlay") || {};
  }

  function isEnabled() {
    return config().skillArrows !== false;
  }

  function calibration() {
    return validFrame(config().skillFrame);
  }

  function state() {
    return { enabled: isEnabled(), calibrated: Boolean(calibration()), calibrating: isOpen(calibrationWindow) };
  }

  function isOpen(win) {
    return Boolean(win && !win.isDestroyed());
  }

  // The watcher reports physical pixels; Electron places windows in DIP.
  function dotaArea() {
    const physical = getDotaRect();
    if (physical) {
      if (process.platform === "win32" && typeof screen.screenToDipRect === "function") {
        try {
          return screen.screenToDipRect(null, physical);
        } catch {
          // Fall through to the raw rect.
        }
      }
      return physical;
    }
    return screen.getPrimaryDisplay().bounds;
  }

  // From every overlay poll: the hint's ability, and the bar's size for calibration.
  function update(data) {
    if (data && Number.isInteger(data.skill_bar) && data.skill_bar > 0 && data.skill_bar <= MAX_SLOTS) {
      barSize = data.skill_bar;
    }
    target = arrowTarget(data);
    refresh();
  }

  function setOverlayVisible(visible) {
    overlayShown = Boolean(visible);
    refresh();
  }

  function refresh() {
    const frame = calibration();
    if (!isEnabled() || !frame || !target || !overlayShown || isOpen(calibrationWindow)) {
      hideArrow();
      return;
    }
    const bar = barRect(frame, dotaArea(), target.slots);
    const layout = arrowLayout(bar, target.slot, target.slots);
    const win = openArrow();
    if (!sameBounds(win.getBounds(), layout.window)) {
      win.setBounds(layout.window);
    }
    const payload = JSON.stringify({ slot: layout.slot, name: target.name, title: target.title, locale: getLocale() });
    if (payload !== lastPayload) {
      lastPayload = payload;
      send(win, "skill-arrow:show", JSON.parse(payload));
    }
    if (!win.isVisible()) {
      win.showInactive();
    }
    win.setAlwaysOnTop(true, ALWAYS_ON_TOP_LEVEL);
    win.moveTop();
  }

  function openArrow() {
    if (isOpen(arrowWindow)) {
      return arrowWindow;
    }
    arrowWindow = new BrowserWindow({
      width: 320,
      height: 140,
      title: "Wardly Skill Arrow",
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
        preload: path.join(__dirname, "skill-arrows-preload.js"),
        contextIsolation: true,
        nodeIntegration: false
      }
    });
    arrowWindow.setIgnoreMouseEvents(true);
    arrowWindow.setVisibleOnAllWorkspaces(true, { visibleOnFullScreen: true });
    arrowWindow.loadFile(path.join(__dirname, "skill-arrows", "index.html"), { query: { mode: "arrow" } });
    arrowWindow.webContents.on("did-finish-load", () => {
      lastPayload = "";
      refresh();
    });
    arrowWindow.on("closed", () => {
      arrowWindow = null;
    });
    return arrowWindow;
  }

  function hideArrow() {
    if (isOpen(arrowWindow) && arrowWindow.isVisible()) {
      arrowWindow.hide();
    }
  }

  // The calibration screen over the bottom of Dota's window: the frame starts
  // where it was saved (or the default), sized for the bar the game shows now.
  function startCalibration() {
    hideArrow();
    const dota = dotaArea();
    const height = Math.round(dota.height * CALIBRATION_SHARE);
    calibrationArea = { x: dota.x, y: dota.y + dota.height - height, width: dota.width, height };
    const frame = calibration() || DEFAULT_FRAME;
    const slots = barSize || frame.slots;
    const rect = barRect(frame, dota, slots);
    const payload = {
      locale: getLocale(),
      slots,
      detected: Boolean(barSize),
      frame: { x: rect.x - calibrationArea.x, y: rect.y - calibrationArea.y, width: rect.width, height: rect.height }
    };
    if (isOpen(calibrationWindow)) {
      calibrationWindow.setBounds(calibrationArea);
      send(calibrationWindow, "skill-arrow:calibrate", payload);
      calibrationWindow.focus();
      return state();
    }
    calibrationWindow = new BrowserWindow({
      ...calibrationArea,
      title: "Wardly — skill arrows",
      frame: false,
      transparent: true,
      backgroundColor: "#00000000",
      alwaysOnTop: true,
      skipTaskbar: true,
      resizable: false,
      maximizable: false,
      minimizable: false,
      fullscreenable: false,
      hasShadow: false,
      show: false,
      webPreferences: {
        preload: path.join(__dirname, "skill-arrows-preload.js"),
        contextIsolation: true,
        nodeIntegration: false
      }
    });
    calibrationWindow.setAlwaysOnTop(true, ALWAYS_ON_TOP_LEVEL);
    calibrationWindow.loadFile(path.join(__dirname, "skill-arrows", "index.html"), { query: { mode: "calibrate" } });
    calibrationWindow.webContents.on("did-finish-load", () => send(calibrationWindow, "skill-arrow:calibrate", payload));
    calibrationWindow.once("ready-to-show", () => {
      calibrationWindow.show();
      calibrationWindow.focus();
    });
    calibrationWindow.on("closed", () => {
      calibrationWindow = null;
      refresh();
    });
    log("Skill arrows: calibration opened.");
    return state();
  }

  function finishCalibration(result) {
    if (result && calibrationArea) {
      const rect = {
        x: calibrationArea.x + Number(result.x),
        y: calibrationArea.y + Number(result.y),
        width: Number(result.width),
        height: Number(result.height)
      };
      const slots = Number(result.slots);
      const frame = validFrame(frameFractions(rect, dotaArea(), Number.isFinite(slots) ? slots : DEFAULT_FRAME.slots));
      if (frame) {
        settings.update("overlay", { skillFrame: frame, skillArrows: true });
        log(`Skill arrows: frame saved (${frame.slots} abilities).`);
      }
    }
    if (isOpen(calibrationWindow)) {
      calibrationWindow.close();
    }
    return state();
  }

  function setEnabled(enabled) {
    settings.update("overlay", { skillArrows: Boolean(enabled) });
    refresh();
    return state();
  }

  function resetCalibration() {
    settings.update("overlay", { skillFrame: undefined });
    refresh();
    return state();
  }

  function send(win, channel, payload) {
    if (isOpen(win)) {
      win.webContents.send(channel, payload);
    }
  }

  function registerIpc(onChange = () => {}) {
    ipcMain.handle("skill-arrow:save", (_event, result) => {
      const next = finishCalibration(result && typeof result === "object" ? result : null);
      onChange();
      return next;
    });
    ipcMain.handle("skill-arrow:cancel", () => {
      const next = finishCalibration(null);
      onChange();
      return next;
    });
  }

  function dispose() {
    for (const win of [arrowWindow, calibrationWindow]) {
      if (isOpen(win)) {
        win.destroy();
      }
    }
    arrowWindow = null;
    calibrationWindow = null;
  }

  return {
    update,
    setOverlayVisible,
    startCalibration,
    finishCalibration,
    setEnabled,
    resetCalibration,
    state,
    registerIpc,
    dispose
  };
}

module.exports = { createSkillArrowController };
