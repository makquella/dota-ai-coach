"use strict";

const { pathToFileURL } = require("node:url");

function localPage(filePath, query = {}) {
  const url = pathToFileURL(filePath);
  for (const [key, value] of Object.entries(query)) url.searchParams.set(key, value);
  return url.href;
}

function samePage(value, expected) {
  try {
    const url = new URL(value);
    url.hash = ""; // In-page anchors do not change the trusted document.
    return url.href === expected;
  } catch {
    return false;
  }
}

function trustedSender(event, window, expectedPage) {
  try {
    if (!window || window.isDestroyed()) return false;
    const contents = window.webContents;
    return !contents.isDestroyed() &&
      event.sender === contents &&
      Boolean(event.senderFrame) &&
      event.senderFrame === contents.mainFrame &&
      samePage(event.senderFrame.url, expectedPage);
  } catch {
    // A frame can disappear while its invoke is being delivered.
    return false;
  }
}

function trustedHandlers(ipcMain, getWindow, filePath, query = {}) {
  const expected = localPage(filePath, query);
  return (channel, handler) => {
    ipcMain.handle(channel, (event, ...args) => {
      if (!trustedSender(event, getWindow(), expected)) throw new Error("Untrusted IPC sender.");
      return handler(event, ...args);
    });
  };
}

function protectWindow(window) {
  const contents = window.webContents;
  contents.setWindowOpenHandler(() => ({ action: "deny" }));
  // loadFile from the main process still works; renderer-initiated navigation
  // and redirects, including subframes/webviews, cannot replace local pages.
  for (const name of ["will-navigate", "will-frame-navigate", "will-redirect", "will-attach-webview"]) {
    contents.on(name, (event) => event.preventDefault());
  }
}

module.exports = { localPage, trustedSender, trustedHandlers, protectWindow };
