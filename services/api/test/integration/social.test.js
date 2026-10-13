// Direct publishing on the real Worker, workerd D1 and R2 (all migrations):
// /connect -> OAuth callback -> sealed account; approval -> deliveries; the
// five-minute cron uploads, polls and reports. The networks are answered by
// the outbound service.
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
const ID = "fedcba9876543210";

async function localWorker(t) {
  const calls = [];
  let igStatus = "IN_PROGRESS";
  const paths = (await readdir(SOURCE, { recursive: true })).filter((name) => name.endsWith(".js") && name !== "index.js");
  const modules = ["index.js", ...paths].map((name) => ({ type: "ESModule", path: path.join(SOURCE, name) }));
  const mf = new Miniflare(
    convertV4MiniflareOptions({
      modules,
      modulesRoot: ROOT,
      compatibilityDate: "2026-09-20",
      d1Databases: { DB: "wardly-social-integration" },
      r2Buckets: ["REPORTS"],
      bindings: {
        ADMIN_TOKEN: "admin-secret",
        TELEGRAM_BOT_TOKEN: BOT,
        TELEGRAM_CHAT_ID: ADMIN,
        TELEGRAM_CHANNEL: "@wardlydota",
        PROMO_PUBLIC_ORIGIN: "https://api.test",
        PROMO_NETWORKS: "instagram,tiktok,youtube",
        YOUTUBE_CLIENT_ID: "yt-id",
        YOUTUBE_CLIENT_SECRET: "yt-secret",
        INSTAGRAM_APP_ID: "ig-id",
        INSTAGRAM_APP_SECRET: "ig-secret"
      },
      outboundService: async (request) => {
        const body = request.method === "GET" ? null : await request.text();
        calls.push({ url: request.url, method: request.method, body });
        const url = new URL(request.url);
        const route = `${url.hostname}${url.pathname}`;
        if (url.hostname === "api.telegram.org") return Response.json({ ok: true, result: { message_id: 77 } });
        if (route === "oauth2.googleapis.com/token") {
          return Response.json({ access_token: "yt-access", refresh_token: "yt-refresh-secret", expires_in: 3600 });
        }
        if (route === "www.googleapis.com/youtube/v3/channels") {
          return Response.json({ items: [{ id: "UC1", snippet: { title: "Wardly" } }] });
        }
        if (route === "www.googleapis.com/upload/youtube/v3/videos") {
          return new Response("{}", { headers: { location: "https://upload.test/s1" } });
        }
        if (route === "upload.test/s1") return Response.json({ id: "vid1", status: { privacyStatus: "public" } });
        if (route === "api.instagram.com/oauth/access_token") return Response.json({ access_token: "ig-short", user_id: 555 });
        if (route === "graph.instagram.com/access_token") return Response.json({ access_token: "ig-long-secret", expires_in: 5184000 });
        if (route === "graph.instagram.com/v21.0/me") return Response.json({ user_id: "555", username: "wardly" });
        if (route === "graph.instagram.com/v21.0/555/media") return Response.json({ id: "cont1" });
        if (route === "graph.instagram.com/v21.0/cont1") return Response.json({ status_code: igStatus });
        if (route === "graph.instagram.com/v21.0/555/media_publish") return Response.json({ id: "reel1" });
        if (route === "graph.instagram.com/v21.0/reel1") return Response.json({ permalink: "https://www.instagram.com/reel/r1/" });
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
  return { mf, db, calls, setIg: (value) => (igStatus = value) };
}

async function update(mf, payload) {
  return mf.dispatchFetch("https://api.test/v1/telegram/webhook", {
    method: "POST",
    headers: { "content-type": "application/json", "x-telegram-bot-api-secret-token": await webhookSecret(BOT) },
    body: JSON.stringify({ update_id: 1, ...payload })
  });
}

function say(mf, text, from = ADMIN) {
  return update(mf, { message: { message_id: 1, text, chat: { id: Number(from), type: "private" }, from: { id: Number(from) } } });
}

function sent(calls, method) {
  return calls.filter((c) => c.url.endsWith(`/${method}`)).map((c) => JSON.parse(c.body));
}

async function connect(mf, calls, network, code) {
  await say(mf, `/connect ${network}`);
  const message = sent(calls, "sendMessage").at(-1);
  const link = new URL(message.reply_markup.inline_keyboard[0][0].url);
  assert.equal(link.searchParams.get("redirect_uri"), `https://api.test/oauth/${network}/callback`);
  const state = link.searchParams.get("state");
  const page = await mf.dispatchFetch(`https://api.test/oauth/${network}/callback?code=${code}&state=${state}`);
  return { page, state };
}

test("accounts connect through the bot, only for the developer, and are stored sealed", async (t) => {
  const { mf, db, calls } = await localWorker(t);
  await say(mf, "/connect youtube", "999"); // a stranger gets no link
  assert.ok(!sent(calls, "sendMessage").some((m) => m.reply_markup));
  const { page, state } = await connect(mf, calls, "youtube", "c1");
  assert.equal(page.status, 200);
  assert.match(await page.text(), /YouTube підключено/);
  const row = await db.prepare("SELECT sealed, account FROM promo_accounts WHERE network = 'youtube'").first();
  assert.equal(row.account, "Wardly");
  assert.ok(!row.sealed.includes("yt-refresh-secret") && !row.sealed.includes("yt-access"));
  // The link works once.
  const again = await mf.dispatchFetch(`https://api.test/oauth/youtube/callback?code=c1&state=${state}`);
  assert.equal(again.status, 400);
  // TikTok has no app secrets here: the bot says which to add.
  await say(mf, "/connect tiktok");
  assert.match(sent(calls, "sendMessage").at(-1).text, /TIKTOK_CLIENT_KEY/);
  await say(mf, "/accounts");
  const list = sent(calls, "sendMessage").at(-1).text;
  assert.match(list, /✅ YouTube: Wardly/);
  assert.match(list, /Instagram: не підключено/);
  assert.match(list, /TikTok: додайте секрети/);
});

test("an approved video goes to YouTube and Instagram by the cron, once, and is reported", async (t) => {
  const { mf, db, calls, setIg } = await localWorker(t);
  await connect(mf, calls, "youtube", "c1");
  await connect(mf, calls, "instagram", "c2");
  const auth = { authorization: "Bearer admin-secret" };
  const created = await mf.dispatchFetch("https://api.test/v1/admin/promo", {
    method: "POST",
    headers: auth,
    body: JSON.stringify({
      id: ID,
      format: "meta",
      topic: "2026-10-12",
      title: "Мета тижня",
      youtube_title: "Мета тижня #shorts",
      caption: "Мета тижня — найбільше перемог:\n1. Wraith King",
      telegram_caption: "Мета тижня"
    })
  });
  const { media_key: key } = await created.json();
  await mf.dispatchFetch(`https://api.test/v1/admin/promo/${ID}/video.mp4`, { method: "PUT", headers: auth, body: new Uint8Array(2048).fill(3) });

  await update(mf, {
    callback_query: {
      id: "cb",
      from: { id: Number(ADMIN) },
      data: `promo:all:${ID}`,
      message: { message_id: 9, chat: { id: Number(ADMIN), type: "private" }, video: { file_id: "F1" } }
    }
  });
  const queued = await db.prepare("SELECT network, status FROM promo_deliveries WHERE post_id = ? ORDER BY network").bind(ID).all();
  assert.deepEqual(queued.results.map((r) => `${r.network}:${r.status}`), ["instagram:queued", "youtube:queued"]);
  const report = sent(calls, "sendMessage").at(-1).text;
  assert.match(report, /Instagram, YouTube: у черзі/);
  assert.match(report, /TikTok: не підключено/);

  const worker = await mf.getWorker();
  await worker.scheduled({ cron: "*/5 * * * *" });
  let rows = await db.prepare("SELECT network, status, url, external_id FROM promo_deliveries WHERE post_id = ? ORDER BY network").bind(ID).all();
  assert.deepEqual(rows.results.map((r) => `${r.network}:${r.status}`), ["instagram:processing", "youtube:published"]);
  assert.equal(rows.results[1].url, "https://youtube.com/shorts/vid1");
  const container = calls.find((c) => c.url.includes("/555/media") && !c.url.includes("publish"));
  assert.equal(new URLSearchParams(container.body).get("video_url"), `https://api.test/m/${key}/video.mp4`);
  assert.equal((await db.prepare("SELECT status FROM promo_posts WHERE id = ?").bind(ID).first()).status, "publishing");

  // Not due yet: nothing happens; once due and finished, published once.
  await worker.scheduled({ cron: "*/5 * * * *" });
  assert.equal(calls.filter((c) => c.url.includes("/cont1")).length, 0);
  await db.prepare("UPDATE promo_deliveries SET next_at = 0 WHERE post_id = ?").bind(ID).run();
  setIg("FINISHED");
  await worker.scheduled({ cron: "*/5 * * * *" });
  await worker.scheduled({ cron: "*/5 * * * *" });
  rows = await db.prepare("SELECT network, status, url FROM promo_deliveries WHERE post_id = ? ORDER BY network").bind(ID).all();
  assert.deepEqual(rows.results.map((r) => `${r.network}:${r.status}`), ["instagram:published", "youtube:published"]);
  assert.equal(calls.filter((c) => c.url.includes("/media_publish")).length, 1);
  assert.equal(calls.filter((c) => c.url.includes("upload.test/s1")).length, 1);
  assert.equal((await db.prepare("SELECT status FROM promo_posts WHERE id = ?").bind(ID).first()).status, "published");
  const final = sent(calls, "sendMessage").at(-1);
  assert.equal(final.reply_to_message_id, 9);
  assert.match(final.text, /✅ Instagram: опубліковано — https:\/\/www.instagram.com\/reel\/r1\//);
  assert.match(final.text, /✅ YouTube: опубліковано — https:\/\/youtube.com\/shorts\/vid1/);
});
