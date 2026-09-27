-- «Поделиться разбором» (docs/DATA_PLAN.md, stage 4): reviews the player chose to
-- publish. The review is the validated public part (src/share.js), gzipped JSON.
CREATE TABLE IF NOT EXISTS shares (
  id TEXT PRIMARY KEY,           -- 10 characters, part of the link /r/<id>
  created_at INTEGER NOT NULL,   -- ms since epoch
  expires_at INTEGER NOT NULL,   -- created_at + 90 days
  install_id TEXT NOT NULL,      -- lets the player delete everything of an installation
  delete_hash TEXT NOT NULL,     -- sha256 of the delete token only the author has
  lang TEXT,
  version TEXT,
  body BLOB NOT NULL
);
CREATE INDEX IF NOT EXISTS shares_expires ON shares (expires_at);
CREATE INDEX IF NOT EXISTS shares_install ON shares (install_id);
