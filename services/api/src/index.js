// Dota AI Coach API (Cloudflare Worker). Stage 1 of docs/DATA_PLAN.md:
// problem reports sent from the launcher on the player's request.
//
//   GET    /health                  -> { ok }
//   GET    /v1/config               -> which uploads are switched on (a kill switch without a release)
//   POST   /v1/report               -> stores the report (R2 + a D1 row), answers { id: "R-XXXXXX" }
//   DELETE /v1/device/<install id>  -> deletes every report of that installation
//   GET    /v1/admin/reports        -> latest reports (Bearer ADMIN_TOKEN; off without the secret)
//   GET    /v1/admin/report/<id>    -> one report as text (same)
//   cron                            -> deletes reports older than RETENTION_DAYS, old rate counters
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

const JSON_HEADERS = { "content-type": "application/json; charset=utf-8", "cache-control": "no-store" };

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
    stats: false,
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

export async function deleteDevice(installId, env) {
  const id = String(installId || "").toLowerCase();
  if (!/^[a-z0-9-]{8,64}$/.test(id)) {
    return json({ ok: false, code: "bad_install_id" }, 400);
  }
  const { results } = await env.DB.prepare("SELECT r2_key FROM reports WHERE install_id = ?1").bind(id).all();
  const rows = results || [];
  await deleteObjects(env, rows);
  await env.DB.prepare("DELETE FROM reports WHERE install_id = ?1").bind(id).run();
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
      const device = path.match(/^\/v1\/device\/([^/]+)$/);
      if (request.method === "DELETE" && device) {
        return await deleteDevice(decodeURIComponent(device[1]), env);
      }
      if (path.startsWith("/v1/admin/")) {
        if (!isAdmin(request, env)) {
          return json({ ok: false, code: "not_found" }, 404);
        }
        if (request.method === "GET" && path === "/v1/admin/reports") {
          return await adminList(env);
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
  }
};
