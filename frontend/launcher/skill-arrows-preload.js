const { contextBridge, ipcRenderer } = require("electron");

// The skill arrow and its calibration screen (skill-arrow-window.js).
contextBridge.exposeInMainWorld("skillArrowApi", {
  onShow: (callback) => {
    ipcRenderer.on("skill-arrow:show", (_event, payload) => callback(payload));
  },
  onCalibrate: (callback) => {
    ipcRenderer.on("skill-arrow:calibrate", (_event, payload) => callback(payload));
  },
  save: (frame) => ipcRenderer.invoke("skill-arrow:save", frame),
  cancel: () => ipcRenderer.invoke("skill-arrow:cancel"),
  auto: () => ipcRenderer.invoke("skill-arrow:auto")
});
