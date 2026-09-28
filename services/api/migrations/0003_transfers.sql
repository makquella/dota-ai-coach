-- «Перенос по коду»: the match history on its way to another computer. The body
-- is encrypted by the launcher with the part of the code the server never sees
-- (src/transfer.js); it lives TRANSFER_MINUTES, TRANSFER_TRIES downloads at most (a
-- mistyped secret part can be retried), and the launcher deletes it once imported.
CREATE TABLE IF NOT EXISTS transfers (
  id TEXT PRIMARY KEY,           -- 4 characters, the first group of the code
  created_at INTEGER NOT NULL,   -- ms since epoch
  expires_at INTEGER NOT NULL,   -- created_at + 15 minutes
  install_id TEXT NOT NULL,      -- the sending installation (device delete)
  size INTEGER NOT NULL,
  tries INTEGER NOT NULL DEFAULT 0,
  body BLOB NOT NULL
);
CREATE INDEX IF NOT EXISTS transfers_expires ON transfers (expires_at);
