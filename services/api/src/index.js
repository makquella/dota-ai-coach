// Wardly API (Cloudflare Worker). Stage 1 of docs/DATA_PLAN.md:
// problem reports sent from the launcher on the player's request.
//
//   GET    /health                  -> { ok }
//   GET    /v1/config               -> which uploads are switched on (a kill switch without a release)
//   POST   /v1/report               -> stores the report (R2 + a D1 row), answers { id: "R-XXXXXX" }
//   DELETE /v1/device/<install id>  -> deletes every report of that installation
//   POST   /v1/share                -> publishes a review (src/share.js), answers { id, url, delete_token }
//   GET    /v1/share/<id>           -> the shared review as JSON
//   DELETE /v1/share/<id>           -> deletes it (header x-delete-token)
//   GET    /r/<id>                  -> the shared review as a page (with an Open Graph preview)
//   POST   /v1/stats                -> the opt-in anonymous daily statistics (src/stats.js), one row per installation and day
//   PUT    /v1/transfer/<id>        -> keeps an encrypted history backup for 15 minutes (src/transfer.js)
//   POST   /v1/transfer/<id>/claim  -> hands it over (3 downloads at most)
//   DELETE /v1/transfer/<id>        -> the receiving launcher deletes it once imported
//   GET    /v1/admin/reports        -> latest reports (Bearer ADMIN_TOKEN; off without the secret)
//   GET    /v1/admin/report/<id>    -> one report as text (same)
//   GET    /v1/admin/stats?days=N   -> the statistics summed over the last N days (same)
//   POST   /v1/hit                  -> +1 visit of the site for a source (src/channels.js; the site sends it once per visit)
//   GET    /d/<source>              -> +1 download for that source, then a redirect to the latest installer
//   GET    /admin, /admin/app.js    -> the statistics page (src/admin-page.js; asks for the token, holds no data;
//                                      404 while ADMIN_TOKEN is not set)
//   cron                            -> deletes reports older than RETENTION_DAYS, expired shares, old rate counters,
//                                      statistics older than STATS_RETENTION_DAYS, source counts older than
//                                      CHANNEL_RETENTION_DAYS; on Mondays a stats note to Telegram
//
// Bindings: DB (D1), REPORTS (R2, optional: without it the gzipped report is
// kept in the D1 row, which is enough for the free tier's 5 GB). Secrets (optional): TELEGRAM_BOT_TOKEN,
// TELEGRAM_CHAT_ID (a message with the report file to the developer), ADMIN_TOKEN.

import {
  LIMITS,
  RATE_PER_HOUR,
  RETENTION_DAYS,
  hourWindow,
  reportId,
  storageKey,
  summarize,
  telegramCaption,
  validateReport
} from "./report.js";
import {
  SHARE_DAYS,
  SHARE_LIMITS,
  SHARE_RATE_PER_HOUR,
  isShareId,
  renderMissingPage,
  renderSharePage,
  shareId,
  validateShare
} from "./share.js";
import { ADMIN_HEADERS, ADMIN_HTML, ADMIN_JS, ADMIN_SCRIPT_HEADERS } from "./admin-page.js";
import {
  STATS_ADMIN_MAX_DAYS,
  STATS_MAX_BYTES,
  STATS_RATE_PER_HOUR,
  STATS_RETENTION_DAYS,
  aggregateStats,
  isoDay,
  validateStats,
  weeklyStatsText
} from "./stats.js";
import {
  CHANNEL_MAX_SOURCES,
  CHANNEL_RATE_PER_HOUR,
  CHANNEL_RETENTION_DAYS,
  aggregateChannels,
  channelSource,
  latestInstaller
} from "./channels.js";
import {
  TRANSFER_MAX_BYTES,
  TRANSFER_MINUTES,
  TRANSFER_RATE_PER_HOUR,
  TRANSFER_TRIES,
  isSealed,
  isTransferId
} from "./transfer.js";

