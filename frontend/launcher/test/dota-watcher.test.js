const assert = require("node:assert/strict");
const test = require("node:test");

const { encodePowerShell, parseWatcherLine, windowsWatchScript } = require("../dota-watcher");

test("parses watcher lines", () => {
  assert.deepEqual(parseWatcherLine('{"running":true,"focused":true,"path":"C:\\\\dota2.exe"}'), {
    running: true,
    focused: true,
    exePath: "C:\\dota2.exe"
  });
  assert.deepEqual(parseWatcherLine('{"running":false,"focused":true,"path":""}'), {
    running: false,
    focused: false,
    exePath: ""
  });
  assert.equal(parseWatcherLine("not json"), null);
});

test("watch script embeds the parent pid and fits a command line", () => {
  const script = windowsWatchScript(4321);
  assert.match(script, /\$parentPid = 4321/);
  assert.doesNotMatch(script, /__[A-Z_]+__/);
  assert.ok(encodePowerShell(script).length < 8000);
});

const { EventEmitter } = require("node:events");
const { PassThrough } = require("node:stream");
const { createDotaWatcher } = require("../dota-watcher");

function failingSpawn() {
  const child = new EventEmitter();
  child.stdout = new PassThrough();
  child.stderr = new PassThrough();
  child.pid = undefined;
  child.kill = () => {};
  setImmediate(() => child.emit("error", new Error("spawn powershell.exe ENOENT")));
  return child;
}

test("a watcher whose helper cannot spawn restarts and finally falls back", async (t) => {
  t.mock.timers.enable({ apis: ["setTimeout"] });
  let spawns = 0;
  const watcher = createDotaWatcher({
    platform: "win32",
    spawnImpl: (...args) => {
      spawns += 1;
      return failingSpawn(...args);
    }
  });
  const reports = [];
  watcher.on("report", (state) => reports.push(state));
  watcher.start();
  for (let i = 0; i < 10 && !reports.length; i += 1) {
    await new Promise((resolve) => setImmediate(resolve));
    t.mock.timers.tick(3000);
  }
  watcher.stop();
  assert.equal(spawns, 5);
  assert.equal(reports.length, 1);
  assert.equal(reports[0].supported, false);
  assert.equal(watcher.getState().supported, false);
});
