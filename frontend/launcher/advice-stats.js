// Opt-in anonymous statistics («Анонімна статистика» in Settings → App, off by
// default): once a day the launcher sends yesterday's counts to the project API
// (services/api `POST /v1/stats`): which advice was shown per decision point,
// which urgent warnings were followed by a death (backend GET /player/usage),
// how many matches were analysed, and the few settings that shape the advice.
// Since 0.56: how many times the app started and crashed that day, how many
// advice cards the player marked «Корисно / Не до речі / Повторювалося» since the
// last upload, which first-run steps this installation has reached so far and
// how many days ago it was installed (a bucket). No match ids, heroes, times,
// advice texts, nickname, Steam ID or keys; the random installation id lets the
// player delete everything with the device delete.
//
// Pure helpers, tested in test/advice-stats.test.js; main.js sends.

const HOUR_MS = 3600 * 1000;
const DAY_MS = 24 * HOUR_MS;
// The daily app counters kept on this computer (settings `statsDaily`).
const APP_COUNTERS = ["launches", "backend_crashes", "renderer_crashes", "unclean_exits"];
const DAILY_KEEP = 10;
// First-run steps, in the order a new player meets them (the Home checklist,
// then the first advice in a match and the first review).
const SETUP_STEPS = ["dota", "gsi", "launch", "data", "preview", "account", "advice", "review", "ai"];
const VERDICTS = ["useful", "irrelevant", "repeated"];
const KIND = /^[A-Z][A-Z0-9_]{1,47}$/;

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
    if (KIND.test(kind) && Number.isInteger(n) && n >= 0) {
      out[kind] = n;
    }
  }
  return out;
}

/** The daily counters with one more `key` on `day` (YYYY-MM-DD); only the last DAILY_KEEP days are kept. */
function bumpDaily(daily, day, key) {
  const out = {};
  for (const [each, row] of Object.entries(daily && typeof daily === "object" ? daily : {})) {
    if (/^\d{4}-\d{2}-\d{2}$/.test(each) && row && typeof row === "object") {
      out[each] = { ...row };
    }
  }
  if (APP_COUNTERS.includes(key)) {
    const row = out[day] || {};
    row[key] = (Number.isInteger(row[key]) ? row[key] : 0) + 1;
    out[day] = row;
  }
  const keep = Object.keys(out).sort().slice(-DAILY_KEEP);
  return Object.fromEntries(keep.map((each) => [each, out[each]]));
}

/** The day's app counters, zeros for what did not happen. */
function appCounts(daily, day) {
  const row = (daily && daily[day]) || {};
  return Object.fromEntries(APP_COUNTERS.map((key) => [key, Number.isInteger(row[key]) && row[key] > 0 ? row[key] : 0]));
}

/**
 * The marks given since the last upload, from the backend's running totals
 * (GET /player/advice-feedback): `marks` per verdict, `noisy` = new «not to the
 * point» and «repeated» marks per decision point. Without a previous snapshot
 * (statistics just switched on) nothing counts yet. A removed mark is not
 * negative: the snapshot simply follows the current totals.
 */
function marksDelta(summary, sent) {
  if (!summary || typeof summary !== "object") {
    // The totals could not be read: nothing this time, and the last snapshot stays.
    return { marks: Object.fromEntries(VERDICTS.map((verdict) => [verdict, 0])), noisy: {}, snapshot: sent || null };
  }
  const totals = summary.totals || {};
  const byDp = (summary && summary.by_decision_point) || {};
  const snapshot = { totals: {}, noisy: {} };
  for (const verdict of VERDICTS) {
    snapshot.totals[verdict] = Number.isInteger(totals[verdict]) && totals[verdict] > 0 ? totals[verdict] : 0;
  }
  for (const [kind, row] of Object.entries(byDp)) {
    if (!KIND.test(kind) || !row) {
      continue;
    }
    const n = (Number(row.irrelevant) || 0) + (Number(row.repeated) || 0);
    if (Number.isInteger(n) && n > 0) {
      snapshot.noisy[kind] = n;
    }
  }
  const marks = Object.fromEntries(VERDICTS.map((verdict) => [verdict, 0]));
  const noisy = {};
  if (sent && sent.totals) {
    for (const verdict of VERDICTS) {
      marks[verdict] = Math.max(0, snapshot.totals[verdict] - (Number(sent.totals[verdict]) || 0));
    }
    for (const [kind, n] of Object.entries(snapshot.noisy)) {
      const added = n - (Number((sent.noisy || {})[kind]) || 0);
      if (added > 0) {
        noisy[kind] = added;
      }
    }
  }
  return { marks, noisy, snapshot };
}

/** Days since installation as a bucket: "0", "1", "2-6", "7-29" or "30+" ("" when unknown). */
function ageBucket(now, installedAt) {
  const since = Number(installedAt);
  if (!since || since > now) {
    return since > now ? "0" : "";
  }
  const days = Math.floor((dayStart(now) - dayStart(since)) / DAY_MS + 0.5);
  if (days <= 0) {
    return "0";
  }
  if (days === 1) {
    return "1";
  }
  return days < 7 ? "2-6" : days < 30 ? "7-29" : "30+";
}

/** The first-run steps this installation has reached: true / false, null where the app cannot tell. */
function setupFlags(state) {
  const s = state || {};
  return Object.fromEntries(
    SETUP_STEPS.map((step) => [step, s[step] === null || s[step] === undefined ? null : Boolean(s[step])])
  );
}

/** The exact body sent (the panel shows it before the player switches it on). */
function buildStats({
  installId,
  day,
  version,
  platform,
  lang,
  usage,
  settings,
  ai,
  opendotaKey,
  fullscreen,
  syncError,
  app,
  marks,
  noisy,
  setup,
  age
}) {
  const u = usage || {};
  const s = settings || {};
  const m = marks || {};
  return {
    install_id: String(installId || ""),
    day,
    version: String(version || ""),
    os: ["win32", "linux", "darwin"].includes(platform) ? platform : "other",
    lang: lang === "uk" ? "uk" : "en",
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
    sync_error: typeof syncError === "string" && /^[a-z_]{1,32}$/.test(syncError) ? syncError : null,
    app: appCounts({ day: app || {} }, "day"),
    marks: Object.fromEntries(VERDICTS.map((verdict) => [verdict, Number.isInteger(m[verdict]) && m[verdict] > 0 ? m[verdict] : 0])),
    noisy: counts(noisy),
    setup: setupFlags(setup),
    age: ["0", "1", "2-6", "7-29", "30+"].includes(age) ? age : ""
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

module.exports = {
  APP_COUNTERS,
  SETUP_STEPS,
  ageBucket,
  appCounts,
  buildStats,
  bumpDaily,
  dayStart,
  dueDay,
  localDay,
  marksDelta,
  setupFlags,
  startFrom,
  uploadOutcome,
  usageQuery
};