const JSON_HEADERS = { "content-type": "application/json; charset=utf-8", "cache-control": "no-store" };
const HTML_HEADERS = {
  "content-type": "text/html; charset=utf-8",
  "x-content-type-options": "nosniff",
  "referrer-policy": "no-referrer",
  // Styles are inline; images come from the site and Valve's CDN; no scripts at all.
  "content-security-policy":
    "default-src 'none'; style-src 'unsafe-inline'; img-src https://luhovyimvp.dev https://cdn.cloudflare.steamstatic.com; base-uri 'none'; form-action 'none'; frame-ancestors 'none'"
};

function json(data, status = 200) {
  return new Response(JSON.stringify(data), { status, headers: JSON_HEADERS });
}

function flag(value, fallback) {
  if (value === undefined || value === null || value === "") {
    return fallback;
  }
  return !["0", "false", "off", "no"].includes(String(value).toLowerCase());
}

export function config(env) {
  return {
    reports: flag(env.REPORTS_ENABLED, true),
    shares: flag(env.SHARES_ENABLED, true),
    transfers: flag(env.TRANSFERS_ENABLED, true),
    transfer_minutes: TRANSFER_MINUTES,
    share_days: SHARE_DAYS,
    stats: flag(env.STATS_ENABLED, true),
    channels: flag(env.CHANNELS_ENABLED, true),
    sessions: false,
    retention_days: RETENTION_DAYS
  };
}

async function sha256(text) {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
  return [...new Uint8Array(digest)].map((b) => b.toString(16).padStart(2, "0")).join("").slice(0, 32);
}

/** +1 for this hour; true while under the limit. */
async function allow(env, key, limit, now) {
  const row = await env.DB.prepare(
    "INSERT INTO rate (key, hour, count) VALUES (?1, ?2, 1) " +
      "ON CONFLICT(key, hour) DO UPDATE SET count = count + 1 RETURNING count"
  )
    .bind(key, hourWindow(now))
    .first();
  return Number(row?.count || 0) <= limit;
}

async function gzip(text) {
  const stream = new Blob([text]).stream().pipeThrough(new CompressionStream("gzip"));
  return new Uint8Array(await new Response(stream).arrayBuffer());
}

async function gunzipText(body) {
  const stream = body.pipeThrough(new DecompressionStream("gzip"));
  return new Response(stream).text();
}

/** Removes the R2 objects of these rows (rows stored in D1 have no key). */
async function deleteObjects(env, rows) {
  const keys = rows.map((row) => row.r2_key).filter(Boolean);
  if (!env.REPORTS) {
    return;
  }
  for (let i = 0; i < keys.length; i += 1000) {
    await env.REPORTS.delete(keys.slice(i, i + 1000));
  }
}

async function notifyTelegram(env, id, report) {
  if (!env.TELEGRAM_BOT_TOKEN || !env.TELEGRAM_CHAT_ID) {
    return;
  }
  const form = new FormData();
  form.append("chat_id", String(env.TELEGRAM_CHAT_ID));
  form.append("caption", telegramCaption(id, report));
  const file = `${report.note ? `Player note:\n${report.note}\n\n` : ""}${report.text}`;
  form.append("document", new Blob([file], { type: "text/plain" }), `${id}.txt`);
  const response = await fetch(`https://api.telegram.org/bot${env.TELEGRAM_BOT_TOKEN}/sendDocument`, {
    method: "POST",
    body: form
  });
  if (!response.ok) {
    console.log(`telegram: HTTP ${response.status}`);
  }
}

