-- Opt-in anonymous statistics (src/stats.js): one row per installation and day,
-- sent by the launcher only when the player switched «Анонімна статистика» on.
-- The body is rebuilt field by field from an allowlist (counts of advice per
-- decision point, a few settings); the installation id is a salted hash.
CREATE TABLE IF NOT EXISTS daily_stats (
  install_hash TEXT NOT NULL,   -- sha256("dac-stats:" + install id), 32 hex
  day TEXT NOT NULL,            -- YYYY-MM-DD, the local day the counts belong to
  created_at INTEGER NOT NULL,  -- ms since epoch, the last upload of that day
  version TEXT NOT NULL,
  body TEXT NOT NULL,           -- JSON
  PRIMARY KEY (install_hash, day)
);
CREATE INDEX IF NOT EXISTS daily_stats_day ON daily_stats (day);
