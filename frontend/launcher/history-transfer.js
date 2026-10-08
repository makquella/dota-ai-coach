"use strict";

const fs = require("node:fs");
const path = require("node:path");
const zlib = require("node:zlib");
const transferCode = require("./transfer-code");

// Main supplies OS/backend/cloud ports. File, gzip, encryption, retry and import
// orchestration live here; trusted IPC registration remains in main.js.
function createHistoryTransfer({getWindow, dialog, reportFolder, requestBackendJson,
  appendLog, showItemInFolder, backendRunning, fetch, apiUrl, installId}) {
  // ---------------------------------------------------------------------------
  // History backup: the backend's whole history (no keys) in one gzipped file
  // ---------------------------------------------------------------------------

  const BACKUP_TIMEOUT_MS = 180000;
  const BACKUP_MAX_BYTES = 512 * 1024 * 1024;

  function backupFailure(error) {
    const payload = error.payload || {};
    return {
      ok: false,
      code: payload.code || (!backendRunning() ? "backend_down" : "failed"),
      error: payload.detail || error.message
    };
  }

  async function exportHistory() {
    const mainWindow = getWindow();
    if (!mainWindow || mainWindow.isDestroyed()) {
      return { ok: false, code: "no_window" };
    }
    const stamp = new Date().toISOString().slice(0, 10);
    const { canceled, filePath } = await dialog.showSaveDialog(mainWindow, {
      defaultPath: path.join(reportFolder(), `Wardly-backup-${stamp}.json.gz`),
      filters: [{ name: "Wardly backup", extensions: ["gz", "json"] }]
    });
    if (canceled || !filePath) {
      return { ok: false, canceled: true };
    }
    try {
      const data = await requestBackendJson("/player/backup", "GET", undefined, BACKUP_TIMEOUT_MS);
      const text = JSON.stringify(data);
      fs.writeFileSync(filePath, filePath.toLowerCase().endsWith(".json") ? text : zlib.gzipSync(text));
      appendLog("launcher", `History backup saved: ${filePath}`, { force: true });
      showItemInFolder(filePath);
      return { ok: true, path: filePath, matches: (data.counts && data.counts.matches) || 0 };
    } catch (error) {
      appendLog("launcher", `History backup failed: ${error.message}`, { force: true });
      return backupFailure(error);
    }
  }

  async function importHistory() {
    const mainWindow = getWindow();
    if (!mainWindow || mainWindow.isDestroyed()) {
      return { ok: false, code: "no_window" };
    }
    const { canceled, filePaths } = await dialog.showOpenDialog(mainWindow, {
      defaultPath: reportFolder(),
      properties: ["openFile"],
      filters: [{ name: "Wardly backup", extensions: ["gz", "json"] }]
    });
    if (canceled || !filePaths || !filePaths[0]) {
      return { ok: false, canceled: true };
    }
    let data;
    try {
      let raw = fs.readFileSync(filePaths[0]);
      if (raw[0] === 0x1f && raw[1] === 0x8b) {
        raw = zlib.gunzipSync(raw, { maxOutputLength: BACKUP_MAX_BYTES });
      }
      data = JSON.parse(raw.toString("utf8"));
    } catch (error) {
      return { ok: false, code: "not_backup", error: error.message };
    }
    try {
      const result = await requestBackendJson("/player/backup", "POST", data, BACKUP_TIMEOUT_MS);
      appendLog("launcher", `History backup loaded: ${filePaths[0]}`, { force: true });
      return { ok: true, ...result };
    } catch (error) {
      appendLog("launcher", `Loading the history backup failed: ${error.message}`, { force: true });
      return backupFailure(error);
    }
  }

  // ---------------------------------------------------------------------------
  // History by code: the backup, gzipped and encrypted with the secret part of a
  // one-time code (transfer-code.js), kept 15 minutes by the API; the other
  // computer downloads it with the code, decrypts, imports and deletes it.
  // ---------------------------------------------------------------------------

  const TRANSFER_TIMEOUT_MS = 60_000;
  const TRANSFER_MAX_BYTES = 1_500_000;

  async function transferFetch(url, options) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), TRANSFER_TIMEOUT_MS);
    try {
      return await fetch(url, { ...options, signal: controller.signal });
    } finally {
      clearTimeout(timer);
    }
  }

  async function sendHistoryByCode() {
    let data;
    try {
      data = await requestBackendJson("/player/backup", "GET", undefined, BACKUP_TIMEOUT_MS);
    } catch (error) {
      return backupFailure(error);
    }
    const packed = zlib.gzipSync(JSON.stringify(data));
    try {
      // A new code when its id is taken (a 4-character id; the API says 409).
      for (let attempt = 0; attempt < 3; attempt += 1) {
        const code = transferCode.newTransferCode();
        const box = transferCode.seal(packed, code);
        if (box.length > TRANSFER_MAX_BYTES) {
          return { ok: false, code: "too_big" };
        }
        const response = await transferFetch(`${apiUrl()}/v1/transfer/${code.id}`, {
          method: "PUT",
          headers: { "content-type": "application/octet-stream", "x-install-id": installId() },
          body: box
        });
        if (response.status === 409) {
          continue;
        }
        const answer = await response.json().catch(() => ({}));
        if (!response.ok) {
          return { ok: false, code: answer.code || `http_${response.status}` };
        }
        appendLog("launcher", `History sent by code (${(data.counts && data.counts.matches) || 0} matches).`, { force: true });
        return { ok: true, code: code.code, expiresAt: Number(answer.expires_at) || null, matches: (data.counts && data.counts.matches) || 0 };
      }
      return { ok: false, code: "taken" };
    } catch (error) {
      return { ok: false, code: "offline", error: error.message };
    }
  }

  async function receiveHistoryByCode(input) {
    const code = transferCode.parseTransferCode(input);
    if (!code) {
      return { ok: false, code: "bad_code" };
    }
    let box;
    try {
      const response = await transferFetch(`${apiUrl()}/v1/transfer/${code.id}/claim`, { method: "POST" });
      if (!response.ok) {
        const answer = await response.json().catch(() => ({}));
        return { ok: false, code: answer.code || `http_${response.status}` };
      }
      box = Buffer.from(await response.arrayBuffer());
    } catch (error) {
      return { ok: false, code: "offline", error: error.message };
    }
    let data;
    try {
      const packed = transferCode.open(box, code);
      data = JSON.parse(zlib.gunzipSync(packed, { maxOutputLength: BACKUP_MAX_BYTES }).toString("utf8"));
    } catch (error) {
      return { ok: false, code: error.code === "bad_code" ? "bad_code" : "not_backup" };
    }
    try {
      const result = await requestBackendJson("/player/backup", "POST", data, BACKUP_TIMEOUT_MS);
      // Imported: nothing left to keep on the server.
      transferFetch(`${apiUrl()}/v1/transfer/${code.id}`, { method: "DELETE" }).catch(() => {});
      appendLog("launcher", "History received by code.", { force: true });
      return { ok: true, ...result };
    } catch (error) {
      return backupFailure(error);
    }
  }

  return {exportHistory, importHistory, sendHistoryByCode, receiveHistoryByCode};
}

module.exports = {createHistoryTransfer};