export async function handleReport(request, env, ctx, now = Date.now()) {
  if (!config(env).reports) {
    return json({ ok: false, code: "disabled" }, 503);
  }
  const length = Number(request.headers.get("content-length") || 0);
  if (length > LIMITS.bodyBytes) {
    return json({ ok: false, code: "too_large" }, 413);
  }
  const raw = await request.text();
  if (raw.length > LIMITS.bodyBytes) {
    return json({ ok: false, code: "too_large" }, 413);
  }
  let body;
  try {
    body = JSON.parse(raw);
  } catch {
    return json({ ok: false, code: "bad_json" }, 400);
  }
  const checked = validateReport(body);
  if (!checked.ok) {
    return json({ ok: false, code: checked.code }, checked.status);
  }
  const report = checked.report;
  const address = await sha256(`dac-rate:${request.headers.get("cf-connecting-ip") || "unknown"}`);
  const underLimit =
    (await allow(env, `report:install:${report.installId}`, RATE_PER_HOUR.install, now)) &&
    (await allow(env, `report:address:${address}`, RATE_PER_HOUR.address, now));
  if (!underLimit) {
    return json({ ok: false, code: "rate_limited" }, 429);
  }

  const id = reportId(crypto.getRandomValues(new Uint8Array(6)));
  const date = new Date(now);
  const stored = `${report.note ? `Player note:\n${report.note}\n\n` : ""}${report.text}`;
  const packed = await gzip(stored);
  let key = null;
  let inline = null;
  if (env.REPORTS) {
    key = storageKey(id, date);
    await env.REPORTS.put(key, packed, {
      httpMetadata: { contentType: "text/plain; charset=utf-8", contentEncoding: "gzip" },
      customMetadata: { id, version: report.version, install: report.installId }
    });
  } else if (packed.byteLength > LIMITS.rowBytes) {
    return json({ ok: false, code: "too_large" }, 413);
  } else {
    inline = packed;
  }
  await env.DB.prepare(
    "INSERT INTO reports (id, created_at, install_id, version, os, lang, size, summary, r2_key, body) " +
      "VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10)"
  )
    .bind(id, now, report.installId, report.version, report.os, report.lang, stored.length, summarize(report), key, inline)
    .run();
  ctx.waitUntil(notifyTelegram(env, id, report).catch((error) => console.log(`telegram: ${error.message}`)));
  return json({ ok: true, id, retention_days: RETENTION_DAYS }, 201);
}

async function readShare(env, id, now) {
  const row = await env.DB.prepare("SELECT body, expires_at, lang FROM shares WHERE id = ?1").bind(id).first();
  if (!row || Number(row.expires_at) <= now) {
    return null;
  }
  const text = await gunzipText(new Blob([new Uint8Array(row.body)]).stream());
  return { review: JSON.parse(text), expiresAt: Number(row.expires_at) };
}

export async function handleShare(request, env, now = Date.now()) {
  if (!config(env).shares) {
    return json({ ok: false, code: "disabled" }, 503);
  }
  const raw = await request.text();
  if (raw.length > SHARE_LIMITS.bodyBytes) {
    return json({ ok: false, code: "too_large" }, 413);
  }
  let body;
  try {
    body = JSON.parse(raw);
  } catch {
    return json({ ok: false, code: "bad_json" }, 400);
  }
  const checked = validateShare(body);
  if (!checked.ok) {
    return json({ ok: false, code: checked.code }, checked.status);
  }
  const { installId, version, review } = checked.share;
  const address = await sha256(`dac-rate:${request.headers.get("cf-connecting-ip") || "unknown"}`);
  const underLimit =
    (await allow(env, `share:install:${installId}`, SHARE_RATE_PER_HOUR.install, now)) &&
    (await allow(env, `share:address:${address}`, SHARE_RATE_PER_HOUR.address, now));
  if (!underLimit) {
    return json({ ok: false, code: "rate_limited" }, 429);
  }
  const id = shareId(crypto.getRandomValues(new Uint8Array(10)));
  const token = [...crypto.getRandomValues(new Uint8Array(24))].map((b) => b.toString(16).padStart(2, "0")).join("");
  const expiresAt = now + SHARE_DAYS * 24 * 3_600_000;
  await env.DB.prepare(
    "INSERT INTO shares (id, created_at, expires_at, install_id, delete_hash, lang, version, body) " +
      "VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8)"
  )
    .bind(id, now, expiresAt, installId, await sha256(`dac-share:${token}`), review.lang, version, await gzip(JSON.stringify(review)))
    .run();
  // SHARE_ORIGIN: the site's own address when a Workers route sends /r/* there
  // (luhovyimvp.dev/r/<id>); the pages work on the API's address too.
  // Launchers before 0.9.0 open only links on the API's own address.
  const siteLinks = /^https:\/\/[a-z0-9.-]+$/.test(String(env.SHARE_ORIGIN || "")) && versionAtLeast(version, SITE_LINKS_SINCE);
  const origin = siteLinks ? env.SHARE_ORIGIN : new URL(request.url).origin;
  const url = `${origin}/r/${id}`;
  return json({ ok: true, id, url, delete_token: token, expires_at: expiresAt }, 201);
}

