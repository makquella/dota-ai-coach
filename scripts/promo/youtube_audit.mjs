// Read-only campaign audit. OAuth credentials stay in memory; only whitelisted
// publication/channel fields and aggregate analytics enter the artifact.
import { mkdir, writeFile } from 'node:fs/promises';
import { NETWORK_CLIENTS, unseal } from '../../services/api/src/social.js';

const required = name => {
  const value = process.env[name]?.trim();
  if (!value) throw new Error(`${name} is not configured`);
  return value;
};
const hidden = Object.entries(process.env).filter(([key]) => /TOKEN|SECRET/.test(key)).map(([, value]) => value).filter(Boolean);
const redact = value => hidden.reduce((result, secret) => result.split(secret).join('[redacted]'), String(value));
const report = { checked_at: new Date().toISOString(), read_only: true, errors: [] };

async function request(url, init = {}) {
  const response = await fetch(url, { ...init, signal: AbortSignal.timeout(45000) });
  const data = await response.json();
  if (!response.ok || data.success === false) {
    const reason = data.error?.errors?.[0]?.reason || data.error?.status || data.errors?.[0]?.code || 'request_failed';
    return { ok: false, status: response.status, reason };
  }
  return { ok: true, status: response.status, data };
}

try {
  const cfToken = required('CLOUDFLARE_API_TOKEN');
  const accountId = required('CLOUDFLARE_ACCOUNT_ID');
  const cfBase = `https://api.cloudflare.com/client/v4/accounts/${accountId}/d1/database`;
  const cfAuth = { authorization: `Bearer ${cfToken}`, 'content-type': 'application/json' };
  const databases = await request(cfBase, { headers: cfAuth });
  if (!databases.ok) throw new Error(`Cloudflare database list: HTTP ${databases.status} (${databases.reason})`);
  const database = databases.data.result.find(row => row.name === 'dota-ai-coach');
  if (!database) throw new Error('Wardly database not found');
  const query = async sql => {
    if (!/^SELECT /i.test(sql)) throw new Error('Audit permits SELECT statements only');
    const result = await request(`${cfBase}/${database.uuid}/query`, {
      method: 'POST', headers: cfAuth, body: JSON.stringify({ sql })
    });
    if (!result.ok) throw new Error(`Cloudflare read query: HTTP ${result.status} (${result.reason})`);
    return result.data.result[0].results;
  };
  const posts = await query("SELECT p.id, p.created_at, p.decided_at, p.topic, p.status AS post_status, p.body, d.status AS delivery_status, d.external_id, d.url, d.detail, d.updated_at FROM promo_posts p LEFT JOIN promo_deliveries d ON d.post_id = p.id AND d.network = 'youtube' WHERE p.topic LIKE 'beta-testers-%' ORDER BY p.created_at DESC LIMIT 12");
  report.campaign = posts.map(row => {
    const body = JSON.parse(row.body);
    return {
      package_id: row.id, topic: row.topic, created_at: new Date(row.created_at).toISOString(),
      decided_at: row.decided_at ? new Date(row.decided_at).toISOString() : null,
      post_status: row.post_status, delivery_status: row.delivery_status,
      video_id: row.external_id?.startsWith('upload:') ? null : row.external_id,
      url: row.url, delivery_detail: row.detail,
      requested: { title: body.youtube_title, language: body.youtube_language, tags: body.youtube_tags }
    };
  });
  const [stored] = await query("SELECT sealed FROM promo_accounts WHERE network = 'youtube'");
  if (!stored) throw new Error('YouTube is not connected');
  const credentials = await unseal({ ADMIN_TOKEN: required('API_ADMIN_TOKEN') }, stored.sealed);
  hidden.push(credentials.access_token, credentials.refresh_token);
  const env = { YOUTUBE_CLIENT_ID: required('YOUTUBE_CLIENT_ID'), YOUTUBE_CLIENT_SECRET: required('YOUTUBE_CLIENT_SECRET') };
  const fresh = await NETWORK_CLIENTS.youtube.fresh(env, credentials, Date.now());
  hidden.push(fresh.account.access_token);
  const auth = { authorization: `Bearer ${fresh.account.access_token}` };
  const google = async (route, params) => request(`https://www.googleapis.com/youtube/v3/${route}?${new URLSearchParams(params)}`, { headers: auth });
  const channel = await google('channels', { part: 'snippet,statistics,status', mine: 'true' });
  if (!channel.ok) throw new Error(`YouTube channel: HTTP ${channel.status} (${channel.reason})`);
  report.channels = channel.data.items.map(row => ({
    id: row.id, title: row.snippet.title, country: row.snippet.country,
    defaultLanguage: row.snippet.defaultLanguage, created_at: row.snippet.publishedAt,
    statistics: row.statistics, madeForKids: row.status?.madeForKids
  }));
  const ids = [...new Set(report.campaign.map(row => row.video_id).filter(Boolean))];
  if (ids.length) {
    const videos = await google('videos', { part: 'snippet,statistics,status,contentDetails,processingDetails,suggestions', id: ids.join(',') });
    if (!videos.ok) throw new Error(`YouTube videos: HTTP ${videos.status} (${videos.reason})`);
    report.videos = videos.data.items.map(row => ({
      id: row.id, url: `https://www.youtube.com/shorts/${row.id}`, published_at: row.snippet.publishedAt,
      age_hours: Math.round((Date.now() - Date.parse(row.snippet.publishedAt)) / 36000) / 100,
      title: row.snippet.title, description: row.snippet.description, tags: row.snippet.tags,
      defaultLanguage: row.snippet.defaultLanguage, defaultAudioLanguage: row.snippet.defaultAudioLanguage,
      categoryId: row.snippet.categoryId, statistics: row.statistics,
      privacyStatus: row.status.privacyStatus, uploadStatus: row.status.uploadStatus,
      rejectionReason: row.status.rejectionReason, failureReason: row.status.failureReason,
      madeForKids: row.status.madeForKids, duration: row.contentDetails.duration,
      regionRestriction: row.contentDetails.regionRestriction, contentRating: row.contentDetails.contentRating,
      processingStatus: row.processingDetails?.processingStatus,
      warnings: row.suggestions?.processingWarnings, errors: row.suggestions?.processingErrors
    }));
    const earliest = report.videos.map(row => row.published_at.slice(0, 10)).sort()[0];
    const analyticsUrl = 'https://youtubeanalytics.googleapis.com/v2/reports?' + new URLSearchParams({
      ids: 'channel==MINE', startDate: earliest, endDate: new Date().toISOString().slice(0, 10),
      metrics: 'views,estimatedMinutesWatched,averageViewDuration,averageViewPercentage',
      dimensions: 'video', filters: `video==${ids.join(',')}`
    });
    const analytics = await request(analyticsUrl, { headers: auth });
    report.analytics = analytics.ok
      ? { ok: true, columns: analytics.data.columnHeaders, rows: analytics.data.rows || [], note: 'Recent analytics may be delayed; no rows is not zero retention.' }
      : { ok: false, status: analytics.status, reason: analytics.reason, required_scope: 'https://www.googleapis.com/auth/yt-analytics.readonly' };
  }
  // Official references are public and independent of all credentialed calls.
  report.references = [];
  for (const [name, url] of [
    ['tags', 'https://support.google.com/youtube/answer/146402?hl=en'],
    ['shorts_discovery', 'https://support.google.com/youtube/answer/11914225?hl=en']
  ]) {
    const response = await fetch(url, { signal: AbortSignal.timeout(20000) });
    const html = await response.text();
    const plain = html.replace(/<script[\s\S]*?<\/script>/gi, '').replace(/<style[\s\S]*?<\/style>/gi, '').replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ');
    report.references.push({ name, url, status: response.status, excerpt: plain.slice(plain.indexOf(name === 'tags' ? 'Tags are' : 'Search and discovery'), plain.indexOf(name === 'tags' ? 'Tags are' : 'Search and discovery') + 11000) });
  }
} catch (error) {
  report.errors.push(redact(error.message));
  process.exitCode = 1;
}
await mkdir('promo-out', { recursive: true });
const serialized = JSON.stringify(report, null, 2);
if (hidden.filter(Boolean).some(value => value.length > 5 && serialized.includes(value))) throw new Error('Refusing to save a report containing credentials');
await writeFile('promo-out/youtube-audit.json', serialized + '\n');
console.log(JSON.stringify({ ok: !report.errors.length, videos: report.videos?.map(video => ({ id: video.id, language: video.defaultAudioLanguage, privacy: video.privacyStatus, views: video.statistics.viewCount, age_hours: video.age_hours })), analytics: report.analytics?.ok, errors: report.errors }));
