// Conditional claim races safely with the ordinary Telegram approval button.
// Query returns the same {results, meta} shape as D1's REST query endpoint.
export async function claimSchedule(query, entry, now) {
  let row = (await query('SELECT status, body, publish_at FROM promo_posts WHERE id = ?1', [entry.package_id])).results[0];
  if (!row) throw new Error('Campaign package was not registered');
  if (row.status === 'pending') {
    await query("UPDATE promo_posts SET status = 'scheduling', decided_at = ?2, publish_at = ?3 WHERE id = ?1 AND status = 'pending' AND NOT EXISTS (SELECT 1 FROM promo_deliveries WHERE post_id = ?1)", [entry.package_id, now, entry.publish_at_utc]);
    row = (await query('SELECT status, body, publish_at FROM promo_posts WHERE id = ?1', [entry.package_id])).results[0];
  }
  if (!['scheduling', 'scheduled'].includes(row.status) || row.publish_at !== entry.publish_at_utc) throw new Error('Package already decided or has a different schedule');
  await query("INSERT OR IGNORE INTO promo_deliveries (post_id, network, status, attempts, next_at, updated_at) VALUES (?1, 'youtube', 'processing', 0, ?2, ?3)", [entry.package_id, 4102444800000, now]);
  return (await query("SELECT status, external_id, url FROM promo_deliveries WHERE post_id = ?1 AND network = 'youtube'", [entry.package_id])).results[0];
}

export async function completeSchedule(query, entry, video, now) {
  const url = `https://www.youtube.com/shorts/${video.id}`;
  const detail = `Native YouTube schedule ${entry.publish_at_utc}`;
  await query("UPDATE promo_deliveries SET status = 'published', external_id = ?2, url = ?3, detail = ?4, updated_at = ?5 WHERE post_id = ?1 AND network = 'youtube'", [entry.package_id, video.id, url, detail, now]);
  await query("UPDATE promo_posts SET status = 'scheduled', result = ?2 WHERE id = ?1 AND status IN ('scheduling', 'scheduled')", [entry.package_id, JSON.stringify({ youtube: { status: 'SCHEDULED', id: video.id, publish_at: entry.publish_at_utc, url } })]);
  return url;
}
