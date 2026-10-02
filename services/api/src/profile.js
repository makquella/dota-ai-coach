// «Друзья»: the profile card a player chose to show (0.35).
//
// The launcher publishes the public part of its «Профиль» tab under a random
// 8-character id — the friend code — with a secret token only it holds
// (PUT /v1/profile/<id>, header x-profile-token). Friends read cards by code
// (POST /v1/profiles {ids}), and /p/<id> is the same card as a page to send
// to a chat. validateProfile() rebuilds the card from known fields only; there
// is no friend graph on the server: who follows whom stays on each computer.

import { SITE_URL, escapeHtml, page, siteHome } from "./share.js";

export const PROFILE_LIMITS = { bodyBytes: 16 * 1024, batch: 50 };
export const PROFILE_RATE_PER_HOUR = { install: 60, address: 120, read: 240 };
export const PROFILE_RETENTION_DAYS = 180;

const ID_ALPHABET = "23456789abcdefghjkmnpqrstuvwxyz";
const ID_LENGTH = 8;
const STEAM64 = /7656119\d{10}/g;
const CONTROL = /[\u0000-\u001f\u007f]/g;
const LOOK = /^(frame|banner|name|title)_[a-z0-9_]{1,30}$/;
const ACHIEVEMENT = /^[a-z_]{2,30}$/;

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

export function isProfileId(value) {
  return new RegExp(`^[${ID_ALPHABET}]{${ID_LENGTH}}$`).test(String(value || ""));
}

/** A friend code as people type it ("WD-4K7P 9QX2", any case) → the id, or null. */
export function normalizeCode(value) {
  const id = String(value || "")
    .toLowerCase()
    .replace(/^wd-?/, "")
    .replace(/[\s-]/g, "");
  return isProfileId(id) ? id : null;
}

/** { ok, put: { installId, version, profile } } or { ok: false, code, status }. */
export function validateProfile(body) {
  if (!body || typeof body !== "object") {
    return { ok: false, code: "bad_request", status: 400 };
  }
  const installId = String(body.install_id || "").toLowerCase();
  if (!/^[a-z0-9-]{8,64}$/.test(installId)) {
    return { ok: false, code: "bad_install_id", status: 400 };
  }
  const input = body.profile;
  if (!input || typeof input !== "object") {
    return { ok: false, code: "bad_profile", status: 400 };
  }
  const name = text(input.name, 32);
  if (!name) {
    return { ok: false, code: "bad_profile", status: 400 };
  }
  const equipped = {};
  for (const kind of ["frame", "banner", "name", "title"]) {
    const value = String(input.equipped?.[kind] || "");
    equipped[kind] = LOOK.test(value) && value.startsWith(`${kind}_`) ? value : null;
  }
  const achievements = (Array.isArray(input.achievements) ? input.achievements : [])
    .filter((a) => a && typeof a === "object" && ACHIEVEMENT.test(String(a.id || "")))
    .slice(0, 20)
    .map((a) => ({ id: a.id, tier: int(a.tier, 0, 6) ?? 0, title: text(a.title, 40) }));
  const stats = input.stats && typeof input.stats === "object" ? input.stats : {};
  const profile = {
    lang: input.lang === "en" ? "en" : "ru",
    name,
    title: text(input.title, 40) || null,
    level: int(input.level, 1, 999) ?? 1,
    rank_tier: int(input.rank_tier, 10, 80),
    rank_label: text(input.rank_label, 30) || null,
    mmr: int(input.mmr, 0, 15000),
    mmr_change: int(input.mmr_change, -5000, 5000),
    equipped,
    achievements,
    stats: {
      app_games: int(stats.app_games, 0, 1_000_000) ?? 0,
      app_winrate: int(stats.app_winrate, 0, 100),
      week_games: int(stats.week_games, 0, 1000) ?? 0
    }
  };
  return { ok: true, put: { installId, version: text(body.version, 32), profile } };
}

