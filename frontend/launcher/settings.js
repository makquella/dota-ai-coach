const fs = require("node:fs");
const path = require("node:path");
const crypto = require("node:crypto");

// Small JSON settings store in the user data folder. The install directory of
// a packaged app may be read-only, so nothing is written next to the code.
// `secretKeys` (share/profile tokens, the Discord webhook) are written sealed by
// `codec` (secret-codec.js: Electron safeStorage, DPAPI on Windows) and kept
// open in memory only. safeStorage works once the app is ready, so sealed values
// wait (reading as their defaults) until `unlockSecrets()`; it opens them and
// seals the plain values an older version wrote. A seal this user cannot open
// is kept on disk as it is and the key reads as its default.
function createSettingsStore(filePath, defaults, { secretKeys = [], codec = null } = {}) {
  const secret = new Set(secretKeys);
  let sealing = false;
  const lockedRaw = {};
  let revision = 0;
  let acknowledged = 0;
  let failures = 0;
  let lastError = null;
  let lastSuccessAt = null;
  let errorSink = null;
  let data = load();

  function fail(operation, error) {
    failures += 1;
    lastError = {operation, code: error.code || error.name || "failed", at: new Date().toISOString()};
    if (errorSink) {
      try { errorSink({...lastError}); } catch { /* Diagnostics cannot break settings. */ }
    }
  }

  function load() {
    try {
      const raw = JSON.parse(fs.readFileSync(filePath, "utf8"));
      return mergeDefaults(defaults, openSecrets(raw));
    } catch (error) {
      if (error.code !== "ENOENT") fail("load", error);
      return structuredClone(defaults);
    }
  }

  function openSecrets(raw) {
    if (!raw || typeof raw !== "object") {
      return raw;
    }
    const opened = { ...raw };
    for (const key of secret) {
      if (codec && codec.isSealed(raw[key])) {
        lockedRaw[key] = raw[key];
        delete opened[key];
      }
    }
    return opened;
  }

  // What goes to disk: secrets sealed, a seal that could not be opened kept.
  function onDisk() {
    const out = { ...data };
    for (const key of secret) {
      if (key in lockedRaw) {
        out[key] = lockedRaw[key];
      } else if (sealing && out[key] !== undefined) {
        const sealed = codec.seal(out[key]);
        if (!sealed) {
          throw Object.assign(new Error("sealing failed"), { code: "seal_failed" });
        }
        out[key] = sealed;
      }
    }
    return out;
  }

  function save() {
    let tempPath = null;
    try {
      tempPath = `${filePath}.${process.pid}.${crypto.randomBytes(6).toString("hex")}.tmp`;
      fs.mkdirSync(path.dirname(filePath), { recursive: true });
      fs.writeFileSync(tempPath, `${JSON.stringify(onDisk(), null, 2)}\n`, {encoding:"utf8", mode:0o600, flag:"wx"});
      fs.renameSync(tempPath, filePath);
      acknowledged = revision;
      lastSuccessAt = new Date().toISOString();
      lastError = null;
      return true;
    } catch (error) {
      // RAM changes remain usable; only a successful rename acknowledges them.
      fail("save", error);
      return false;
    } finally {
      try { if (tempPath) fs.unlinkSync(tempPath); } catch (error) {
        if (error.code !== "ENOENT") fail("cleanup", error);
      }
    }
  }

  return {
    get(key) {
      return data[key];
    },
    all() {
      return structuredClone(data);
    },
    set(key, value) {
      data[key] = value;
      delete lockedRaw[key];
      revision += 1;
      save();
    },
    update(key, patch) {
      data[key] = { ...(data[key] || {}), ...patch };
      delete lockedRaw[key];
      revision += 1;
      save();
      return data[key];
    },
    // A sealed value not opened yet (before ready) or not openable (another user).
    isLocked(key) {
      return key in lockedRaw;
    },
    // Once the app is ready: open the sealed values, seal the plain ones.
    unlockSecrets() {
      if (sealing || !codec || !secret.size || !codec.available()) {
        return {sealing, locked:Object.keys(lockedRaw).length};
      }
      sealing = true;
      for (const key of secret) {
        if (key in lockedRaw) {
          const plain = codec.open(lockedRaw[key]);
          if (plain !== undefined) {
            data[key] = mergeDefaults({ [key]: defaults[key] }, { [key]: plain })[key];
            delete lockedRaw[key];
          }
        }
      }
      revision += 1;
      save();
      return {sealing, locked:Object.keys(lockedRaw).length};
    },
    health() {
      return {revision, acknowledged, pending:revision !== acknowledged, failures,
        lastError:lastError ? {...lastError} : null, lastSuccessAt,
        secrets:{sealing, locked:Object.keys(lockedRaw).length}};
    },
    onError(sink) {
      errorSink = sink;
      if (lastError && errorSink) {
        try { errorSink({...lastError}); } catch { /* Keep the app running. */ }
      }
    },
    filePath
  };
}

function mergeDefaults(defaults, raw) {
  const merged = structuredClone(defaults);
  if (!raw || typeof raw !== "object") {
    return merged;
  }
  for (const [key, value] of Object.entries(raw)) {
    const base = merged[key];
    if (base && typeof base === "object" && !Array.isArray(base) && value && typeof value === "object") {
      merged[key] = { ...base, ...value };
    } else {
      merged[key] = value;
    }
  }
  return merged;
}

module.exports = { createSettingsStore };
