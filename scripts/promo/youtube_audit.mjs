// Read-only campaign audit. OAuth credentials stay in memory; only whitelisted
// publication/channel fields and aggregate analytics enter the artifact.
import { copyFile, mkdir, writeFile } from 'node:fs/promises';
import { NETWORK_CLIENTS, unseal } from '../../services/api/src/social.js';

const required = name => {
  const value = process.env[name]?.trim();
  if (!value) throw new Error(`${name} is not configured`);
  return value;
};
const hidden = Object.entries(process.env).filter(([key]) => /TOKEN|SECRET/.test(key)).map(([, value]) => value).filter(Boolean);
const redact = value => hidden.reduce((result, secret) => result.split(secret).join('[redacted]'), String(value));
const report = { checked_at: new Date().toISOString(), read_only: true, errors: [], warnings: [] };

// These channels were manually selected from the public search by language and
// relevance. A public contact is a way to ask, never permission to advertise.
const selectedCreators = [
  ['uk', 'UCQut_NvqjmTcYjlAI6es80w', 'hFHKjO-j6h0'],
  ['uk', 'UCkei_sEPZde5SRYUxPWQ97Q', 'YYOCJgFf3Q8'],
  ['uk', 'UCwqbubdeglCU60ntcz7A-7w', 'QL_4xrLzPRc'],
  ['uk', 'UCXjZjHhyrkODi2PBNvHrRvw', 'ggG8BLsFvV0'],
  ['en', 'UC4GP0zkMKGbXicHNx3UckSw', 'CvaGSR9ZfWw'],
  ['en', 'UCYldE7tGQHjNwIVHQ7bDNoA', 'J6m5LDaP_B0']
];
function publicContacts(description = '') {
  const urls = [...new Set(description.match(/https?:\/\/[^\s<>"\u200b]+/gu) || [])];
  return {
    links: urls.map(url => url.replace(/[),.;!?]+$/, '')).filter(url => {
      try {
        return /(^|\.)(t\.me|telegram\.me|discord\.gg|discord\.com|twitch\.tv|instagram\.com|twitter\.com|x\.com|facebook\.com|maincast\.com)$/.test(new URL(url).hostname);
      } catch { return false; }
    }),
    emails: [...new Set(description.match(/[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/gi) || [])]
  };
}

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
  report.tracked_site_sources = await query("SELECT day, src, visits, downloads FROM channel_counts WHERE (src IN ('promo-beta-uk', 'promo-beta-en') OR src LIKE 'shorts-%') AND day >= date('now', '-7 days') ORDER BY day, src");
  report.attribution_note = 'Visits/downloads are aggregate source counters, not unique people or confirmed testers. Missing rows are not proof of no visits (beacons may be blocked).';
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
  // Public, active channels for a targeted outreach shortlist. This only reads
  // search results; it does not post comments or contact any creator.
  const candidates = [];
  const publishedAfter = new Date(Date.now() - 90 * 86400000).toISOString();
  for (const [language, q] of [
    ['uk', 'Dota 2 українською'], ['uk', 'Dota 2 Свен українською'],
    ['en', 'Dota 2 carry low mmr coaching']
  ]) {
    const search = await google('search', { part: 'snippet', type: 'video', q, relevanceLanguage: language, publishedAfter, maxResults: '8' });
    if (!search.ok) { report.errors.push(`Public search: HTTP ${search.status} (${search.reason})`); continue; }
    for (const item of search.data.items || []) candidates.push({
      language, channel_id: item.snippet.channelId, channel_title: item.snippet.channelTitle,
      sample_title: item.snippet.title, sample_url: `https://www.youtube.com/watch?v=${item.id.videoId}`,
      sample_published_at: item.snippet.publishedAt
    });
  }
  const creatorIds = [...new Set(candidates.map(row => row.channel_id))];
  if (creatorIds.length) {
    const creators = await google('channels', { part: 'snippet,statistics', id: creatorIds.join(',') });
    if (creators.ok) report.outreach_candidates = creators.data.items.map(row => ({
      channel_id: row.id, title: row.snippet.title, url: `https://www.youtube.com/channel/${row.id}`,
      subscribers: row.statistics.subscriberCount,
      examples: candidates.filter(candidate => candidate.channel_id === row.id)
    }));
  }
  const [contactChannels, contactVideos] = await Promise.all([
    google('channels', { part: 'snippet', id: selectedCreators.map(row => row[1]).join(',') }),
    google('videos', { part: 'snippet', id: selectedCreators.map(row => row[2]).join(',') })
  ]);
  report.public_contacts = selectedCreators.map(([language, channelId, videoId]) => {
    const channel = contactChannels.data?.items?.find(row => row.id === channelId);
    const video = contactVideos.data?.items?.find(row => row.id === videoId && row.snippet.channelId === channelId);
    return {
      language, channel_id: channelId, title: channel?.snippet.title,
      sources: [
        channel && { url: `https://www.youtube.com/channel/${channelId}/about`, ...publicContacts(channel.snippet.description) },
        video && { url: `https://www.youtube.com/watch?v=${videoId}`, ...publicContacts(video.snippet.description) }
      ].filter(Boolean),
      contacted: false, community_post_permission: 'not requested'
    };
  });
  for (const result of [contactChannels, contactVideos]) {
    if (!result.ok) report.warnings.push(`Public contacts: HTTP ${result.status} (${result.reason})`);
  }
  const communityUrls = [...new Set(report.public_contacts.flatMap(row => row.sources.flatMap(source => source.links)))].filter(url => /https:\/\/(t\.me|discord\.gg|discord\.com)\//.test(url) && !/\/\d+\/?$/.test(url));
  report.public_community_checks = await Promise.all(communityUrls.map(async url => {
    try {
      if (url.includes('discord.')) {
        const code = new URL(url).pathname.split('/').filter(Boolean).at(-1);
        const result = await request(`https://discord.com/api/v10/invites/${code}?with_counts=true`);
        return { url, status: result.status, available: result.ok, community: result.data?.guild?.name, member_count: result.data?.approximate_member_count, rules_verified: false };
      }
      const response = await fetch(url, { signal: AbortSignal.timeout(15000) });
      const html = await response.text();
      const metas = [...html.matchAll(/<meta\s+property="og:(title|description)"\s+content="([^"]*)"/g)];
      return { url, status: response.status, available: response.ok, public_preview: Object.fromEntries(metas.map(([, key, value]) => [key, value.replace(/&amp;/g, '&').replace(/&#(?:39|x27);/g, "'").replace(/&quot;/g, '"')])), rules_verified: false };
    } catch (error) {
      return { url, available: false, error: redact(error.message), rules_verified: false };
    }
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
      : { ok: false, status: analytics.status, reason: analytics.reason, service_enable_required: analytics.reason === 'accessNotConfigured', required_scope: 'https://www.googleapis.com/auth/yt-analytics.readonly' };
  }
  // Official references are public and independent of all credentialed calls.
  report.references = [];
  for (const [name, url] of [
    ['tags', 'https://support.google.com/youtube/answer/146402?hl=en'],
    ['shorts_discovery', 'https://support.google.com/youtube/answer/11914225?hl=en']
  ]) {
    try {
      const response = await fetch(url, { signal: AbortSignal.timeout(20000) });
      const html = await response.text();
      const plain = html.replace(/<script[\s\S]*?<\/script>/gi, '').replace(/<style[\s\S]*?<\/style>/gi, '').replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ');
      const terms = name === 'tags' ? ['Tags are', 'minimal role'] : ['performance', 'personalization', 'average view duration', 'minimum posting', 'competition', 'topic interest'];
      const excerpts = terms.map(term => {
        const at = plain.toLowerCase().indexOf(term.toLowerCase());
        return at < 0 ? null : plain.slice(Math.max(0, at - 150), at + 900);
      }).filter(Boolean);
      report.references.push({ name, url, status: response.status, excerpts });
    } catch (error) {
      report.references.push({ name, url, verified: false, error: redact(error.message) });
      report.warnings.push(`Optional reference ${name}: ${redact(error.message)}`);
    }
  }
  report.community_rules = [];
  for (const name of ['DotA2', 'learndota2']) {
    const url = `https://www.reddit.com/r/${name}/about/rules.json`;
    try {
      const response = await fetch(url, { headers: { 'user-agent': 'Wardly research (read-only)' }, signal: AbortSignal.timeout(20000) });
      if (!response.ok) { report.community_rules.push({ community: name, url, status: response.status, verified: false }); continue; }
      const data = await response.json();
      report.community_rules.push({ community: name, url, status: response.status, verified: true, rules: data.rules?.map(rule => ({ title: rule.short_name, description: rule.description })) });
    } catch (error) {
      report.community_rules.push({ community: name, url, verified: false, error: redact(error.message) });
      report.warnings.push(`Optional community rules ${name}: ${redact(error.message)}`);
    }
  }
} catch (error) {
  report.errors.push(redact(error.message));
  process.exitCode = 1;
}
await mkdir('promo-out', { recursive: true });
const serialized = JSON.stringify(report, null, 2);
if (hidden.filter(Boolean).some(value => value.length > 5 && serialized.includes(value))) throw new Error('Refusing to save a report containing credentials');
await writeFile('promo-out/youtube-audit.json', serialized + '\n');
await copyFile(new URL('../../docs/marketing/beta-acquisition.md', import.meta.url), 'promo-out/beta-acquisition.md');
console.log(JSON.stringify({ ok: !report.errors.length, videos: report.videos?.map(video => ({ id: video.id, language: video.defaultAudioLanguage, privacy: video.privacyStatus, views: video.statistics.viewCount, age_hours: video.age_hours })), analytics: report.analytics?.ok, errors: report.errors }));
