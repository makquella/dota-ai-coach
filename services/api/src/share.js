// «Поділитися розбором»: a match review the player chose to publish.
//
// The launcher sends the public part of a review (backend/app/share_review.py);
// validateShare() builds a new object from known fields only, with type and
// length limits, and drops anything that looks like a Steam ID. The page
// (renderSharePage) is plain HTML with every text escaped, and an Open Graph
// preview (title and the hero's portrait) for Discord and Telegram.

export const SHARE_DAYS = 90;
export const SHARE_LIMITS = { bodyBytes: 64 * 1024 };
export const SHARE_RATE_PER_HOUR = { install: 20, address: 40 };
export const SITE_URL = "https://luhovyimvp.dev";

/** The site in the page's language, tagged so the site counts where the visit came from. */
export function siteHome(lang) {
  return `${SITE_URL}/${lang === "en" ? "en/" : ""}?ref=share`;
}
const PORTRAIT = "https://cdn.cloudflare.steamstatic.com/apps/dota2/images/dota_react/heroes";

const STEAM64 = /7656119\d{10}/g;
// Control characters (keeps tab / newline out of one-line fields anyway).
const CONTROL = /[\u0000-\u001f\u007f]/g;
const ID_ALPHABET = "23456789abcdefghjkmnpqrstuvwxyz";
const ID_LENGTH = 10;

function text(value, max) {
  return String(value ?? "")
    .replace(CONTROL, " ")
    .replace(STEAM64, "")
    .trim()
    .slice(0, max);
}

function int(value, min, max) {
  return Number.isInteger(value) && value >= min && value <= max ? value : null;
}

function list(value, max) {
  return Array.isArray(value) ? value.filter((item) => item && typeof item === "object").slice(0, max) : [];
}

export function shareId(bytes) {
  return [...bytes].slice(0, ID_LENGTH).map((b) => ID_ALPHABET[b % ID_ALPHABET.length]).join("");
}

export function isShareId(value) {
  return new RegExp(`^[${ID_ALPHABET}]{${ID_LENGTH}}$`).test(String(value || ""));
}

/** { ok, share: { installId, version, review } } or { ok: false, code, status }. */
export function validateShare(body) {
  if (!body || typeof body !== "object") {
    return { ok: false, code: "bad_request", status: 400 };
  }
  const installId = String(body.install_id || "").toLowerCase();
  if (!/^[a-z0-9-]{8,64}$/.test(installId)) {
    return { ok: false, code: "bad_install_id", status: 400 };
  }
  if (body.progress !== undefined) {
    const progress = validateProgress(body.progress);
    return progress ? { ok: true, share: { installId, version: text(body.version, 32), review: progress } } : { ok: false, code: "bad_progress", status: 400 };
  }
  const input = body.review;
  if (!input || typeof input !== "object") {
    return { ok: false, code: "bad_review", status: 400 };
  }
  const stats = {};
  for (const key of ["kills", "deaths", "assists", "gpm", "xpm", "last_hits", "denies", "net_worth", "hero_damage"]) {
    stats[key] = int(input.stats?.[key], 0, 1_000_000);
  }
  const review = {
    lang: input.lang === "en" ? "en" : "uk",
    hero: text(input.hero, 40),
    hero_key: /^[a-z0-9_]{1,40}$/.test(String(input.hero_key || "")) ? input.hero_key : null,
    win: typeof input.win === "boolean" ? input.win : null,
    duration: int(input.duration, 0, 4 * 3600),
    played_on: /^\d{4}-\d{2}-\d{2}$/.test(String(input.played_on || "")) ? input.played_on : null,
    score: int(input.score, 0, 100),
    grade: /^[A-F][+-]?$/.test(String(input.grade || "")) ? input.grade : null,
    role: text(input.role, 30) || null,
    parsed: input.parsed === true,
    stats,
    sections: list(input.sections, 6).map((s) => ({ label: text(s.label, 30), score: int(s.score, 0, 100) })),
    strengths: list(input.strengths, 3).map((f) => ({ title: text(f.title, 120), text: text(f.text, 400) })),
    improvements: list(input.improvements, 4).map((f) => ({
      title: text(f.title, 120),
      text: text(f.text, 400),
      drill: text(f.drill, 300) || null
    })),
    deaths:
      input.deaths && typeof input.deaths === "object"
        ? {
            count: int(input.deaths.count, 0, 200) ?? 0,
            enemy_half: int(input.deaths.enemy_half, 0, 200) ?? 0,
            unspent_gold: int(input.deaths.unspent_gold, 0, 200) ?? 0
          }
        : null,
    coach: text(input.coach, 800) || null
  };
  if (!review.hero) {
    return { ok: false, code: "bad_review", status: 400 };
  }
  return { ok: true, share: { installId, version: text(body.version, 32), review } };
}

