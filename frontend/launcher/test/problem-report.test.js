const assert = require("node:assert/strict");
const test = require("node:test");

const { buildReport, redact, reportFileName, tail, LOG_TAIL_LINES } = require("../problem-report");

test("redact removes every provider key format", () => {
  const text = [
    "gemini AIzaSyA1234567890abcdefghijklmn",
    "studio AQ.Zz9TestKeyOnly0000-abcdefghijklm",
    "groq gsk_1234567890abcdefXYZ",
    "openrouter sk-or-v1-1234567890abcdef",
    "Authorization: Bearer abc.def-1234567890",
    '{"api_key": "plain-secret-without-prefix", "provider": "gemini"}',
    "url: /api/players/1?api_key=00000000-1111-2222-3333-444455556666&limit=5"
  ].join("\n");
  const result = redact(text);
  assert.equal((result.match(/\[redacted\]/g) || []).length, 7);
  assert.ok(!result.includes("00000000-1111"));
  assert.ok(!/1234567890|plain-secret|Zz9TestKey/.test(result));
  assert.match(result, /"provider": "gemini"/);
});

test("tail keeps the last lines", () => {
  const log = Array.from({ length: LOG_TAIL_LINES + 50 }, (_, index) => `line ${index}`).join("\n");
  const lines = tail(`${log}\n\n`).split("\n");
  assert.equal(lines.length, LOG_TAIL_LINES);
  assert.equal(lines.at(-1), `line ${LOG_TAIL_LINES + 49}`);
});

test("report has every section and no secrets", () => {
  const report = buildReport(
    {
      app: { version: "0.1.0" },
      status: { backend: "running" },
      settings: { overlay: { position: "right-center" } },
      watcher: { running: true },
      diagnostics: { errors: { last: [{ message: "HTTP 400 key=AIzaSyA1234567890abcdefghijklmn" }] } },
      launcherLog: "2026-09-27T10:00:00Z [backend] started\n"
    },
    new Date("2026-09-27T10:05:00Z")
  );
  for (const title of ["App", "Launcher status", "Settings", "Dota watcher", "Service diagnostics", "Launcher log"]) {
    assert.match(report, new RegExp(`===== ${title}`));
  }
  assert.ok(!report.includes("AIzaSy"));
  assert.match(report, /\[backend\] started/);
});

test("missing diagnostics are explained", () => {
  const report = buildReport({ diagnosticsError: "Backend is not running." });
  assert.match(report, /Not available: Backend is not running\./);
});

test("report file name is sortable", () => {
  assert.equal(reportFileName(new Date(2026, 8, 27, 9, 5)), "DotaAICoach-report-2026-09-27-0905.txt");
});
