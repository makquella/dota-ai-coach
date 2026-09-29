-- Where players come from (src/channels.js): visits to the site with ?ref=<source>
-- (or a referrer class: search, direct, other…) and installer downloads through
-- GET /d/<source>, as numbers per day and source. No cookies, URLs, IPs or ids.
CREATE TABLE IF NOT EXISTS channel_counts (
  day TEXT NOT NULL,                  -- YYYY-MM-DD (UTC)
  src TEXT NOT NULL,                  -- [a-z0-9_-], up to 24 characters
  visits INTEGER NOT NULL DEFAULT 0,
  downloads INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (day, src)
);
