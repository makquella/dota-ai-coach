-- Deletion capabilities (0.53.54). Launchers from 0.53.54 send a random device
-- key (x-device-key) with every upload; only sha256("dac-device:" + key) is
-- stored. The device delete removes owned rows only with that key; rows without
-- an owner hash (older launchers) keep the install-id delete. A transfer stores
-- the hash of a delete token derived from the part of the code the server never
-- sees, so only someone with the whole code can cancel it.
ALTER TABLE reports ADD COLUMN owner_hash TEXT;
ALTER TABLE shares ADD COLUMN owner_hash TEXT;
ALTER TABLE profiles ADD COLUMN owner_hash TEXT;
ALTER TABLE transfers ADD COLUMN owner_hash TEXT;
ALTER TABLE transfers ADD COLUMN delete_hash TEXT;
CREATE INDEX IF NOT EXISTS reports_owner ON reports (owner_hash);
CREATE INDEX IF NOT EXISTS shares_owner ON shares (owner_hash);
CREATE INDEX IF NOT EXISTS profiles_owner ON profiles (owner_hash);
CREATE INDEX IF NOT EXISTS transfers_owner ON transfers (owner_hash);
