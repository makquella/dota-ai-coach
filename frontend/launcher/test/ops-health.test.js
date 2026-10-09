const test = require("node:test");
const assert = require("node:assert/strict");
const OpsHealth = require("../renderer/ops-health.js");
const I18N = require("../renderer/app-texts.js").create(require("../renderer/whats-new.js"));

const tr = (lang) => (key, ...args) => {
  const value = I18N[lang][key];
  assert.ok(value !== undefined, `${lang}.${key} is missing`);
  return typeof value === "function" ? value(...args) : value;
};
const trOr = (lang) => (key, fallback) => (typeof I18N[lang][key] === "string" ? I18N[lang][key] : fallback);

const HEALTHY = {
  warnings: [],
  queues: {
    jobs: { queued: 0, completed: 7, failed: 0, worker_alive: true },
    ai_jobs: { queued: 2, oldest_due_s: 12.5, running: true, running_kind: "coach", running_for_s: 4.2 }
  },
  match_finish: { pending_finishes: 0, last_ack_at: "2026-10-09T10:05:00+00:00" },
  live_path: { "gsi.total": { count: 1200, p50_ms: 3.1, p95_ms: 9.4 }, "gsi.persistence": { failed: 0 } },
  freshness: { sync_state: "done", sync_at: "2026-10-09T10:00:00+00:00", builds_generated: "2026-10-06", builds_age_days: 3 }
};

for (const lang of ["en", "ru"]) {
  test(`${lang}: every line of a healthy app reads without a warning`, () => {
    const rows = OpsHealth.rows(HEALTHY, tr(lang));
    assert.deepEqual(rows.map((row) => row.key), ["opsJobs", "opsAi", "opsMatch", "opsGsi", "opsData"]);
    assert.ok(rows.every((row) => row.state !== "bad"));
    assert.equal(rows[2].state, "good");
    assert.match(rows[1].value, /coach/);
    assert.match(rows[3].value, /1200/);
    assert.match(rows[4].value, /2026-10-06/);
    assert.deepEqual(OpsHealth.warningTexts(HEALTHY, trOr(lang)), []);
  });

  test(`${lang}: every backend warning code has words and marks its line`, () => {
    const codes = [
      "jobs_waiting", "jobs_running_long", "jobs_no_worker", "ai_jobs_waiting", "ai_jobs_running_long", "ai_jobs_no_worker",
      "match_not_saved", "recovery_write_failed", "gsi_persistence_failed", "gsi_slow", "sync_failed", "builds_stale"
    ];
    const health = { ...HEALTHY, warnings: codes, match_finish: { pending_finishes: 1 } };
    const texts = OpsHealth.warningTexts(health, trOr(lang));
    texts.forEach((text, index) => assert.notEqual(text, codes[index], `${lang} has no words for ${codes[index]}`));
    assert.ok(OpsHealth.rows(health, tr(lang)).every((row) => row.state === "bad"));
    // A code from a newer backend stays readable as itself.
    assert.deepEqual(OpsHealth.warningTexts({ warnings: ["new_thing"] }, trOr(lang)), ["new_thing"]);
  });
}

test("queue lines cover idle, waiting, scheduled and failed", () => {
  const t = tr("en");
  assert.equal(OpsHealth.queueLine({ completed: 3 }, t), "idle · 3 done");
  assert.equal(OpsHealth.queueLine({ queued: 2, oldest_due_s: 30 }, t), "2 waiting · the oldest for 30 s");
  assert.equal(OpsHealth.queueLine({ queued: 1, next_in_s: 45 }, t), "1 scheduled · next in 45 s");
  assert.match(OpsHealth.queueLine({ completed: 1, failed: 1, last_failed_at: "bad" }, t), /1 failed$/);
  assert.equal(OpsHealth.clock(null), "");
});

test("missing or empty health draws dashes, not errors", () => {
  const rows = OpsHealth.rows({}, tr("en"));
  assert.equal(rows.length, 5);
  assert.equal(rows[3].value, "no packets in this session");
});
