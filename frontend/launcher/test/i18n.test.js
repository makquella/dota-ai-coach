// Every visible text exists in both languages: the control panel (I18N in
// renderer/app.js + data-i18n keys in index.html), the match screens (TEXT in
// renderer/match-texts.js) and the overlay card (OVERLAY_TEXT in overlay/app.js).
// The tables are object literals inside browser scripts, so they are cut out
// of the source and evaluated on their own.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const ROOT = path.join(__dirname, "..");

function tableFrom(file, declaration) {
  return vm.runInNewContext(`(${tableSource(file, declaration)})`, {
    window: { WardlyWhatsNew: require("../renderer/whats-new") }
  });
}

function tableSource(file, declaration) {
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
        return source.slice(open, index + 1);
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

// Keys written twice in one object: the later one silently wins (a
// "buildTitle" function once replaced the plain title of another card).
function duplicateKeys(text) {
  const found = [];
  const stack = [];
  let quote = null;
  let expectKey = false;
  for (let index = 0; index < text.length; index += 1) {
    const char = text[index];
    if (quote) {
      if (char === "\\") {
        index += 1;
      } else if (char === quote) {
        quote = null;
      }
      continue;
    }
    if (char === "/" && text[index + 1] === "/") {
      index = text.indexOf("\n", index);
      if (index < 0) {
        break;
      }
      continue;
    }
    if (char === "{") {
      stack.push(new Set());
      expectKey = true;
      continue;
    }
    if (char === "}") {
      stack.pop();
      expectKey = false;
      continue;
    }
    if (char === ",") {
      expectKey = true;
      continue;
    }
    if (/\s/.test(char)) {
      continue;
    }
    if (expectKey) {
      expectKey = false;
      const match = /^(?:"([^"]+)"|([A-Za-z_$][\w$]*))\s*:/.exec(text.slice(index));
      if (match && stack.length) {
        const key = match[1] || match[2];
        const keys = stack[stack.length - 1];
        if (keys.has(key)) {
          found.push(key);
        }
        keys.add(key);
      }
    }
    if (char === '"' || char === "'" || char === "`") {
      quote = char;
    }
  }
  return found;
}

test("no text key is written twice in one table", () => {
  for (const [file, declaration] of [
    ["renderer/app.js", "const I18N ="],
    ["renderer/whats-new.js", "const TEXT ="],
    ["renderer/match-texts.js", "const TEXT ="],
    ["overlay/app.js", "const OVERLAY_TEXT ="]
  ]) {
    assert.deepEqual(duplicateKeys(tableSource(file, declaration)), [], file);
  }
});

test("control panel texts exist in both languages", () => {
  assertSameKeys(tableFrom("renderer/app.js", "const I18N ="), "renderer/app.js");
});

test("update history texts exist in both languages", () => {
  assertSameKeys(tableFrom("renderer/whats-new.js", "const TEXT ="), "renderer/whats-new.js");
});

test("every data-i18n key of the control panel is defined", () => {
  const table = tableFrom("renderer/app.js", "const I18N =");
  const html = fs.readFileSync(path.join(ROOT, "renderer/index.html"), "utf8");
  const keys = [...html.matchAll(/data-i18n(?:-title|-placeholder|-aria)?="([^"]+)"/g)].map((match) => match[1]);
  assert.ok(keys.length > 30);
  const known = new Set(keyPaths(table.en));
  assert.deepEqual(keys.filter((key) => !known.has(key)), []);
});

test("match screen texts exist in both languages", () => {
  assertSameKeys(tableFrom("renderer/match-texts.js", "const TEXT ="), "renderer/match-texts.js");
});

test("overlay texts exist in both languages", () => {
  assertSameKeys(tableFrom("overlay/app.js", "const OVERLAY_TEXT ="), "overlay/app.js");
});

test("text functions get their arguments through t(), never t(key)(…)", () => {
  // t() already calls a text function (with no arguments here) and returns a
  // string; calling that string threw and left the review on its skeleton.
  for (const file of ["renderer/app.js", "renderer/matches.js", "overlay/app.js"]) {
    const source = fs.readFileSync(path.join(ROOT, file), "utf8");
    const calls = source.match(/\bt\(\s*["'`][\w.]+["'`]\s*\)\s*\(/g) || [];
    assert.deepEqual(calls, [], `${file} calls a translated text as a function`);
  }
});

test("every id in index.html is unique (aria-labelledby resolves to the first one)", () => {
  const html = fs.readFileSync(path.join(ROOT, "renderer", "index.html"), "utf8");
  const ids = [...html.matchAll(/\sid="([^"]+)"/g)].map((match) => match[1]);
  const repeated = ids.filter((id, index) => ids.indexOf(id) !== index);
  assert.deepEqual(repeated, []);
});

test("the autostart hint says which state the switch is in", () => {
  const table = tableFrom("renderer/app.js", "const I18N");
  for (const lang of ["en", "ru"]) {
    assert.notEqual(table[lang].autostartOn, table[lang].autostartOff, lang);
  }
});
