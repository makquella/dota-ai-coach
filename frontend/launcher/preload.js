const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("launcherApi", {
  getStatus: () => ipcRenderer.invoke("launcher:get-status"),
  getLogs: () => ipcRenderer.invoke("launcher:get-logs"),
  clearLogs: () => ipcRenderer.invoke("launcher:clear-logs"),
  copyLogs: () => ipcRenderer.invoke("launcher:copy-logs"),
  startBackend: () => ipcRenderer.invoke("launcher:start-backend"),
  stopBackend: () => ipcRenderer.invoke("launcher:stop-backend"),
  startOverlay: () => ipcRenderer.invoke("launcher:start-overlay"),
  stopOverlay: () => ipcRenderer.invoke("launcher:stop-overlay"),
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
  openLogs: () => ipcRenderer.invoke("launcher:open-logs"),
  openSimulationResults: () => ipcRenderer.invoke("launcher:open-simulation-results"),
  openSessionRecords: () => ipcRenderer.invoke("launcher:open-session-records"),
  openReadme: () => ipcRenderer.invoke("launcher:open-readme"),
  onStatus: (callback) => {
    ipcRenderer.on("launcher:status", (_event, status) => callback(status));
  },
  onLogs: (callback) => {
    ipcRenderer.on("launcher:logs", (_event, logs) => callback(logs));
  }
});