const SITE_LINKS_SINCE = [0, 9, 0];

/** "0.9.1" >= [0, 9, 0]; anything that is not a version is older. */
export function versionAtLeast(version, [major, minor, patch]) {
  const parts = String(version || "").match(/^(\d+)\.(\d+)\.(\d+)/);
  if (!parts) {
    return false;
  }
  const [a, b, c] = parts.slice(1).map(Number);
  return a !== major ? a > major : b !== minor ? b > minor : c >= patch;
}

export async function deleteShare(request, id, env) {
  const token = request.headers.get("x-delete-token") || "";
  const row = await env.DB.prepare("SELECT delete_hash FROM shares WHERE id = ?1").bind(id).first();
  if (!row) {
    return json({ ok: false, code: "not_found" }, 404);
  }
  if (!token || (await sha256(`dac-share:${token}`)) !== row.delete_hash) {
    return json({ ok: false, code: "forbidden" }, 403);
  }
  await env.DB.prepare("DELETE FROM shares WHERE id = ?1").bind(id).run();
  return json({ ok: true });
}

export async function sharePage(request, id, env, now = Date.now()) {
  const shared = isShareId(id) ? await readShare(env, id, now) : null;
  const lang = (request.headers.get("accept-language") || "").toLowerCase().startsWith("ru") ? "ru" : "en";
  if (!shared) {
    return new Response(renderMissingPage(lang), { status: 404, headers: { ...HTML_HEADERS, "cache-control": "no-store" } });
  }
  const html = renderSharePage(shared.review, { url: request.url, expiresAt: shared.expiresAt });
  return new Response(html, { headers: { ...HTML_HEADERS, "cache-control": "public, max-age=300" } });
}

function clientAddress(request) {
  return request.headers.get("cf-connecting-ip") || "unknown";
}

export async function putTransfer(request, id, env, now = Date.now()) {
  if (!config(env).transfers) {
    return json({ ok: false, code: "disabled" }, 503);
  }
  if (!isTransferId(id)) {
    return json({ ok: false, code: "bad_id" }, 400);
  }
  const installId = String(request.headers.get("x-install-id") || "").toLowerCase();
  if (!/^[a-z0-9-]{8,64}$/.test(installId)) {
    return json({ ok: false, code: "bad_install_id" }, 400);
  }
  const length = Number(request.headers.get("content-length") || 0);
  if (length > TRANSFER_MAX_BYTES) {
    return json({ ok: false, code: "too_big" }, 413);
  }
  const body = new Uint8Array(await request.arrayBuffer());
  if (body.length > TRANSFER_MAX_BYTES) {
    return json({ ok: false, code: "too_big" }, 413);
  }
  if (!isSealed(body)) {
    return json({ ok: false, code: "bad_body" }, 400);
  }
  const address = await sha256(`dac-rate:${clientAddress(request)}`);
  const allowed =
    (await allow(env, `transfer:install:${installId}`, TRANSFER_RATE_PER_HOUR.install, now)) &&
    (await allow(env, `transfer:address:${address}`, TRANSFER_RATE_PER_HOUR.address, now));
  if (!allowed) {
    return json({ ok: false, code: "rate_limited" }, 429);
  }
  await env.DB.prepare("DELETE FROM transfers WHERE expires_at < ?1").bind(now).run();
  const taken = await env.DB.prepare("SELECT id FROM transfers WHERE id = ?1").bind(id).first();
  if (taken) {
    return json({ ok: false, code: "taken" }, 409);
  }
  const expiresAt = now + TRANSFER_MINUTES * 60_000;
  await env.DB.prepare(
    "INSERT INTO transfers (id, created_at, expires_at, install_id, size, body) VALUES (?1, ?2, ?3, ?4, ?5, ?6)"
  )
    .bind(id, now, expiresAt, installId, body.length, body)
    .run();
  return json({ ok: true, id, expires_at: expiresAt }, 201);
}

