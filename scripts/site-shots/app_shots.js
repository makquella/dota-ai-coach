// Screenshots of the real launcher renderer (frontend/launcher/renderer) on the
// demo backend, without Electron: window.launcherApi is stubbed and player ops
// go to the backend. Usage: node app_shots.js <out-dir> [backend-url] [app-url]
const fs = require("node:fs");
const path = require("node:path");
const { chromium } = require("playwright");
const { createAssetHandler } = require("../../frontend/launcher/dota-assets");

// Hero portraits and item icons: the app loads them from dota-asset:// (its
// main process). Here the same handler (dota-assets.js) serves them from a disk
// cache, downloading from Valve's CDN once. Node's fetch needs
// NODE_USE_ENV_PROXY=1 behind a proxy.
const assets = createAssetHandler({ root: process.env.ASSET_CACHE || path.join(require("node:os").tmpdir(), "dota-assets"), fetchImpl: fetch });

async function serveDotaAssets(page) {
  await page.addInitScript(() => {
    const local = (value) => String(value).replace(/^dota-asset:\/\//, "https://dota-asset.local/");
    const descriptor = Object.getOwnPropertyDescriptor(HTMLImageElement.prototype, "src");
    Object.defineProperty(HTMLImageElement.prototype, "src", {
      ...descriptor,
      set(value) {
        descriptor.set.call(this, local(value));
      }
    });
    // The match map is an SVG <image href="dota-asset://map/...">.
    const setAttribute = Element.prototype.setAttribute;
    Element.prototype.setAttribute = function (name, value) {
      return setAttribute.call(this, name, name === "href" ? local(value) : value);
    };
  });
  await page.route("https://dota-asset.local/**", async (route) => {
    const response = await assets({ url: route.request().url().replace("https://dota-asset.local/", "dota-asset://") });
    await route.fulfill({ status: response.status, contentType: response.headers.get("content-type") || "image/png", body: Buffer.from(await response.arrayBuffer()) });
  });
}

const [outDir = "out", BACKEND = "http://127.0.0.1:8777", APP = "http://127.0.0.1:8766"] = process.argv.slice(2);
const SIZE = { width: 720, height: 620 };

const ADVICE = {
  ru: [
    ["Навёрстывайте фарм по самому безопасному маршруту из волн и лагерей.", "medium", "18:01"],
    ["Держите свиток телепортации в слоте: купите его сейчас, курьер принесёт.", "medium", "15:12"],
    ["Уходите с волны сейчас и восстановите HP, прежде чем вернуться.", "high", "12:34"],
    ["Купите части следующего предмета на 1800 золота сейчас — заберёте их у фонтана.", "medium", "9:40"]
  ],
  en: [
    ["Recover farm through the safest wave-and-camp route.", "medium", "18:01"],
    ["Keep a TP scroll in its slot: buy one now, the courier can bring it.", "medium", "15:12"],
    ["Leave the wave now and reset HP before rejoining.", "high", "12:34"],
    ["Buy parts of your next item now with your 1800 gold: they wait for you at the fountain.", "medium", "9:40"]
  ]
};

function status(lang) {
  return {
    locale: lang,
    language: lang,
    live: { connected: true, inMatch: true, hero: "Juggernaut", coverage: "full", clockTime: 1134, secondsSinceLastGsi: 0.4, stage: "game" },
    recentAdvice: ADVICE[lang].map(([action, priority, time], i) => ({ timestamp: 10 - i, action, priority, game_time: time })),
    overlayPosition: "top-right",
    overlayVoice: { mode: "urgent", volume: 0.8 },
    overlaySize: "normal",
    adviceFrequency: "normal",
    overlayLocked: true,
    dotaRunning: true,
    dotaFocused: true,
    dotaFullscreen: false,
    appVersion: "0.2.0",
    update: { state: "idle" },
    player: { linked: true, name: "farm_or_die", accountId: 52079950, lastReview: null, aiConfigured: true, opendotaKey: false, liveMatch: null, today: null },
    setup: { gsiSeen: true, dismissed: true },
    whatsNew: "",
    overlayReasonCode: "in_game",
    backend: "running",
    backendPort: 8000,
    backendUrl: "http://127.0.0.1:8000",
    gsiEndpoint: "http://127.0.0.1:8000/gsi",
    overlay: "running",
    overlayVisible: true,
    overlayReason: "",
    dota: "in_game",
    dotaDir: "C:\\Steam\\steamapps\\common\\dota 2 beta",
    launchOption: "ok",
    demo: "stopped",
    demoPreset: "",
    recording: "stopped",
    gsiConfig: "installed",
    gsiPath: "",
    mode: "live",
    llm: "off",
    logMode: "normal",
    autostart: true,
    autostartSupported: true
  };
}

// The launcher's PLAYER_OPS (main.js), for the read-only ops the pages use.
function playerRequest(lang, op, args = {}) {
  const hero = args.heroId ? `&hero_id=${args.heroId}` : "";
  switch (op) {
    case "status":
      return "/player";
    case "matches":
      return `/player/matches?limit=${args.limit || 30}&offset=${args.offset || 0}${hero}${args.result ? `&result=${args.result}` : ""}`;
    case "match":
      return `/player/matches/${args.matchId || args.id}?lang=${lang}`;
    case "career":
      return `/player/career?lang=${lang}${hero}`;
    case "week":
      return `/player/week?lang=${lang}`;
    case "friend":
      return `/player/friend?lang=${lang}&group=${args.group || "all"}`;
    case "aiStatus":
      return "/player/ai";
    case "opendotaStatus":
      return "/player/opendota";
    default:
      return null;
  }
}

const scrollTo = (selector) => `(() => { const el = document.querySelector(${JSON.stringify(selector)}); if (el) window.scrollTo(0, el.getBoundingClientRect().top + window.scrollY - 16); })()`;

// name -> steps; every step list starts on the Home tab.
const SHOTS = {
  home: [],
  matches: [{ click: "#tab-matches", wait: 1500 }],
  review: [{ click: "#tab-matches", wait: 1500 }, { click: "tr.row-link", wait: 2500 }],
  "review-ai": [{ click: "#tab-matches", wait: 1500 }, { click: "tr.row-link", wait: 2500 }, { eval: scrollTo(".coach-card") }],
  progress: [{ click: "#tab-progress", wait: 2500 }],
  "progress-ai": [{ click: "#tab-progress", wait: 2500 }, { eval: scrollTo(".coach-card") }],
  "progress-friend": [{ click: "#tab-progress", wait: 3000 }, { eval: scrollTo(".friend-card") }]
};

// Single cards of the match review (by their title), for the site's detail row.
const CARDS = {
  map: { ru: "Карта матча", en: "Match map" },
  build: { ru: "Сборка", en: "Build" },
  chart: { ru: "По ходу матча", en: "Over the match" }
};

async function openPage(browser, lang, label) {
  const page = await browser.newPage({ viewport: SIZE, deviceScaleFactor: 2, locale: lang === "ru" ? "ru-RU" : "en-US" });
  page.on("pageerror", (error) => console.error(`${lang}/${label}:`, error.message));
  await serveDotaAssets(page);
  await page.exposeFunction("__player", async (op, args) => {
    const endpoint = playerRequest(lang, op, args);
    if (!endpoint) {
      return { ok: false, code: "unknown_op" };
    }
    const response = await fetch(BACKEND + endpoint);
    return response.ok ? { ok: true, data: await response.json() } : { ok: false, status: response.status };
  });
  await page.addInitScript((current) => {
    const noop = async () => ({ ok: true });
    window.launcherApi = new Proxy(
      {
        getStatus: async () => current,
        getLogs: async () => [],
        player: (op, args) => window.__player(op, args),
        onPlayerEvent() {},
        onStatus() {},
        onLogs() {}
      },
      { get: (target, key) => (key in target ? target[key] : noop) }
    );
  }, status(lang));
  await page.goto(`${APP}/renderer/index.html`, { waitUntil: "networkidle" });
  await page.waitForTimeout(800);
  return page;
}

// Pictures are lazy: scroll the whole page once so every one of them loads.
async function loadPictures(page) {
  const height = await page.evaluate(() => document.documentElement.scrollHeight);
  for (let y = 0; y < height; y += 400) {
    await page.evaluate((top) => window.scrollTo(0, top), y);
    await page.waitForTimeout(60);
  }
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.waitForTimeout(1200);
}

(async () => {
  fs.mkdirSync(outDir, { recursive: true });
  const browser = await chromium.launch(process.env.CHROMIUM ? { executablePath: process.env.CHROMIUM } : {});
  for (const lang of ["ru", "en"]) {
    for (const [name, steps] of Object.entries(SHOTS)) {
      const page = await openPage(browser, lang, name);
      for (const step of steps) {
        if (step.click) await page.click(step.click);
        if (step.eval) await page.evaluate(step.eval);
        await page.waitForTimeout(step.wait || 500);
      }
      await loadPictures(page);
      for (const step of steps.filter((item) => item.eval)) {
        await page.evaluate(step.eval);
      }
      await page.waitForTimeout(300);
      await page.screenshot({ path: path.join(outDir, `${lang}-${name}.png`) });
      console.log(`${lang}-${name}.png`);
      await page.close();
    }
    const page = await openPage(browser, lang, "cards");
    await page.click("#tab-matches");
    await page.waitForTimeout(1500);
    await page.click("tr.row-link");
    await page.waitForTimeout(2500);
    await loadPictures(page);
    for (const [name, titles] of Object.entries(CARDS)) {
      const card = page.locator("section.card", { has: page.locator("h2", { hasText: new RegExp(`^${titles[lang]}$`) }) }).first();
      await card.scrollIntoViewIfNeeded();
      await page.waitForTimeout(400);
      await card.screenshot({ path: path.join(outDir, `${lang}-card-${name}.png`) });
      console.log(`${lang}-card-${name}.png`);
    }
    await page.close();
  }
  await browser.close();
})();
