// «Поделиться разбором»: a match review the player chose to publish.
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
  const input = body.review;
  if (!input || typeof input !== "object") {
    return { ok: false, code: "bad_review", status: 400 };
  }
  const stats = {};
  for (const key of ["kills", "deaths", "assists", "gpm", "xpm", "last_hits", "denies", "net_worth", "hero_damage"]) {
    stats[key] = int(input.stats?.[key], 0, 1_000_000);
  }
  const review = {
    lang: input.lang === "ru" ? "ru" : "en",
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

// --- the page -----------------------------------------------------------------------

const TEXTS = {
  ru: {
    win: "Победа",
    loss: "Поражение",
    score: "Оценка разбора",
    of: "из 100",
    kda: "У / С / П",
    gpm: "Золото / опыт в мин",
    lh: "Добивания / денаи",
    damage: "Урон по героям",
    sections: "По разделам",
    strengths: "Что получилось",
    improvements: "Что улучшить",
    drill: "В следующий раз",
    deaths: (d) => `Смертей: ${d.count}${d.enemy_half ? ` · на половине противника: ${d.enemy_half}` : ""}${d.unspent_gold ? ` · с непотраченным золотом: ${d.unspent_gold}` : ""}`,
    coach: "Разбор ИИ-тренера",
    data: (parsed) => (parsed ? "Полный разбор реплея (OpenDota)" : "Данные матча без разбора реплея"),
    made: "Разбор сделан в Wardly — бесплатном тренере по Dota 2: подсказки во время игры и честный разбор после.",
    cta: "Скачать Wardly",
    expires: (date) => `Ссылка работает до ${date}.`,
    missingTitle: "Разбор не найден",
    missing: "Ссылка устарела (разборы хранятся 90 дней) или автор её удалил.",
    home: "На сайт Wardly",
    title: (r) => `${r.hero} · ${r.win === true ? "победа" : r.win === false ? "поражение" : "матч"}${r.score !== null ? ` · оценка ${r.score}` : ""}`,
    description: "Разбор матча Dota 2 в Wardly: линия, фарм, выживание, драки и что улучшить."
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

/** "2026-09-21" -> "21.09.2026" (ru) / "21 Sep 2026" (en). */
function day(iso, lang) {
  const [y, m, d] = String(iso || "").split("-").map(Number);
  if (!y || !m || !d) {
    return "";
  }
  const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  return lang === "ru" ? `${String(d).padStart(2, "0")}.${String(m).padStart(2, "0")}.${y}` : `${d} ${months[m - 1]} ${y}`;
}

function num(value) {
  return value === null || value === undefined ? "—" : String(value).replace(/\B(?=(\d{3})+(?!\d))/g, " ");
}

const STYLE = `
:root{--bg:#0c0d0f;--card:#17181c;--line:rgba(255,255,255,.08);--text:#f3f3f4;--muted:#a0a2a9;--faint:#6d7078;--accent:#f2b33d;--good:#4fbf7f;--bad:#e5484d;color-scheme:dark}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:15px/1.55 Inter,system-ui,-apple-system,"Segoe UI",sans-serif}
main{max-width:760px;margin:0 auto;padding:24px 16px 48px}a{color:inherit}
.top{display:flex;align-items:center;gap:10px;margin-bottom:24px;text-decoration:none}.top img{width:28px;height:28px}.top b{font-size:18px}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:20px;margin-bottom:16px}
.head{display:flex;gap:16px;align-items:center}.head img{width:112px;height:63px;border-radius:8px;object-fit:cover;background:#222}
.head h1{margin:0;font-size:24px}.meta{color:var(--muted);font-size:14px}.dot{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:6px}
.score{margin-left:auto;text-align:right}.score b{font-size:40px;line-height:1;font-variant-numeric:tabular-nums}.score span{display:block;color:var(--faint);font-size:12px}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px;margin-top:16px}.stats p{margin:0;color:var(--muted);font-size:13px}.stats b{font-size:17px;font-variant-numeric:tabular-nums}
h2{font-size:16px;margin:0 0 12px}.row{display:grid;grid-template-columns:120px 1fr 32px;gap:12px;align-items:center;margin:8px 0}
.bar{height:6px;border-radius:3px;background:rgba(255,255,255,.08);overflow:hidden}.bar i{display:block;height:100%;background:var(--accent)}
.row b{text-align:right;font-variant-numeric:tabular-nums}ul{list-style:none;margin:0;padding:0}li{margin:0 0 14px}li:last-child{margin:0}
li b{display:block}li p{margin:4px 0 0;color:var(--muted)}.drill{margin-top:8px;padding:8px 12px;border-radius:8px;background:rgba(255,255,255,.04);color:var(--muted);font-size:14px}
.coach{white-space:pre-line}.foot{color:var(--muted);font-size:14px}.cta{display:inline-block;margin-top:12px;padding:10px 18px;border-radius:10px;background:var(--accent);color:#17120a;font-weight:600;text-decoration:none}
.small{color:var(--faint);font-size:13px;margin-top:12px}@media (max-width:520px){.head{flex-wrap:wrap}.score{margin-left:0;text-align:left}.row{grid-template-columns:96px 1fr 28px}}`;

function page({ lang, title, description, image, url, body }) {
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
<a class="top" href="${SITE_URL}/"><img src="${SITE_URL}/assets/logo-mark.png" alt="" /><b>Wardly</b></a>
${body}
</main></body>
</html>`;
}

export function renderSharePage(review, { url, expiresAt }) {
  const t = TEXTS[review.lang] || TEXTS.en;
  const portrait = review.hero_key ? `${PORTRAIT}/${review.hero_key}.png` : `${SITE_URL}/assets/og.jpg`;
  const result = review.win === true ? t.win : review.win === false ? t.loss : "";
  const tone = review.win === true ? "var(--good)" : "var(--bad)";
  const s = review.stats || {};
  const metaLine = [
    result ? `<span class="dot" style="background:${tone}"></span>${escapeHtml(result)}` : "",
    escapeHtml(clock(review.duration)),
    escapeHtml(review.role || ""),
    escapeHtml(day(review.played_on, review.lang))
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
<section class="card foot">${t.made}<br /><a class="cta" href="${SITE_URL}/">${t.cta}</a>
<p class="small">${escapeHtml(t.expires(day(new Date(expiresAt).toISOString().slice(0, 10), review.lang)))}</p></section>`;
  return page({
    lang: review.lang,
    title: t.title(review),
    description: review.coach ? review.coach.slice(0, 200) : t.description,
    image: portrait,
    url,
    body
  });
}

export function renderMissingPage(lang = "ru") {
  const t = TEXTS[lang] || TEXTS.ru;
  return page({
    lang,
    title: t.missingTitle,
    description: t.missing,
    image: `${SITE_URL}/assets/og.jpg`,
    url: null,
    body: `<section class="card"><h2>${t.missingTitle}</h2><p class="foot">${t.missing}</p><a class="cta" href="${SITE_URL}/">${t.home}</a></section>`
  });
}
