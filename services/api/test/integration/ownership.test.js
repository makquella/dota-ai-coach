// Deletion capabilities on the actual Worker and workerd D1 with every
// migration: the device key's hash owns uploads, rows of older launchers keep
// the install-id delete, and a transfer with a delete token needs that token.
import assert from "node:assert/strict";
import { readdir, readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { test } from "node:test";
import { Miniflare, convertV4MiniflareOptions } from "miniflare";

const ROOT = fileURLToPath(new URL("../..", import.meta.url));
const SOURCE = path.join(ROOT, "src");
const MINE = "12345678-1234-4123-8123-123456789abc";
const OTHER = "87654321-4321-4321-8321-cba987654321";
const KEY = "a".repeat(64);
const WRONG = "b".repeat(64);

async function localWorker(t) {
  const paths = (await readdir(SOURCE, { recursive: true })).filter((name) => name.endsWith(".js") && name !== "index.js");
  const modules = ["index.js", ...paths].map((name) => ({ type: "ESModule", path: path.join(SOURCE, name) }));
  const mf = new Miniflare(convertV4MiniflareOptions({
    modules,
    modulesRoot: ROOT,
    compatibilityDate: "2026-09-20",
    d1Databases: { DB: "wardly-ownership-integration" },
    r2Buckets: ["REPORTS"],
  }));
  t.after(() => mf.dispose());
  const db = await mf.getD1Database("DB");
  for (const file of (await readdir(path.join(ROOT, "migrations"))).filter((name) => name.endsWith(".sql")).sort()) {
    const sql = await readFile(path.join(ROOT, "migrations", file), "utf8");
    for (const statement of sql.replace(/--[^\n]*/g, "").split(";").map((part) => part.trim()).filter(Boolean)) {
      await db.prepare(statement).run();
    }
  }
  return { mf, db };
}

let ip = 0;
function headers(key, extra = {}) {
  ip += 1;
  return { "content-type": "application/json", "cf-connecting-ip": `198.51.100.${ip}`, ...(key ? { "x-device-key": key } : {}), ...extra };
}

function report(mf, install, key) {
  return mf.dispatchFetch("https://local.test/v1/report", {
    method: "POST",
    headers: headers(key),
    body: JSON.stringify({ install_id: install, version: "0.53.54", os: "win32", lang: "ru", note: "", text: "ERROR sync failed" }),
  });
}

function share(mf, install, key) {
  return mf.dispatchFetch("https://local.test/v1/share", {
    method: "POST",
    headers: headers(key),
    body: JSON.stringify({
      install_id: install,
      version: "0.53.54",
      review: { lang: "ru", hero: "Juggernaut", hero_key: "juggernaut", win: true, duration: 2000, played_on: "2026-10-09", score: 70, grade: "B", role: "кор", parsed: true, stats: {}, sections: [], strengths: [], improvements: [], deaths: { count: 2 } },
    }),
  });
}

function profile(mf, id, install, key, token = "0123456789abcdef0123456789abcdef") {
  return mf.dispatchFetch(`https://local.test/v1/profile/${id}`, {
    method: "PUT",
    headers: headers(key, { "x-profile-token": token }),
    body: JSON.stringify({ install_id: install, version: "0.53.54", profile: { lang: "ru", name: "player", level: 3, achievements: [], stats: { app_games: 1, app_winrate: null }, equipped: {} } }),
  });
}

function transfer(mf, id, install, key, deleteToken) {
  const body = new Uint8Array(64);
  body.set([0x57, 0x44, 0x54, 0x31]);
  return mf.dispatchFetch(`https://local.test/v1/transfer/${id}`, {
    method: "PUT",
    headers: { ...headers(key, deleteToken ? { "x-delete-token": deleteToken } : {}), "content-type": "application/octet-stream", "x-install-id": install },
    body,
  });
}

function deleteDevice(mf, install, key) {
  return mf.dispatchFetch(`https://local.test/v1/device/${install}`, { method: "DELETE", headers: headers(key) });
}

async function counts(db) {
  const out = {};
  for (const table of ["reports", "shares", "profiles", "transfers"]) {
    const { results } = await db.prepare(`SELECT install_id, owner_hash IS NOT NULL AS owned FROM ${table} ORDER BY install_id, owned`).all();
    out[table] = results.map((row) => `${row.install_id === MINE ? "mine" : "other"}:${row.owned ? "owned" : "legacy"}`);
  }
  return out;
}

test("the device delete takes owned rows only with the key; legacy rows keep the install-id delete", async (t) => {
  const { mf, db } = await localWorker(t);
  for (const [install, key] of [[MINE, KEY], [MINE, null], [OTHER, KEY.replace(/a/g, "c")]]) {
    assert.equal((await report(mf, install, key)).status, 201);
    assert.equal((await share(mf, install, key)).status, 201);
  }
  assert.equal((await profile(mf, "4k7p9qx2", MINE, KEY)).status, 201);
  assert.equal((await profile(mf, "5m8r2wz3", MINE, null)).status, 201);
  assert.equal((await transfer(mf, "AB2C", MINE, KEY)).status, 201);
  assert.equal((await transfer(mf, "CD3E", MINE, null)).status, 201);
  const owner = await db.prepare("SELECT owner_hash FROM reports WHERE owner_hash IS NOT NULL LIMIT 1").first();
  assert.match(owner.owner_hash, /^[a-f0-9]{32,64}$/);
  assert.notEqual(owner.owner_hash, KEY);

  // An older launcher (no key) or someone who only knows the install id.
  assert.equal((await deleteDevice(mf, MINE, null)).status, 200);
  assert.deepEqual(await counts(db), {
    reports: ["mine:owned", "other:owned"],
    shares: ["mine:owned", "other:owned"],
    profiles: ["mine:owned"],
    transfers: ["mine:owned"],
  });
  // A wrong key removes nothing more.
  await deleteDevice(mf, MINE, WRONG);
  assert.equal((await counts(db)).reports.length, 2);
  // The key: everything it uploaded; the other installation is untouched.
  assert.deepEqual(await (await deleteDevice(mf, MINE, KEY)).json(), { ok: true, deleted: 1 });
  assert.deepEqual(await counts(db), { reports: ["other:owned"], shares: ["other:owned"], profiles: [], transfers: [] });
});

test("a card published before device keys gets its owner on the next publish", async (t) => {
  const { mf, db } = await localWorker(t);
  assert.equal((await profile(mf, "4k7p9qx2", MINE, null)).status, 201);
  assert.equal((await profile(mf, "4k7p9qx2", MINE, KEY)).status, 200);
  assert.equal((await profile(mf, "4k7p9qx2", MINE, WRONG)).status, 200);
  const row = await db.prepare("SELECT owner_hash FROM profiles WHERE id = '4k7p9qx2'").first();
  assert.ok(row.owner_hash);
  await deleteDevice(mf, MINE, WRONG);
  assert.equal((await counts(db)).profiles.length, 1, "the first owner stays");
  await deleteDevice(mf, MINE, KEY);
  assert.equal((await counts(db)).profiles.length, 0);
});

test("a transfer with a delete token is cancelled only with it; an old one by its id", async (t) => {
  const { mf, db } = await localWorker(t);
  const token = "d".repeat(64);
  assert.equal((await transfer(mf, "AB2C", MINE, KEY, token)).status, 201);
  const cancel = (id, value) => mf.dispatchFetch(`https://local.test/v1/transfer/${id}`, {
    method: "DELETE",
    headers: headers(null, value ? { "x-delete-token": value } : {}),
  });
  assert.equal((await cancel("AB2C")).status, 403);
  assert.equal((await cancel("AB2C", "e".repeat(64))).status, 403);
  assert.ok(await db.prepare("SELECT id FROM transfers WHERE id = 'AB2C'").first());
  const stored = await db.prepare("SELECT delete_hash FROM transfers WHERE id = 'AB2C'").first();
  assert.notEqual(stored.delete_hash, token);
  assert.equal((await cancel("AB2C", token)).status, 200);
  assert.equal(await db.prepare("SELECT id FROM transfers WHERE id = 'AB2C'").first(), null);

  assert.equal((await transfer(mf, "CD3E", MINE, null)).status, 201);
  assert.equal((await cancel("CD3E")).status, 200);
  assert.equal(await db.prepare("SELECT id FROM transfers WHERE id = 'CD3E'").first(), null);
});
