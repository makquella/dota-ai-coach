# Secrets at rest (0.53.53)

Keys and tokens on the player's disk are sealed with the operating system's
per-user protection (DPAPI on Windows), so a copied data folder, settings file
or disk image does not carry usable secrets. There is no server account and no
password; the protection is the Windows user's.

## Backend: AI and OpenDota keys (`backend/app/secret_box.py`)

- `SecretBox` seals with `CryptProtectData` (current user, app entropy, no UI)
  through `ctypes`; no new dependency. A sealed value is `dpapi:v1:<base64>`.
- `PlayerService` seals `ai_settings` and `opendota_api_key` on write and opens
  them on read. On start, plain values an older version wrote are sealed
  (`_seal_stored_secrets`).
- A seal must open back to the same text before it is stored; otherwise the
  plain value is kept, so a sealing fault never loses a key.
- A seal this Windows user cannot open (copied from another user/computer)
  reads as missing: the AI coach shows as off and the player enters the key
  again, which replaces it. Nothing else is deleted.
- Elsewhere (Linux/macOS development, CI) there is no OS sealing; values stay
  as before. `scripts/check_secret_box.py` runs on the Windows CI job and
  proves a DPAPI round trip for the runner's user.
- `/diagnostics` `player.secrets`: `{sealing, sealed, plain, locked}` counts,
  never values.

## Launcher: tokens and the webhook (`frontend/launcher/secret-codec.js`)

- `settings.js` seals `shares` (review delete tokens), `friendsProfile` (the
  public profile token) and `discordWebhook` with Electron `safeStorage`
  (`safe:v1:<base64>` of the JSON value) and keeps them open in memory only.
- `safeStorage` works once the app is ready, so `main.js` calls
  `settings.unlockSecrets()` first thing in `whenReady` (and in the smoke
  test). Before that, sealed values read as their defaults and are written back
  untouched; after it, plain values of an older version are sealed.
- A seal that does not open back is refused: the write fails (`seal_failed` in
  settings health) and the value stays in memory, never written in plain text
  once sealing is on. A foreign seal is kept on disk and reads as the default
  until the player sets a new value.
- `settings.health().secrets`: `{sealing, locked}`.

Backups (`history_backup.py`) never contained these keys and still do not.

Tests: `backend/tests/test_secret_box.py` (a reversible per-user stand-in for
DPAPI: sealed writes, migration, foreign seal, broken sealing, diagnostics),
`frontend/launcher/test/secret-settings.test.js` (a stand-in for safeStorage:
migration after ready, seals preserved before ready, foreign seal, no sealing,
refused seal).
