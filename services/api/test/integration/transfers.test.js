// Actual Worker, workerd D1 and all migrations. No SQL string-pattern fake.
import assert from "node:assert/strict";
import { readdir, readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { test } from "node:test";
import { Miniflare, convertV4MiniflareOptions } from "miniflare";
import { claimTransfer } from "../../src/index.js";

const ROOT = fileURLToPath(new URL("../..", import.meta.url));
const SOURCE = path.join(ROOT, "src");
const INSTALL = "12345678-1234-4123-8123-123456789abc";

async function localWorker(t) {
  const paths = (await readdir(SOURCE, { recursive: true })).filter((name) => name.endsWith(".js") && name !== "index.js");
  const modules = ["index.js", ...paths].map((name) => ({ type: "ESModule", path: path.join(SOURCE, name) }));
  const mf = new Miniflare(convertV4MiniflareOptions({
    modules,
    modulesRoot: ROOT,
    compatibilityDate: "2026-09-20",
    d1Databases: { DB: "wardly-transfer-integration" },
    r2Buckets: ["REPORTS"],
  }));
  t.after(() => mf.dispose());
  const db = await mf.getD1Database("DB");
  // Current migrations are DDL statements without triggers/string semicolons.
  // Execute every statement against D1, not a fixture schema approximation.
  for (const file of (await readdir(path.join(ROOT, "migrations"))).filter((name) => name.endsWith(".sql")).sort()) {
    const sql = await readFile(path.join(ROOT, "migrations", file), "utf8");
    for (const statement of sql.replace(/--[^\n]*/g, "").split(";").map((part) => part.trim()).filter(Boolean)) {
      await db.prepare(statement).run();
    }
  }
  return { mf, db };
}

function sealed(marker) {
  const bytes = new Uint8Array(64);
  bytes.set([0x57, 0x44, 0x54, 0x31]);
  bytes.fill(marker, 4);
  return bytes;
}

function put(mf, id, marker = 1, install = INSTALL) {
  return mf.dispatchFetch(`https://local.test/v1/transfer/${id}`, {
    method: "PUT",
    headers: { "content-type": "application/octet-stream", "x-install-id": install, "cf-connecting-ip": "198.51.100.10" },
    body: sealed(marker),
  });
}

function claim(mf, id) {
  return mf.dispatchFetch(`https://local.test/v1/transfer/${id}/claim`, {
    method: "POST", headers: { "cf-connecting-ip": "198.51.100.11" },
  });
}

test("real D1 permits only three concurrent downloads of the stored ciphertext", async (t) => {
  const { mf, db } = await localWorker(t);
  assert.equal((await put(mf, "AB2C", 7)).status, 201);
  const responses = await Promise.all(Array.from({ length: 12 }, () => claim(mf, "AB2C")));
  assert.equal(responses.filter((response) => response.status === 200).length, 3);
  assert.equal(responses.filter((response) => response.status === 404).length, 9);
  for (const response of responses.filter((item) => item.status === 200)) {
    assert.deepEqual(new Uint8Array(await response.arrayBuffer()), sealed(7));
    assert.equal(response.headers.get("cache-control"), "no-store");
  }
  assert.equal(await db.prepare("SELECT id FROM transfers WHERE id = ?").bind("AB2C").first(), null);
  assert.equal((await claim(mf, "AB2C")).status, 404);
});

test("real D1 concurrent id collisions keep exactly one owner's upload", async (t) => {
  const { mf, db } = await localWorker(t);
  const responses = await Promise.all(Array.from({ length: 8 }, (_, index) => put(mf, "EF3G", index + 1, `installation-${index}`)));
  const winner = responses.findIndex((response) => response.status === 201);
  assert.ok(winner >= 0);
  assert.equal(responses.filter((response) => response.status === 201).length, 1);
  assert.equal(responses.filter((response) => response.status === 409).length, 7);
  const row = await db.prepare("SELECT body, install_id FROM transfers WHERE id = ?").bind("EF3G").first();
  assert.equal(row.install_id, `installation-${winner}`);
  assert.deepEqual(new Uint8Array(row.body), sealed(winner + 1));
  const unrelated = await mf.dispatchFetch(`https://local.test/v1/device/installation-other`, { method: "DELETE" });
  assert.equal(unrelated.status, 200);
  assert.ok(await db.prepare("SELECT id FROM transfers WHERE id = ?").bind("EF3G").first());
  assert.equal((await mf.dispatchFetch(`https://local.test/v1/device/installation-${winner}`, { method: "DELETE" })).status, 200);
  assert.equal((await claim(mf, "EF3G")).status, 404);
});

for (const phase of ["expired", "final"]) {
  test(`delayed ${phase} claim cleanup preserves a freshly reused id on real D1`, async (t) => {
    const { mf, db } = await localWorker(t);
    assert.equal((await put(mf, "CD3E", 1)).status, 201);
    if (phase === "expired") {
      await db.prepare("UPDATE transfers SET expires_at = ? WHERE id = ?").bind(Date.now() - 1000, "CD3E").run();
    } else {
      assert.equal((await claim(mf, "CD3E")).status, 200);
      assert.equal((await claim(mf, "CD3E")).status, 200);
    }
    let announce;
    let resume;
    const waiting = new Promise((resolve) => { announce = resolve; });
    const released = new Promise((resolve) => { resume = resolve; });
    // Pause the real handler at its external D1 cleanup boundary. Every query,
    // including the held one, still runs on the real D1 binding unchanged.
    const env = { DB: { prepare(sql) {
      const statement = db.prepare(sql);
      if (!sql.startsWith("DELETE FROM transfers WHERE id")) return statement;
      return { bind(...args) {
        const bound = statement.bind(...args);
        return { async run() { announce(); await released; return bound.run(); } };
      } };
    } } };
    const oldClaim = claimTransfer(new Request("https://local.test/v1/transfer/CD3E/claim", { method: "POST" }), "CD3E", env);
    let timeout;
    try {
      await Promise.race([waiting, new Promise((_, reject) => {
        timeout = setTimeout(() => reject(new Error("Old claim did not reach cleanup")), 5000);
      })]);
      if (phase === "final") {
        // A concurrent failed fourth claim cleans the exhausted old row.
        assert.equal((await claim(mf, "CD3E")).status, 404);
      }
      assert.equal((await put(mf, "CD3E", 9)).status, 201);
    } finally {
      clearTimeout(timeout);
      resume();
    }
    const oldResponse = await oldClaim;
    assert.equal(oldResponse.status, phase === "expired" ? 404 : 200);
    if (phase === "final") assert.deepEqual(new Uint8Array(await oldResponse.arrayBuffer()), sealed(1));
    const fresh = await claim(mf, "CD3E");
    assert.equal(fresh.status, 200);
    assert.deepEqual(new Uint8Array(await fresh.arrayBuffer()), sealed(9));
  });
}
