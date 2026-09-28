const assert = require("node:assert/strict");
const test = require("node:test");

const { buildWeeklyMessage, dueWeek, parseWebhookUrl, postOutcome, webhookHint, weekQuery, weekStart } = require("../discord-weekly");

const TOKEN = "a".repeat(30) + "B-c_" + "d".repeat(34);
const HOOK = `https://discord.com/api/webhooks/123456789012345678/${TOKEN}`;

test("webhook links: Discord hosts and paths only, stored in one form", () => {
  assert.equal(parseWebhookUrl(`  ${HOOK}  `), HOOK);
  assert.equal(parseWebhookUrl(`https://discordapp.com/api/webhooks/123456789012345678/${TOKEN}?wait=true`), HOOK);
  assert.equal(parseWebhookUrl(`https://canary.discord.com/api/v10/webhooks/123456789012345678/${TOKEN}/`), HOOK);
  for (const bad of [
    "",
    "not a url",
    `http://discord.com/api/webhooks/123456789012345678/${TOKEN}`,
    `https://discord.com.evil.example/api/webhooks/123456789012345678/${TOKEN}`,
    `https://evil.example/api/webhooks/123456789012345678/${TOKEN}`,
    `https://user:pass@discord.com/api/webhooks/123456789012345678/${TOKEN}`,
    `https://discord.com/api/webhooks/123456789012345678/${TOKEN}/slack`,
    "https://discord.com/api/webhooks/123/short",
    "https://discord.com/channels/1/2"
  ]) {
    assert.equal(parseWebhookUrl(bad), null, bad);
  }
  assert.equal(webhookHint(HOOK), "…dddd");
  assert.equal(webhookHint(""), "");
});

test("the week to post: the calendar week that ended on Monday, once", () => {
  const wednesday = new Date(2026, 8, 30, 15, 0).getTime(); // Wed 30 Sep 2026
  const monday = new Date(2026, 8, 28).getTime();
  assert.equal(weekStart(wednesday), monday);
  assert.equal(weekStart(monday), monday, "Monday 00:00 starts its own week");
  assert.equal(weekStart(new Date(2026, 9, 4, 23, 59).getTime()), monday, "Sunday night is still that week");
  const due = dueWeek(wednesday, 0);
  assert.deepEqual(due, { start: new Date(2026, 8, 21).getTime(), end: monday });
  assert.equal(dueWeek(wednesday, monday), null, "already posted");
  // Away for a month: only the last week.
  assert.deepEqual(dueWeek(wednesday, new Date(2026, 7, 31).getTime()), due);
});

const WEEK = {
  games: 5,
  wins: 3,
  losses: 2,
  avg_score: 64,
  prev_avg_score: 58,
  score_change: 6,
  heroes: [
    { hero: "Juggernaut", hero_id: 8, games: 3, wins: 2 },
    { hero: "Lina", hero_id: 25, games: 2, wins: 1 }
  ],
  best: { match_id: 8123456789, hero: "Juggernaut", hero_id: 8, score: 82, win: true },
  top_problem: { id: "death_streak", title: "Смерти подряд", count: 3, of: 5 },
  focus: { id: "death_streak", title: "Меньше смертей", drill: "…", results: [{ met: true }, { met: false }, { met: true }], met: 2, plan: 3 }
};

test("the message: numbers and heroes, no match ids, no pings", () => {
  const period = { start: new Date(2026, 8, 21).getTime(), end: new Date(2026, 8, 28).getTime() };
  const message = buildWeeklyMessage(WEEK, { lang: "ru", period });
  const [embed] = message.embeds;
  assert.deepEqual(message.allowed_mentions, { parse: [] });
  assert.equal(message.username, "Wardly");
  assert.match(embed.title, /^Неделя в Dota 2 · 21 сент\.? – 27 сент/);
  assert.equal(embed.description, "**5 матчей** · 3 победы · 2 поражения");
  const fields = Object.fromEntries(embed.fields.map((f) => [f.name, f.value]));
  assert.equal(fields["Средняя оценка"], "64/100 (+6 к прошлой неделе)");
  assert.equal(fields["Герои"], "Juggernaut — 3 матча, 2 победы\nLina — 2 матча, 1 победа");
  assert.equal(fields["Лучший матч"], "Juggernaut · 82/100 · победа");
  assert.equal(fields["Чаще всего повторялось"], "Смерти подряд (3 из 5)");
  assert.equal(fields["Фокус"], "Меньше смертей: 2 из 3 матчей");
  assert.ok(!JSON.stringify(message).includes("8123456789"), "no match id");

  const en = buildWeeklyMessage({ games: 1, wins: 0, losses: 1, avg_score: null, heroes: [] }, { lang: "en", period });
  assert.equal(en.embeds[0].description, "**1 match** · 0 wins · 1 loss");
  assert.deepEqual(en.embeds[0].fields, []);
  assert.equal(buildWeeklyMessage({ games: 0 }, { lang: "en", period }), null);
  assert.equal(buildWeeklyMessage(null, { lang: "en", period }), null);
});

test("the query names both ends of a local week, 169 hours long across a clock change", () => {
  // Europe: clocks go back on Sunday 25 Oct 2026, so that week is an hour longer.
  const period = { start: Date.UTC(2026, 9, 18, 22), end: Date.UTC(2026, 9, 25, 23) };
  assert.equal(weekQuery(period, "ru"), "/player/week?lang=ru&since=1792360800&until=1792969200");
  assert.equal((period.end - period.start) / 3600000, 169);
  assert.match(weekQuery(period, "de"), /lang=en/);
});

test("a webhook deleted in Discord is disconnected, not posted to again", () => {
  assert.deepEqual(postOutcome({ ok: false, code: "webhook_gone" }), { done: true, disconnect: true });
  assert.deepEqual(postOutcome({ ok: true, sent: true }), { done: true, disconnect: false });
  assert.deepEqual(postOutcome({ ok: true, sent: false, code: "no_matches" }), { done: true, disconnect: false });
  for (const code of ["offline", "rate_limited", "backend_down", "http_500"]) {
    assert.deepEqual(postOutcome({ ok: false, code }), { done: false, disconnect: false }, code);
  }
});
