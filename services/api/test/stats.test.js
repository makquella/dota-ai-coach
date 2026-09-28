import assert from "node:assert/strict";
import test from "node:test";

import worker, { cleanup, config, sendWeeklyStats } from "../src/index.js";
import { aggregateStats, isoDay, validateStats } from "../src/stats.js";

const DAY = 24 * 3_600_000;
// The Worker checks the day against the real clock, so the tests run on it too.
const NOW = Date.now();
// The next Monday (UTC) on or after today: the weekly note covers the 7 days before it.
const MONDAY = NOW + ((8 - new Date(NOW).getUTCDay()) % 7) * DAY;
const INSTALL = "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d";

const STATS = {
  install_id: INSTALL,
  day: isoDay(NOW - DAY),
  version: "0.17.0",
  os: "win32",
  lang: "ru",
  usage: {
    matches: 3,
    with_advice: 2,
    advice: { LOW_HP_WARNING: 5, LANING_FARM_CHECK: 2, "bad kind": 7 },
    ignored: { LOW_HP_WARNING: 2 }
  },
  settings: { overlay: true, voice: "urgent", frequency: "normal", role: "auto", map_hints: true, discord: false, nickname: "x" },
  ai: "ready",
  opendota_key: false,
  fullscreen: false,
  sync_error: null,
  // Nothing outside the allowlist is kept.
  steam_id: "76561198000000000",
  hero: "Juggernaut",
  match_id: 8843382732
};

// A D1 stand-in for the statements the statistics use (and the ones the device
// delete and the cleanup run on the other tables).
function fakeEnv(vars = {}) {
  const daily = new Map();
  const rate = new Map();
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
          throw new Error(`unexpected first(): ${sql}`);
        },
        async all() {
          if (sql.startsWith("SELECT install_hash, day, version, body FROM daily_stats WHERE day >=")) {
            return { results: [...daily.values()].filter((r) => r.day >= args[0]) };
          }
          if (sql.startsWith("SELECT r2_key FROM reports") || sql.startsWith("SELECT id, r2_key FROM reports")) {
            return { results: [] };
          }
          throw new Error(`unexpected all(): ${sql}`);
        },
        async run() {
          if (sql.startsWith("INSERT INTO daily_stats")) {
            const [install_hash, day, created_at, version, body] = args;
            daily.set(`${install_hash}|${day}`, { install_hash, day, created_at, version, body });
          } else if (sql.startsWith("DELETE FROM daily_stats WHERE install_hash")) {
            for (const [key, row] of [...daily]) if (row.install_hash === args[0]) daily.delete(key);
          } else if (sql.startsWith("DELETE FROM daily_stats WHERE day <")) {
            for (const [key, row] of [...daily]) if (row.day < args[0]) daily.delete(key);
          } else if (!sql.startsWith("DELETE FROM")) {
            throw new Error(`unexpected run(): ${sql}`);
          }
          return { success: true };
        }
      };
      return stmt;
    }
  };
  return { env: { DB, ...vars }, daily };
}

const ctx = { waitUntil: (promise) => promise };

function post(body, ip = "203.0.113.9") {
  return new Request("https://api.example/v1/stats", {
    method: "POST",
    headers: { "content-type": "application/json", "cf-connecting-ip": ip },
    body: typeof body === "string" ? body : JSON.stringify(body)
  });
}

test("only allowlisted fields and counts are kept", () => {
  const checked = validateStats(STATS, NOW);
  assert.equal(checked.ok, true);
  assert.deepEqual(checked.row, {
    os: "win32",
    lang: "ru",
    matches: 3,
    with_advice: 2,
    advice: { LOW_HP_WARNING: 5, LANING_FARM_CHECK: 2 },
    ignored: { LOW_HP_WARNING: 2 },
    settings: { voice: "urgent", frequency: "normal", role: "auto", overlay: true, map_hints: true, discord: false },
    ai: "ready",
    opendota_key: false,
    fullscreen: false,
    sync_error: null
  });
  const stored = JSON.stringify(checked.row);
  for (const secret of ["76561198", "Juggernaut", "8843382732", "nickname", INSTALL]) {
    assert.ok(!stored.includes(secret), secret);
  }
  assert.equal(validateStats({ ...STATS, day: isoDay(NOW + 3 * DAY) }, NOW).code, "bad_day");
  assert.equal(validateStats({ ...STATS, day: isoDay(NOW - 10 * DAY) }, NOW).code, "bad_day");
  assert.equal(validateStats({ ...STATS, install_id: "x" }, NOW).code, "bad_install_id");
  assert.equal(validateStats({ ...STATS, version: "dev" }, NOW).code, "bad_version");
  assert.equal(validateStats({ ...STATS, usage: { matches: -1, advice: { A_B: 1e9 } } }, NOW).row.matches, 0);
});

