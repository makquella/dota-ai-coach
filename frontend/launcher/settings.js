const fs = require("node:fs");
const path = require("node:path");
const crypto = require("node:crypto");

// Small JSON settings store in the user data folder. The install directory of
// a packaged app may be read-only, so nothing is written next to the code.
function createSettingsStore(filePath, defaults) {
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
      return mergeDefaults(defaults, raw);
    } catch (error) {
      if (error.code !== "ENOENT") fail("load", error);
      return structuredClone(defaults);
    }
  }

  function save() {
    let tempPath = null;
    try {
      tempPath = `${filePath}.${process.pid}.${crypto.randomBytes(6).toString("hex")}.tmp`;
      fs.mkdirSync(path.dirname(filePath), { recursive: true });
      fs.writeFileSync(tempPath, `${JSON.stringify(data, null, 2)}\n`, {encoding:"utf8", mode:0o600, flag:"wx"});
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
      revision += 1;
      save();
    },
    update(key, patch) {
      data[key] = { ...(data[key] || {}), ...patch };
      revision += 1;
      save();
      return data[key];
    },
    health() {
      return {revision, acknowledged, pending:revision !== acknowledged, failures,
        lastError:lastError ? {...lastError} : null, lastSuccessAt};
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
