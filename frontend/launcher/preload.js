const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("launcherApi", {
  getStatus: () => ipcRenderer.invoke("launcher:get-status"),
  getLogs: () => ipcRenderer.invoke("launcher:get-logs"),
  clearLogs: () => ipcRenderer.invoke("launcher:clear-logs"),
  copyLogs: () => ipcRenderer.invoke("launcher:copy-logs"),
  startBackend: () => ipcRenderer.invoke("launcher:start-backend"),
  stopBackend: () => ipcRenderer.invoke("launcher:stop-backend"),
  restartBackend: () => ipcRenderer.invoke("launcher:restart-backend"),
  startOverlay: () => ipcRenderer.invoke("launcher:start-overlay"),
  stopOverlay: () => ipcRenderer.invoke("launcher:stop-overlay"),
  setAutostart: (enabled) => ipcRenderer.invoke("launcher:set-autostart", enabled),
  runDemo: (presetName) => ipcRenderer.invoke("launcher:run-demo", presetName),
  runDeepReview: (presetName) => ipcRenderer.invoke("launcher:run-deep-review", presetName),
  stopDemo: () => ipcRenderer.invoke("launcher:stop-demo"),
  setLogMode: (mode) => ipcRenderer.invoke("launcher:set-log-mode", mode),
  checkLiveGsi: () => ipcRenderer.invoke("launcher:check-live-gsi"),
  startLiveRecording: () => ipcRenderer.invoke("launcher:start-live-recording"),
  stopLiveRecording: () => ipcRenderer.invoke("launcher:stop-live-recording"),
  checkGsi: (customPath) => ipcRenderer.invoke("launcher:check-gsi", customPath),
  installGsi: (customPath) => ipcRenderer.invoke("launcher:install-gsi", customPath),
  chooseGsiFolder: () => ipcRenderer.invoke("launcher:choose-gsi-folder"),
  chooseDotaFolder: () => ipcRenderer.invoke("launcher:choose-dota-folder"),
  setOverlayPosition: (preset) => ipcRenderer.invoke("launcher:set-overlay-position", preset),
  setLanguage: (value) => ipcRenderer.invoke("launcher:set-language", value),
  setAdviceFrequency: (value) => ipcRenderer.invoke("launcher:set-advice-frequency", value),
  setOverlaySize: (name) => ipcRenderer.invoke("launcher:set-overlay-size", name),
  setOverlayVoice: (mode, volume) => ipcRenderer.invoke("launcher:set-overlay-voice", mode, volume),
  setOverlayLocked: (locked) => ipcRenderer.invoke("launcher:set-overlay-locked", locked),
  dismissFullscreenWarning: () => ipcRenderer.invoke("launcher:dismiss-fullscreen-warning"),
  checkForUpdates: () => ipcRenderer.invoke("launcher:check-updates"),
  installUpdate: () => ipcRenderer.invoke("launcher:install-update"),
  // Linked player, match table, post-match review, career (see PLAYER_OPS in main.js).
  player: (op, args) => ipcRenderer.invoke("launcher:player", op, args),
  onPlayerEvent: (callback) => {
    ipcRenderer.on("launcher:player-event", (_event, payload) => callback(payload));
  },
  openLogs: () => ipcRenderer.invoke("launcher:open-logs"),
  exportPdf: (kind, id) => ipcRenderer.invoke("launcher:export-pdf", kind, id),
  dismissSetup: () => ipcRenderer.invoke("launcher:dismiss-setup"),
  saveProblemReport: () => ipcRenderer.invoke("launcher:save-problem-report"),
  openSimulationResults: () => ipcRenderer.invoke("launcher:open-simulation-results"),
  openSessionRecords: () => ipcRenderer.invoke("launcher:open-session-records"),
  openReadme: () => ipcRenderer.invoke("launcher:open-readme"),
  openAiKeyPage: (provider) => ipcRenderer.invoke("launcher:open-ai-key-page", provider),
  onStatus: (callback) => {
    ipcRenderer.on("launcher:status", (_event, status) => callback(status));
  },
  onLogs: (callback) => {
    ipcRenderer.on("launcher:logs", (_event, logs) => callback(logs));
  }
});
