// The real overlay card (frontend/launcher/overlay) for each case in
// overlay_cases.json, at the overlay window's width (420 px), transparent
// background. Usage: node overlay_shots.js <out-dir> [app-url]
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
    const descriptor = Object.getOwnPropertyDescriptor(HTMLImageElement.prototype, "src");
    Object.defineProperty(HTMLImageElement.prototype, "src", {
      ...descriptor,
      set(value) {
        descriptor.set.call(this, String(value).replace(/^dota-asset:\/\//, "https://dota-asset.local/"));
      }
    });
  });
  await page.route("https://dota-asset.local/**", async (route) => {
    const response = await assets({ url: route.request().url().replace("https://dota-asset.local/", "dota-asset://") });
    await route.fulfill({ status: response.status, contentType: "image/png", body: Buffer.from(await response.arrayBuffer()) });
  });
}

const [outDir = "out", APP = "http://127.0.0.1:8766"] = process.argv.slice(2);
const cases = JSON.parse(fs.readFileSync(path.join(__dirname, "overlay_cases.json"), "utf8"));

(async () => {
  fs.mkdirSync(outDir, { recursive: true });
  const browser = await chromium.launch(process.env.CHROMIUM ? { executablePath: process.env.CHROMIUM } : {});
  for (const [lang, entries] of Object.entries(cases)) {
    for (const [name, data] of Object.entries(entries)) {
      // The overlay's CSP allows dota-asset: images only; the icons come from
      // the rewritten https://dota-asset.local/ address here.
      const page = await browser.newPage({ viewport: { width: 420, height: 320 }, deviceScaleFactor: 2, bypassCSP: true });
      page.on("pageerror", (error) => console.error(`${lang}/${name}:`, error.message));
      await serveDotaAssets(page);
      await page.addInitScript(([locale, answer]) => {
        window.overlayApi = {
          getConfig: async () => ({ locale, backendStatus: "running", locked: true, voice: "off", autoHideMs: 1e9, urgentAutoHideMs: 1e9 }),
          fetchRecommendation: async () => ({ ok: true, data: answer }),
          onConfigUpdated() {},
          onMuted() {},
          onRepeat() {},
          onToggleDebug() {}
        };
      }, [lang, data]);
      await page.goto(`${APP}/overlay/index.html`, { waitUntil: "networkidle" });
      await page.waitForTimeout(1200);
      await (await page.$(".overlay-shell")).screenshot({ path: path.join(outDir, `${lang}-${name}.png`), omitBackground: true });
      console.log(`${lang}-${name}.png`);
      await page.close();
    }
  }
  await browser.close();
})();
