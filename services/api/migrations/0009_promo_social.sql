-- Direct publishing to YouTube, Instagram and TikTok (src/social.js,
-- docs/MARKETING_ENGINE.md). The developer connects each account once with
-- the bot's /connect command; tokens are stored sealed (AES-GCM, a key derived
-- from ADMIN_TOKEN), never in plain text. An approved post gets one delivery
-- per network, worked by the five-minute cron until it is published or failed.
CREATE TABLE IF NOT EXISTS promo_accounts (
  network TEXT PRIMARY KEY,
  sealed TEXT NOT NULL,
  account TEXT,
  updated_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS promo_oauth (
  state TEXT PRIMARY KEY,
  network TEXT NOT NULL,
  created_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS promo_deliveries (
  post_id TEXT NOT NULL,
  network TEXT NOT NULL,
  status TEXT NOT NULL,
  attempts INTEGER NOT NULL DEFAULT 0,
  next_at INTEGER NOT NULL,
  external_id TEXT,
  url TEXT,
  detail TEXT,
  updated_at INTEGER NOT NULL,
  PRIMARY KEY (post_id, network)
);
CREATE INDEX IF NOT EXISTS promo_deliveries_due ON promo_deliveries (status, next_at);
ALTER TABLE promo_posts ADD COLUMN approval_chat TEXT;
ALTER TABLE promo_posts ADD COLUMN approval_message INTEGER;
