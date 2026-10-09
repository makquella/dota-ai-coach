import assert from "node:assert/strict";
import test from "node:test";

import worker, { cleanup, config, versionAtLeast } from "../src/index.js";
import { RATE_PER_HOUR, redact, reportId, summarize, validateReport } from "../src/report.js";
import { siteHome } from "../src/share.js";
import { readFileSync } from "node:fs";
import vm from "node:vm";
import { ADMIN_JS } from "../src/admin-page.js";
import { renderProfilePage } from "../src/profile.js";

// In-memory stand-ins for the D1 and R2 bindings, for the statements the Worker uses.
function fakeEnv(vars = {}, { r2 = true } = {}) {
  const reports = [];
  const shares = [];
  const transfers = [];
  const profiles = [];
  const daily = new Map();
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
          if (sql.startsWith("SELECT r2_key, body FROM reports WHERE id")) {
            return reports.find((r) => r.id === args[0]) || null;
          }
          if (sql.startsWith("SELECT body, expires_at, lang FROM shares WHERE id") || sql.startsWith("SELECT delete_hash FROM shares WHERE id")) {
            return shares.find((r) => r.id === args[0]) || null;
          }
          if (sql.startsWith("SELECT token_hash FROM profiles WHERE id") || sql.startsWith("SELECT body FROM profiles WHERE id")) {
            return profiles.find((r) => r.id === args[0]) || null;
          }
          if (sql.startsWith("INSERT INTO transfers")) {
            const [id, created_at, expires_at, install_id, size, body] = args;
            if (transfers.some((row) => row.id === id)) return null;
            transfers.push({ id, created_at, expires_at, install_id, size, tries: 0, body: [...body] });
            return { id };
          }
          if (sql.startsWith("UPDATE transfers SET tries")) {
            const row = transfers.find((r) => r.id === args[0] && r.tries < args[1] && r.expires_at >= args[2]);
            if (!row) return null;
            row.tries += 1;
            return { body: [...row.body], tries: row.tries };
          }
          throw new Error(`unexpected first(): ${sql}`);
        },
        async all() {
          if (sql.startsWith("SELECT id, updated_at, body FROM profiles WHERE id IN")) {
            return { results: profiles.filter((r) => args.includes(r.id)) };
          }
          if (sql.startsWith("SELECT r2_key FROM reports WHERE install_id")) {
            return { results: reports.filter((r) => r.install_id === args[0]) };
          }
          if (sql.startsWith("SELECT id, r2_key FROM reports WHERE created_at <")) {
            const limit = Number(sql.match(/LIMIT (\d+)/)[1]);
            return { results: reports.filter((r) => r.created_at < args[0]).slice(0, limit) };
          }
          if (sql.startsWith("SELECT install_hash, day, version, body FROM daily_stats WHERE day >=")) {
            return { results: [...daily.values()].filter((r) => r.day >= args[0]) };
          }
          if (sql.startsWith("SELECT id, created_at")) {
            return { results: [...reports].reverse() };
          }
          throw new Error(`unexpected all(): ${sql}`);
        },
        async run() {
          if (sql.startsWith("INSERT INTO shares")) {
            const [id, created_at, expires_at, install_id, delete_hash, lang, version, body] = args;
            shares.push({ id, created_at, expires_at, install_id, delete_hash, lang, version, body: [...body] });
          } else if (sql.startsWith("DELETE FROM shares WHERE id")) {
            shares.splice(0, shares.length, ...shares.filter((r) => r.id !== args[0]));
          } else if (sql.startsWith("DELETE FROM shares WHERE install_id")) {
            shares.splice(0, shares.length, ...shares.filter((r) => r.install_id !== args[0]));
          } else if (sql.startsWith("DELETE FROM shares WHERE expires_at")) {
            shares.splice(0, shares.length, ...shares.filter((r) => r.expires_at >= args[0]));
          } else if (sql.startsWith("INSERT INTO profiles")) {
            const [id, created_at, install_id, token_hash, version, body] = args;
            profiles.push({ id, created_at, updated_at: created_at, install_id, token_hash, version, body });
          } else if (sql.startsWith("UPDATE profiles SET updated_at")) {
            Object.assign(profiles.find((r) => r.id === args[0]), { updated_at: args[1], version: args[2], body: args[3] });
          } else if (sql.startsWith("DELETE FROM profiles WHERE id")) {
            profiles.splice(0, profiles.length, ...profiles.filter((r) => r.id !== args[0]));
          } else if (sql.startsWith("DELETE FROM profiles WHERE install_id")) {
            profiles.splice(0, profiles.length, ...profiles.filter((r) => r.install_id !== args[0]));
          } else if (sql.startsWith("DELETE FROM profiles WHERE updated_at <")) {
            profiles.splice(0, profiles.length, ...profiles.filter((r) => r.updated_at >= args[0]));
          } else if (sql.startsWith("DELETE FROM transfers WHERE id")) {
            transfers.splice(0, transfers.length, ...transfers.filter((r) => {
              if (r.id !== args[0]) return true;
              if (sql.includes("expires_at <")) return !(r.expires_at < args[1] || r.tries >= args[2]);
              if (sql.includes("tries >=")) return r.tries < args[1];
              return false;
            }));
          } else if (sql.startsWith("DELETE FROM transfers WHERE install_id")) {
            transfers.splice(0, transfers.length, ...transfers.filter((r) => r.install_id !== args[0]));
          } else if (sql.startsWith("DELETE FROM transfers WHERE expires_at")) {
            transfers.splice(0, transfers.length, ...transfers.filter((r) => r.expires_at >= args[0]));
          } else if (sql.startsWith("INSERT INTO daily_stats")) {
            const [install_hash, day, created_at, version, body] = args;
            daily.set(`${install_hash}|${day}`, { install_hash, day, created_at, version, body });
          } else if (sql.startsWith("DELETE FROM daily_stats WHERE install_hash")) {
            for (const [key, row] of [...daily]) if (row.install_hash === args[0]) daily.delete(key);
          } else if (sql.startsWith("DELETE FROM daily_stats WHERE day <")) {
            for (const [key, row] of [...daily]) if (row.day < args[0]) daily.delete(key);
          } else if (sql.startsWith("DELETE FROM channel_counts WHERE day <")) {
            // Source counts (test/channels.test.js) are not kept by this fake.
          } else if (sql.startsWith("INSERT INTO reports")) {
            const [id, created_at, install_id, version, os, lang, size, summary, r2_key, body] = args;
            // D1 returns a BLOB as an array of bytes.
            const blob = body ? [...body] : null;
            reports.push({ id, created_at, install_id, version, os, lang, size, summary, r2_key, body: blob });
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
  return { env: { DB, ...(r2 ? { REPORTS } : {}), ...vars }, reports, shares, transfers, profiles, objects, daily };
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
  assert.deepEqual(answer, {
    reports: false,
    shares: true,
    transfers: true,
    transfer_minutes: 15,
    share_days: 90,
    stats: true,
    channels: true,
    profiles: true,
    sessions: false,
    retention_days: 180
  });
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

test("the admin page script runs, also as the deploy bundles it", () => {
  // wrangler/esbuild add __name(...) calls inside the function's text; without
  // the helper the script died on its first line and «Показать» did nothing.
  const bundled = ADMIN_JS.replace('const KEY = ', '__name(() => 0, "probe");\n  const KEY = ');
  assert.notEqual(bundled, ADMIN_JS);
  for (const source of [ADMIN_JS, bundled]) {
    const listeners = {};
    const node = (id) => ({
      id,
      value: "",
      textContent: "",
      className: "",
      classList: { add() {}, remove() {} },
      addEventListener(type) {
        listeners[`${id}:${type}`] = true;
      },
      replaceChildren() {}
    });
    const nodes = {};
    const context = {
      document: { getElementById: (id) => (nodes[id] ||= node(id)), createElement: () => node("x") },
      sessionStorage: { getItem: () => "", setItem() {}, removeItem() {} },
      fetch: async () => ({ status: 404 })
    };
    vm.runInNewContext(source, context);
    assert.ok(listeners["login:submit"], "the form listens for submit");
    assert.ok(listeners["days:change"]);
  }
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
  // A secret pasted with a trailing newline still matches; another token does not.
  const pasted = fakeEnv({ ADMIN_TOKEN: "t0ken\n" });
  assert.equal((await worker.fetch(new Request("https://api.example/v1/admin/reports", auth), pasted.env, ctx)).status, 200);
  const wrong = { headers: { authorization: "Bearer t0ke" } };
  assert.equal((await worker.fetch(new Request("https://api.example/v1/admin/reports", wrong), pasted.env, ctx)).status, 404);
  const blank = fakeEnv({ ADMIN_TOKEN: " \n" });
  const empty = { headers: { authorization: "Bearer " } };
  assert.equal((await worker.fetch(new Request("https://api.example/v1/admin/reports", empty), blank.env, ctx)).status, 404);
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

test("without an R2 bucket the report is kept in D1", async () => {
  const { env, reports } = fakeEnv({ ADMIN_TOKEN: "t0ken" }, { r2: false });
  const response = await worker.fetch(upload(REPORT), env, ctx);
  assert.equal(response.status, 201);
  const { id } = await response.json();
  assert.equal(reports[0].r2_key, null);
  assert.ok(reports[0].body.length > 0);
  const auth = { headers: { authorization: "Bearer t0ken" } };
  const text = await (await worker.fetch(new Request(`https://api.example/v1/admin/report/${id}`, auth), env, ctx)).text();
  assert.ok(text.startsWith("Player note:\nОверлей не видно"));
  assert.equal(await cleanup(env, Date.now() + 181 * 24 * 3_600_000), 1);
  assert.equal(reports.length, 0);
  await worker.fetch(upload(REPORT), env, ctx);
  const gone = await worker.fetch(new Request(`https://api.example/v1/device/${REPORT.install_id}`, { method: "DELETE" }), env, ctx);
  assert.deepEqual(await gone.json(), { ok: true, deleted: 1 });
});

// --- «Поделиться разбором» ------------------------------------------------------------

const REVIEW = {
  lang: "ru",
  hero: "Juggernaut",
  hero_key: "juggernaut",
  win: false,
  duration: 2280,
  played_on: "2026-09-21",
  score: 31,
  grade: "D",
  role: "кор",
  parsed: true,
  stats: { kills: 3, deaths: 9, assists: 6, gpm: 390, xpm: 430, last_hits: 160, denies: 3, net_worth: 11500, hero_damage: 9000 },
  sections: [{ label: "Линия", score: 20 }],
  strengths: [],
  improvements: [{ title: "Проиграна линия <script>alert(1)</script>", text: "36 добиваний к 10:00", drill: "Добивайте под вышкой" }],
  deaths: { count: 9, enemy_half: 5, unspent_gold: 2 },
  coach: "Матч решила линия. Steam 76561198000000001"
};

function shareRequest(body, ip = "198.51.100.7") {
  return new Request("https://api.example/v1/share", {
    method: "POST",
    headers: { "content-type": "application/json", "cf-connecting-ip": ip },
    body: JSON.stringify(body)
  });
}

test("a shared review is published, shown as a page and deleted by its author", async () => {
  const { env, shares } = fakeEnv();
  const response = await worker.fetch(
    shareRequest({ install_id: REPORT.install_id, version: "0.5.0", review: { ...REVIEW, match_id: 8012345678, extra: "x" } }),
    env,
    ctx
  );
  assert.equal(response.status, 201);
  const answer = await response.json();
  assert.match(answer.id, /^[2-9a-z]{10}$/);
  assert.equal(answer.url, `https://api.example/r/${answer.id}`);
  assert.equal(shares.length, 1);
  // With a Workers route on the site, the link points at the site.
  const siteEnv = { ...env, SHARE_ORIGIN: "https://luhovyimvp.dev" };
  const onSite = await (
    await worker.fetch(shareRequest({ install_id: REPORT.install_id, version: "0.9.0", review: REVIEW }), siteEnv, ctx)
  ).json();
  assert.match(onSite.url, /^https:\/\/luhovyimvp\.dev\/r\/[2-9a-z]{10}$/);
  // A 0.8 launcher opens only links on the API's address: it keeps getting those.
  const older = await (
    await worker.fetch(shareRequest({ install_id: REPORT.install_id, version: "0.8.0", review: REVIEW }), siteEnv, ctx)
  ).json();
  assert.match(older.url, /^https:\/\/api\.example\/r\//);
  shares.splice(1);

  const json = await (await worker.fetch(new Request(`https://api.example/v1/share/${answer.id}`), env, ctx)).json();
  assert.equal(json.review.hero, "Juggernaut");
  assert.ok(!("match_id" in json.review) && !("extra" in json.review));
  assert.ok(!json.review.coach.includes("76561198000000001"), "Steam IDs are cut out");

  const page = await worker.fetch(new Request(`https://api.example/r/${answer.id}`), env, ctx);
  assert.equal(page.status, 200);
  assert.match(page.headers.get("content-security-policy"), /default-src 'none'/);
  const html = await page.text();
  assert.match(html, /<meta property="og:title" content="Juggernaut · поражение · оценка 31"/);
  assert.match(html, /heroes\/juggernaut\.png/);
  assert.ok(!html.includes("<script>alert(1)</script>"), "texts are escaped");
  assert.ok(html.includes("&lt;script&gt;"));
  // A visible way to try it, leading to the site in the review's language, tagged.
  assert.match(html, /<a class="try" href="https:\/\/luhovyimvp\.dev\/\?ref=share">Попробовать бесплатно<\/a>/);
  assert.ok(!html.includes('href="https://luhovyimvp.dev/"'), "every site link carries ?ref=share");

  const noToken = await worker.fetch(new Request(`https://api.example/v1/share/${answer.id}`, { method: "DELETE" }), env, ctx);
  assert.equal(noToken.status, 403);
  const deleted = await worker.fetch(
    new Request(`https://api.example/v1/share/${answer.id}`, { method: "DELETE", headers: { "x-delete-token": answer.delete_token } }),
    env,
    ctx
  );
  assert.equal(deleted.status, 200);
  const gone = await worker.fetch(new Request(`https://api.example/r/${answer.id}`, { headers: { "accept-language": "ru-RU" } }), env, ctx);
  assert.equal(gone.status, 404);
  assert.match(await gone.text(), /Разбор не найден/);
  assert.equal(siteHome("en"), "https://luhovyimvp.dev/en/?ref=share");
  assert.equal(siteHome("ru"), "https://luhovyimvp.dev/?ref=share");
});

test("shares are checked, limited, expire and go with the installation", async () => {
  const { env, shares } = fakeEnv();
  const bad = await worker.fetch(shareRequest({ install_id: REPORT.install_id, review: { hero: "" } }), env, ctx);
  assert.equal(bad.status, 400);
  const off = await worker.fetch(shareRequest({ install_id: REPORT.install_id, review: REVIEW }), { ...env, SHARES_ENABLED: "false" }, ctx);
  assert.equal(off.status, 503);
  const now = Date.now();
  for (let i = 0; i < 20; i += 1) {
    const ok = await worker.fetch(shareRequest({ install_id: REPORT.install_id, review: REVIEW }), env, ctx);
    assert.equal(ok.status, 201);
  }
  const limited = await worker.fetch(shareRequest({ install_id: REPORT.install_id, review: REVIEW }), env, ctx);
  assert.equal(limited.status, 429);
  // 90 days later the cron removes them all.
  await cleanup(env, now + 91 * 24 * 3_600_000);
  assert.equal(shares.length, 0);
  await worker.fetch(shareRequest({ install_id: REPORT.install_id, review: REVIEW }, "198.51.100.8"), env, ctx);
  await worker.fetch(new Request(`https://api.example/v1/device/${REPORT.install_id}`, { method: "DELETE" }), env, ctx);
  assert.equal(shares.length, 0);
  assert.equal((await worker.fetch(new Request("https://api.example/r/not-an-id!"), env, ctx)).status, 404);
});

// --- «Поделиться прогрессом» ----------------------------------------------------------

const PROGRESS = {
  kind: "progress",
  lang: "ru",
  matches: 14,
  analyzed: 12,
  wins: 9,
  losses: 5,
  winrate: 64,
  rank: "Легенда",
  period: { from: "2026-09-01", to: "2026-09-21" },
  averages: { kda: 8, gpm: 578.6, xpm: 632.9, lh_10: 58.7, deaths: 4.6, score: 70.3 },
  trend: [
    { key: "score", recent: 66.4, previous: 90, better: false },
    { key: "hacked", recent: 1, previous: 2, better: true }
  ],
  heroes: [{ hero: "Juggernaut", hero_key: "juggernaut", matches: 13, winrate: 62, match_id: 8012345678 }],
  strengths: [{ title: "Сильная линия", count: 8, of: 12, drill: "not for strengths" }],
  problems: [{ title: "Фарм ниже <b>соперника</b>", count: 4, of: 12, drill: "Не отдавайте волны" }],
  focus: { title: "Смерти на линии", met: 2, total: 3, results: [{ match_id: 1 }] },
  coach: "Стабильный фарм. Steam 76561198000000001",
  series: [{ match_id: 8012345678 }]
};

test("a shared progress page is checked field by field and rendered", async () => {
  const { env } = fakeEnv();
  const response = await worker.fetch(shareRequest({ install_id: REPORT.install_id, version: "0.7.0", progress: PROGRESS }), env, ctx);
  assert.equal(response.status, 201);
  const answer = await response.json();
  const { review } = await (await worker.fetch(new Request(`https://api.example/v1/share/${answer.id}`), env, ctx)).json();
  assert.equal(review.kind, "progress");
  assert.deepEqual(review.trend.map((t) => t.key), ["score"], "unknown trend keys are dropped");
  assert.ok(!("series" in review) && !("match_id" in review.heroes[0]) && !("results" in review.focus));
  assert.ok(!("drill" in review.strengths[0]));
  assert.ok(!review.coach.includes("76561198000000001"));
  const html = await (await worker.fetch(new Request(`https://api.example/r/${answer.id}`), env, ctx)).text();
  assert.match(html, /<meta property="og:title" content="Прогресс в Dota 2 · 14 матчей · 64% побед"/);
  assert.match(html, /heroes\/juggernaut\.png/);
  assert.ok(html.includes("Фарм ниже &lt;b&gt;соперника&lt;/b&gt;"), "texts are escaped");
  assert.ok(html.includes("Выполнен в 2 из 3 матчей"));

  const bad = await worker.fetch(shareRequest({ install_id: REPORT.install_id, progress: { analyzed: 0 } }), env, ctx);
  assert.equal(bad.status, 400);
  assert.equal((await bad.json()).code, "bad_progress");
});


// --- «Перенос истории по коду» --------------------------------------------------------

function sealed(size = 64) {
  const bytes = new Uint8Array(size);
  bytes.set([0x57, 0x44, 0x54, 0x31]);
  return bytes;
}

function putTransferRequest(id, body, { install = REPORT.install_id, ip = "198.51.100.9" } = {}) {
  return new Request(`https://api.example/v1/transfer/${id}`, {
    method: "PUT",
    headers: { "content-type": "application/octet-stream", "x-install-id": install, "cf-connecting-ip": ip },
    body
  });
}

function claimRequest(id, ip = "198.51.100.10") {
  return new Request(`https://api.example/v1/transfer/${id}/claim`, { method: "POST", headers: { "cf-connecting-ip": ip } });
}

test("an encrypted history is kept 15 minutes, downloaded and deleted by the receiver", async () => {
  const { env, transfers } = fakeEnv();
  const put = await worker.fetch(putTransferRequest("AB2C", sealed()), env, ctx);
  assert.equal(put.status, 201);
  assert.equal((await put.json()).id, "AB2C");
  assert.equal(transfers.length, 1);
  assert.equal((await worker.fetch(putTransferRequest("AB2C", sealed()), env, ctx)).status, 409, "the id is taken");

  const claim = await worker.fetch(claimRequest("AB2C"), env, ctx);
  assert.equal(claim.status, 200);
  const bytes = new Uint8Array(await claim.arrayBuffer());
  assert.deepEqual([...bytes.slice(0, 4)], [0x57, 0x44, 0x54, 0x31]);
  assert.equal(transfers.length, 1, "kept for a retry after a mistyped code");
  const done = await worker.fetch(new Request("https://api.example/v1/transfer/AB2C", { method: "DELETE" }), env, ctx);
  assert.equal(done.status, 200);
  assert.equal(transfers.length, 0);
  assert.equal((await worker.fetch(claimRequest("AB2C"), env, ctx)).status, 404);
});

test("three downloads at most", async () => {
  const { env, transfers } = fakeEnv();
  await worker.fetch(putTransferRequest("EF3G", sealed()), env, ctx);
  for (let i = 0; i < 3; i += 1) {
    assert.equal((await worker.fetch(claimRequest("EF3G"), env, ctx)).status, 200);
  }
  assert.equal(transfers.length, 0);
  assert.equal((await worker.fetch(claimRequest("EF3G"), env, ctx)).status, 404);
});

test("transfers refuse other bodies, big files and expire", async () => {
  const { env, transfers } = fakeEnv();
  assert.equal((await worker.fetch(putTransferRequest("AB2C", new Uint8Array(64)), env, ctx)).status, 400);
  assert.equal((await worker.fetch(putTransferRequest("ab2c", sealed()), env, ctx)).status, 400, "lowercase is not an id");
  assert.equal((await worker.fetch(putTransferRequest("AB2C", sealed(1_600_000)), env, ctx)).status, 413);
  assert.equal((await worker.fetch(putTransferRequest("AB2C", sealed(), { install: "x" }), env, ctx)).status, 400);
  const off = await worker.fetch(putTransferRequest("AB2C", sealed()), { ...env, TRANSFERS_ENABLED: "false" }, ctx);
  assert.equal(off.status, 503);

  await worker.fetch(putTransferRequest("CD3E", sealed()), env, ctx);
  assert.equal(transfers.length, 1);
  await cleanup(env, Date.now() + 16 * 60_000);
  assert.equal(transfers.length, 0);
  await worker.fetch(putTransferRequest("CD3E", sealed()), env, ctx);
  await worker.fetch(new Request(`https://api.example/v1/device/${REPORT.install_id}`, { method: "DELETE" }), env, ctx);
  assert.equal(transfers.length, 0, "the device delete removes it too");
});

test("guessing codes is slow", async () => {
  const { env } = fakeEnv();
  for (let i = 0; i < 30; i += 1) {
    assert.equal((await worker.fetch(claimRequest("ZZZZ", "203.0.113.5"), env, ctx)).status, 404);
  }
  assert.equal((await worker.fetch(claimRequest("ZZZZ", "203.0.113.5"), env, ctx)).status, 429);
});

test("version gate for site links", () => {
  assert.equal(versionAtLeast("0.9.0", [0, 9, 0]), true);
  assert.equal(versionAtLeast("0.10.2", [0, 9, 0]), true);
  assert.equal(versionAtLeast("1.0.0", [0, 9, 0]), true);
  assert.equal(versionAtLeast("0.8.9", [0, 9, 0]), false);
  assert.equal(versionAtLeast("", [0, 9, 0]), false);
  assert.equal(versionAtLeast("dev", [0, 9, 0]), false);
});


// --- «Друзья»: profile cards by friend code (src/profile.js) ---------------------

const INSTALL = "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d";
const TOKEN = "0123456789abcdef0123456789abcdef";
const CARD = {
  lang: "ru",
  name: "farm_or_die 76561198000000000",
  avatar: "0123456789abcdef0123456789abcdef01234567",
  title: "Легенда Wardly",
  level: 7,
  rank_tier: 54,
  rank_label: "Легенда 4",
  mmr: 3619,
  equipped: { frame: "frame_arcana", banner: "banner_aurora", name: "name_prism", title: "title_legend", extra: "x" },
  achievements: [{ id: "app_games", tier: 2, title: "С тренером" }, { id: "Bad Id", tier: 9 }],
  stats: { app_games: 12, app_winrate: 58, week_games: 4 },
  steam_id: "76561198000000000"
};

function putCard(id, { token = TOKEN, card = CARD, ip = "203.0.113.9" } = {}) {
  return new Request(`https://api.example/v1/profile/${id}`, {
    method: "PUT",
    headers: { "content-type": "application/json", "x-profile-token": token, "cf-connecting-ip": ip },
    body: JSON.stringify({ install_id: INSTALL, version: "0.35.0", profile: card })
  });
}

test("a profile card is published, read by friend code and shown as a page", async () => {
  const { env, profiles } = fakeEnv();
  let response = await worker.fetch(putCard("4k7p9qx2"), env, ctx);
  assert.equal(response.status, 201);
  const created = await response.json();
  assert.equal(created.code, "WD-4K7P9QX2");
  assert.match(created.url, /\/p\/4k7p9qx2$/);
  const stored = JSON.parse(profiles[0].body);
  assert.equal(stored.name, "farm_or_die"); // a Steam ID is cut from the text
  assert.equal(stored.steam_id, undefined);
  assert.deepEqual(Object.keys(stored.equipped), ["frame", "banner", "name", "title"]);
  assert.deepEqual(stored.achievements.map((a) => a.id), ["app_games"]);
  // The same launcher updates it; another token cannot.
  response = await worker.fetch(putCard("4k7p9qx2", { card: { ...CARD, level: 8 } }), env, ctx);
  assert.equal(response.status, 200);
  response = await worker.fetch(putCard("4k7p9qx2", { token: "f".repeat(32) }), env, ctx);
  assert.equal(response.status, 409);
  // Friends read cards by code, as people type it.
  response = await worker.fetch(
    new Request("https://api.example/v1/profiles", { method: "POST", body: JSON.stringify({ ids: ["WD-4K7P 9QX2", "nope", "22222222"] }) }),
    env,
    ctx
  );
  const read = await response.json();
  assert.deepEqual(Object.keys(read.profiles), ["4k7p9qx2"]);
  assert.equal(read.profiles["4k7p9qx2"].level, 8);
  // The page: escaped, with the code to add.
  response = await worker.fetch(new Request("https://api.example/p/4k7p9qx2"), env, ctx);
  assert.equal(response.status, 200);
  const html = await response.text();
  assert.match(html, /WD-4K7P9QX2/);
  assert.match(html, /Легенда Wardly/);
  assert.doesNotMatch(html, /76561198/);
  // The looks and the avatar as the launcher draws them.
  assert.match(html, /class="pf-banner cos-banner_aurora"/);
  assert.match(html, /class="pf-avatar-wrap cos-frame_arcana"/);
  assert.match(html, /src="https:\/\/avatars\.steamstatic\.com\/0123456789abcdef0123456789abcdef01234567_full\.jpg"/);
  assert.match(response.headers.get("content-security-policy"), /img-src [^;]*https:\/\/avatars\.steamstatic\.com/);
  response = await worker.fetch(new Request("https://api.example/p/zzzzzzzz"), env, ctx);
  assert.equal(response.status, 404);
});

test("a profile page without looks or avatar wears the free looks, and a bad avatar is dropped", async () => {
  const { env, profiles } = fakeEnv();
  const card = { ...CARD, avatar: "https://evil.example/x.jpg", equipped: {} };
  await worker.fetch(putCard("4k7p9qx2", { card }), env, ctx);
  assert.equal(JSON.parse(profiles[0].body).avatar, null);
  const html = await (await worker.fetch(new Request("https://api.example/p/4k7p9qx2"), env, ctx)).text();
  assert.match(html, /class="pf-banner cos-banner_plain"/);
  assert.match(html, /class="pf-avatar-wrap cos-frame_plain"/);
  assert.doesNotMatch(html, /<img src="https:\/\/evil/);
});

// The cos- rules of a stylesheet, selector -> declarations, with whitespace,
// comments and leading zeros folded and the launcher's tokens filled in.
function lookRules(css, tokens = {}) {
  const fold = (text) =>
    text
      .replace(/\/\*[\s\S]*?\*\//g, "")
      .replace(/var\((--[a-z0-9-]+)\)/g, (all, name) => tokens[name] || all)
      .replace(/\s+/g, " ")
      .replace(/\s*([{}:;,>()])\s*/g, "$1")
      .replace(/(^|[^0-9.])0\./g, "$1.")
      .replace(/;$/, "")
      .trim();
  const rules = new Map();
  for (const [, selector, body] of css.matchAll(/([^{}]+)\{([^{}]*)\}/g)) {
    const key = fold(selector);
    if (key.includes(".cos-")) {
      rules.set(key, [rules.get(key), fold(body)].filter(Boolean).join(";"));
    }
  }
  return rules;
}

test("the profile page wears every look exactly as the launcher draws it", () => {
  const read = (path) => readFileSync(new URL(`../../../frontend/launcher/${path}`, import.meta.url), "utf8");
  const root = read("assets/ui/tokens.css").match(/:root\s*\{([^}]*)\}/)[1];
  const tokens = Object.fromEntries([...root.matchAll(/(--[a-z0-9-]+)\s*:\s*([^;]+);/g)].map(([, name, value]) => [name, value.trim()]));
  const launcher = lookRules(read("renderer/styles.css"), tokens);
  assert.ok(launcher.size > 15);
  const html = renderProfilePage({ ...CARD, name: "x", avatar: null, achievements: [], stats: { app_games: 0, app_winrate: null }, mmr: null }, { id: "4k7p9qx2", url: "" });
  const page = lookRules([...html.matchAll(/<style>([\s\S]*?)<\/style>/g)].map((match) => match[1]).join("\n"));
  assert.deepEqual(Object.fromEntries(page), Object.fromEntries(launcher));
});

test("a profile card is hidden with its token, by the device delete and after 180 days", async () => {
  const { env, profiles } = fakeEnv();
  await worker.fetch(putCard("4k7p9qx2"), env, ctx);
  let response = await worker.fetch(
    new Request("https://api.example/v1/profile/4k7p9qx2", { method: "DELETE", headers: { "x-profile-token": "f".repeat(32) } }),
    env,
    ctx
  );
  assert.equal(response.status, 403);
  response = await worker.fetch(
    new Request("https://api.example/v1/profile/4k7p9qx2", { method: "DELETE", headers: { "x-profile-token": TOKEN } }),
    env,
    ctx
  );
  assert.equal(response.status, 200);
  assert.equal(profiles.length, 0);
  await worker.fetch(putCard("4k7p9qx2"), env, ctx);
  await worker.fetch(new Request(`https://api.example/v1/device/${INSTALL}`, { method: "DELETE" }), env, ctx);
  assert.equal(profiles.length, 0);
  await worker.fetch(putCard("4k7p9qx2"), env, ctx);
  await cleanup(env, Date.now() + 181 * 24 * 3_600_000);
  assert.equal(profiles.length, 0);
});

test("bad profile requests are refused", async () => {
  const { env } = fakeEnv();
  assert.equal((await worker.fetch(putCard("UPPER123"), env, ctx)).status, 400);
  assert.equal((await worker.fetch(putCard("4k7p9qx2", { token: "short" }), env, ctx)).status, 400);
  assert.equal((await worker.fetch(putCard("4k7p9qx2", { card: { ...CARD, name: "" } }), env, ctx)).status, 400);
  const off = fakeEnv({ PROFILES_ENABLED: "false" });
  assert.equal((await worker.fetch(putCard("4k7p9qx2"), off.env, ctx)).status, 503);
  assert.equal(config(off.env).profiles, false);
});