export async function claimTransfer(request, id, env, now = Date.now()) {
  if (!config(env).transfers) {
    return json({ ok: false, code: "disabled" }, 503);
  }
  const address = await sha256(`dac-rate:${clientAddress(request)}`);
  // Every claim counts, found or not: guessing ids is slow.
  if (!(await allow(env, `transfer:claim:${address}`, TRANSFER_RATE_PER_HOUR.claim, now))) {
    return json({ ok: false, code: "rate_limited" }, 429);
  }
  if (!isTransferId(id)) {
    return json({ ok: false, code: "not_found" }, 404);
  }
  const row = await env.DB.prepare("SELECT body, expires_at, tries FROM transfers WHERE id = ?1").bind(id).first();
  if (!row || Number(row.expires_at) < now) {
    await env.DB.prepare("DELETE FROM transfers WHERE id = ?1").bind(id).run();
    return json({ ok: false, code: "not_found" }, 404);
  }
  if (Number(row.tries) + 1 >= TRANSFER_TRIES) {
    await env.DB.prepare("DELETE FROM transfers WHERE id = ?1").bind(id).run();
  } else {
    await env.DB.prepare("UPDATE transfers SET tries = tries + 1 WHERE id = ?1").bind(id).run();
  }
  return new Response(new Uint8Array(row.body), {
    headers: { "content-type": "application/octet-stream", "cache-control": "no-store" }
  });
}

export async function deleteTransfer(request, id, env, now = Date.now()) {
  const address = await sha256(`dac-rate:${clientAddress(request)}`);
  if (!(await allow(env, `transfer:claim:${address}`, TRANSFER_RATE_PER_HOUR.claim, now))) {
    return json({ ok: false, code: "rate_limited" }, 429);
  }
  if (isTransferId(id)) {
    await env.DB.prepare("DELETE FROM transfers WHERE id = ?1").bind(id).run();
  }
  return json({ ok: true });
}

function statsHash(installId) {
  return sha256(`dac-stats:${installId}`);
}

export async function handleStats(request, env, now = Date.now()) {
  if (!config(env).stats) {
    return json({ ok: false, code: "disabled" }, 503);
  }
  const raw = await request.text();
  if (raw.length > STATS_MAX_BYTES) {
    return json({ ok: false, code: "too_large" }, 413);
  }
  let body;
  try {
    body = JSON.parse(raw);
  } catch {
    return json({ ok: false, code: "bad_json" }, 400);
  }
  const checked = validateStats(body, now);
  if (!checked.ok) {
    return json({ ok: false, code: checked.code }, checked.status);
  }
  const address = await sha256(`dac-rate:${clientAddress(request)}`);
  // The install id is kept only as the salted hash, the rate counter included.
  const installHash = await statsHash(checked.installId);
  const underLimit =
    (await allow(env, `stats:install:${installHash}`, STATS_RATE_PER_HOUR.install, now)) &&
    (await allow(env, `stats:address:${address}`, STATS_RATE_PER_HOUR.address, now));
  if (!underLimit) {
    return json({ ok: false, code: "rate_limited" }, 429);
  }
  // One row per installation and day: sending the same day again replaces it.
  await env.DB.prepare(
    "INSERT INTO daily_stats (install_hash, day, created_at, version, body) VALUES (?1, ?2, ?3, ?4, ?5) " +
      "ON CONFLICT(install_hash, day) DO UPDATE SET created_at = excluded.created_at, version = excluded.version, body = excluded.body"
  )
    .bind(installHash, checked.day, now, checked.version, JSON.stringify(checked.row))
    .run();
  return json({ ok: true, day: checked.day, retention_days: STATS_RETENTION_DAYS }, 201);
}

