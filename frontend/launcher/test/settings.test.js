const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");
const {createSettingsStore} = require("../settings");
const {buildReport} = require("../problem-report");

function workspace(t) {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), "wardly-settings-"));
  t.after(() => fs.rmSync(directory, {recursive:true, force:true}));
  return directory;
}

test("settings acknowledge actual replacement and preserve legacy defaults", t => {
  const directory = workspace(t);
  const file = path.join(directory, "settings.json");
  const defaults = {overlay:{enabled:true, position:"right"}, language:"ru"};
  const store = createSettingsStore(file, defaults);
  assert.equal(store.health().failures, 0);
  assert.equal(store.health().lastSuccessAt, null);
  assert.deepEqual(store.update("overlay", {position:"left"}), {enabled:true, position:"left"});
  store.set("language", "en");
  assert.deepEqual(JSON.parse(fs.readFileSync(file, "utf8")), store.all());
  assert.deepEqual(createSettingsStore(file, defaults).all(), store.all());
  assert.equal(store.health().acknowledged, 2);
  assert.equal(store.health().pending, false);
  assert.ok(store.health().lastSuccessAt);
  assert.deepEqual(fs.readdirSync(directory), ["settings.json"]);
});

test("failed replacement retains RAM edits and can acknowledge a later retry", t => {
  const directory = workspace(t);
  const file = path.join(directory, "settings.json");
  const store = createSettingsStore(file, {language:"ru"});
  const events = [];
  store.onError(error => events.push(error));
  fs.mkdirSync(file); // A directory cannot be replaced by a settings file.
  store.set("language", "en");
  assert.equal(store.get("language"), "en");
  assert.equal(store.health().pending, true);
  assert.equal(store.health().acknowledged, 0);
  assert.equal(store.health().failures, 1);
  assert.equal(events[0].operation, "save");
  assert.deepEqual(fs.readdirSync(directory), ["settings.json"]);
  const detached = store.health();
  detached.lastError.code = "changed";
  assert.notEqual(store.health().lastError.code, "changed");
  fs.rmdirSync(file);
  store.set("language", store.get("language"));
  assert.equal(JSON.parse(fs.readFileSync(file, "utf8")).language, "en");
  assert.equal(store.health().pending, false);
  assert.equal(store.health().acknowledged, 2);
  assert.equal(store.health().lastError, null);
});

test("corrupt settings retain load diagnosis without leaking content to reports", t => {
  const file = path.join(workspace(t), "settings.json");
  fs.writeFileSync(file, '{"api_key":"private-load-value"');
  const store = createSettingsStore(file, {language:"ru"});
  const events = [];
  store.onError(error => events.push(error));
  assert.equal(store.get("language"), "ru");
  assert.equal(events.length, 1);
  assert.equal(events[0].operation, "load");
  const report = buildReport({settingsHealth:store.health()});
  assert.match(report, /Settings persistence/);
  assert.match(report, /SyntaxError/);
  assert.ok(!report.includes("private-load-value"));
  store.onError(() => { throw new Error("diagnostics unavailable"); });
  store.set("language", "en");
  assert.equal(store.health().pending, false);
});

test("encoding failure preserves the previous settings file and cleans temporary files", t => {
  const directory = workspace(t);
  const file = path.join(directory, "settings.json");
  const store = createSettingsStore(file, {language:"ru"});
  store.set("language", "en");
  const previous = fs.readFileSync(file, "utf8");
  const cyclic = {secret:"private-encoding-value"};
  cyclic.self = cyclic;
  store.set("invalid", cyclic);
  assert.equal(fs.readFileSync(file, "utf8"), previous);
  assert.deepEqual(fs.readdirSync(directory), ["settings.json"]);
  assert.equal(store.health().pending, true);
  assert.equal(store.health().acknowledged, 1);
  assert.equal(store.health().lastError.code, "TypeError");
  assert.ok(!JSON.stringify(store.health()).includes("private-encoding-value"));
});
