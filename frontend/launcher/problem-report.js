// Problem report: one text file a tester can send to the developer. Pure
// helpers (no Electron) so they are unit-tested; main.js gathers the parts
// and writes the file.
//
// Nothing secret may leave the machine: API keys are cut out of every part
// (log lines and JSON fields named api_key included).

const SECRET_PATTERNS = [
  /AIza[\w-]{20,}/g, // Google / Gemini
  /AQ\.[\w-]{20,}/g, // Google AI Studio (new format)
  /gsk_[\w-]{16,}/g, // Groq
  /sk-[\w-]{16,}/g, // OpenRouter and other OpenAI-style keys
  /Bearer\s+[\w.-]{12,}/g,
  /(?<=api_key=)[^&\s'"]+/g // OpenDota key in a URL
];
const KEY_FIELD = /("api_?key"\s*:\s*")[^"]*"/gi;

const LOG_TAIL_LINES = 600;

function redact(text) {
  let result = String(text ?? "").replace(KEY_FIELD, '$1[redacted]"');
  for (const pattern of SECRET_PATTERNS) {
    result = result.replace(pattern, "[redacted]");
  }
  return result;
}

function tail(text, lines = LOG_TAIL_LINES) {
  const all = String(text ?? "").replace(/\r/g, "").split("\n");
  while (all.length && all[all.length - 1] === "") {
    all.pop();
  }
  return all.slice(-lines).join("\n");
}

function reportFileName(date = new Date()) {
  const pad = (value) => String(value).padStart(2, "0");
  const stamp = `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}-${pad(date.getHours())}${pad(date.getMinutes())}`;
  return `DotaAICoach-report-${stamp}.txt`;
}

function section(title, body) {
  const text = typeof body === "string" ? body : JSON.stringify(body, null, 2);
  return `===== ${title} =====\n${text || "(empty)"}\n`;
}

// parts: { app, status, settings, watcher, diagnostics, diagnosticsError, launcherLog, note }
function buildReport(parts, date = new Date()) {
  const blocks = [
    `Dota AI Coach problem report\nCreated: ${date.toISOString()}\n` +
      "API keys are removed from this file. Send it to the developer together with a short description.\n",
    section("App", parts.app || {}),
    section("Launcher status", parts.status || {}),
    section("Settings", parts.settings || {}),
    section("Dota watcher", parts.watcher || {}),
    section(
      "Service diagnostics (GET /diagnostics)",
      parts.diagnostics || `Not available: ${parts.diagnosticsError || "the service is not running"}`
    ),
    section(`Launcher log (last ${LOG_TAIL_LINES} lines)`, tail(parts.launcherLog))
  ];
  return redact(blocks.join("\n"));
}

// --- Sending the report (docs/DATA_PLAN.md, stage 1) ------------------------
// «Отправить разработчику» posts the same report to the project's API; when it
// cannot be sent now it waits in an outbox and goes out later.

const API_URL = "https://api.luhovyimvp.dev";
const PRIVACY_URL = "https://luhovyimvp.dev/privacy.html";
const NOTE_MAX = 1000;
const OUTBOX_MAX = 10;

function apiUrl(env = process.env) {
  return String(env.DOTA_AI_API_URL || API_URL).replace(/\/+$/, "");
}

// app: { version, os, locale }
function uploadPayload({ text, note, installId, app = {} }) {
  return {
    install_id: String(installId || ""),
    version: String(app.version || ""),
    os: String(app.os || "").slice(0, 64),
    lang: String(app.locale || "").slice(0, 8),
    note: redact(String(note || "").trim().slice(0, NOTE_MAX)),
    text: redact(text)
  };
}

// Send again later: no connection, the service is busy or switched off. A
// report the service refuses (too large, malformed) is never sent again.
function isRetryable(result) {
  if (!result || result.ok) {
    return false;
  }
  const status = Number(result.status || 0);
  return result.code === "offline" || status === 429 || status >= 500;
}

// Outbox files are named by time; the oldest go when there are too many.
function outboxOverflow(names, max = OUTBOX_MAX) {
  const sorted = [...names].filter((name) => name.endsWith(".json")).sort();
  return sorted.slice(0, Math.max(0, sorted.length - max));
}

module.exports = {
  API_URL,
  NOTE_MAX,
  OUTBOX_MAX,
  PRIVACY_URL,
  apiUrl,
  buildReport,
  isRetryable,
  outboxOverflow,
  redact,
  reportFileName,
  tail,
  uploadPayload,
  LOG_TAIL_LINES
};