/** +1 visit or download for a source today; a flood of new names counts as "other". */
async function countChannel(env, src, kind, now) {
  const day = isoDay(now);
  const seen = await env.DB.prepare(
    "SELECT COUNT(*) AS sources, SUM(src = ?2) AS known FROM channel_counts WHERE day = ?1"
  )
    .bind(day, src)
    .first();
  const name = !Number(seen?.known) && Number(seen?.sources) >= CHANNEL_MAX_SOURCES ? "other" : src;
  await env.DB.prepare(
    "INSERT INTO channel_counts (day, src, visits, downloads) VALUES (?1, ?2, ?3, ?4) " +
      "ON CONFLICT(day, src) DO UPDATE SET visits = visits + excluded.visits, downloads = downloads + excluded.downloads"
  )
    .bind(day, name, kind === "visit" ? 1 : 0, kind === "download" ? 1 : 0)
    .run();
}

async function underChannelLimit(request, env, kind, now) {
  const address = await sha256(`dac-rate:${clientAddress(request)}`);
  return allow(env, `channel:${kind}:${address}`, CHANNEL_RATE_PER_HOUR[kind], now);
}

// The site sends { src } with navigator.sendBeacon (text/plain: no preflight),
// so the answer carries no data and needs no CORS headers.
export async function handleHit(request, env, now = Date.now()) {
  if (!config(env).channels) {
    return new Response(null, { status: 204 });
  }
  const raw = await request.text();
  let src = null;
  if (raw.length <= 200) {
    try {
      src = channelSource(JSON.parse(raw).src);
    } catch {
      src = null;
    }
  }
  if (!src) {
    return json({ ok: false, code: "bad_source" }, 400);
  }
  if (await underChannelLimit(request, env, "visit", now)) {
    await countChannel(env, src, "visit", now);
  }
  return new Response(null, { status: 204 });
}

// Always redirects: counting is best effort and never blocks the download.
export async function handleDownload(request, src, env, now = Date.now(), fetchImpl = fetch) {
  const name = channelSource(src) || "site";
  if (config(env).channels) {
    try {
      if (await underChannelLimit(request, env, "download", now)) {
        await countChannel(env, name, "download", now);
      }
    } catch (error) {
      console.log(`download count: ${error.message}`);
    }
  }
  return new Response(null, {
    status: 302,
    headers: { location: await latestInstaller(fetchImpl, now), "cache-control": "no-store", "referrer-policy": "no-referrer" }
  });
}

async function statsSummary(env, days, now) {
  const since = isoDay(now - days * 24 * 3_600_000);
  const { results } = await env.DB.prepare("SELECT install_hash, day, version, body FROM daily_stats WHERE day >= ?1")
    .bind(since)
    .all();
  const summary = aggregateStats(results || []);
  const channels = await env.DB.prepare("SELECT day, src, visits, downloads FROM channel_counts WHERE day >= ?1")
    .bind(since)
    .all();
  summary.channels = aggregateChannels(channels.results || []);
  return summary;
}

async function adminStats(url, env, now = Date.now()) {
  const days = Math.min(Math.max(Number.parseInt(url.searchParams.get("days") || "30", 10) || 30, 1), STATS_ADMIN_MAX_DAYS);
  return json({ ok: true, days, stats: await statsSummary(env, days, now) });
}

export async function sendWeeklyStats(env, now = Date.now()) {
  if (!env.TELEGRAM_BOT_TOKEN || !env.TELEGRAM_CHAT_ID || new Date(now).getUTCDay() !== 1) {
    return false;
  }
  const summary = await statsSummary(env, 7, now);
  if (!summary.rows && !summary.channels.length) {
    return false;
  }
  const response = await fetch(`https://api.telegram.org/bot${env.TELEGRAM_BOT_TOKEN}/sendMessage`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ chat_id: String(env.TELEGRAM_CHAT_ID), text: weeklyStatsText(summary) })
  });
  return response.ok;
}

