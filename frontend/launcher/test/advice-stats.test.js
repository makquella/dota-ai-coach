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
    sync_error: "timeout"
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
