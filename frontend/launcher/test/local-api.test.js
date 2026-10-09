"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const os = require("node:os");
const { loadLocalApiAuth, controlHeaders, renderGsiConfig } = require("../local-api");
const { redact } = require("../problem-report");

test("GSI credentials survive relaunch while control credentials rotate", (t) => {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), "wardly-auth-"));
  t.after(() => fs.rmSync(directory, { recursive: true, force: true }));
  const file = path.join(directory, "local-api-gsi.json");
  const first = loadLocalApiAuth(file);
  const second = loadLocalApiAuth(file);
  assert.match(first.control, /^[a-f0-9]{64}$/);
  assert.match(first.gsi, /^[a-f0-9]{64}$/);
  assert.notEqual(first.control, first.gsi);
  assert.equal(first.gsi, second.gsi);
  assert.notEqual(first.control, second.control);
  assert.ok(!fs.readFileSync(file, "utf8").includes(first.control));
  assert.deepEqual(fs.readdirSync(directory), ["local-api-gsi.json"]);
  if (process.platform !== "win32") assert.equal(fs.statSync(file).mode & 0o777, 0o600);
});

test("bad stored credentials fail without revealing their contents or rotating", (t) => {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), "wardly-auth-bad-"));
  t.after(() => fs.rmSync(directory, { recursive: true, force: true }));
  const file = path.join(directory, "local-api-gsi.json");
  for (const content of ['{"gsi":"private-incomplete', '{"version":true,"gsi":"private-value"}', '{"version":1,"gsi":"private-value"}']) {
    fs.writeFileSync(file, content);
    assert.throws(() => loadLocalApiAuth(file), (error) => !error.message.includes("private"));
    assert.equal(fs.readFileSync(file, "utf8"), content);
  }
});

test("control credentials cannot be forwarded to a remote or credential-bearing URL", () => {
  const base = "http://127.0.0.1:8000";
  const token = "a".repeat(64);
  assert.equal(controlHeaders("/player", base, token).Authorization, `Bearer ${token}`);
  for (const endpoint of ["https://example.com/player", "//example.com/player", "http://127.0.0.1:8001/player", "http://user:pass@127.0.0.1:8000/player"]) {
    assert.throws(() => controlHeaders(endpoint, base, token));
  }
  assert.throws(() => controlHeaders("/player", "http://example.com", token));
});

test("Valve config contains only the restricted GSI token and the selected local port", () => {
  const control = "a".repeat(64), gsi = "b".repeat(64);
  const config = renderGsiConfig("http://127.0.0.1:51234/gsi", gsi);
  assert.match(config, /"uri"\s+"http:\/\/127\.0\.0\.1:51234\/gsi"/);
  assert.match(config, /"auth"\s*\{\s*"token"\s+"[a-f0-9]{64}"\s*\}/);
  assert.ok(config.includes(gsi) && !config.includes(control));
  assert.throws(() => renderGsiConfig("http://example.com/gsi", gsi));
  assert.throws(() => renderGsiConfig("http://127.0.0.1/gsi?token=x", gsi));
  assert.throws(() => renderGsiConfig("http://127.0.0.1/gsi", '\"injection'));
  assert.ok(!redact(config).includes(gsi));
  assert.ok(!redact(JSON.stringify({ control, gsi })).includes(control));
});
