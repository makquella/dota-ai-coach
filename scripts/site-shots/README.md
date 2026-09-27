# Website screenshots

The pictures on the website are the real app, not mockups: the launcher's
renderer and the overlay card, filled by a demo backend (the test fixtures with
varied heroes and a scripted AI coach whose texts pass the real fact check).
No Electron, no network.

From the repository root:

```bash
# 1. Demo backend (port 8777) and the launcher files over HTTP (port 8766)
backend/.venv/bin/python scripts/site-shots/demo_backend.py 8777 &
(cd frontend/launcher && python3 -m http.server 8766) &

# 2. Screenshots (Playwright; CHROMIUM= points at a local Chromium if needed)
npm i --no-save --prefix /tmp/site-shots playwright
export NODE_PATH=/tmp/site-shots/node_modules
node scripts/site-shots/app_shots.js /tmp/site-shots/raw
node scripts/site-shots/overlay_shots.js /tmp/site-shots/raw

# 3. Into site/assets (JPEG / WebP at web sizes; needs Pillow)
python3 scripts/site-shots/export.py /tmp/site-shots/raw
```

- `app_shots.js` — Home, Matches, a match review (top and the AI coach card),
  Progress (top and the AI coach card), 720×620 at 2x, both languages.
- `overlay_shots.js` — one overlay card per case in `overlay_cases.json`, at the
  overlay window's width (420 px), transparent background. The texts are the
  app's own advice strings (see `backend/app/advice_i18n.py`).
- Hero portraits and item icons show as initials here: the app downloads them
  from Valve's CDN at runtime, which the screenshot machine may not reach.
