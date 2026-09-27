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
  Progress (top and the AI coach card) and the map / build / chart cards,
  720×620 at 2x (the launcher's default window is 760 wide), both languages.
  Hero portraits and item icons go through the app's own `dota-assets.js`
  handler (cached in `$ASSET_CACHE`, default the system temp folder).
- `overlay_shots.js` — one overlay card per case in `overlay_cases.json`, at the
  overlay window's width (420 px), transparent background. The texts are the
  app's own advice strings (see `backend/app/advice_i18n.py`).
- `game_frames.py` — six store screenshots cropped for the "In game" tiles,
  the in-game view (Juggernaut at 1:12 with the real plan card where the
  overlay sits, at the large card size) and the 21 carry portraits.