export async function deleteDevice(installId, env) {
  const id = String(installId || "").toLowerCase();
  if (!/^[a-z0-9-]{8,64}$/.test(id)) {
    return json({ ok: false, code: "bad_install_id" }, 400);
  }
  const { results } = await env.DB.prepare("SELECT r2_key FROM reports WHERE install_id = ?1").bind(id).all();
  const rows = results || [];
  await deleteObjects(env, rows);
  await env.DB.prepare("DELETE FROM reports WHERE install_id = ?1").bind(id).run();
  await env.DB.prepare("DELETE FROM shares WHERE install_id = ?1").bind(id).run();
  await env.DB.prepare("DELETE FROM transfers WHERE install_id = ?1").bind(id).run();
  await env.DB.prepare("DELETE FROM daily_stats WHERE install_hash = ?1").bind(await statsHash(id)).run();
  return json({ ok: true, deleted: rows.length });
}

function isAdmin(request, env) {
  const token = env.ADMIN_TOKEN;
  return Boolean(token) && request.headers.get("authorization") === `Bearer ${token}`;
}

async function adminList(env) {
  const { results } = await env.DB.prepare(
    "SELECT id, created_at, version, os, lang, size, summary FROM reports ORDER BY created_at DESC LIMIT 50"
  ).all();
  return json({ ok: true, reports: results || [] });
}

async function adminReport(id, env) {
  const row = await env.DB.prepare("SELECT r2_key, body FROM reports WHERE id = ?1").bind(id).first();
  let packed = null;
  if (row?.body) {
    packed = new Blob([new Uint8Array(row.body)]).stream();
  } else if (row?.r2_key && env.REPORTS) {
    packed = (await env.REPORTS.get(row.r2_key))?.body || null;
  }
  if (!packed) {
    return json({ ok: false, code: "not_found" }, 404);
  }
  return new Response(await gunzipText(packed), {
    headers: { "content-type": "text/plain; charset=utf-8", "cache-control": "no-store" }
  });
}

// D1 binds at most 100 parameters per statement, so old reports go in batches.
const CLEANUP_BATCH = 100;
const CLEANUP_MAX_BATCHES = 50;

