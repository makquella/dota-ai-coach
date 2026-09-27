-- Problem reports sent from the launcher (docs/DATA_PLAN.md, stage 1).
-- The gzipped report text is in R2 (r2_key) when the bucket is bound, else in
-- this table (body; D1 allows up to 2 MB per value).
CREATE TABLE IF NOT EXISTS reports (
  id TEXT PRIMARY KEY,           -- "R-7F3KQ2", shown to the player
  created_at INTEGER NOT NULL,   -- ms since epoch
  install_id TEXT NOT NULL,      -- random per installation, lets the player delete their data
  version TEXT,
  os TEXT,
  lang TEXT,
  size INTEGER,
  summary TEXT,                  -- the player's note or the first error line
  r2_key TEXT,
  body BLOB
);
CREATE INDEX IF NOT EXISTS reports_created ON reports (created_at);
CREATE INDEX IF NOT EXISTS reports_install ON reports (install_id);

-- Uploads per hour per installation / hashed address (rate limits).
CREATE TABLE IF NOT EXISTS rate (
  key TEXT NOT NULL,
  hour INTEGER NOT NULL,
  count INTEGER NOT NULL,
  PRIMARY KEY (key, hour)
);
