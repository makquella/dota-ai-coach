// Explicit, one-off owner authorization: six reviewed films, Oct 16/17/18 2026
// at 17:00 Europe/Kyiv. Upload privately now; YouTube releases them natively.
import { readFile, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { createHash } from 'node:crypto';
import { NETWORK_CLIENTS, unseal } from '../../services/api/src/social.js';
import { claimSchedule, completeSchedule } from './series_schedule_state.mjs';
import { scheduledVideoState } from './series_schedule_verify.mjs';

const root = resolve(process.argv[2] || 'promo-out');
const required = name => { const value = process.env[name]?.trim(); if (!value) throw new Error(`${name} is not configured`); return value; };
const hidden = Object.entries(process.env).filter(([key]) => /TOKEN|SECRET/.test(key)).map(([, value]) => value).filter(Boolean);
const redact = value => hidden.filter(Boolean).reduce((s, value) => s.split(value).join('[redacted]'), String(value)).replace(/https?:\/\/\S+/g, '[URL redacted]');
const report = { authorized_schedule: '2026-10-16/17/18 17:00 Europe/Kyiv', checked_at: new Date().toISOString(), complete: false, videos: [], errors: [] };
const channelId = 'UCKR63Rvtlfebo9ChyMjX6tQ';
const pause = ms => new Promise(resolve => setTimeout(resolve, ms));

async function request(url, init = {}) {
  const response = await fetch(url, { ...init, signal: AbortSignal.timeout(45000) });
  const data = await response.json();
  if (!response.ok || data.success === false) {
    const reason = data.error?.errors?.[0]?.reason || data.error?.status || data.errors?.[0]?.code || 'request_failed';
    throw new Error(`HTTP ${response.status} (${reason})`);
  }
  return data;
}

try {
  const manifest = JSON.parse(await readFile(resolve(root, 'series-manifest.json'), 'utf8'));
  if (manifest.timezone !== 'Europe/Kyiv' || manifest.entries?.length !== 6 || !manifest.explicit_owner_schedule) throw new Error('Expected the owner-authorized six-video Kyiv manifest');
  const expected = new Set(['sven/uk','sven/en','juggernaut/uk','juggernaut/en','terrorblade/uk','terrorblade/en']);
  const entries = [];
  for (const entry of manifest.entries) {
    if (!expected.delete(entry.folder) || entry.folder !== `${entry.creative}/${entry.language}`) throw new Error('Unexpected or duplicate series entry');
    const day = { sven: 16, juggernaut: 17, terrorblade: 18 }[entry.creative];
    if (entry.publish_at_utc !== `2026-10-${day}T14:00:00Z` || Date.parse(entry.publish_at_utc) <= Date.now() + 600000) throw new Error('Schedule differs from the authorized future dates');
    const folder = resolve(root, entry.folder);
    const bytes = await readFile(resolve(folder, 'video.mp4'));
    const video = JSON.parse(await readFile(resolve(folder, 'package.json'), 'utf8'));
    const speech = JSON.parse(await readFile(resolve(folder, 'speech-check.json'), 'utf8'));
    const meta = JSON.parse(await readFile(resolve(folder, 'youtube-metadata.json'), 'utf8'));
    const sha = createHash('sha256').update(bytes).digest('hex');
    if (sha !== entry.sha256 || sha !== video.sha256 || sha !== speech.sha256 || !speech.ok || speech.language !== entry.language || !video.layout?.ok || !video.quality?.fully_decoded || video.draft || video.kind !== 'wardly-beta-recruitment' || meta.id !== entry.package_id || meta.youtube_language !== entry.language) throw new Error('Reviewed media, language, metadata or speech integrity failed');
    entries.push({ ...entry, folder, bytes, meta });
  }
  if (expected.size || new Set(entries.map(e => e.package_id)).size !== 6) throw new Error('Six distinct packages are required');
  const cfBase = `https://api.cloudflare.com/client/v4/accounts/${required('CLOUDFLARE_ACCOUNT_ID')}/d1/database`;
  const cfHeaders = { authorization: `Bearer ${required('CLOUDFLARE_API_TOKEN')}`, 'content-type': 'application/json' };
  const databases = await request(cfBase, { headers: cfHeaders });
  const database = databases.result.find(row => row.name === 'dota-ai-coach');
  if (!database) throw new Error('Wardly database not found');
  const query = async (sql, params = []) => {
    const data = await request(`${cfBase}/${database.uuid}/query`, { method: 'POST', headers: cfHeaders, body: JSON.stringify({ sql, params }) });
    return data.result[0];
  };
  const stored = (await query("SELECT sealed FROM promo_accounts WHERE network='youtube'")).results[0];
  if (!stored) throw new Error('YouTube is not connected');
  const credentials = await unseal({ ADMIN_TOKEN: required('API_ADMIN_TOKEN') }, stored.sealed);
  hidden.push(credentials.access_token, credentials.refresh_token);
  const env = { YOUTUBE_CLIENT_ID: required('YOUTUBE_CLIENT_ID'), YOUTUBE_CLIENT_SECRET: required('YOUTUBE_CLIENT_SECRET') };
  const fresh = await NETWORK_CLIENTS.youtube.fresh(env, credentials, Date.now());
  hidden.push(fresh.account.access_token);
  const google = (route, params) => request(`https://www.googleapis.com/youtube/v3/${route}?${new URLSearchParams(params)}`, { headers: { authorization: `Bearer ${fresh.account.access_token}` } });
  const channels = await google('channels', { part: 'snippet', mine: 'true' });
  if (channels.items?.[0]?.id !== channelId) throw new Error('Connected YouTube channel is not the reviewed Wardly channel');
  report.channel_id = channelId;
  // Check every existing decision before registering or uploading anything.
  for (const entry of entries) {
    const row = (await query('SELECT status,publish_at FROM promo_posts WHERE id=?1', [entry.package_id])).results[0];
    if (row && (row.status !== 'pending' && (!['scheduling','scheduled'].includes(row.status) || row.publish_at !== entry.publish_at_utc))) throw new Error(`${entry.creative}/${entry.language} was already decided outside this schedule`);
  }
  const admin = { authorization: `Bearer ${required('API_ADMIN_TOKEN')}` };
  for (const entry of entries) {
    const before = (await query('SELECT status,body FROM promo_posts WHERE id=?1', [entry.package_id])).results[0];
    if (!before) {
      const registered = await request(`${required('API_URL')}/v1/admin/promo`, { method: 'POST', headers: { ...admin, 'content-type': 'application/json' }, body: JSON.stringify(entry.meta) });
      if (!registered.youtube_ready || registered.youtube_language !== entry.language || JSON.stringify(registered.youtube_tags) !== JSON.stringify(entry.meta.youtube_tags)) throw new Error('API did not preserve the reviewed YouTube metadata');
      for (const [name, type] of [['video.mp4','video/mp4'],['cover.jpg','image/jpeg']]) await request(`${required('API_URL')}/v1/admin/promo/${entry.package_id}/${name}`, { method: 'PUT', headers: { ...admin, 'content-type': type }, body: await readFile(resolve(entry.folder, name)) });
    }
    const row = (await query('SELECT body FROM promo_posts WHERE id=?1', [entry.package_id])).results[0];
    const body = JSON.parse(row.body);
    for (const key of ['youtube_title','caption','youtube_language','youtube_tags']) if (JSON.stringify(body[key]) !== JSON.stringify(entry.meta[key])) throw new Error('Persisted metadata differs from the reviewed package');
  }
  // Claim all six first: old Telegram publish buttons cannot race the upload.
  const deliveries = new Map();
  for (const entry of entries) deliveries.set(entry.package_id, await claimSchedule(query, entry, Date.now()));
  for (const entry of entries) {
    const current = deliveries.get(entry.package_id);
    let external = current.external_id;
    const receipt = { creative: entry.creative, language: entry.language, package_id: entry.package_id, sha256: entry.sha256, publish_at: entry.publish_at_utc, verified: false };
    report.videos.push(receipt);
    for (let attempt = 0; (!external || external.startsWith('upload:')) && attempt < 5; attempt++) {
      const result = await NETWORK_CLIENTS.youtube.step(env, fresh.account, { body: entry.meta, publish_at: entry.publish_at_utc, external_id: external, media: { size: entry.bytes.length, open: async (offset = 0) => entry.bytes.subarray(offset) } });
      if ('external_id' in result) {
        external = result.external_id;
        await query("UPDATE promo_deliveries SET external_id=?2, updated_at=?3 WHERE post_id=?1 AND network='youtube'", [entry.package_id, external, Date.now()]);
      }
      if (result.status === 'error') throw new Error(result.detail || 'YouTube upload failed');
      if (result.status === 'retry') {
        if (!/429|500|502|503|504/.test(result.detail || '')) throw new Error(result.detail || 'Upload retry required; session preserved');
        await pause(2000);
      }
    }
    if (!external || external.startsWith('upload:')) throw new Error('Upload not completed; resumable session preserved');
    receipt.video_id = external;
    for (let poll = 0; poll < 24; poll++) {
      const data = await google('videos', { part: 'snippet,status,processingDetails,contentDetails', id: external });
      const video = data.items?.[0];
      const state = scheduledVideoState(video, entry, channelId);
      receipt.youtube_metadata = state.metadata;
      if (state.ready) {
        receipt.verified = true;
        receipt.youtube_status = { privacyStatus: video.status.privacyStatus, publishAt: video.status.publishAt, uploadStatus: video.status.uploadStatus, processingStatus: video.processingDetails.processingStatus };
        receipt.url = await completeSchedule(query, entry, video, Date.now());
        await writeFile(resolve(entry.folder, 'native-schedule.json'), JSON.stringify(receipt, null, 2) + '\n');
        console.log(JSON.stringify({ creative: entry.creative, language: entry.language, video_id: external, publish_at: video.status.publishAt, verified: true }));
        break;
      }
      await pause(5000);
    }
    if (!receipt.verified) throw new Error('YouTube processing or exact metadata verification is still pending; schedule retained for verification on resume');
  }
  report.complete = report.videos.length === 6 && report.videos.every(video => video.verified);
} catch (error) {
  report.errors.push(redact(error.message));
  process.exitCode = 1;
}
const serialized = JSON.stringify(report, null, 2);
if (hidden.filter(Boolean).some(secret => secret.length > 5 && serialized.includes(secret))) throw new Error('Refusing to save credentials in the schedule receipt');
await writeFile(resolve(root, 'series-schedule.json'), serialized + '\n');
console.log(JSON.stringify({ complete: report.complete, verified_videos: report.videos.filter(video => video.verified).length, errors: report.errors }));
