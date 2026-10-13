import assert from "node:assert/strict";
import test from "node:test";

import { NETWORK_CLIENTS, seal, socialConfigured, unseal } from "../src/social.js";

const ENV = {
  ADMIN_TOKEN: "admin-secret",
  YOUTUBE_CLIENT_ID: "yt-id",
  YOUTUBE_CLIENT_SECRET: "yt-secret",
  INSTAGRAM_APP_ID: "ig-id",
  INSTAGRAM_APP_SECRET: "ig-secret",
  TIKTOK_CLIENT_KEY: "tt-key",
  TIKTOK_CLIENT_SECRET: "tt-secret"
};
const BODY = { caption: "Мета тижня — найбільше перемог:\n1. Wraith King", youtube_title: "Мета тижня #shorts", title: "Мета тижня" };

function job(extra = {}) {
  return {
    body: BODY,
    external_id: null,
    media: { url: "https://api.test/m/key/video.mp4", size: 4096, open: async () => new Uint8Array(4096).fill(1) },
    ...extra
  };
}

// fetch stand-in: answers by URL, records what was sent.
function stub(t, routes) {
  const calls = [];
  const original = globalThis.fetch;
  globalThis.fetch = async (url, init = {}) => {
    const href = String(url);
    calls.push({ url: href, method: init.method || "GET", headers: init.headers || {}, body: init.body });
    const route = routes.find(([pattern]) => href.includes(pattern));
    if (!route) return new Response("not found", { status: 404 });
    const [, answer] = route;
    return typeof answer === "function" ? answer(href, init) : Response.json(answer);
  };
  t.after(() => {
    globalThis.fetch = original;
  });
  return calls;
}

test("tokens are sealed with a key from ADMIN_TOKEN and nothing readable is stored", async () => {
  const sealed = await seal(ENV, { access_token: "very-secret-token" });
  assert.ok(sealed.startsWith("v1.") && !sealed.includes("very-secret-token"));
  assert.equal((await unseal(ENV, sealed)).access_token, "very-secret-token");
  await assert.rejects(unseal({ ...ENV, ADMIN_TOKEN: "other" }, sealed));
  await assert.rejects(seal({}, { a: 1 }), /ADMIN_TOKEN/);
});

test("each network needs its own app secrets and asks for the right scopes", () => {
  assert.ok(socialConfigured(ENV, "youtube"));
  assert.ok(!socialConfigured({ YOUTUBE_CLIENT_ID: "x" }, "youtube"));
  const redirect = "https://api.test/oauth/youtube/callback";
  const yt = new URL(NETWORK_CLIENTS.youtube.authUrl(ENV, redirect, "s1"));
  assert.equal(yt.searchParams.get("client_id"), "yt-id");
  assert.equal(yt.searchParams.get("access_type"), "offline");
  assert.match(yt.searchParams.get("scope"), /youtube\.upload/);
  assert.equal(yt.searchParams.get("state"), "s1");
  const ig = new URL(NETWORK_CLIENTS.instagram.authUrl(ENV, redirect, "s2"));
  assert.match(ig.searchParams.get("scope"), /instagram_business_content_publish/);
  const inbox = new URL(NETWORK_CLIENTS.tiktok.authUrl(ENV, redirect, "s3"));
  assert.equal(inbox.searchParams.get("client_key"), "tt-key");
  assert.ok(!inbox.searchParams.get("scope").includes("video.publish"));
  const direct = new URL(NETWORK_CLIENTS.tiktok.authUrl({ ...ENV, TIKTOK_MODE: "direct" }, redirect, "s4"));
  assert.ok(direct.searchParams.get("scope").includes("video.publish"));
});

