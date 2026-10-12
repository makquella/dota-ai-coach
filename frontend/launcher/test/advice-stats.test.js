const assert = require("node:assert/strict");
const test = require("node:test");

const stats = require("../advice-stats");

const HOUR = 3600 * 1000;

test("yesterday is sent once a day; a week away sends yesterday only", () => {
  const now = new Date(2026, 8, 28, 15, 30).getTime();
  const due = stats.dueDay(now, 0);
  assert.equal(due.start, new Date(2026, 8, 27).getTime());
  assert.equal(due.end, new Date(2026, 8, 28).getTime());
  assert.equal(due.day, "2026-09-27");
  assert.equal(stats.dueDay(now, due.end), null);
  assert.equal(stats.dueDay(now + 10 * HOUR, due.end).day, "2026-09-28");
  assert.equal(stats.dueDay(now + 7 * 24 * HOUR, due.end).day, "2026-10-04");
  assert.equal(stats.usageQuery(due), `/player/usage?since=${due.start / 1000}&until=${due.end / 1000}`);
});

test("the body holds counts and settings only", () => {
  const body = stats.buildStats({
    installId: "a1b2c3d4-e5f6",
    day: "2026-09-27",
    version: "0.17.0",
    platform: "win32",
    lang: "uk",
    usage: { matches: 2, with_advice: 1, advice: { LOW_HP_WARNING: 3, "bad kind": 1 }, ignored: { LOW_HP_WARNING: 1 }, hero: "Juggernaut" },
    settings: { overlay: true, voice: "urgent", frequency: "calm", role: "mid", mapHints: false, discord: true, discordWebhook: "https://discord.com/api/webhooks/1/secret" },
    ai: true,
    opendotaKey: false,
    fullscreen: true,
    syncError: "timeout"
  });
  assert.deepEqual(body, {
    install_id: "a1b2c3d4-e5f6",
    day: "2026-09-27",
    version: "0.17.0",
    os: "win32",
    lang: "uk",
    usage: { matches: 2, with_advice: 1, advice: { LOW_HP_WARNING: 3 }, ignored: { LOW_HP_WARNING: 1 } },
    settings: { overlay: true, voice: "urgent", frequency: "calm", role: "mid", map_hints: false, discord: true },
    ai: "ready",
    opendota_key: false,
    fullscreen: true,
    sync_error: "timeout",
    app: { launches: 0, backend_crashes: 0, renderer_crashes: 0, unclean_exits: 0 },
    marks: { useful: 0, irrelevant: 0, repeated: 0 },
    noisy: {},
    setup: { dota: null, gsi: null, launch: null, data: null, preview: null, account: null, advice: null, review: null, ai: null },
    age: ""
  });
  const text = JSON.stringify(body);
  assert.ok(!text.includes("Juggernaut") && !text.includes("secret"));
});

test("which results end the day", () => {
  assert.equal(stats.uploadOutcome({ ok: true, status: 201 }).done, true);
  assert.equal(stats.uploadOutcome({ ok: false, status: 400, code: "bad_day" }).done, true);
  assert.equal(stats.uploadOutcome({ ok: false, status: 503, code: "disabled" }).done, true);
  assert.equal(stats.uploadOutcome({ ok: false, status: 503 }).done, false);
  assert.equal(stats.uploadOutcome({ ok: false, status: 429, code: "rate_limited" }).done, false);
  assert.equal(stats.uploadOutcome({ ok: false, code: "offline" }).done, false);
});

test("nothing from before the consent (or a server delete) is counted", () => {
  const consent = new Date(2026, 8, 27, 20, 15).getTime();
  const schedule = stats.startFrom(consent);
  assert.deepEqual(schedule, { statsLastDay: new Date(2026, 8, 27).getTime(), statsSince: consent });
  // The first upload the next day covers the evening after the switch, not the whole day.
  const due = stats.dueDay(new Date(2026, 8, 28, 9).getTime(), schedule.statsLastDay, schedule.statsSince);
  assert.equal(due.day, "2026-09-27");
  assert.equal(due.start, consent);
  assert.equal(due.end, new Date(2026, 8, 28).getTime());
  // A later day is whole again.
  assert.equal(stats.dueDay(new Date(2026, 8, 29, 9).getTime(), due.end, schedule.statsSince).start, new Date(2026, 8, 28).getTime());
  // Deleted just after midnight, with yesterday not sent yet: yesterday is never sent.
  const deleted = stats.startFrom(new Date(2026, 8, 28, 0, 5).getTime());
  assert.equal(stats.dueDay(new Date(2026, 8, 28, 0, 10).getTime(), deleted.statsLastDay, deleted.statsSince), null);
});

