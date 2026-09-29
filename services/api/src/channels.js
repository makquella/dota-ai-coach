// Where players come from: visits to the site and installer downloads per
// source and day (the posts link to luhovyimvp.dev/?ref=<source>; the site's
// download buttons go through GET /d/<source>). Numbers only: no cookies,
// URLs, IP addresses or ids are stored — one row per day and source.

export const CHANNEL_RETENTION_DAYS = 365;
// Per IP and hour: more is still redirected, just not counted.
export const CHANNEL_RATE_PER_HOUR = { visit: 30, download: 10 };
// A day holds at most this many sources; later new ones count as "other".
export const CHANNEL_MAX_SOURCES = 60;

const REPO = "makquella/dota-ai-coach";
export const RELEASES_PAGE = `https://github.com/${REPO}/releases/latest`;
const SOURCE = /^[a-z0-9][a-z0-9_-]{0,23}$/;

/** The source name as stored, or null (the caller then counts nothing). */
export function channelSource(value) {
  const src = String(value || "").trim().toLowerCase();
  return SOURCE.test(src) ? src : null;
}

/** The installer of the release `releases/latest` redirects to (…/releases/tag/v1.2.3). */
export function installerUrl(location) {
  const tag = String(location || "").match(/\/releases\/tag\/v(\d{1,3}\.\d{1,3}\.\d{1,3})$/);
  return tag ? `https://github.com/${REPO}/releases/download/v${tag[1]}/Wardly-Setup-${tag[1]}.exe` : null;
}

let latest = { url: null, at: 0 };

/** The latest installer's URL, looked up at most every 10 minutes; the releases page when unknown. */
export async function latestInstaller(fetchImpl = fetch, now = Date.now()) {
  if (latest.url && now - latest.at < 10 * 60_000) {
    return latest.url;
  }
  try {
    const response = await fetchImpl(RELEASES_PAGE, {
      method: "HEAD",
      redirect: "manual",
      headers: { "user-agent": "wardly-api" }
    });
    const url = installerUrl(response.headers.get("location"));
    if (url) {
      latest = { url, at: now };
      return url;
    }
  } catch {
    // GitHub unreachable: the releases page still works.
  }
  return latest.url || RELEASES_PAGE;
}

export function resetInstallerCache() {
  latest = { url: null, at: 0 };
}

/** Sums over stored rows ({ day, src, visits, downloads }), most visits first. */
export function aggregateChannels(rows) {
  const bySource = new Map();
  for (const row of rows) {
    const item = bySource.get(row.src) || { src: row.src, visits: 0, downloads: 0 };
    item.visits += Number(row.visits) || 0;
    item.downloads += Number(row.downloads) || 0;
    bySource.set(row.src, item);
  }
  return [...bySource.values()]
    .map((item) => ({ ...item, rate: item.visits ? Math.round((100 * item.downloads) / item.visits) : null }))
    .sort((a, b) => b.visits - a.visits || b.downloads - a.downloads || a.src.localeCompare(b.src));
}
