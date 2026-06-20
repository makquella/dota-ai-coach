const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("overlayApi", {
  getConfig: () => ipcRenderer.invoke("overlay:get-config"),
  fetchRecommendation: (backendUrl) => ipcRenderer.invoke("overlay:fetch-recommendation", backendUrl),
  onConfigUpdated: (callback) => {
    ipcRenderer.on("overlay-config-updated", (_event, config) => callback(config));
  },
  onMuted: (callback) => {
    ipcRenderer.on("overlay-muted", (_event, mutedUntil) => callback(mutedUntil));
  },
  onToggleDebug: (callback) => {
    ipcRenderer.on("overlay-toggle-debug", (_event, visible) => callback(visible));
  }
});
