// The promo approval flow on the real Worker, workerd D1 and R2 (all
// migrations). Telegram and Metricool are answered by the outbound service.
import assert from "node:assert/strict";
import { readdir, readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { test } from "node:test";
import { Miniflare, convertV4MiniflareOptions } from "miniflare";
import { webhookSecret } from "../../src/promo.js";

const ROOT = fileURLToPath(new URL("../..", import.meta.url));
const SOURCE = path.join(ROOT, "src");
const BOT = "123456:test-token";
const ADMIN = "4242";
const ID = "0123456789abcdef";

async function localWorker(t, bindings = {}) {
  const calls = [];
  const paths = (await readdir(SOURCE, { recursive: true })).filter((name) => name.endsWith(".js") && name !== "index.js");
  const modules = ["index.js", ...paths].map((name) => ({ type: "ESModule", path: path.join(SOURCE, name) }));
  const mf = new Miniflare(
    convertV4MiniflareOptions({
      modules,
      modulesRoot: ROOT,
      compatibilityDate: "2026-09-20",
      d1Databases: { DB: "wardly-promo-integration" },
      r2Buckets: ["REPORTS"],
      bindings: {
        ADMIN_TOKEN: "admin-secret",
        TELEGRAM_BOT_TOKEN: BOT,
        TELEGRAM_CHAT_ID: ADMIN,
        TELEGRAM_CHANNEL: "@wardlydota",
        ...bindings
      },
      outboundService: async (request) => {
        const body = request.method === "GET" ? null : await request.text();
        calls.push({ url: request.url, method: request.method, body, headers: Object.fromEntries(request.headers) });
        const url = new URL(request.url);
        if (url.hostname === "api.telegram.org") {
          return Response.json({ ok: true, result: { message_id: 77 } });
        }
        if (url.pathname.endsWith("/actions/normalize/image/url")) {
          return new Response("https://static.metricool.test/normalized.mp4");
        }
        if (url.pathname.endsWith("/v2/scheduler/posts")) {
          return Response.json({ data: { id: 991, uuid: "u-1" } });
        }
        return new Response("not found", { status: 404 });
      }
    })
  );
  t.after(() => mf.dispose());
  const db = await mf.getD1Database("DB");
  for (const file of (await readdir(path.join(ROOT, "migrations"))).filter((name) => name.endsWith(".sql")).sort()) {
    const sql = await readFile(path.join(ROOT, "migrations", file), "utf8");
    for (const statement of sql.replace(/--[^\n]*/g, "").split(";").map((part) => part.trim()).filter(Boolean)) {
      await db.prepare(statement).run();
    }
  }
  return { mf, db, calls };
}

const PACKAGE = {
  id: ID,
  format: "coach",
  topic: "sniper",
  hook: 1,
  title: "Sniper: що підкаже Wardly в матчі",
  youtube_title: "Sniper: що підкаже Wardly в матчі #shorts",
  caption: "Що Wardly скаже на Sniper просто в матчі 👇\n• Використайте Concussive Grenade зараз",
  telegram_caption: "Що Wardly скаже на Sniper просто в матчі 👇"
};

function admin(mf, url, init = {}) {
  return mf.dispatchFetch(`https://api.test${url}`, {
    ...init,
    headers: { authorization: "Bearer admin-secret", ...(init.headers || {}) }
  });
}

async function press(mf, action, { from = ADMIN, secret } = {}) {
  return mf.dispatchFetch("https://api.test/v1/telegram/webhook", {
    method: "POST",
    headers: {
      "content-type": "application/json",
      "x-telegram-bot-api-secret-token": secret ?? (await webhookSecret(BOT))
    },
    body: JSON.stringify({
      update_id: 1,
      callback_query: {
        id: "cb1",
        from: { id: Number(from) },
        data: `promo:${action}:${ID}`,
        message: { message_id: 5, chat: { id: Number(ADMIN), type: "private" }, video: { file_id: "VIDEO-FILE" } }
      }
    })
  });
}

async function upload(mf) {
  const created = await admin(mf, "/v1/admin/promo", { method: "POST", body: JSON.stringify(PACKAGE) });
  assert.equal(created.status, 201);
  const { media_key: key } = await created.json();
  assert.match(key, /^[a-f0-9]{32}$/);
  const video = new Uint8Array(4096).fill(7);
  assert.equal((await admin(mf, `/v1/admin/promo/${ID}/video.mp4`, { method: "PUT", body: video })).status, 200);
  return key;
}

test("a package waits for the developer, then goes to the channel and to Metricool as a draft, once", async (t) => {
  const { mf, db, calls } = await localWorker(t, {
    METRICOOL_TOKEN: "mc-token",
    METRICOOL_USER_ID: "11",
    METRICOOL_BLOG_ID: "22"
  });
  // Not without the admin token, not with a bad package.
  assert.equal((await mf.dispatchFetch("https://api.test/v1/admin/promo", { method: "POST", body: "{}" })).status, 404);
  assert.equal((await admin(mf, "/v1/admin/promo", { method: "POST", body: JSON.stringify({ id: "x" }) })).status, 400);
  const key = await upload(mf);

  // The media is public by its random key, ranges included (players, Metricool).
  const whole = await mf.dispatchFetch(`https://api.test/m/${key}/video.mp4`);
  assert.equal(whole.status, 200);
  assert.equal(whole.headers.get("content-type"), "video/mp4");
  assert.equal((await whole.arrayBuffer()).byteLength, 4096);
  const part = await mf.dispatchFetch(`https://api.test/m/${key}/video.mp4`, { headers: { range: "bytes=0-99" } });
  assert.equal(part.status, 206);
  assert.equal(part.headers.get("content-range"), "bytes 0-99/4096");

  // A forged update and someone else's button do nothing.
  assert.equal((await press(mf, "all", { secret: "wrong" })).status, 404);
  await press(mf, "all", { from: "999" });
  assert.equal((await db.prepare("SELECT status FROM promo_posts WHERE id = ?").bind(ID).first()).status, "pending");
  assert.equal(calls.filter((c) => c.url.includes("metricool")).length, 0);

  // Two presses at once: one publication.
  await Promise.all([press(mf, "all"), press(mf, "all")]);
  const row = await db.prepare("SELECT status, metricool_id, result FROM promo_posts WHERE id = ?").bind(ID).first();
  assert.equal(row.status, "scheduled");
  assert.equal(row.metricool_id, "991");
  const posts = calls.filter((c) => c.url.includes("/v2/scheduler/posts"));
  assert.equal(posts.length, 1);
  const body = JSON.parse(posts[0].body);
  assert.equal(body.draft, true); // PROMO_METRICOOL_MODE is not "publish"
  assert.equal(body.autoPublish, false);
  assert.deepEqual(body.media, ["https://static.metricool.test/normalized.mp4"]);
  assert.deepEqual(body.providers.map((p) => p.network), ["instagram", "tiktok", "youtube"]);
  assert.equal(body.publicationDate.timezone, "Europe/Kyiv");
  assert.equal(posts[0].headers["x-mc-auth"], "mc-token");
  const normalize = calls.find((c) => c.url.includes("/actions/normalize/image/url"));
  assert.equal(new URL(normalize.url).searchParams.get("url"), `https://api.test/m/${key}/video.mp4`);
  const channel = calls.filter((c) => c.url.endsWith("/sendVideo"));
  assert.equal(channel.length, 1);
  assert.equal(JSON.parse(channel[0].body).chat_id, "@wardlydota");
  assert.equal(JSON.parse(channel[0].body).video, "VIDEO-FILE");
  assert.ok(calls.some((c) => c.url.endsWith("/answerCallbackQuery") && JSON.parse(c.body).text === "Вже вирішено раніше"));
});

test("a rejected package is never published and its media are gone", async (t) => {
  const { mf, db, calls } = await localWorker(t);
  const key = await upload(mf);
  await press(mf, "no");
  assert.equal((await db.prepare("SELECT status FROM promo_posts WHERE id = ?").bind(ID).first()).status, "rejected");
  assert.equal((await mf.dispatchFetch(`https://api.test/m/${key}/video.mp4`)).status, 404);
  assert.equal(calls.filter((c) => c.url.endsWith("/sendVideo")).length, 0);
  await press(mf, "all");
  assert.equal(calls.filter((c) => c.url.endsWith("/sendVideo")).length, 0);
});

test("only the Telegram channel when no network is connected and Metricool is off", async (t) => {
  const { mf, db, calls } = await localWorker(t);
  await upload(mf);
  await press(mf, "all");
  const row = await db.prepare("SELECT status, result FROM promo_posts WHERE id = ?").bind(ID).first();
  assert.equal(row.status, "published");
  assert.deepEqual(JSON.parse(row.result).skipped, ["instagram", "tiktok", "youtube"]);
  assert.match(calls.filter((c) => c.url.endsWith("/sendMessage")).map((c) => JSON.parse(c.body).text).at(-1), /не підключено/);
  assert.equal(calls.filter((c) => c.url.endsWith("/sendVideo")).length, 1);
});
