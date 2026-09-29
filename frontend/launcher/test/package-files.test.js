// The installer carries only the files listed in package.json `build.files`:
// a module that main.js (or one of its modules) requires but the list misses
// works in dev and breaks the packaged app at start.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const ROOT = path.join(__dirname, "..");
const files = JSON.parse(fs.readFileSync(path.join(ROOT, "package.json"), "utf8")).build.files;

function packaged(relative) {
  return files.some((entry) => entry === relative || (entry.endsWith("/**/*") && relative.startsWith(entry.slice(0, -4))));
}

function localRequires(file) {
  const text = fs.readFileSync(path.join(ROOT, file), "utf8");
  return [...text.matchAll(/require\(\s*"(\.{1,2}\/[^"]+)"\s*\)/g)].map((match) =>
    path.relative(ROOT, path.resolve(path.dirname(path.join(ROOT, file)), match[1])).split(path.sep).join("/")
  );
}

test("every module main.js loads is in the installer", () => {
  const seen = new Set();
  const queue = ["main.js", "preload.js", "overlay-preload.js"];
  while (queue.length) {
    const file = queue.shift();
    if (seen.has(file)) continue;
    seen.add(file);
    for (const dependency of localRequires(file)) {
      const withJs = dependency.endsWith(".js") || dependency.endsWith(".json") ? dependency : `${dependency}.js`;
      if (fs.existsSync(path.join(ROOT, withJs))) queue.push(withJs);
    }
  }
  const missing = [...seen].filter((file) => !packaged(file));
  assert.deepEqual(missing, []);
});