test("launches and crashes are counted per local day and only the last days are kept", () => {
  let daily = {};
  daily = stats.bumpDaily(daily, "2026-10-12", "launches");
  daily = stats.bumpDaily(daily, "2026-10-12", "launches");
  daily = stats.bumpDaily(daily, "2026-10-12", "backend_crashes");
  daily = stats.bumpDaily(daily, "2026-10-12", "not a counter");
  assert.deepEqual(stats.appCounts(daily, "2026-10-12"), { launches: 2, backend_crashes: 1, renderer_crashes: 0, unclean_exits: 0 });
  assert.deepEqual(stats.appCounts(daily, "2026-10-11"), { launches: 0, backend_crashes: 0, renderer_crashes: 0, unclean_exits: 0 });
  for (let day = 1; day <= 15; day += 1) {
    daily = stats.bumpDaily(daily, `2026-11-${String(day).padStart(2, "0")}`, "launches");
  }
  assert.equal(Object.keys(daily).length, 10);
  assert.ok(!("2026-10-12" in daily) && "2026-11-15" in daily);
});

test("marks are sent once: the new ones since the last upload, nothing on the first day", () => {
  const first = stats.marksDelta(
    { totals: { useful: 4, irrelevant: 2, repeated: 1 }, by_decision_point: { FARM: { useful: 1, irrelevant: 2, repeated: 1 } } },
    null
  );
  assert.deepEqual(first.marks, { useful: 0, irrelevant: 0, repeated: 0 });
  assert.deepEqual(first.noisy, {});
  const next = stats.marksDelta(
    {
      totals: { useful: 6, irrelevant: 3, repeated: 1 },
      by_decision_point: { FARM: { useful: 1, irrelevant: 3, repeated: 1 }, "bad kind": { irrelevant: 9 } }
    },
    first.snapshot
  );
  assert.deepEqual(next.marks, { useful: 2, irrelevant: 1, repeated: 0 });
  assert.deepEqual(next.noisy, { FARM: 1 });
  // Totals that could not be read send nothing and keep the snapshot (no resend from zero later).
  const unread = stats.marksDelta(null, next.snapshot);
  assert.deepEqual(unread.marks, { useful: 0, irrelevant: 0, repeated: 0 });
  assert.equal(unread.snapshot, next.snapshot);
  const after = stats.marksDelta({ totals: { useful: 7, irrelevant: 3, repeated: 1 }, by_decision_point: {} }, unread.snapshot);
  assert.deepEqual(after.marks, { useful: 1, irrelevant: 0, repeated: 0 });
  // A removed mark never goes negative.
  const removed = stats.marksDelta({ totals: { useful: 5, irrelevant: 3, repeated: 1 }, by_decision_point: {} }, next.snapshot);
  assert.deepEqual(removed.marks, { useful: 0, irrelevant: 0, repeated: 0 });
});

test("first-run steps and the installation age go as plain flags and a bucket", () => {
  const body = stats.buildStats({
    installId: "a1b2c3d4-e5f6",
    day: "2026-10-12",
    version: "0.56.0",
    app: { launches: 3, renderer_crashes: 1, extra: 5 },
    marks: { useful: 2, irrelevant: -1 },
    noisy: { FARM: 1, "bad kind": 2 },
    setup: { dota: true, gsi: 1, launch: null, data: false, hero: "Juggernaut" },
    age: "2-6"
  });
  assert.deepEqual(body.app, { launches: 3, backend_crashes: 0, renderer_crashes: 1, unclean_exits: 0 });
  assert.deepEqual(body.marks, { useful: 2, irrelevant: 0, repeated: 0 });
  assert.deepEqual(body.noisy, { FARM: 1 });
  assert.deepEqual(body.setup, { dota: true, gsi: true, launch: null, data: false, preview: null, account: null, advice: null, review: null, ai: null });
  assert.equal(body.age, "2-6");
  assert.ok(!JSON.stringify(body).includes("Juggernaut"));
  const day = new Date(2026, 9, 12, 15).getTime();
  assert.equal(stats.ageBucket(day, new Date(2026, 9, 12, 9).getTime()), "0");
  assert.equal(stats.ageBucket(day, new Date(2026, 9, 11, 23).getTime()), "1");
  assert.equal(stats.ageBucket(day, new Date(2026, 9, 8).getTime()), "2-6");
  assert.equal(stats.ageBucket(day, new Date(2026, 9, 1).getTime()), "7-29");
  assert.equal(stats.ageBucket(day, new Date(2026, 6, 1).getTime()), "30+");
  assert.equal(stats.ageBucket(day, 0), "");
});
