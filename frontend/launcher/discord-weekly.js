// The week in Discord: once a week the launcher posts the last calendar week
// (backend GET /player/week?until=<Monday 00:00>) to a channel webhook the
// player created on their own server (Server settings → Integrations →
// Webhooks). No bot and no token of ours: the webhook link is the player's and
// stays in settings.json; the post goes from this computer straight to Discord.
// Heroes, results and the review numbers only: no nickname, Steam ID or match id.
//
// Pure helpers, tested in test/discord-weekly.test.js; main.js sends.

const WEBHOOK_HOSTS = new Set(["discord.com", "discordapp.com", "ptb.discord.com", "canary.discord.com"]);
const WEBHOOK_PATH = /^\/api\/(?:v\d+\/)?webhooks\/(\d{15,22})\/([\w-]{40,120})\/?$/;
const SITE_URL = "https://luhovyimvp.dev";
const AVATAR_URL = `${SITE_URL}/assets/logo-mark.png`;
const COLOR = 0xd23a46;
const DAY_MS = 24 * 3600 * 1000;

/** A Discord channel webhook link → its canonical form, or null. */
function parseWebhookUrl(text) {
  let url;
  try {
    url = new URL(String(text || "").trim());
  } catch {
    return null;
  }
  if (url.protocol !== "https:" || !WEBHOOK_HOSTS.has(url.hostname) || url.username || url.password || url.port) {
    return null;
  }
  const match = WEBHOOK_PATH.exec(url.pathname);
  return match ? `https://discord.com/api/webhooks/${match[1]}/${match[2]}` : null;
}

/** What the panel may show of a stored link: the last four characters of its token. */
function webhookHint(url) {
  const match = /\/webhooks\/\d+\/([\w-]+)$/.exec(String(url || ""));
  return match ? `…${match[1].slice(-4)}` : "";
}

/** Local Monday 00:00 of the week `now` is in (ms). */
function weekStart(now) {
  const date = new Date(now);
  const sinceMonday = (date.getDay() + 6) % 7;
  return new Date(date.getFullYear(), date.getMonth(), date.getDate() - sinceMonday).getTime();
}

/**
 * The week to post now, or null: the calendar week that ended at this
 * Monday 00:00, once (`lastWeekEnd` = the end of the week already posted).
 * A player away for a month gets the last week only, not four posts.
 */
function dueWeek(now, lastWeekEnd) {
  const end = weekStart(now);
  if (Number(lastWeekEnd) >= end) {
    return null;
  }
  return { start: weekStart(end - DAY_MS), end };
}

/** The backend path for a period: both ends, since a local week is not always 168 hours. */
function weekQuery(period, lang) {
  return `/player/week?lang=${lang === "uk" ? "uk" : "en"}&since=${Math.floor(period.start / 1000)}&until=${Math.floor(period.end / 1000)}`;
}

/**
 * What a post's result means for the schedule: `done` — the week is handled
 * (posted, nothing to post, or the webhook is gone); `disconnect` — Discord
 * says the webhook no longer exists, so it is not tried again next Monday.
 */
function postOutcome(result) {
  const gone = Boolean(result) && result.code === "webhook_gone";
  return { done: Boolean(result && result.ok) || gone, disconnect: gone };
}

