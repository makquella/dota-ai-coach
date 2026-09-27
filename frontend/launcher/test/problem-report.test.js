const assert = require("node:assert/strict");
const test = require("node:test");

const {
  anonymize,
  apiUrl,
  buildReport,
  isRetryable,
  outboxOverflow,
  redact,
  reportFileName,
  tail,
  uploadPayload,
  withNote,
  LOG_TAIL_LINES,
  NOTE_MAX,
  OUTBOX_MAX
} = require("../problem-report");

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
  assert.equal(reportFileName(new Date(2026, 8, 27, 9, 5)), "Wardly-report-2026-09-27-0905.txt");
});

test("upload payload is limited and has no keys", () => {
  const payload = uploadPayload({
    text: '{"api_key": "plain-secret"}\nERROR x',
    note: `  ${"n".repeat(NOTE_MAX + 50)} gsk_1234567890abcdefXYZ`,
    installId: "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
    app: { version: "0.2.1", os: "win32 10.0.22631", locale: "ru" }
  });
  assert.deepEqual(Object.keys(payload).sort(), ["install_id", "lang", "note", "os", "text", "version"]);
  assert.equal(payload.note.length, NOTE_MAX);
  assert.ok(!payload.text.includes("plain-secret"));
  assert.equal(payload.lang, "ru");
  assert.ok(!uploadPayload({ text: "x", note: "key gsk_1234567890abcdefXYZ" }).note.includes("gsk_"));
});

test("only temporary failures are sent again", () => {
  assert.equal(isRetryable({ ok: true, status: 201 }), false);
  assert.equal(isRetryable({ ok: false, code: "offline" }), true);
  assert.equal(isRetryable({ ok: false, status: 429 }), true);
  assert.equal(isRetryable({ ok: false, status: 503 }), true);
  assert.equal(isRetryable({ ok: false, status: 400, code: "bad_json" }), false);
  assert.equal(isRetryable({ ok: false, status: 413 }), false);
});

test("outbox keeps the newest reports", () => {
  const names = Array.from({ length: OUTBOX_MAX + 2 }, (_, i) => `2026-09-27-${String(i).padStart(2, "0")}.json`);
  assert.deepEqual(outboxOverflow([...names].reverse().concat("notes.txt")), names.slice(0, 2));
  assert.deepEqual(outboxOverflow(names.slice(0, 3)), []);
});

test("api address can be changed for development", () => {
  assert.equal(apiUrl({}), "https://api.luhovyimvp.dev");
  assert.equal(apiUrl({ DOTA_AI_API_URL: "http://127.0.0.1:8799/" }), "http://127.0.0.1:8799");
});

test("reports carry no nickname, Steam id or Windows user name", () => {
  const report = buildReport({
    status: { player: { linked: true, accountId: 123456789 } },
    app: { userData: "C:\\Users\\Artem\\AppData\\Roaming\\DotaAICoach" },
    diagnostics: { player: { account_id: 123456789, persona_name: "Nick", sync: "ok" } },
    launcherLog: "GET https://api.opendota.com/api/players/123456789/matches\nsteam 76561197960389013 linked\n"
  });
  for (const secret of ["123456789", "76561197960389013", "Nick", "Artem"]) {
    assert.ok(!report.includes(secret), secret);
  }
  assert.match(report, /"sync": "ok"/);
  assert.match(report, /Users\\\\\[user\]/);
  assert.equal(anonymize("/home/artem/logs and C:/Users/Artem/x"), "/home/[user]/logs and C:/Users/[user]/x");
  assert.ok(!uploadPayload({ text: '{"accountId": 55}' }).text.includes("55"));
});

test("a report saved instead of sent keeps the player's note", () => {
  assert.equal(withNote("REPORT", "  Overlay is gone gsk_1234567890abcdefXYZ "), "Player note:\nOverlay is gone [redacted]\n\nREPORT");
  assert.equal(withNote("REPORT", "   "), "REPORT");
});
