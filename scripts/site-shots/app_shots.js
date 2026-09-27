// Screenshots of the real launcher renderer (frontend/launcher/renderer) on the
// demo backend, without Electron: window.launcherApi is stubbed and player ops
// go to the backend. Usage: node app_shots.js <out-dir> [backend-url] [app-url]
const fs = require("node:fs");
const path = require("node:path");
const { chromium } = require("playwright");

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
  "progress-ai": [{ click: "#tab-progress", wait: 2500 }, { eval: scrollTo(".coach-card") }]
};

(async () => {
  fs.mkdirSync(outDir, { recursive: true });
  const browser = await chromium.launch(process.env.CHROMIUM ? { executablePath: process.env.CHROMIUM } : {});
  for (const lang of ["ru", "en"]) {
    for (const [name, steps] of Object.entries(SHOTS)) {
      const page = await browser.newPage({ viewport: SIZE, deviceScaleFactor: 2, locale: lang === "ru" ? "ru-RU" : "en-US" });
      page.on("pageerror", (error) => console.error(`${lang}/${name}:`, error.message));
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
      for (const step of steps) {
        if (step.click) await page.click(step.click);
        if (step.eval) await page.evaluate(step.eval);
        await page.waitForTimeout(step.wait || 500);
      }
      await page.screenshot({ path: path.join(outDir, `${lang}-${name}.png`) });
      console.log(`${lang}-${name}.png`);
      await page.close();
    }
  }
  await browser.close();
})();
