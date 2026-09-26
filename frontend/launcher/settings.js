const fs = require("node:fs");
const path = require("node:path");

// Small JSON settings store in the user data folder. The install directory of
// a packaged app may be read-only, so nothing is written next to the code.
function createSettingsStore(filePath, defaults) {
  let data = load();

  function load() {
    try {
      const raw = JSON.parse(fs.readFileSync(filePath, "utf8"));
      return mergeDefaults(defaults, raw);
    } catch {
      return structuredClone(defaults);
    }
  }

  function save() {
    try {
      fs.mkdirSync(path.dirname(filePath), { recursive: true });
      const tempPath = `${filePath}.tmp`;
      fs.writeFileSync(tempPath, `${JSON.stringify(data, null, 2)}\n`, "utf8");
      fs.renameSync(tempPath, filePath);
    } catch {
      // Settings are a convenience; failing to persist them must not break the app.
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
      save();
    },
    update(key, patch) {
      data[key] = { ...(data[key] || {}), ...patch };
      save();
      return data[key];
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
