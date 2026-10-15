import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { test } from 'node:test';
import { Miniflare, convertV4MiniflareOptions } from 'miniflare';
import { claimSchedule, completeSchedule } from '../../../../scripts/promo/series_schedule_state.mjs';

test('native schedule claims exclude Telegram approval and preserve upload sessions across retries on real D1', async t => {
  const mf = new Miniflare(convertV4MiniflareOptions({
    modules: true, script: 'export default { fetch() { return new Response("ok") } }',
    compatibilityDate: '2026-09-20', d1Databases: { DB: 'wardly-series-schedule-test' }
  }));
  t.after(() => mf.dispose());
  const db = await mf.getD1Database('DB');
  for (const name of ['0008_promo.sql', '0009_promo_social.sql']) {
    const sql = await readFile(new URL(`../../migrations/${name}`, import.meta.url), 'utf8');
    for (const statement of sql.replace(/--[^\n]*/g, '').split(';').map(s => s.trim()).filter(Boolean)) await db.prepare(statement).run();
  }
  const query = (sql, params = []) => db.prepare(sql).bind(...params).all();
  const entry = { package_id: '0123456789abcdef', publish_at_utc: '2026-10-16T14:00:00Z' };
  await query("INSERT INTO promo_posts (id,media_key,created_at,format,topic,body,status) VALUES (?1,'key',1,'release','beta','{}','pending')", [entry.package_id]);
  assert.equal((await claimSchedule(query, entry, 1000)).status, 'processing');
  const button = await query("UPDATE promo_posts SET status='publishing' WHERE id=?1 AND status='pending'", [entry.package_id]);
  assert.equal(button.meta.changes, 0);
  await query("UPDATE promo_deliveries SET external_id='upload:private-session' WHERE post_id=?1", [entry.package_id]);
  assert.equal((await claimSchedule(query, entry, 2000)).external_id, 'upload:private-session');
  await completeSchedule(query, entry, { id: 'video123' }, 3000);
  assert.equal((await claimSchedule(query, entry, 4000)).external_id, 'video123');
  const post = (await query('SELECT status,publish_at,result FROM promo_posts WHERE id=?1', [entry.package_id])).results[0];
  assert.equal(post.status, 'scheduled');
  assert.equal(post.publish_at, entry.publish_at_utc);
  assert.equal(JSON.parse(post.result).youtube.status, 'SCHEDULED');
  await assert.rejects(claimSchedule(query, { ...entry, publish_at_utc: '2026-10-17T14:00:00Z' }, 5000), /different schedule/);
  await query("UPDATE promo_posts SET status='published' WHERE id=?1", [entry.package_id]);
  await assert.rejects(claimSchedule(query, entry, 6000), /already decided/);
  assert.equal((await query('SELECT external_id FROM promo_deliveries WHERE post_id=?1', [entry.package_id])).results[0].external_id, 'video123');
});