const TREND_KEYS = ["score", "winrate", "gpm", "lh_10", "deaths"];
const AVERAGE_KEYS = ["kda", "gpm", "xpm", "lh_10", "deaths", "score"];

function number(value, min, max) {
  return typeof value === "number" && Number.isFinite(value) && value >= min && value <= max ? Math.round(value * 10) / 10 : null;
}

function isoDay(value) {
  return /^\d{4}-\d{2}-\d{2}$/.test(String(value || "")) ? value : null;
}

/** «Поділитися прогресом» (backend/app/share_progress.py): a new object from known fields. */
export function validateProgress(input) {
  if (!input || typeof input !== "object") {
    return null;
  }
  const analyzed = int(input.analyzed, 1, 10_000);
  if (analyzed === null) {
    return null;
  }
  const averages = {};
  for (const key of AVERAGE_KEYS) {
    averages[key] = number(input.averages?.[key], 0, 100_000);
  }
  const recurring = (items, max, drill) =>
    list(items, max).map((r) => ({
      title: text(r.title, 120),
      count: int(r.count, 0, 1000),
      of: int(r.of, 0, 1000),
      ...(drill ? { drill: text(r.drill, 300) || null } : {})
    }));
  const trendInput = list(input.trend, TREND_KEYS.length);
  return {
    kind: "progress",
    lang: input.lang === "en" ? "en" : "uk",
    matches: int(input.matches, 0, 10_000),
    analyzed,
    wins: int(input.wins, 0, 10_000),
    losses: int(input.losses, 0, 10_000),
    winrate: int(input.winrate, 0, 100),
    rank: text(input.rank, 30) || null,
    period:
      input.period && typeof input.period === "object"
        ? { from: isoDay(input.period.from), to: isoDay(input.period.to) }
        : null,
    averages,
    trend: TREND_KEYS.map((key) => trendInput.find((t) => t.key === key))
      .filter(Boolean)
      .map((t) => ({
        key: t.key,
        recent: number(t.recent, 0, 100_000),
        previous: number(t.previous, 0, 100_000),
        better: typeof t.better === "boolean" ? t.better : null
      })),
    heroes: list(input.heroes, 5).map((h) => ({
      hero: text(h.hero, 40),
      hero_key: /^[a-z0-9_]{1,40}$/.test(String(h.hero_key || "")) ? h.hero_key : null,
      matches: int(h.matches, 0, 10_000),
      winrate: int(h.winrate, 0, 100)
    })),
    strengths: recurring(input.strengths, 3, false),
    problems: recurring(input.problems, 3, true),
    focus:
      input.focus && typeof input.focus === "object" && text(input.focus.title, 120)
        ? { title: text(input.focus.title, 120), met: int(input.focus.met, 0, 1000) ?? 0, total: int(input.focus.total, 0, 1000) ?? 0 }
        : null,
    coach: text(input.coach, 800) || null
  };
}

// --- the page -----------------------------------------------------------------------

