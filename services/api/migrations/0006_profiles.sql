-- «Друзья» (0.35): the profile cards players chose to show. The id is the
-- friend code; who follows whom is kept only on each player's computer.
CREATE TABLE IF NOT EXISTS profiles (
  id TEXT PRIMARY KEY,           -- 8 characters, the friend code (WD-XXXXXXXX)
  created_at INTEGER NOT NULL,   -- ms since epoch
  updated_at INTEGER NOT NULL,   -- the last publish; cards untouched for 180 days are deleted
  install_id TEXT NOT NULL,      -- lets the player delete everything of an installation
  token_hash TEXT NOT NULL,      -- sha256 of the token only the publishing launcher has
  version TEXT,
  body TEXT NOT NULL             -- the validated card (src/profile.js), JSON
);
CREATE INDEX IF NOT EXISTS profiles_updated ON profiles (updated_at);
CREATE INDEX IF NOT EXISTS profiles_install ON profiles (install_id);