test("one row per installation and day; the device delete and the cleanup remove it", async () => {
  const { env, daily } = fakeEnv();
  const first = await worker.fetch(post(STATS), env, ctx);
  assert.equal(first.status, 201);
  // Sent again (a retry): replaced, not added.
  await worker.fetch(post({ ...STATS, usage: { ...STATS.usage, matches: 4 } }), env, ctx);
  assert.equal(daily.size, 1);
  const [row] = daily.values();
  assert.equal(JSON.parse(row.body).matches, 4);
  assert.notEqual(row.install_hash, INSTALL);
  assert.ok(!row.body.includes(INSTALL));

  await worker.fetch(new Request(`https://api.example/v1/device/${INSTALL}`, { method: "DELETE" }), env, ctx);
  assert.equal(daily.size, 0);

  await worker.fetch(post(STATS), env, ctx);
  await cleanup(env, NOW + 366 * DAY);
  assert.equal(daily.size, 0);
});

test("the kill switch, bad bodies and the rate limit", async () => {
  const { env } = fakeEnv();
  assert.equal(config({ STATS_ENABLED: "false" }).stats, false);
  assert.equal((await worker.fetch(post(STATS), { ...env, STATS_ENABLED: "false" }, ctx)).status, 503);
  assert.equal((await worker.fetch(post("{"), env, ctx)).status, 400);
  assert.equal((await worker.fetch(post("x".repeat(20_000)), env, ctx)).status, 413);
  const statuses = [];
  for (let i = 0; i < 7; i += 1) {
    statuses.push((await worker.fetch(post(STATS), env, ctx)).status);
  }
  assert.deepEqual(statuses, [201, 201, 201, 201, 201, 201, 429]);
});

test("the admin summary and the weekly note", async () => {
  const { env } = fakeEnv({ ADMIN_TOKEN: "t0ken" });
  await worker.fetch(post(STATS), env, ctx);
  await worker.fetch(post({ ...STATS, install_id: "other-install-1", lang: "en", usage: { matches: 1, advice: { LOW_HP_WARNING: 1 } } }, "203.0.113.10"), env, ctx);
  assert.equal((await worker.fetch(new Request("https://api.example/v1/admin/stats"), env, ctx)).status, 404);
  const answer = await (
    await worker.fetch(new Request("https://api.example/v1/admin/stats?days=7", { headers: { authorization: "Bearer t0ken" } }), env, ctx)
  ).json();
  assert.equal(answer.stats.devices, 2);
  assert.equal(answer.stats.matches, 4);
  assert.deepEqual(answer.stats.advice, { LOW_HP_WARNING: 6, LANING_FARM_CHECK: 2 });
  assert.deepEqual(answer.stats.ignored_share, { LOW_HP_WARNING: 33 });
  assert.deepEqual(answer.stats.langs, { ru: 1, en: 1 });

  const sent = [];
  const realFetch = globalThis.fetch;
  globalThis.fetch = async (url, init) => {
    sent.push({ url, body: JSON.parse(init.body) });
    return new Response("{}", { status: 200 });
  };
  try {
    const telegram = { ...env, TELEGRAM_BOT_TOKEN: "bot", TELEGRAM_CHAT_ID: "1" };
    assert.equal(await sendWeeklyStats(telegram, MONDAY), true);
    assert.equal(await sendWeeklyStats(telegram, MONDAY + DAY), false, "Mondays only");
    assert.equal(await sendWeeklyStats(env, MONDAY), false, "no Telegram secrets");
  } finally {
    globalThis.fetch = realFetch;
  }
  assert.equal(sent.length, 1);
  assert.ok(sent[0].body.text.includes("Devices: 2"));
  assert.ok(sent[0].body.text.includes("LOW_HP_WARNING 6"));
});

test("aggregate skips broken rows", () => {
  assert.equal(aggregateStats([{ install_hash: "a", day: "2026-09-27", version: "0.17.0", body: "{" }]).rows, 0);
});