export async function cleanup(env, now = Date.now()) {
  const cutoff = now - RETENTION_DAYS * 24 * 3_600_000;
  let removed = 0;
  for (let batch = 0; batch < CLEANUP_MAX_BATCHES; batch += 1) {
    const { results } = await env.DB.prepare(
      `SELECT id, r2_key FROM reports WHERE created_at < ?1 LIMIT ${CLEANUP_BATCH}`
    )
      .bind(cutoff)
      .all();
    const rows = results || [];
    if (!rows.length) {
      break;
    }
    // Objects first, then exactly those index rows: a failure in between
    // leaves rows that the next run deletes again, never unindexed objects.
    await deleteObjects(env, rows);
    const marks = rows.map((_, i) => `?${i + 1}`).join(", ");
    await env.DB.prepare(`DELETE FROM reports WHERE id IN (${marks})`)
      .bind(...rows.map((row) => row.id))
      .run();
    removed += rows.length;
    if (rows.length < CLEANUP_BATCH) {
      break;
    }
  }
  await env.DB.prepare("DELETE FROM shares WHERE expires_at < ?1").bind(now).run();
  await env.DB.prepare("DELETE FROM transfers WHERE expires_at < ?1").bind(now).run();
  await env.DB.prepare("DELETE FROM daily_stats WHERE day < ?1")
    .bind(isoDay(now - STATS_RETENTION_DAYS * 24 * 3_600_000))
    .run();
  await env.DB.prepare("DELETE FROM channel_counts WHERE day < ?1")
    .bind(isoDay(now - CHANNEL_RETENTION_DAYS * 24 * 3_600_000))
    .run();
  await env.DB.prepare("DELETE FROM rate WHERE hour < ?1").bind(hourWindow(now) - 48).run();
  return removed;
}

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const path = url.pathname.replace(/\/+$/, "") || "/";
    try {
      if (request.method === "GET" && (path === "/" || path === "/health")) {
        return json({ ok: true, service: "dota-ai-coach-api" });
      }
      if (request.method === "GET" && path === "/v1/config") {
        return json(config(env));
      }
      if (request.method === "POST" && path === "/v1/report") {
        return await handleReport(request, env, ctx);
      }
      if (request.method === "POST" && path === "/v1/stats") {
        return await handleStats(request, env);
      }
      if (request.method === "POST" && path === "/v1/hit") {
        return await handleHit(request, env);
      }
      const download = path.match(/^\/d(?:\/([^/]{1,40}))?$/);
      if (download && (request.method === "GET" || request.method === "HEAD")) {
        return await handleDownload(request, download[1], env);
      }
      if (request.method === "POST" && path === "/v1/share") {
        return await handleShare(request, env);
      }
      const share = path.match(/^\/v1\/share\/([a-z0-9]{1,20})$/);
      if (share && request.method === "DELETE") {
        return await deleteShare(request, share[1], env);
      }
      if (share && request.method === "GET") {
        const shared = isShareId(share[1]) ? await readShare(env, share[1], Date.now()) : null;
        return shared
          ? json({ ok: true, review: shared.review, expires_at: shared.expiresAt })
          : json({ ok: false, code: "not_found" }, 404);
      }
      const transfer = path.match(/^\/v1\/transfer\/([^/]{1,8})(\/claim)?$/);
      if (transfer && request.method === "PUT" && !transfer[2]) {
        return await putTransfer(request, transfer[1], env);
      }
      if (transfer && request.method === "POST" && transfer[2]) {
        return await claimTransfer(request, transfer[1], env);
      }
      if (transfer && request.method === "DELETE" && !transfer[2]) {
        return await deleteTransfer(request, transfer[1], env);
      }
      const pageMatch = path.match(/^\/r\/([^/]{1,40})$/);
      if (pageMatch && (request.method === "GET" || request.method === "HEAD")) {
        return await sharePage(request, pageMatch[1], env);
      }
      const device = path.match(/^\/v1\/device\/([^/]+)$/);
      if (request.method === "DELETE" && device) {
        return await deleteDevice(decodeURIComponent(device[1]), env);
      }
      if (request.method === "GET" && (path === "/admin" || path === "/admin/app.js")) {
        if (!env.ADMIN_TOKEN) {
          return json({ ok: false, code: "not_found" }, 404);
        }
        return path === "/admin"
          ? new Response(ADMIN_HTML, { headers: ADMIN_HEADERS })
          : new Response(ADMIN_JS, { headers: ADMIN_SCRIPT_HEADERS });
      }
      if (path.startsWith("/v1/admin/")) {
        if (!isAdmin(request, env)) {
          return json({ ok: false, code: "not_found" }, 404);
        }
        if (request.method === "GET" && path === "/v1/admin/reports") {
          return await adminList(env);
        }
        if (request.method === "GET" && path === "/v1/admin/stats") {
          return await adminStats(url, env);
        }
        const one = path.match(/^\/v1\/admin\/report\/(R-[A-Z0-9]{6})$/);
        if (request.method === "GET" && one) {
          return await adminReport(one[1], env);
        }
      }
      return json({ ok: false, code: "not_found" }, 404);
    } catch (error) {
      console.log(`error: ${error.stack || error.message}`);
      return json({ ok: false, code: "internal" }, 500);
    }
  },

  async scheduled(_event, env, ctx) {
    ctx.waitUntil(cleanup(env).then((count) => console.log(`cleanup: ${count} old reports`)));
    ctx.waitUntil(sendWeeklyStats(env).catch((error) => console.log(`weekly stats: ${error.message}`)));
  }
};