const TEXTS = {
  uk: {
    win: "Перемога",
    loss: "Поразка",
    score: "Оцінка розбору",
    of: "зі 100",
    kda: "В / С / Д",
    gpm: "Золото / досвід за хв",
    lh: "Добивання / денаї",
    damage: "Шкода по героях",
    sections: "За розділами",
    strengths: "Що вдалося",
    improvements: "Що покращити",
    drill: "Наступного разу",
    deaths: (d) => `Смертей: ${d.count}${d.enemy_half ? ` · на половині суперника: ${d.enemy_half}` : ""}${d.unspent_gold ? ` · з невитраченим золотом: ${d.unspent_gold}` : ""}`,
    coach: "Розбір ШІ-тренера",
    data: (parsed) => (parsed ? "Повний розбір реплею (OpenDota)" : "Дані матчу без розбору реплею"),
    made: "Розбір зроблено у Wardly — безкоштовному тренері з Dota 2: підказки під час гри й чесний розбір після.",
    cta: "Завантажити Wardly",
    expires: (date) => `Посилання працює до ${date}.`,
    missingTitle: "Розбір не знайдено",
    missing: "Посилання застаріло (розбори зберігаються 90 днів) або автор його видалив.",
    home: "На сайт Wardly",
    title: (r) => `${r.hero} · ${r.win === true ? "перемога" : r.win === false ? "поразка" : "матч"}${r.score !== null ? ` · оцінка ${r.score}` : ""}`,
    description: "Розбір матчу Dota 2 у Wardly: лінія, фарм, виживання, бійки й що покращити."
  },
  en: {
    win: "Win",
    loss: "Loss",
    score: "Review score",
    of: "of 100",
    kda: "K / D / A",
    gpm: "GPM / XPM",
    lh: "Last hits / denies",
    damage: "Hero damage",
    sections: "By area",
    strengths: "What went well",
    improvements: "What to improve",
    drill: "Next time",
    deaths: (d) => `Deaths: ${d.count}${d.enemy_half ? ` · on the enemy half: ${d.enemy_half}` : ""}${d.unspent_gold ? ` · with unspent gold: ${d.unspent_gold}` : ""}`,
    coach: "AI coach review",
    data: (parsed) => (parsed ? "Full replay review (OpenDota)" : "Match data without a parsed replay"),
    made: "Reviewed with Wardly, a free Dota 2 coach: advice during the game and an honest review after it.",
    cta: "Download Wardly",
    expires: (date) => `This link works until ${date}.`,
    missingTitle: "Review not found",
    missing: "The link has expired (reviews are kept for 90 days) or its author deleted it.",
    home: "Go to the Wardly website",
    title: (r) => `${r.hero} · ${r.win === true ? "win" : r.win === false ? "loss" : "match"}${r.score !== null ? ` · score ${r.score}` : ""}`,
    description: "A Dota 2 match review in Wardly: laning, farm, survival, fights and what to improve."
  }
};

export function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
}