const TEXT = {
  uk: {
    title: (from, to) => `Тиждень у Dota 2 · ${from} – ${to}`,
    games: (n) => `${n} ${plural(n, "матч", "матчі", "матчів")}`,
    record: (w, l) => `${w} ${plural(w, "перемога", "перемоги", "перемог")} · ${l} ${plural(l, "поразка", "поразки", "поразок")}`,
    score: "Середня оцінка",
    change: (d) => (d > 0 ? `+${d} до минулого тижня` : d < 0 ? `${d} до минулого тижня` : "як минулого тижня"),
    heroes: "Герої",
    heroLine: (h) => `${h.hero} — ${h.games} ${plural(h.games, "матч", "матчі", "матчів")}, ${h.wins} ${plural(h.wins, "перемога", "перемоги", "перемог")}`,
    best: "Найкращий матч",
    bestLine: (b) => `${b.hero} · ${b.score}/100${b.win === true ? " · перемога" : b.win === false ? " · поразка" : ""}`,
    problem: "Найчастіше повторювалося",
    problemLine: (p) => `${p.title} (${p.count} з ${p.of})`,
    focus: "Фокус",
    focusLine: (f) => `${f.title}: ${f.met} з ${f.results.length} матчів`,
    footer: "Wardly — тренер з Dota 2"
  },
  en: {
    title: (from, to) => `The week in Dota 2 · ${from} – ${to}`,
    games: (n) => `${n} ${n === 1 ? "match" : "matches"}`,
    record: (w, l) => `${w} ${w === 1 ? "win" : "wins"} · ${l} ${l === 1 ? "loss" : "losses"}`,
    score: "Average score",
    change: (d) => (d > 0 ? `+${d} vs the week before` : d < 0 ? `${d} vs the week before` : "same as the week before"),
    heroes: "Heroes",
    heroLine: (h) => `${h.hero} — ${h.games} ${h.games === 1 ? "match" : "matches"}, ${h.wins} ${h.wins === 1 ? "win" : "wins"}`,
    best: "Best match",
    bestLine: (b) => `${b.hero} · ${b.score}/100${b.win === true ? " · win" : b.win === false ? " · loss" : ""}`,
    problem: "Came back most often",
    problemLine: (p) => `${p.title} (${p.count} of ${p.of})`,
    focus: "Focus",
    focusLine: (f) => `${f.title}: ${f.met} of ${f.results.length} matches`,
    footer: "Wardly — a Dota 2 coach"
  }
};

function plural(n, one, few, many) {
  const mod10 = n % 10;
  const mod100 = n % 100;
  if (mod10 === 1 && mod100 !== 11) {
    return one;
  }
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) {
    return few;
  }
  return many;
}

function day(ms, lang) {
  return new Date(ms).toLocaleDateString(lang === "uk" ? "uk-UA" : "en-GB", { day: "numeric", month: "short" });
}

function clip(text, max) {
  const value = String(text ?? "");
  return value.length > max ? `${value.slice(0, max - 1)}…` : value;
}

/**
 * The webhook body for a week (backend weekly_summary), or null when no match
 * was played. `period` = { start, end } in ms; the last day shown is end − 1 day.
 */
function buildWeeklyMessage(week, { lang, period }) {
  if (!week || !Number(week.games)) {
    return null;
  }
  const t = TEXT[lang === "uk" ? "uk" : "en"];
  const lines = [`**${t.games(week.games)}** · ${t.record(week.wins || 0, week.losses || 0)}`];
  const fields = [];
  if (Number.isFinite(week.avg_score)) {
    const change = Number.isFinite(week.score_change) ? ` (${t.change(week.score_change)})` : "";
    fields.push({ name: t.score, value: `${week.avg_score}/100${change}`, inline: false });
  }
  const heroes = Array.isArray(week.heroes) ? week.heroes.filter((h) => h && h.hero) : [];
  if (heroes.length) {
    fields.push({ name: t.heroes, value: clip(heroes.map(t.heroLine).join("\n"), 1000), inline: false });
  }
  if (week.best && week.best.hero && Number.isFinite(week.best.score)) {
    fields.push({ name: t.best, value: clip(t.bestLine(week.best), 200), inline: false });
  }
  if (week.top_problem && week.top_problem.title) {
    fields.push({ name: t.problem, value: clip(t.problemLine(week.top_problem), 300), inline: false });
  }
  if (week.focus && week.focus.title && Array.isArray(week.focus.results) && week.focus.results.length) {
    fields.push({ name: t.focus, value: clip(t.focusLine(week.focus), 300), inline: false });
  }
  return {
    username: "Wardly",
    avatar_url: AVATAR_URL,
    // Hero and finding names are plain text: never ping anyone.
    allowed_mentions: { parse: [] },
    embeds: [
      {
        title: clip(t.title(day(period.start, lang), day(period.end - DAY_MS, lang)), 250),
        url: `${SITE_URL}/${lang === "uk" ? "" : "en/"}?ref=discord-week`,
        description: lines.join("\n"),
        color: COLOR,
        fields,
        footer: { text: t.footer }
      }
    ]
  };
}

module.exports = { buildWeeklyMessage, dueWeek, parseWebhookUrl, postOutcome, webhookHint, weekQuery, weekStart };
