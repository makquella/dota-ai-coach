import assert from "node:assert/strict";
import test from "node:test";

import worker, { cleanup, config } from "../src/index.js";
import { RATE_PER_HOUR, redact, reportId, summarize, validateReport } from "../src/report.js";

// In-memory stand-ins for the D1 and R2 bindings, for the statements the Worker uses.
function fakeEnv(vars = {}) {
  const reports = [];
  const rate = new Map();
  const objects = new Map();
  const DB = {
    prepare(sql) {
      let args = [];
      const stmt = {
        bind(...values) {
          args = values;
          return stmt;
        },
        async first() {
          if (sql.startsWith("INSERT INTO rate")) {
            const key = `${args[0]}|${args[1]}`;
            rate.set(key, (rate.get(key) || 0) + 1);
            return { count: rate.get(key) };
          }
          if (sql.startsWith("SELECT r2_key FROM reports WHERE id")) {
            return reports.find((r) => r.id === args[0]) || null;
          }
          throw new Error(`unexpected first(): ${sql}`);
        },
        async all() {
          if (sql.startsWith("SELECT r2_key FROM reports WHERE install_id")) {
            return { results: reports.filter((r) => r.install_id === args[0]) };
          }
          if (sql.startsWith("SELECT id, r2_key FROM reports WHERE created_at <")) {
            const limit = Number(sql.match(/LIMIT (\d+)/)[1]);
            return { results: reports.filter((r) => r.created_at < args[0]).slice(0, limit) };
          }
          if (sql.startsWith("SELECT id, created_at")) {
            return { results: [...reports].reverse() };
          }
          throw new Error(`unexpected all(): ${sql}`);
        },
        async run() {
          if (sql.startsWith("INSERT INTO reports")) {
            const [id, created_at, install_id, version, os, lang, size, summary, r2_key] = args;
            reports.push({ id, created_at, install_id, version, os, lang, size, summary, r2_key });
          } else if (sql.startsWith("DELETE FROM reports WHERE install_id")) {
            reports.splice(0, reports.length, ...reports.filter((r) => r.install_id !== args[0]));
          } else if (sql.startsWith("DELETE FROM reports WHERE id IN")) {
            reports.splice(0, reports.length, ...reports.filter((r) => !args.includes(r.id)));
          } else if (sql.startsWith("DELETE FROM rate")) {
            for (const key of [...rate.keys()]) {
              if (Number(key.split("|")[1]) < args[0]) rate.delete(key);
            }
          } else {
            throw new Error(`unexpected run(): ${sql}`);
          }
          return { success: true };
        }
      };
      return stmt;
    }
  };
  const REPORTS = {
    async put(key, body, options) {
      objects.set(key, { body, options });
    },
    async get(key) {
      const object = objects.get(key);
      return object ? { body: new Blob([object.body]).stream() } : null;
    },
    async delete(keys) {
      for (const key of [].concat(keys)) objects.delete(key);
    }
  };
  return { env: { DB, REPORTS, ...vars }, reports, objects };
}

const ctx = { waitUntil: (promise) => promise };

function upload(body, ip = "203.0.113.5") {
  return new Request("https://api.example/v1/report", {
    method: "POST",
    headers: { "content-type": "application/json", "cf-connecting-ip": ip },
    body: typeof body === "string" ? body : JSON.stringify(body)
  });
}

const REPORT = {
  install_id: "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
  version: "0.2.1",
  os: "win32 10.0.22631",
  lang: "ru",
  note: "Оверлей не видно",
  text: '===== Settings =====\n{"api_key": "gsk_abcdefghijklmnopqrstu"}\nERROR sync failed\n'
};

test("keys never reach storage", () => {
  const text = [
    '{"apiKey": "secret-value"}',
    "Authorization: Bearer abcdefghijklmnop",
    "GET /players/1?api_key=0000aaaa-1111-bbbb",
    "AIzaSyA1234567890abcdefghijk",
    "AQ.FakeStudioKey000000-abcdefgh"
  ].join("\n");
  const clean = redact(text);
  for (const secret of ["secret-value", "abcdefghijklmnop", "0000aaaa", "AIzaSyA123", "FakeStudioKey"]) {
    assert.ok(!clean.includes(secret), secret);
  }
});

test("uploads are checked before anything is stored", () => {
  assert.equal(validateReport(null).code, "bad_json");
  assert.equal(validateReport({ install_id: "x", text: "a" }).code, "bad_install_id");
  assert.equal(validateReport({ install_id: REPORT.install_id, text: "  " }).code, "empty_report");
  assert.equal(validateReport({ install_id: REPORT.install_id, text: "a".repeat(1_500_001) }).status, 413);
  const ok = validateReport({ ...REPORT, extra: "dropped", note: "n".repeat(5000) });
  assert.equal(ok.ok, true);
  assert.equal(ok.report.note.length, 1000);
  assert.ok(!("extra" in ok.report));
  assert.match(reportId(new Uint8Array([0, 1, 2, 3, 4, 31])), /^R-[2-9A-HJ-NP-Z]{6}$/);
  assert.equal(summarize({ note: "", text: "===== x =====\nok\nERROR sync failed: timeout\n" }), "ERROR sync failed: timeout");
});

