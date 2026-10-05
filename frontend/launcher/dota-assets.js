const fs = require("node:fs");
const path = require("node:path");

// Hero portraits and item icons for the panel and the overlay:
// dota-asset://hero/juggernaut, dota-asset://hero-icon/juggernaut, dota-asset://item/bfury,
// dota-asset://hero-crop/juggernaut (the hero to the waist on a transparent
// background, 400×250: the art of the review header and the current match).
// Each picture is downloaded once from Valve's CDN (the same files dota2.com
// and OpenDota use) and kept on disk, so it works offline afterwards. Without
// a picture the page shows its text fallback. No Electron imports, so it can
// be unit-tested with plain `node --test`.

const SCHEME = "dota-asset";
const CDN = "https://cdn.cloudflare.steamstatic.com/apps/dota2/images/dota_react";
const KINDS = {
  hero: "heroes",
  "hero-icon": "heroes/icons",
  "hero-crop": "heroes/crops",
  item: "items",
  // The game's minimap art for the match review's map (dota-asset://map/detailed_740):
  // Valve's picture as OpenDota publishes it (github.com/odota/web, public/assets).
  map: "map"
};
const MAP_BASE = "https://www.opendota.com/assets/images/dota2/map";
// PNG from Valve's CDN; the map is WebP.
const FORMATS = {
  png: { type: "image/png", check: (b) => b.length > 8 && b[0] === 0x89 && b[1] === 0x50 && b[2] === 0x4e && b[3] === 0x47 },
  webp: { type: "image/webp", check: (b) => b.length > 12 && b.toString("latin1", 0, 4) === "RIFF" && b.toString("latin1", 8, 12) === "WEBP" }
};
const formatOf = (kind) => (kind === "map" ? "webp" : "png");
const NAME_RE = /^[a-z0-9_]{1,64}$/;
// A picture that could not be downloaded is not asked for again for a while
// (offline, or a name the CDN does not know).
const RETRY_AFTER_MS = 10 * 60 * 1000;
const MAX_BYTES = 2 * 1024 * 1024;

function parseAssetUrl(url) {
  let parsed;
  try {
    parsed = new URL(String(url || ""));
  } catch {
    return null;
  }
  if (parsed.protocol !== `${SCHEME}:`) {
    return null;
  }
  const kind = parsed.hostname;
  const name = decodeURIComponent(parsed.pathname.replace(/^\/+/, "")).replace(/\.(png|webp)$/, "");
  if (!Object.hasOwn(KINDS, kind) || !NAME_RE.test(name)) {
    return null;
  }
  return { kind, name };
}

function cdnUrl(kind, name) {
  if (kind === "map") {
    return `${MAP_BASE}/${name}.webp`;
  }
  return `${CDN}/${KINDS[kind]}/${name}.png`;
}

function cachePath(root, kind, name) {
  return path.join(root, kind, `${name}.${formatOf(kind)}`);
}

function imageResponse(kind, buffer) {
  return new Response(buffer, {
    status: 200,
    headers: { "content-type": FORMATS[formatOf(kind)].type, "cache-control": "max-age=86400" }
  });
}

function notFound() {
  return new Response("", { status: 404 });
}

/**
 * Handler for protocol.handle(SCHEME, ...). `fetchImpl` is Electron's net.fetch
 * (system proxy aware); `root` is the cache folder.
 */
function createAssetHandler({ root, fetchImpl, fsImpl = fs, now = Date.now, log = () => {} }) {
  const failedUntil = new Map();
  const inFlight = new Map();

  async function download(kind, name, file) {
    const response = await fetchImpl(cdnUrl(kind, name));
    if (!response || !response.ok) {
      throw new Error(`HTTP ${response ? response.status : "?"}`);
    }
    const buffer = Buffer.from(await response.arrayBuffer());
    if (buffer.length > MAX_BYTES || !FORMATS[formatOf(kind)].check(buffer)) {
      throw new Error(`not a ${formatOf(kind).toUpperCase()}`);
    }
    fsImpl.mkdirSync(path.dirname(file), { recursive: true });
    fsImpl.writeFileSync(file, buffer);
    return buffer;
  }

  return async function handle(request) {
    const asset = parseAssetUrl(request && request.url);
    if (!asset) {
      return notFound();
    }
    const { kind, name } = asset;
    const file = cachePath(root, kind, name);
    try {
      return imageResponse(kind, fsImpl.readFileSync(file));
    } catch {
      // Not cached yet.
    }
    const key = `${kind}/${name}`;
    if ((failedUntil.get(key) || 0) > now()) {
      return notFound();
    }
    if (!inFlight.has(key)) {
      inFlight.set(
        key,
        download(kind, name, file).finally(() => inFlight.delete(key))
      );
    }
    try {
      return imageResponse(kind, await inFlight.get(key));
    } catch (error) {
      failedUntil.set(key, now() + RETRY_AFTER_MS);
      log(`${key}: ${error.message}`);
      return notFound();
    }
  };
}

module.exports = { CDN, KINDS, SCHEME, cachePath, cdnUrl, createAssetHandler, parseAssetUrl };
