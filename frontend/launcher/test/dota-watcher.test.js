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