test("a report is stored, indexed and answered with its number", async () => {
  const { env, reports, objects } = fakeEnv();
  const response = await worker.fetch(upload(REPORT), env, ctx);
  assert.equal(response.status, 201);
  const answer = await response.json();
  assert.match(answer.id, /^R-[A-Z0-9]{6}$/);
  assert.equal(reports.length, 1);
  assert.equal(reports[0].summary, "Оверлей не видно");
  const [key] = objects.keys();
  assert.match(key, /^reports\/\d{4}\/\d{2}\/R-[A-Z0-9]{6}\.txt\.gz$/);
  const stored = await new Response(
    new Blob([objects.get(key).body]).stream().pipeThrough(new DecompressionStream("gzip"))
  ).text();
  assert.ok(stored.startsWith("Player note:\nОверлей не видно"));
  assert.ok(stored.includes('"api_key": "[redacted]"') && !stored.includes("gsk_"));
});

test("bad bodies, rate limits and the kill switch", async () => {
  const { env } = fakeEnv();
  assert.equal((await worker.fetch(upload("not json"), env, ctx)).status, 400);
  for (let i = 0; i < RATE_PER_HOUR.install; i += 1) {
    assert.equal((await worker.fetch(upload(REPORT), env, ctx)).status, 201);
  }
  const limited = await worker.fetch(upload(REPORT), env, ctx);
  assert.equal(limited.status, 429);
  assert.equal((await limited.json()).code, "rate_limited");

  const off = fakeEnv({ REPORTS_ENABLED: "false" });
  assert.equal(config(off.env).reports, false);
  assert.equal((await worker.fetch(upload(REPORT), off.env, ctx)).status, 503);
  const answer = await (await worker.fetch(new Request("https://api.example/v1/config"), off.env, ctx)).json();
  assert.deepEqual(answer, { reports: false, stats: false, sessions: false, retention_days: 180 });
});

test("a player can delete their reports; old ones expire", async () => {
  const { env, reports, objects } = fakeEnv();
  await worker.fetch(upload(REPORT), env, ctx);
  await worker.fetch(upload({ ...REPORT, install_id: "other-install-1" }), env, ctx);
  const gone = await worker.fetch(
    new Request(`https://api.example/v1/device/${REPORT.install_id}`, { method: "DELETE" }),
    env,
    ctx
  );
  assert.deepEqual(await gone.json(), { ok: true, deleted: 1 });
  assert.equal(reports.length, 1);
  assert.equal(objects.size, 1);
  // 181 days later the last one is removed by the daily cleanup.
  assert.equal(await cleanup(env, Date.now() + 181 * 24 * 3_600_000), 1);
  assert.equal(reports.length, 0);
  assert.equal(objects.size, 0);
});

test("admin endpoints need the token and hide otherwise", async () => {
  const { env } = fakeEnv({ ADMIN_TOKEN: "t0ken" });
  const { id } = await (await worker.fetch(upload(REPORT), env, ctx)).json();
  const hidden = await worker.fetch(new Request("https://api.example/v1/admin/reports"), env, ctx);
  assert.equal(hidden.status, 404);
  const auth = { headers: { authorization: "Bearer t0ken" } };
  const list = await (await worker.fetch(new Request("https://api.example/v1/admin/reports", auth), env, ctx)).json();
  assert.equal(list.reports[0].id, id);
  const text = await (await worker.fetch(new Request(`https://api.example/v1/admin/report/${id}`, auth), env, ctx)).text();
  assert.ok(text.includes("ERROR sync failed"));
  const noToken = fakeEnv();
  assert.equal((await worker.fetch(new Request("https://api.example/v1/admin/reports", auth), noToken.env, ctx)).status, 404);
});

test("cleanup removes every expired report, object and row together", async () => {
  const { env, reports, objects } = fakeEnv();
  for (let i = 0; i < 250; i += 1) {
    const id = `R-OLD${String(i).padStart(3, "0")}`;
    reports.push({ id, created_at: 1, install_id: "old-install-1", r2_key: `reports/2026/01/${id}.txt.gz` });
    objects.set(`reports/2026/01/${id}.txt.gz`, { body: new Uint8Array() });
  }
  await worker.fetch(upload(REPORT), env, ctx);
  assert.equal(await cleanup(env, Date.now()), 250);
  assert.equal(reports.length, 1);
  assert.equal(objects.size, 1);
  assert.deepEqual([...objects.keys()], [reports[0].r2_key]);
});
