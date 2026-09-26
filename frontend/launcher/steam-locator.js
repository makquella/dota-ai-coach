const { execFile } = require("node:child_process");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");

// Finds the Dota 2 install through Steam: registry -> Steam root(s) ->
// steamapps/libraryfolders.vdf -> every library on every drive. No Electron
// imports, so it can be unit-tested with plain `node --test`.

const DOTA_APP_ID = "570";
const DOTA_FOLDER = "dota 2 beta";
const GSI_RELATIVE_DIR = ["game", "dota", "cfg", "gamestate_integration"];

const STEAM_REGISTRY_VALUES = [
  ["HKCU\\Software\\Valve\\Steam", "SteamPath"],
  ["HKLM\\SOFTWARE\\WOW6432Node\\Valve\\Steam", "InstallPath"],
  ["HKLM\\SOFTWARE\\Valve\\Steam", "InstallPath"]
];
const DOTA_UNINSTALL_REGISTRY_VALUES = [
  ["HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\Steam App 570", "InstallLocation"],
  ["HKLM\\SOFTWARE\\WOW6432Node\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\Steam App 570", "InstallLocation"]
];

// Minimal Valve KeyValues (VDF) text parser: quoted or bare tokens, nested
// blocks, `//` comments and backslash escapes. Keys are kept as written.
function parseVdf(text) {
  const tokens = tokenizeVdf(String(text || ""));
  let index = 0;

  function parseBlock() {
    const block = {};
    while (index < tokens.length) {
      const token = tokens[index];
      if (token.type === "close") {
        index += 1;
        return block;
      }
      if (token.type !== "string") {
        index += 1;
        continue;
      }
      const key = token.value;
      index += 1;
      const next = tokens[index];
      if (!next) {
        break;
      }
      if (next.type === "open") {
        index += 1;
        block[key] = parseBlock();
      } else if (next.type === "string") {
        index += 1;
        block[key] = next.value;
      }
    }
    return block;
  }

  return parseBlock();
}