// --- the page -----------------------------------------------------------------

const TEXTS = {
  ru: {
    level: (n) => `Уровень ${n}`,
    games: "Матчей с Wardly",
    winrate: "Побед",
    rating: "Рейтинг (оценка)",
    achievements: "Награды",
    title: (p) => `${p.name} · уровень ${p.level} в Wardly`,
    description: (p) => `Профиль игрока Dota 2 в Wardly: уровень ${p.level}, ${p.stats.app_games} матчей с тренером.`,
    add: (code) => `Код друга: ${code} — добавьте в Wardly на вкладке «Профиль».`,
    missing: "Профиль не найден или скрыт."
  },
  en: {
    level: (n) => `Level ${n}`,
    games: "Matches with Wardly",
    winrate: "Wins",
    rating: "Rating (estimate)",
    achievements: "Achievements",
    title: (p) => `${p.name} · level ${p.level} in Wardly`,
    description: (p) => `A Dota 2 player's profile in Wardly: level ${p.level}, ${p.stats.app_games} matches with the coach.`,
    add: (code) => `Friend code: ${code} — add it in Wardly on the «Profile» tab.`,
    missing: "The profile is not there or is hidden."
  }
};

// The look of the card: a subset of the launcher's cos-<id> styles, static.
const BANNERS = {
  banner_dusk: "linear-gradient(115deg,#1f1735,#5b2a5c 45%,#c45a5a 80%,#e8945e)",
  banner_radiant: "linear-gradient(120deg,#123b2a,#2f7d4f 55%,#a8c95a)",
  banner_dire: "linear-gradient(120deg,#120607,#4a0e12 55%,#8f1d1d)",
  banner_aurora: "linear-gradient(120deg,#06121f,#0f5e5c,#3ddc97,#3a6bd6,#6b3fd6)",
  banner_ember: "radial-gradient(circle at 15% 85%,rgba(255,122,26,.6),transparent 30%),radial-gradient(circle at 55% 100%,rgba(232,54,30,.55),transparent 35%),#160806",
  banner_climb: "repeating-linear-gradient(60deg,rgba(240,85,96,.22) 0 14px,transparent 14px 28px),linear-gradient(0deg,#1a0d10,#3a1720 60%,#7a2a36)"
};
const FRAMES = {
  frame_bronze: "#b8753f",
  frame_silver: "linear-gradient(135deg,#e7eaf0,#8f96a3 60%,#dfe3ea)",
  frame_gold: "linear-gradient(135deg,#fff1b8,#e3b341 45%,#9a6b12 70%,#f6d77a)",
  frame_ice: "linear-gradient(160deg,#e6fbff,#7fd3ff 40%,#3a7bd5 75%,#c9f3ff)",
  frame_fire: "conic-gradient(#ffcf5c,#ff7a1a,#e8361e,#ffb03a,#ff5a1f,#ffcf5c)",
  frame_arcana: "conic-gradient(#ff5f6d,#ffc371,#f9f871,#3ddc97,#3ab0ff,#8a63ff,#ff5f6d)",
  frame_champion: "conic-gradient(from 45deg,#e3b341,#f05560,#e3b341,#f05560,#e3b341)"
};
const NAMES = { name_gold: "#f2c94c", name_ice: "#8fd8ff", name_toxic: "#8be36b", name_prism: "#c9a7ff" };
const TIER_COLORS = ["#3a3a42", "#c08457", "#b8bcc6", "#e3b341", "#6fc7c2", "#7aa7ff", "#f05560"];

export function friendCode(id) {
  return `WD-${String(id).toUpperCase()}`;
}