test("YouTube: the session is kept before upload, authorized, resumed, never started twice", async (t) => {
  let stage = "fresh";
  const calls = stub(t, [
    [
      "upload/youtube/v3/videos",
      () => new Response("{}", { status: 200, headers: { location: "https://upload.test/session-1" } })
    ],
    [
      "upload.test/session-1",
      (url, init) => {
        if (String(init.headers["content-range"] || "").startsWith("bytes */")) {
          if (stage === "partial") return new Response(null, { status: 308, headers: { range: "bytes=0-1023" } });
          if (stage === "done") return Response.json({ id: "vid123", status: { privacyStatus: "public" } });
          if (stage === "lost") return new Response(null, { status: 404 });
          return new Response(null, { status: 308 });
        }
        return Response.json({ id: "vid123", status: { privacyStatus: "private" } });
      }
    ]
  ]);
  const opened = [];
  const media = { url: "u", size: 4096, open: async (offset = 0) => (opened.push(offset), new Uint8Array(4096 - offset)) };
  const account = { access_token: "at" };
  const first = await NETWORK_CLIENTS.youtube.step(ENV, account, job({ media }));
  assert.deepEqual([first.status, first.external_id], ["processing", "upload:https://upload.test/session-1"]);
  const meta = JSON.parse(calls[0].body);
  assert.equal(meta.snippet.title, BODY.youtube_title);
  assert.equal(meta.snippet.categoryId, "20");
  assert.equal(meta.status.selfDeclaredMadeForKids, false);
  assert.equal(opened.length, 0); // no bytes before the session is stored

  const out = await NETWORK_CLIENTS.youtube.step(ENV, account, job({ media, external_id: first.external_id }));
  assert.deepEqual([out.status, out.url], ["published", "https://youtube.com/shorts/vid123"]);
  assert.match(out.detail, /private/);
  const puts = calls.filter((c) => c.method === "PUT");
  assert.ok(puts.every((c) => c.headers.authorization === "Bearer at"));
  assert.deepEqual(opened, [0]);

  stage = "partial"; // 1 KB arrived before the answer was lost: send the rest
  await NETWORK_CLIENTS.youtube.step(ENV, account, job({ media, external_id: first.external_id }));
  assert.equal(opened.at(-1), 1024);
  assert.equal(calls.at(-1).headers["content-range"], "bytes 1024-4095/4096");
  stage = "done"; // finished but the answer was lost: no second upload
  const count = opened.length;
  assert.equal((await NETWORK_CLIENTS.youtube.step(ENV, account, job({ media, external_id: first.external_id }))).status, "published");
  assert.equal(opened.length, count);
  stage = "lost";
  const lost = await NETWORK_CLIENTS.youtube.step(ENV, account, job({ media, external_id: first.external_id }));
  assert.equal(lost.status, "retry");
  assert.equal(lost.restart, true);
});

test("YouTube refreshes an expiring access token, keeps a fresh one", async (t) => {
  stub(t, [["oauth2.googleapis.com/token", { access_token: "new", expires_in: 3600 }]]);
  const now = 1_000_000;
  const kept = await NETWORK_CLIENTS.youtube.fresh(ENV, { access_token: "a", refresh_token: "r", expires_at: now + 3_600_000 }, now);
  assert.equal(kept.changed, false);
  const renewed = await NETWORK_CLIENTS.youtube.fresh(ENV, { access_token: "a", refresh_token: "r", expires_at: now + 1000 }, now);
  assert.equal(renewed.account.access_token, "new");
  assert.equal(renewed.account.refresh_token, "r");
});

test("Instagram: a Reel container, polled until finished, published once", async (t) => {
  let status = "IN_PROGRESS";
  const calls = stub(t, [
    ["/media_publish", { id: "media9" }],
    ["/123/media", { id: "container7" }],
    ["/container7?", () => Response.json({ status_code: status })],
    ["/media9?", { permalink: "https://www.instagram.com/reel/abc/" }]
  ]);
  const account = { access_token: "ig", id: "123", refreshed_at: Date.now() };
  const first = await NETWORK_CLIENTS.instagram.step(ENV, account, job());
  assert.deepEqual([first.status, first.external_id], ["processing", "container7"]);
  const sent = new URLSearchParams(calls[0].body);
  assert.equal(sent.get("media_type"), "REELS");
  assert.equal(sent.get("video_url"), "https://api.test/m/key/video.mp4");
  assert.equal(sent.get("caption"), BODY.caption);
  const waiting = await NETWORK_CLIENTS.instagram.step(ENV, account, job({ external_id: "container7" }));
  assert.equal(waiting.status, "processing");
  status = "FINISHED";
  const done = await NETWORK_CLIENTS.instagram.step(ENV, account, job({ external_id: "container7" }));
  assert.deepEqual([done.status, done.url], ["published", "https://www.instagram.com/reel/abc/"]);
  assert.equal(calls.filter((c) => c.url.includes("/media_publish")).length, 1);
  status = "ERROR";
  assert.equal((await NETWORK_CLIENTS.instagram.step(ENV, account, job({ external_id: "container7" }))).status, "error");
});

