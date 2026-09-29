// Opt-in anonymous statistics («Анонимная статистика» in Settings → App, off by
// default): once a day the launcher sends yesterday's counts to the project API
// (services/api `POST /v1/stats`): which advice was shown per decision point,
// which urgent warnings were followed by a death (backend GET /player/usage),
// how many matches were analysed, and the few settings that shape the advice.
// No match ids, heroes, times, advice texts, nickname, Steam ID or keys; the
// random installation id lets the player delete everything with the device delete.
//
// Pure helpers, tested in test/advice-stats.test.js; main.js sends.

const HOUR_MS = 3600 * 1000;

/** Local midnight of the day `now` is in (ms). */
function dayStart(now) {
  const date = new Date(now);
  return new Date(date.getFullYear(), date.getMonth(), date.getDate()).getTime();
}

/** YYYY-MM-DD of the local day that starts at `start`. */
function localDay(start) {
  const date = new Date(start);
  const pad = (n) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

/**
 * The day to send now, or null: yesterday, once (`lastDayEnd` = the end of the
 * day already sent). A computer that was off for a week sends yesterday only.
 * `since` (ms): nothing before it counts — the moment the player switched the
 * statistics on, or deleted their server data.
 */
function dueDay(now, lastDayEnd, since = 0) {
  const end = dayStart(now);
  if (Number(lastDayEnd) >= end) {
    return null;
  }
  // 12 hours back is inside yesterday even around a clock change.
  const dayBegins = dayStart(end - 12 * HOUR_MS);
  const start = Math.min(Math.max(dayBegins, Number(since) || 0), end);
  return { start, end, day: localDay(dayBegins) };
}

/**
 * The schedule from `now` on: switching the statistics on, or deleting the
 * server data, starts counting at that moment; the first upload comes the next
 * day and carries only what happened after it.
 */
function startFrom(now) {
  return { statsLastDay: dayStart(now), statsSince: now };
}

/** The backend path with the day's counts. */
function usageQuery(period) {
  return `/player/usage?since=${Math.floor(period.start / 1000)}&until=${Math.floor(period.end / 1000)}`;
}

function counts(value) {
  const out = {};
  for (const [kind, n] of Object.entries(value || {})) {
    if (/^[A-Z][A-Z0-9_]{1,47}$/.test(kind) && Number.isInteger(n) && n >= 0) {
      out[kind] = n;
    }
  }
  return out;
}

/** The exact body sent (the panel shows it before the player switches it on). */
function buildStats({ installId, day, version, platform, lang, usage, settings, ai, opendotaKey, fullscreen, syncError }) {
  const u = usage || {};
  const s = settings || {};
  return {
    install_id: String(installId || ""),
    day,
    version: String(version || ""),
    os: ["win32", "linux", "darwin"].includes(platform) ? platform : "other",
    lang: lang === "ru" ? "ru" : "en",
    usage: {
      matches: Number.isInteger(u.matches) ? u.matches : 0,
      with_advice: Number.isInteger(u.with_advice) ? u.with_advice : 0,
      advice: counts(u.advice),
      ignored: counts(u.ignored)
    },
    settings: {
      overlay: Boolean(s.overlay),
      voice: ["off", "urgent", "all"].includes(s.voice) ? s.voice : "off",
      frequency: ["calm", "normal", "active"].includes(s.frequency) ? s.frequency : "normal",
      role: ["auto", "carry", "mid", "offlane", "support"].includes(s.role) ? s.role : "auto",
      map_hints: s.mapHints !== false,
      discord: Boolean(s.discord)
    },
    ai: ai ? "ready" : "off",
    opendota_key: Boolean(opendotaKey),
    fullscreen: Boolean(fullscreen),
    sync_error: typeof syncError === "string" && /^[a-z_]{1,32}$/.test(syncError) ? syncError : null
  };
}

/**
 * What an upload's result means for the schedule: `done` — the day is handled
 * (stored, or refused for good: a bad body, the kill switch); otherwise it is
 * tried again at the next check (offline, rate limit, server error).
 */
function uploadOutcome(result) {
  if (result && result.ok) {
    return { done: true };
  }
  const status = Number(result && result.status);
  return { done: status === 400 || status === 413 || Boolean(result && result.code === "disabled") };
}

module.exports = { buildStats, dayStart, dueDay, localDay, startFrom, uploadOutcome, usageQuery };