export function renderProfilePage(profile, { id, url }) {
  const lang = profile.lang === "en" ? "en" : "ru";
  const t = TEXTS[lang];
  const banner = BANNERS[profile.equipped?.banner] || "repeating-linear-gradient(-45deg,#1c1c21 0 10px,#151518 10px 20px)";
  const frame = FRAMES[profile.equipped?.frame] || "#f05560";
  const nameColor = NAMES[profile.equipped?.name] || "#f4f4f5";
  const initials = escapeHtml(profile.name.slice(0, 2).toUpperCase());
  const badges = profile.achievements
    .filter((a) => a.tier > 0)
    .map((a) => `<li><span class="medal" style="border-color:${TIER_COLORS[a.tier] || TIER_COLORS[0]};color:${TIER_COLORS[a.tier] || TIER_COLORS[0]}">${a.tier}</span>${escapeHtml(a.title)}</li>`)
    .join("");
  const tiles = [
    [t.games, String(profile.stats.app_games)],
    [t.winrate, profile.stats.app_winrate === null ? "—" : `${profile.stats.app_winrate}%`],
    profile.mmr !== null ? [t.rating, `≈ ${profile.mmr}`] : null
  ]
    .filter(Boolean)
    .map(([label, value]) => `<div class="tile"><p>${escapeHtml(label)}</p><b>${escapeHtml(value)}</b></div>`)
    .join("");
  const body = `<style>
.pcard{border:1px solid #2a2a30;border-radius:12px;overflow:hidden;background:#141417}
.pbanner{height:96px;background:${banner}}
.pid{display:flex;gap:16px;align-items:flex-end;padding:0 20px 18px;margin-top:-40px;flex-wrap:wrap}
.pring{width:96px;height:96px;border-radius:50%;background:${frame};display:grid;place-items:center;flex:none}
.pava{width:86px;height:86px;border-radius:50%;background:#1c1c21;box-shadow:0 0 0 3px #141417;display:grid;place-items:center;font-size:24px;font-weight:600;color:#a1a1aa}
.pname{font-size:28px;font-weight:600;color:${nameColor};margin:44px 0 2px}
.ptitle{font-size:12px;font-weight:600;letter-spacing:.08em;text-transform:uppercase;color:#e3b341;margin:0}
.pmeta{color:#a1a1aa;margin:4px 0 0}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px;margin:16px 0}
.tile{border:1px solid #2a2a30;border-radius:10px;padding:12px 16px}.tile p{margin:0;color:#71717a;font-size:12px}.tile b{font-size:22px}
.badges{list-style:none;padding:0;display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:8px}
.badges li{display:flex;gap:10px;align-items:center}.medal{width:28px;height:28px;border-radius:50%;border:2px solid;display:grid;place-items:center;font-weight:600;font-size:13px}
.code{color:#a1a1aa;margin-top:16px}
</style>
<section class="pcard"><div class="pbanner"></div><div class="pid"><div class="pring"><div class="pava">${initials}</div></div><div>
<p class="pname">${escapeHtml(profile.name)}</p>${profile.title ? `<p class="ptitle">${escapeHtml(profile.title)}</p>` : ""}
<p class="pmeta">${escapeHtml(t.level(profile.level))}${profile.rank_label ? ` · ${escapeHtml(profile.rank_label)}` : ""}</p></div></div></section>
<div class="tiles">${tiles}</div>
${badges ? `<h2>${escapeHtml(t.achievements)}</h2><ul class="badges">${badges}</ul>` : ""}
<p class="code">${escapeHtml(t.add(friendCode(id)))}</p>`;
  return page({
    lang,
    title: t.title(profile),
    description: t.description(profile),
    image: `${SITE_URL}/assets/og.jpg`,
    url,
    body
  });
}

export function renderMissingProfile(lang = "ru") {
  const t = TEXTS[lang === "en" ? "en" : "ru"];
  return page({
    lang: lang === "en" ? "en" : "ru",
    title: t.missing,
    description: t.missing,
    image: `${SITE_URL}/assets/og.jpg`,
    url: "",
    body: `<p>${escapeHtml(t.missing)}</p><p><a href="${siteHome(lang)}">Wardly</a></p>`
  });
}
