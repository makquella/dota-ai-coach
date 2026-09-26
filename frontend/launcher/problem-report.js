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
  /Bearer\s+[\w.-]{12,}/g
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

module.exports = { buildReport, redact, reportFileName, tail, LOG_TAIL_LINES };