function clock(seconds) {
  if (!Number.isInteger(seconds)) {
    return "—";
  }
  return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`;
}

/** "2026-09-21" -> "21.09.2026" (uk) / "21 Sep 2026" (en). */
function day(iso, lang) {
  const [y, m, d] = String(iso || "").split("-").map(Number);
  if (!y || !m || !d) {
    return "";
  }
  const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  return lang === "uk" ? `${String(d).padStart(2, "0")}.${String(m).padStart(2, "0")}.${y}` : `${d} ${months[m - 1]} ${y}`;
}

function num(value) {
  return value === null || value === undefined ? "—" : String(value).replace(/\B(?=(\d{3})+(?!\d))/g, " ");
}

const STYLE = `
:root{--bg:#0c0d0f;--card:#17181c;--line:rgba(255,255,255,.08);--text:#f3f3f4;--muted:#a0a2a9;--faint:#6d7078;--accent:#d23a46;--cream:#efe5d4;--good:#4fbf7f;--bad:#e5484d;color-scheme:dark}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:15px/1.55 Inter,system-ui,-apple-system,"Segoe UI",sans-serif}
main{max-width:760px;margin:0 auto;padding:24px 16px 48px}a{color:inherit}
.top{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:24px}.brand{display:flex;align-items:center;gap:10px;color:var(--text);text-decoration:none}.brand img{width:28px;height:28px}.brand b{font-size:18px}.try{padding:8px 14px;border-radius:10px;background:var(--accent);color:#fff;font-size:14px;font-weight:600;text-decoration:none;white-space:nowrap}.try:hover{filter:brightness(1.08)}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:20px;margin-bottom:16px}
.head{display:flex;gap:16px;align-items:center}.head img{width:112px;height:63px;border-radius:8px;object-fit:cover;background:#222}
.head h1{margin:0;font-size:24px}.meta{color:var(--muted);font-size:14px}.dot{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:6px}
.score{margin-left:auto;text-align:right}.score b{font-size:40px;line-height:1;font-variant-numeric:tabular-nums}.score span{display:block;color:var(--faint);font-size:12px}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px;margin-top:16px}.stats p{margin:0;color:var(--muted);font-size:13px}.stats b{font-size:17px;font-variant-numeric:tabular-nums}
h2{font-size:16px;margin:0 0 12px}.row{display:grid;grid-template-columns:120px 1fr 32px;gap:12px;align-items:center;margin:8px 0}
.bar{height:6px;border-radius:3px;background:rgba(255,255,255,.08);overflow:hidden}.bar i{display:block;height:100%;background:var(--cream)}
.row b{text-align:right;font-variant-numeric:tabular-nums}ul{list-style:none;margin:0;padding:0}li{margin:0 0 14px}li:last-child{margin:0}
li b{display:block}li p{margin:4px 0 0;color:var(--muted)}.drill{margin-top:8px;padding:8px 12px;border-radius:8px;background:rgba(255,255,255,.04);color:var(--muted);font-size:14px}
.coach{white-space:pre-line}.foot{color:var(--muted);font-size:14px}.cta{display:inline-block;margin-top:12px;padding:10px 18px;border-radius:10px;background:var(--accent);color:#fff;font-weight:600;text-decoration:none}
.small{color:var(--faint);font-size:13px;margin-top:12px}.trend{grid-template-columns:1fr auto}.heroes li{display:flex;gap:12px;align-items:center}.heroes img{width:64px;height:36px;border-radius:6px;object-fit:cover;background:#222}@media (max-width:520px){.head{flex-wrap:wrap}.score{margin-left:0;text-align:left}.row{grid-template-columns:96px 1fr 28px}}`;

export function page({ lang, title, description, image, url, body }) {
  return `<!doctype html>
<html lang="${lang}">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>${escapeHtml(title)} — Wardly</title>
<meta name="description" content="${escapeHtml(description)}" />
<meta name="robots" content="noindex" />
<meta property="og:type" content="article" />
<meta property="og:site_name" content="Wardly" />
<meta property="og:title" content="${escapeHtml(title)}" />
<meta property="og:description" content="${escapeHtml(description)}" />
${url ? `<meta property="og:url" content="${escapeHtml(url)}" />` : ""}
<meta property="og:image" content="${escapeHtml(image)}" />
<meta name="twitter:card" content="summary_large_image" />
<link rel="icon" href="${SITE_URL}/assets/favicon.png" type="image/png" />
<style>${STYLE}</style>
</head>
<body><main>
<header class="top"><a class="brand" href="${siteHome(lang)}"><img src="${SITE_URL}/assets/logo-mark.png" alt="" /><b>Wardly</b></a><a class="try" href="${siteHome(lang)}">${lang === "en" ? "Try it free" : "Спробувати безкоштовно"}</a></header>
${body}
</main></body>
</html>`;
}

const PROGRESS_TEXTS = {
  uk: {
    heading: "Прогрес у Dota 2",
    matches: (p) => `${p.matches ?? p.analyzed} матчів, з них розібрано ${p.analyzed}`,
    period: (from, to) => `${from} — ${to}`,
    record: "Перемоги / поразки",
    winrate: "Відсоток перемог",
    score: "Середня оцінка",
    kda: "KDA",
    gpm: "Золото / досвід за хв",
    lh10: "Добивання до 10:00",
    deaths: "Смертей за гру",
    trend: "Останні 10 матчів проти 10 до них",
    trendKeys: { score: "Оцінка", winrate: "Перемоги, %", gpm: "Золото за хв", lh_10: "Добивання до 10:00", deaths: "Смерті" },
    heroes: "Герої",
    heroGames: (h) => `${h.matches} матчів · ${h.winrate ?? "—"}% перемог`,
    strengths: "Що вдається",
    problems: "Над чим працювати",
    inMatches: (r) => (r.count !== null && r.of !== null ? `У ${r.count} з ${r.of} розібраних матчів` : ""),
    drill: "Вправа",
    focus: "Фокус",
    focusResult: (f) => `Виконано в ${f.met} з ${f.total} матчів`,
    coach: "Висновок ШІ-тренера",
    title: (p) => `Прогрес у Dota 2 · ${p.matches ?? p.analyzed} матчів${p.winrate !== null ? ` · ${p.winrate}% перемог` : ""}`,
    description: "Прогрес гравця Dota 2 у Wardly: цифри, герої, що вдається й над чим працювати."
  },
  en: {
    heading: "Dota 2 progress",
    matches: (p) => `${p.matches ?? p.analyzed} matches, ${p.analyzed} of them reviewed`,
    period: (from, to) => `${from} — ${to}`,
    record: "Wins / losses",
    winrate: "Win rate",
    score: "Average score",
    kda: "KDA",
    gpm: "GPM / XPM",
    lh10: "Last hits at 10:00",
    deaths: "Deaths a game",
    trend: "Last 10 matches against the 10 before",
    trendKeys: { score: "Score", winrate: "Wins, %", gpm: "GPM", lh_10: "Last hits at 10:00", deaths: "Deaths" },
    heroes: "Heroes",
    heroGames: (h) => `${h.matches} matches · ${h.winrate ?? "—"}% wins`,
    strengths: "What goes well",
    problems: "What to work on",
    inMatches: (r) => (r.count !== null && r.of !== null ? `In ${r.count} of ${r.of} reviewed matches` : ""),
    drill: "Drill",
    focus: "Focus",
    focusResult: (f) => `Met in ${f.met} of ${f.total} matches`,
    coach: "AI coach summary",
    title: (p) => `Dota 2 progress · ${p.matches ?? p.analyzed} matches${p.winrate !== null ? ` · ${p.winrate}% wins` : ""}`,
    description: "A Dota 2 player's progress in Wardly: numbers, heroes, what goes well and what to work on."
  }
};

function renderProgressPage(p, { url, expiresAt }) {
  // Shares from before 0.54 were stored as «ru»: everything but English reads in Ukrainian.
  const lang = p.lang === "en" ? "en" : "uk";
  const t = PROGRESS_TEXTS[lang];
  const base = TEXTS[lang];
  const top = p.heroes.find((h) => h.hero_key);
  const image = top ? `${PORTRAIT}/${top.hero_key}.png` : `${SITE_URL}/assets/og.jpg`;
  const a = p.averages || {};
  const period = p.period && p.period.from && p.period.to ? t.period(day(p.period.from, lang), day(p.period.to, lang)) : "";
  const meta = [escapeHtml(t.matches(p)), escapeHtml(p.rank || ""), escapeHtml(period)].filter(Boolean).join(" · ");
  const trend = p.trend.length
    ? `<section class="card"><h2>${t.trend}</h2>${p.trend
        .map((x) => {
          const tone = x.better === true ? "var(--good)" : x.better === false ? "var(--bad)" : "var(--faint)";
          return `<div class="row trend"><span>${escapeHtml(t.trendKeys[x.key] || x.key)}</span><span class="meta">${num(x.previous)} → <b style="color:${tone}">${num(x.recent)}</b></span></div>`;
        })
        .join("")}</section>`
    : "";
  const heroes = p.heroes.length
    ? `<section class="card"><h2>${t.heroes}</h2><ul class="heroes">${p.heroes
        .map(
          (h) =>
            `<li>${h.hero_key ? `<img src="${PORTRAIT}/${escapeHtml(h.hero_key)}.png" alt="" />` : ""}<div><b>${escapeHtml(h.hero)}</b><p>${escapeHtml(t.heroGames(h))}</p></div></li>`
        )
        .join("")}</ul></section>`
    : "";
  const recurring = (title, items) =>
    items.length
      ? `<section class="card"><h2>${title}</h2><ul>${items
          .map(
            (r) =>
              `<li><b>${escapeHtml(r.title)}</b><p>${escapeHtml(t.inMatches(r))}</p>${r.drill ? `<div class="drill">${t.drill}: ${escapeHtml(r.drill)}</div>` : ""}</li>`
          )
          .join("")}</ul></section>`
      : "";
  const body = `
<section class="card">
  <div class="head">
    <img src="${escapeHtml(image)}" alt="" />
    <div><h1>${t.heading}</h1><div class="meta">${meta}</div></div>
    ${p.winrate !== null ? `<div class="score"><b>${num(p.winrate)}%</b><span>${t.winrate}</span></div>` : ""}
  </div>
  <div class="stats">
    <div><p>${t.record}</p><b>${num(p.wins)} / ${num(p.losses)}</b></div>
    <div><p>${t.score}</p><b>${num(a.score)}</b></div>
    <div><p>${t.kda}</p><b>${num(a.kda)}</b></div>
    <div><p>${t.gpm}</p><b>${num(a.gpm)} / ${num(a.xpm)}</b></div>
    <div><p>${t.lh10}</p><b>${num(a.lh_10)}</b></div>
    <div><p>${t.deaths}</p><b>${num(a.deaths)}</b></div>
  </div>
</section>
${p.coach ? `<section class="card"><h2>${t.coach}</h2><p class="coach">${escapeHtml(p.coach)}</p></section>` : ""}
${p.focus ? `<section class="card"><h2>${t.focus}</h2><ul><li><b>${escapeHtml(p.focus.title)}</b><p>${escapeHtml(t.focusResult(p.focus))}</p></li></ul></section>` : ""}
${trend}
${recurring(t.problems, p.problems)}
${recurring(t.strengths, p.strengths)}
${heroes}
<section class="card foot">${base.made}<br /><a class="cta" href="${siteHome(lang)}">${base.cta}</a>
<p class="small">${escapeHtml(base.expires(day(new Date(expiresAt).toISOString().slice(0, 10), lang)))}</p></section>`;
  return page({ lang: lang, title: t.title(p), description: p.coach ? p.coach.slice(0, 200) : t.description, image, url, body });
}

export function renderSharePage(review, { url, expiresAt }) {
  const lang = review.lang === "en" ? "en" : "uk";
  const t = TEXTS[lang];
  if (review.kind === "progress") {
    return renderProgressPage(review, { url, expiresAt });
  }
  const portrait = review.hero_key ? `${PORTRAIT}/${review.hero_key}.png` : `${SITE_URL}/assets/og.jpg`;
  const result = review.win === true ? t.win : review.win === false ? t.loss : "";
  const tone = review.win === true ? "var(--good)" : "var(--bad)";
  const s = review.stats || {};
  const metaLine = [
    result ? `<span class="dot" style="background:${tone}"></span>${escapeHtml(result)}` : "",
    escapeHtml(clock(review.duration)),
    escapeHtml(review.role || ""),
    escapeHtml(day(review.played_on, lang))
  ]
    .filter(Boolean)
    .join(" · ");
  const sections = review.sections.length
    ? `<section class="card"><h2>${t.sections}</h2>${review.sections
        .map(
          (x) =>
            `<div class="row"><span>${escapeHtml(x.label)}</span><span class="bar"><i style="width:${Number(x.score) || 0}%"></i></span><b>${num(x.score)}</b></div>`
        )
        .join("")}</section>`
    : "";
  const findings = (title, items, drill) =>
    items.length
      ? `<section class="card"><h2>${title}</h2><ul>${items
          .map(
            (f) =>
              `<li><b>${escapeHtml(f.title)}</b><p>${escapeHtml(f.text)}</p>${
                drill && f.drill ? `<div class="drill">${t.drill}: ${escapeHtml(f.drill)}</div>` : ""
              }</li>`
          )
          .join("")}</ul></section>`
      : "";
  const body = `
<section class="card">
  <div class="head">
    <img src="${escapeHtml(portrait)}" alt="" />
    <div><h1>${escapeHtml(review.hero)}</h1><div class="meta">${metaLine}</div></div>
    ${review.score !== null ? `<div class="score"><b>${num(review.score)}</b><span>${t.of}${review.grade ? ` · ${escapeHtml(review.grade)}` : ""}</span></div>` : ""}
  </div>
  <div class="stats">
    <div><p>${t.kda}</p><b>${num(s.kills)} / ${num(s.deaths)} / ${num(s.assists)}</b></div>
    <div><p>${t.gpm}</p><b>${num(s.gpm)} / ${num(s.xpm)}</b></div>
    <div><p>${t.lh}</p><b>${num(s.last_hits)} / ${num(s.denies)}</b></div>
    <div><p>${t.damage}</p><b>${num(s.hero_damage)}</b></div>
  </div>
  ${review.deaths ? `<p class="small">${escapeHtml(t.deaths(review.deaths))}</p>` : ""}
  <p class="small">${t.data(review.parsed)}</p>
</section>
${review.coach ? `<section class="card"><h2>${t.coach}</h2><p class="coach">${escapeHtml(review.coach)}</p></section>` : ""}
${sections}
${findings(t.improvements, review.improvements, true)}
${findings(t.strengths, review.strengths, false)}
<section class="card foot">${t.made}<br /><a class="cta" href="${siteHome(lang)}">${t.cta}</a>
<p class="small">${escapeHtml(t.expires(day(new Date(expiresAt).toISOString().slice(0, 10), lang)))}</p></section>`;
  return page({
    lang: lang,
    title: t.title(review),
    description: review.coach ? review.coach.slice(0, 200) : t.description,
    image: portrait,
    url,
    body
  });
}

export function renderMissingPage(lang = "uk") {
  const t = TEXTS[lang] || TEXTS.uk;
  return page({
    lang,
    title: t.missingTitle,
    description: t.missing,
    image: `${SITE_URL}/assets/og.jpg`,
    url: null,
    body: `<section class="card"><h2>${t.missingTitle}</h2><p class="foot">${t.missing}</p><a class="cta" href="${siteHome(lang)}">${t.home}</a></section>`
  });
}
