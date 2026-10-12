-- Wardly Marketing Engine (docs/MARKETING_ENGINE.md). A promo package waits
-- here for the developer's decision in Telegram; nothing is published before
-- the callback from TELEGRAM_CHAT_ID moves it out of 'pending'. The media live
-- in R2 under promo/<media_key>/ and are served at /m/<media_key>/ (a random
-- key, so a package id alone does not reveal them).
CREATE TABLE IF NOT EXISTS promo_posts (
  id TEXT PRIMARY KEY,
  media_key TEXT NOT NULL UNIQUE,
  created_at INTEGER NOT NULL,
  format TEXT NOT NULL,
  topic TEXT NOT NULL,
  hook INTEGER NOT NULL DEFAULT 0,
  body TEXT NOT NULL,
  status TEXT NOT NULL,
  decided_at INTEGER,
  publish_at TEXT,
  metricool_id TEXT,
  result TEXT
);
CREATE INDEX IF NOT EXISTS promo_posts_status ON promo_posts (status, created_at);
-- The latest numbers of a published post per network (Metricool analytics).
CREATE TABLE IF NOT EXISTS promo_stats (
  post_id TEXT NOT NULL,
  network TEXT NOT NULL,
  updated_at INTEGER NOT NULL,
  url TEXT,
  views INTEGER NOT NULL DEFAULT 0,
  likes INTEGER NOT NULL DEFAULT 0,
  comments INTEGER NOT NULL DEFAULT 0,
  shares INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (post_id, network)
);
