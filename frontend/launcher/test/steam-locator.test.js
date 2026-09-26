const assert = require("node:assert/strict");
const path = require("node:path");
const test = require("node:test");

const {
  dotaDirFromExecutable,
  libraryFoldersFromVdf,
  locateDota,
  parseRegQueryValue,
  parseVdf
} = require("../steam-locator");

const MODERN_VDF = `
"libraryfolders"
{
	"0"
	{
		"path"		"C:\\\\Program Files (x86)\\\\Steam"
		"label"		""
		"apps"
		{
			"228980"		"417337782"
		}
	}
	"1"
	{
		"path"		"E:\\\\Games\\\\SteamLibrary"
		"apps"
		{
			"570"		"41503957013"
		}
	}
}
`;

const LEGACY_VDF = `
"LibraryFolders"
{
	"TimeNextStatsReport"		"1611111111"
	"ContentStatsID"		"-123"
	"1"		"D:\\\\SteamLibrary"
}
`;

test("parses the current libraryfolders.vdf format", () => {
  const libraries = libraryFoldersFromVdf(parseVdf(MODERN_VDF));
  assert.deepEqual(libraries, [
    { path: "C:\\Program Files (x86)\\Steam", apps: ["228980"] },
    { path: "E:\\Games\\SteamLibrary", apps: ["570"] }
  ]);
});

test("parses the legacy libraryfolders.vdf format and ignores non-library keys", () => {
  assert.deepEqual(libraryFoldersFromVdf(parseVdf(LEGACY_VDF)), [{ path: "D:\\SteamLibrary", apps: [] }]);
});

test("vdf parser keeps unknown escapes and skips comments", () => {
  const parsed = parseVdf('// comment\n"root" { "path" "C:\\Games\\Steam" "quote" "a\\"b" }');
  assert.equal(parsed.root.path, "C:\\Games\\Steam");
  assert.equal(parsed.root.quote, 'a"b');
});

test("reads REG_SZ values from reg.exe output", () => {
  const output = "\r\nHKEY_CURRENT_USER\\Software\\Valve\\Steam\r\n    SteamPath    REG_SZ    c:/program files (x86)/steam\r\n\r\n";
  assert.equal(parseRegQueryValue(output, "SteamPath"), "c:/program files (x86)/steam");
  assert.equal(parseRegQueryValue(output, "InstallPath"), "");
});

test("derives the Dota folder from the running dota2.exe path", () => {
  assert.equal(
    dotaDirFromExecutable("E:\\Games\\SteamLibrary\\steamapps\\common\\dota 2 beta\\game\\bin\\win64\\dota2.exe", "win32"),
    "E:\\Games\\SteamLibrary\\steamapps\\common\\dota 2 beta"
  );
  assert.equal(dotaDirFromExecutable("C:\\Other\\bin\\win64\\dota2.exe", "win32"), "");
  assert.equal(dotaDirFromExecutable("", "win32"), "");
});

function fakeFs(files) {
  const known = new Set();
  for (const file of Object.keys(files)) {
    let current = path.win32.normalize(file).toLowerCase();
    while (current && !known.has(current)) {
      known.add(current);
      const parent = path.win32.dirname(current);
      if (parent === current) {
        break;
      }
      current = parent;
    }
  }
  return {
    existsSync: (target) => known.has(path.win32.normalize(target).toLowerCase()),
    readFileSync: (target) => {
      const key = Object.keys(files).find((file) => file.toLowerCase() === path.win32.normalize(target).toLowerCase());
      if (key === undefined) {
        throw new Error(`ENOENT ${target}`);
      }
      return files[key];
    }
  };
}

test("finds Dota in a secondary library on another drive via registry + libraryfolders.vdf", async () => {
  const fsImpl = fakeFs({
    "D:\\Steam\\steamapps\\libraryfolders.vdf": MODERN_VDF,
    "E:\\Games\\SteamLibrary\\steamapps\\common\\dota 2 beta\\game\\dota\\gameinfo.gi": ""
  });
  const registry = {
    "HKCU\\Software\\Valve\\Steam|SteamPath": "d:/steam"
  };
  const result = await locateDota({
    platform: "win32",
    env: { "ProgramFiles(x86)": "C:\\Program Files (x86)", ProgramFiles: "C:\\Program Files" },
    fs: fsImpl,
    queryRegistry: async (key, value) => registry[`${key}|${value}`] || ""
  });
  assert.deepEqual(result.steamRoots, ["d:\\steam"]);
  assert.equal(result.dotaDir, "E:\\Games\\SteamLibrary\\steamapps\\common\\dota 2 beta");
  assert.equal(
    result.gsiDir,
    "E:\\Games\\SteamLibrary\\steamapps\\common\\dota 2 beta\\game\\dota\\cfg\\gamestate_integration"
  );
});

test("reports not found when no library has Dota", async () => {
  const result = await locateDota({
    platform: "win32",
    env: {},
    fs: fakeFs({ "C:\\Program Files (x86)\\Steam\\steamapps\\libraryfolders.vdf": LEGACY_VDF }),
    queryRegistry: async () => ""
  });
  assert.equal(result.dotaDir, "");
  assert.equal(result.gsiDir, "");
  assert.ok(result.libraries.includes("D:\\SteamLibrary"));
});

test("uses the running game's folder when Steam knows nothing about it", async () => {
  const result = await locateDota({
    platform: "win32",
    env: {},
    fs: fakeFs({ "F:\\dota 2 beta\\game\\dota\\gameinfo.gi": "" }),
    queryRegistry: async () => "",
    extraDotaDirs: ["F:\\dota 2 beta"]
  });
  assert.equal(result.dotaDir, "F:\\dota 2 beta");
});