test("TikTok inbox: one-chunk upload, then a draft in the app", async (t) => {
  const calls = stub(t, [
    ["/v2/post/publish/inbox/video/init/", { data: { publish_id: "p1", upload_url: "https://tt-upload.test/u1" } }],
    ["tt-upload.test/u1", () => new Response(null, { status: 201 })],
    ["/v2/post/publish/status/fetch/", { data: { status: "SEND_TO_USER_INBOX" } }]
  ]);
  const account = { access_token: "tt" };
  const first = await NETWORK_CLIENTS.tiktok.step(ENV, account, job());
  assert.deepEqual([first.status, first.external_id], ["processing", "p1"]);
  const init = JSON.parse(calls[0].body);
  assert.deepEqual(init.source_info, { source: "FILE_UPLOAD", video_size: 4096, chunk_size: 4096, total_chunk_count: 1 });
  assert.equal(calls[1].headers["content-range"], "bytes 0-4095/4096");
  const done = await NETWORK_CLIENTS.tiktok.step(ENV, account, job({ external_id: "p1" }));
  assert.equal(done.status, "draft");
});

test("TikTok status errors end or retry the delivery, never poll forever", async (t) => {
  let code = 401;
  stub(t, [["/v2/post/publish/status/fetch/", () => Response.json({ error: { code: "access_token_invalid" } }, { status: code })]]);
  assert.equal((await NETWORK_CLIENTS.tiktok.step(ENV, { access_token: "tt" }, job({ external_id: "p1" }))).status, "error");
  code = 429;
  assert.equal((await NETWORK_CLIENTS.tiktok.step(ENV, { access_token: "tt" }, job({ external_id: "p1" }))).status, "retry");
});

test("TikTok direct: the most public privacy the account allows", async (t) => {
  const calls = stub(t, [
    ["/creator_info/query/", { data: { privacy_level_options: ["FOLLOWER_OF_CREATOR", "SELF_ONLY"] } }],
    ["/v2/post/publish/video/init/", { data: { publish_id: "p2", upload_url: "https://tt-upload.test/u2" } }],
    ["tt-upload.test/u2", () => new Response(null, { status: 201 })],
    ["/status/fetch/", { data: { status: "PUBLISH_COMPLETE", publicaly_available_post_id: [7001] } }]
  ]);
  const env = { ...ENV, TIKTOK_MODE: "direct" };
  await NETWORK_CLIENTS.tiktok.step(env, { access_token: "tt" }, job());
  const init = JSON.parse(calls.find((c) => c.url.includes("/video/init/")).body);
  assert.equal(init.post_info.privacy_level, "FOLLOWER_OF_CREATOR");
  assert.equal(init.post_info.title, BODY.caption);
  const done = await NETWORK_CLIENTS.tiktok.step(env, { access_token: "tt" }, job({ external_id: "p2" }));
  assert.deepEqual([done.status, done.url], ["published", "https://www.tiktok.com/video/7001"]);
});

test("numbers from each network", async (t) => {
  stub(t, [
    ["youtube/v3/videos?part=statistics", { items: [{ id: "v1", statistics: { viewCount: "120", likeCount: "9", commentCount: "2" } }] }],
    [
      "/m1/insights",
      { data: [{ name: "views", values: [{ value: 800 }] }, { name: "likes", values: [{ value: 40 }] }, { name: "shares", total_value: { value: 3 } }] }
    ],
    [
      "/v2/video/list/",
      { data: { videos: [{ id: "x9", video_description: "Мета тижня — найбільше перемог: ...", view_count: 500, like_count: 20, share_url: "https://tt/x9" }] } }
    ]
  ]);
  const yt = await NETWORK_CLIENTS.youtube.stats(ENV, { access_token: "a" }, [{ external_id: "v1" }]);
  assert.deepEqual(yt[0], { external_id: "v1", views: 120, likes: 9, comments: 2, shares: 0 });
  const ig = await NETWORK_CLIENTS.instagram.stats(ENV, { access_token: "a" }, [{ external_id: "m1" }]);
  assert.deepEqual(ig[0], { external_id: "m1", views: 800, likes: 40, comments: 0, shares: 3 });
  const tt = await NETWORK_CLIENTS.tiktok.stats(ENV, { access_token: "a" }, [{ external_id: "p1", caption: BODY.caption }]);
  assert.equal(tt[0].views, 500);
  assert.equal(tt[0].url, "https://tt/x9");
});