function tokenizeVdf(text) {
  const tokens = [];
  let i = 0;
  while (i < text.length) {
    const char = text[i];
    if (char === "/" && text[i + 1] === "/") {
      while (i < text.length && text[i] !== "\n") {
        i += 1;
      }
    } else if (char === "{") {
      tokens.push({ type: "open" });
      i += 1;
    } else if (char === "}") {
      tokens.push({ type: "close" });
      i += 1;
    } else if (char === '"') {
      let value = "";
      i += 1;
      while (i < text.length && text[i] !== '"') {
        const escaped = text[i + 1];
        if (text[i] === "\\" && ["\\", '"', "n", "t"].includes(escaped)) {
          value += escaped === "n" ? "\n" : escaped === "t" ? "\t" : escaped;
          i += 2;
        } else {
          // Unknown escapes (e.g. a single "\" in a hand-edited path) stay literal.
          value += text[i];
          i += 1;
        }
      }
      i += 1;
      tokens.push({ type: "string", value });
    } else if (/\s/.test(char)) {
      i += 1;
    } else {
      let value = "";
      while (i < text.length && !/[\s{}"]/.test(text[i])) {
        value += text[i];
        i += 1;
      }
      tokens.push({ type: "string", value });
    }
  }
  return tokens;
}

function findKey(object, name) {
  if (!object || typeof object !== "object") {
    return undefined;
  }
  const wanted = name.toLowerCase();
  const key = Object.keys(object).find((candidate) => candidate.toLowerCase() === wanted);
  return key === undefined ? undefined : object[key];
}

// Supports both the current format ("0" { "path" "D:\\SteamLibrary" "apps" { "570" "..." } })
// and the legacy one ("1" "D:\\SteamLibrary").
function libraryFoldersFromVdf(parsed) {
  const root = findKey(parsed, "libraryfolders");
  if (!root || typeof root !== "object") {
    return [];
  }
  const libraries = [];
  for (const [key, value] of Object.entries(root)) {
    if (!/^\d+$/.test(key)) {
      continue;
    }
    if (typeof value === "string") {
      libraries.push({ path: value, apps: [] });
    } else if (value && typeof value === "object") {
      const libraryPath = findKey(value, "path");
      if (typeof libraryPath === "string" && libraryPath) {
        const apps = findKey(value, "apps");
        libraries.push({ path: libraryPath, apps: apps && typeof apps === "object" ? Object.keys(apps) : [] });
      }
    }
  }
  return libraries;
}

function parseRegQueryValue(output, valueName) {
  const pattern = new RegExp(`^\\s*${valueName}\\s+REG_(?:EXPAND_)?SZ\\s+(.+?)\\s*$`, "im");
  const match = String(output || "").match(pattern);
  return match ? match[1] : "";
}

function queryRegistryValue(key, valueName) {
  return new Promise((resolve) => {
    execFile(
      "reg.exe",
      ["query", key, "/v", valueName],
      { windowsHide: true, timeout: 4000 },
      (error, stdout) => resolve(error ? "" : parseRegQueryValue(stdout, valueName))
    );
  });
}

function defaultSteamRoots({ platform = process.platform, env = process.env, homedir = os.homedir() } = {}) {
  if (platform === "win32") {
    const programFilesX86 = env["ProgramFiles(x86)"] || "C:\\Program Files (x86)";
    const programFiles = env.ProgramFiles || "C:\\Program Files";
    return [path.win32.join(programFilesX86, "Steam"), path.win32.join(programFiles, "Steam")];
  }
  return [
    path.join(homedir, ".steam", "steam"),
    path.join(homedir, ".local", "share", "Steam"),
    path.join(homedir, ".var", "app", "com.valvesoftware.Steam", ".local", "share", "Steam")
  ];
}

function normalizeDir(dir, platform) {
  const pathApi = platform === "win32" ? path.win32 : path.posix;
  return pathApi.normalize(String(dir).trim());
}

function uniqueDirs(dirs, platform) {
  const seen = new Set();
  const result = [];
  for (const dir of dirs) {
    if (!dir) {
      continue;
    }
    const normalized = normalizeDir(dir, platform);
    const key = platform === "win32" ? normalized.toLowerCase() : normalized;
    if (!seen.has(key)) {
      seen.add(key);
      result.push(normalized);
    }
  }
  return result;
}

function dotaDirForLibrary(libraryDir, platform) {
  const pathApi = platform === "win32" ? path.win32 : path.posix;
  return pathApi.join(libraryDir, "steamapps", "common", DOTA_FOLDER);
}

function gsiDirForDotaDir(dotaDir, platform = process.platform) {
  const pathApi = platform === "win32" ? path.win32 : path.posix;
  return pathApi.join(dotaDir, ...GSI_RELATIVE_DIR);
}

// ...\dota 2 beta\game\bin\win64\dota2.exe -> ...\dota 2 beta
function dotaDirFromExecutable(executablePath, platform = process.platform) {
  if (!executablePath) {
    return "";
  }
  const pathApi = platform === "win32" ? path.win32 : path.posix;
  const dir = pathApi.resolve(pathApi.dirname(executablePath), "..", "..", "..");
  return pathApi.basename(dir).toLowerCase() === DOTA_FOLDER ? dir : "";
}

/**
 * Locate Dota 2. Returns { steamRoots, libraries, dotaDir, gsiDir, source }.
 * dotaDir/gsiDir are "" when Dota is not installed in any known library.
 */
async function locateDota(options = {}) {
  const platform = options.platform || process.platform;
  const fsImpl = options.fs || fs;
  const queryRegistry = options.queryRegistry || queryRegistryValue;
  const exists = (target) => {
    try {
      return fsImpl.existsSync(target);
    } catch {
      return false;
    }
  };
  const pathApi = platform === "win32" ? path.win32 : path.posix;

  const registryRoots = [];
  const registryDotaDirs = [];
  if (platform === "win32") {
    for (const [key, valueName] of STEAM_REGISTRY_VALUES) {
      registryRoots.push(await queryRegistry(key, valueName));
    }
    for (const [key, valueName] of DOTA_UNINSTALL_REGISTRY_VALUES) {
      registryDotaDirs.push(await queryRegistry(key, valueName));
    }
  }

  const steamRoots = uniqueDirs(
    [...registryRoots, ...defaultSteamRoots({ platform, env: options.env, homedir: options.homedir })],
    platform
  ).filter(exists);

  const libraries = [];
  for (const root of steamRoots) {
    libraries.push({ path: root, apps: [], source: "steam root" });
    for (const vdfPath of [
      pathApi.join(root, "steamapps", "libraryfolders.vdf"),
      pathApi.join(root, "config", "libraryfolders.vdf")
    ]) {
      if (!exists(vdfPath)) {
        continue;
      }
      try {
        for (const library of libraryFoldersFromVdf(parseVdf(fsImpl.readFileSync(vdfPath, "utf8")))) {
          libraries.push({ ...library, source: vdfPath });
        }
      } catch {
        // A broken libraryfolders.vdf must not stop the other candidates.
      }
    }
  }

  // Libraries that list app 570 first, then the rest.
  const ordered = [
    ...libraries.filter((library) => library.apps.includes(DOTA_APP_ID)),
    ...libraries.filter((library) => !library.apps.includes(DOTA_APP_ID))
  ];
  const candidates = uniqueDirs(
    [
      ...(options.extraDotaDirs || []),
      ...registryDotaDirs,
      ...ordered.map((library) => dotaDirForLibrary(library.path, platform))
    ],
    platform
  );
  const dotaDir = candidates.find((dir) => exists(pathApi.join(dir, "game", "dota"))) || "";
  return {
    steamRoots,
    libraries: uniqueDirs(libraries.map((library) => library.path), platform),
    dotaDir,
    gsiDir: dotaDir ? gsiDirForDotaDir(dotaDir, platform) : "",
    source: dotaDir ? "steam" : "not found"
  };
}

module.exports = {
  DOTA_APP_ID,
  defaultSteamRoots,
  dotaDirFromExecutable,
  gsiDirForDotaDir,
  libraryFoldersFromVdf,
  locateDota,
  parseRegQueryValue,
  parseVdf
};
