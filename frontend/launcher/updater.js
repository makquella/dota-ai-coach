const { EventEmitter } = require("node:events");

// Auto-update from GitHub Releases through electron-updater (packaged Windows
// NSIS build only; dev runs and the portable exe are never updated).
//
// Flow: check at start and every few hours -> download in the background ->
// "ready". A ready update is installed
//   - when the user picks "Restart and update" (tray or control panel),
//   - when the app quits (electron-updater autoInstallOnAppQuit),
//   - or by itself once Dota is not running and the control panel is not open
//     (canInstallNow), so an "open and forget" tray app does not stay on an
//     old version for weeks. The app then comes back hidden in the tray.
// Nothing is ever installed while Dota is running.

const CHECK_INTERVAL_MS = 4 * 60 * 60 * 1000;
const FIRST_CHECK_DELAY_MS = 15 * 1000;
const IDLE_INSTALL_POLL_MS = 60 * 1000;
// Dota must have been closed this long before an unattended install.
const IDLE_INSTALL_AFTER_MS = 5 * 60 * 1000;

const STATUS = {
  DISABLED: "disabled",
  IDLE: "idle",
  CHECKING: "checking",
  UP_TO_DATE: "up-to-date",
  DOWNLOADING: "downloading",
  READY: "ready",
  ERROR: "error"
};

function defaultLoadAutoUpdater() {
  return require("electron-updater").autoUpdater;
}

/**
 * @param {object} options
 * @param {string}   options.currentVersion  app.getVersion()
 * @param {boolean}  options.supported       packaged NSIS build on Windows
 * @param {Function} options.isGameRunning   () => boolean; blocks every install, manual ones too
 * @param {Function} options.canInstallNow   () => boolean; extra condition for the unattended install (panel hidden…)
 * @param {Function} options.beforeInstall   ({ unattended }) => void; e.g. remember to restart hidden
 * @param {Function} options.loadAutoUpdater () => electron-updater autoUpdater (injectable for tests)
 */
function createUpdater({
  currentVersion = "0.0.0",
  supported = false,
  isGameRunning = () => false,
  canInstallNow = () => false,
  beforeInstall = () => {},
  loadAutoUpdater = defaultLoadAutoUpdater,
  log = () => {},
  now = () => Date.now()
} = {}) {
  const emitter = new EventEmitter();
  let autoUpdater = null;
  let checkTimer = null;
  let idleTimer = null;
  let firstCheckTimer = null;
  let idleSince = null;
  let installing = false;
  let state = {
    supported,
    status: supported ? STATUS.IDLE : STATUS.DISABLED,
    currentVersion,
    version: "",
    percent: 0,
    error: "",
    checkedAt: null
  };

  function update(patch) {
    const next = { ...state, ...patch };
    const changed = Object.keys(next).some((key) => next[key] !== state[key]);
    state = next;
    if (changed) {
      emitter.emit("change", emitter.getState());
    }
  }

  function wire(updater) {
    updater.autoDownload = true;
    updater.autoInstallOnAppQuit = true;
    updater.allowPrerelease = false;
    updater.allowDowngrade = false;
    updater.logger = {
      info: (message) => log(String(message)),
      warn: (message) => log(`warn: ${message}`),
      error: (message) => log(`error: ${message}`),
      debug: () => {}
    };
    updater.on("checking-for-update", () => {
      if (state.status !== STATUS.READY && state.status !== STATUS.DOWNLOADING) {
        update({ status: STATUS.CHECKING, error: "" });
      }
    });
    updater.on("update-available", (info) => {
      log(`Update ${info?.version || "?"} is available; downloading.`);
      update({ status: STATUS.DOWNLOADING, version: String(info?.version || ""), percent: 0, error: "" });
    });
    updater.on("update-not-available", () => {
      update({ status: STATUS.UP_TO_DATE, checkedAt: now(), error: "" });
    });
    updater.on("download-progress", (progress) => {
      const percent = Math.max(0, Math.min(100, Math.round(Number(progress?.percent) || 0)));
      update({ status: STATUS.DOWNLOADING, percent });
    });
    updater.on("update-downloaded", (info) => {
      log(`Update ${info?.version || state.version} downloaded; it installs on restart.`);
      update({ status: STATUS.READY, version: String(info?.version || state.version), percent: 100, checkedAt: now() });
    });
    updater.on("error", (error) => {
      log(`Update error: ${error?.message || error}`);
      // A failed check must not hide an update that is already downloaded.
      if (state.status !== STATUS.READY) {
        update({ status: STATUS.ERROR, error: String(error?.message || error || "unknown error"), checkedAt: now() });
      }
    });
  }

  async function check() {
    if (!autoUpdater || installing) {
      return emitter.getState();
    }
    if (state.status === STATUS.DOWNLOADING || state.status === STATUS.READY) {
      return emitter.getState();
    }
    try {
      await autoUpdater.checkForUpdates();
    } catch (error) {
      // Also reported through the "error" event; keep the promise quiet.
      if (state.status !== STATUS.ERROR && state.status !== STATUS.READY) {
        update({ status: STATUS.ERROR, error: String(error?.message || error), checkedAt: now() });
      }
    }
    return emitter.getState();
  }

  function install({ unattended = false } = {}) {
    if (!autoUpdater || state.status !== STATUS.READY || installing) {
      return false;
    }
    if (isGameRunning()) {
      // Installing restarts the app and stops the overlay: never mid-game.
      log("Update install postponed: Dota is running.");
      return false;
    }
    installing = true;
    log(`Installing update ${state.version}${unattended ? " (Dota is closed, installing in the background)" : ""}.`);
    try {
      beforeInstall({ unattended });
    } catch (error) {
      log(`beforeInstall failed: ${error.message}`);
    }
    // isSilent: no installer UI; isForceRunAfter: start the app again.
    autoUpdater.quitAndInstall(true, true);
    return true;
  }

  function idleTick() {
    if (state.status !== STATUS.READY || installing) {
      idleSince = null;
      return;
    }
    if (isGameRunning() || !canInstallNow()) {
      idleSince = null;
      return;
    }
    if (idleSince === null) {
      idleSince = now();
      return;
    }
    if (now() - idleSince >= IDLE_INSTALL_AFTER_MS) {
      install({ unattended: true });
    }
  }

  emitter.start = () => {
    if (!supported || autoUpdater) {
      return;
    }
    try {
      autoUpdater = loadAutoUpdater();
    } catch (error) {
      log(`Auto-update is unavailable: ${error.message}`);
      update({ supported: false, status: STATUS.DISABLED, error: error.message });
      return;
    }
    wire(autoUpdater);
    firstCheckTimer = setTimeout(check, FIRST_CHECK_DELAY_MS);
    checkTimer = setInterval(check, CHECK_INTERVAL_MS);
    idleTimer = setInterval(idleTick, IDLE_INSTALL_POLL_MS);
    for (const timer of [firstCheckTimer, checkTimer, idleTimer]) {
      timer.unref?.();
    }
  };

  emitter.stop = () => {
    clearTimeout(firstCheckTimer);
    clearInterval(checkTimer);
    clearInterval(idleTimer);
  };

  emitter.check = check;
  emitter.install = install;
  emitter.idleTick = idleTick;
  emitter.getState = () => ({ ...state });
  return emitter;
}

module.exports = {
  createUpdater,
  UPDATE_STATUS: STATUS,
  IDLE_INSTALL_AFTER_MS
};
