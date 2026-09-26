// Every visible text exists in both languages: the control panel (I18N in
// renderer/app.js + data-i18n keys in index.html), the match screens (TEXT in
// renderer/matches.js) and the overlay card (OVERLAY_TEXT in overlay/app.js).
// The tables are object literals inside browser scripts, so they are cut out
// of the source and evaluated on their own.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const ROOT = path.join(__dirname, "..");

function tableFrom(file, declaration) {
  const source = fs.readFileSync(path.join(ROOT, file), "utf8");
  const start = source.indexOf(declaration);
  assert.ok(start >= 0, `${declaration} not found in ${file}`);
  const open = source.indexOf("{", start);
  let depth = 0;
  let quote = null;
  for (let index = open; index < source.length; index += 1) {
    const char = source[index];
    if (quote) {
      if (char === "\\") {
        index += 1;
      } else if (char === quote) {
        quote = null;
      }
      continue;
    }
    if (char === '"' || char === "'" || char === "`") {
      quote = char;
    } else if (char === "{") {
      depth += 1;
    } else if (char === "}") {
      depth -= 1;
      if (depth === 0) {
        return vm.runInNewContext(`(${source.slice(open, index + 1)})`);
      }
    }
  }
  throw new Error(`Unbalanced ${declaration} in ${file}`);
}

function keyPaths(node, prefix = "") {
  if (!node || typeof node !== "object" || Array.isArray(node)) {
    return [prefix];
  }
  return Object.entries(node).flatMap(([key, value]) => keyPaths(value, prefix ? `${prefix}.${key}` : key));
}

function assertSameKeys(table, name) {
  const en = new Set(keyPaths(table.en));
  const ru = new Set(keyPaths(table.ru));
  assert.deepEqual([...en].filter((key) => !ru.has(key)), [], `${name}: missing in ru`);
  assert.deepEqual([...ru].filter((key) => !en.has(key)), [], `${name}: missing in en`);
}

test("control panel texts exist in both languages", () => {
  assertSameKeys(tableFrom("renderer/app.js", "const I18N ="), "renderer/app.js");
});

test("every data-i18n key of the control panel is defined", () => {
  const table = tableFrom("renderer/app.js", "const I18N =");
  const html = fs.readFileSync(path.join(ROOT, "renderer/index.html"), "utf8");
  const keys = [...html.matchAll(/data-i18n(?:-title|-placeholder)?="([^"]+)"/g)].map((match) => match[1]);
  assert.ok(keys.length > 30);
  const known = new Set(keyPaths(table.en));
  assert.deepEqual(keys.filter((key) => !known.has(key)), []);
});

test("match screen texts exist in both languages", () => {
  assertSameKeys(tableFrom("renderer/matches.js", "const TEXT ="), "renderer/matches.js");
});

test("overlay texts exist in both languages", () => {
  assertSameKeys(tableFrom("overlay/app.js", "const OVERLAY_TEXT ="), "overlay/app.js");
});
