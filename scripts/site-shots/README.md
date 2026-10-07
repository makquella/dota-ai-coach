# Website pictures

Everything on the website is real, not mockups: the launcher's renderer and the
overlay card, filled by a demo backend (the test fixtures with varied heroes, a
live-recorded first match for the map, and a scripted AI coach whose texts pass
the real fact check), plus Dota 2 itself — gameplay frames from its Steam page
and hero portraits / item icons from Valve's CDN (the same files the app shows).

From the repository root:

```bash
# 1. Demo backend (port 8777) and the launcher files over HTTP (port 8766)
backend/.venv/bin/python scripts/site-shots/demo_backend.py 8777 &
(cd frontend/launcher && python3 -m http.server 8766) &

# 2. Screenshots (Playwright; CHROMIUM= points at a local Chromium if needed;
#    behind an HTTPS proxy Node's fetch needs NODE_USE_ENV_PROXY=1)
npm i --no-save --prefix /tmp/site-shots playwright
export NODE_PATH=/tmp/site-shots/node_modules
node scripts/site-shots/app_shots.js /tmp/site-shots/raw
node scripts/site-shots/overlay_shots.js /tmp/site-shots/raw

# 3. Into site/assets (JPEG / WebP at web sizes), then the game frames,
#    the in-game view and the carry portraits
backend/.venv/bin/python scripts/site-shots/export.py /tmp/site-shots/raw
backend/.venv/bin/python scripts/site-shots/game_frames.py /tmp/site-shots/raw
```

- `app_shots.js` — Home, Matches, a match review (top and the AI coach card),
  Progress (top and the AI coach card) at 1280×800 at 2x (the wide layout:
  side navigation and two columns; `export.py` makes them 1600×1000, and the
  site opens them at full size on click), and the map / build / chart cards
  from a 720×620 window (larger on the page), both languages. The demo
  matches are dated this week (the newest three hours ago) so Home has a week.
  Hero portraits and item icons go through the app's own `dota-assets.js`
  handler (cached in `$ASSET_CACHE`, default the system temp folder).
  Its Node bridge reads the demo backend's private `backend/local-api-auth.json`
  or the shared `DOTA_AI_CONTROL_TOKEN` environment variable. Credentials stay
  outside the browser; the demo backend still enforces normal local API checks.
- Profile pictures (`profile`, `profile-shop`, `profile-friends`): run the demo
  backend with `DEMO_LOOKS=frame_gold,title_immortal` (looks a profile of its
  level can own — every demo match then counts as played with the app, so the
  level, sparks and tiers are real) and shoot with
  `ONLY=profile,profile-friends` into an empty folder (`export.py` exports every picture it finds there and skips the rest).
- `overlay_shots.js` — one overlay card per case in `overlay_cases.json`, at the
  overlay window's width (420 px), transparent background. The texts are the
  app's own advice strings (see `backend/app/advice_i18n.py`).
- `game_frames.py` — six store screenshots cropped for the "In game" tiles,
  the in-game view (Juggernaut at 1:12 with the real plan card where the
  overlay sits, at the large card size) and the 21 carry portraits.

After a reshoot bump `SHOTS_VERSION` in `site/app.js` and the matching `?v=` of the
`assets/{app,overlay,shots}/` pictures and the in-game view in `site/index.html`: the site sends pictures
with a 4-hour cache, so returning visitors would see the old ones otherwise.
