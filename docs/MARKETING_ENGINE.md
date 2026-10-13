# Wardly Marketing Engine

Short vertical videos (TikTok, Instagram Reels, YouTube Shorts) and Telegram
posts, made three times a week from the project's own data, with no gameplay
recording, editing or screen capture. Every video goes to the developer's
Telegram first; nothing is published without a button press there. Publishing
goes straight to YouTube, Instagram and TikTok through their own free APIs.

## Pipeline

```mermaid
flowchart LR
    Data[(hero profiles · weekly meta · release notes)] --> Topics[topics.py]
    Backend[real live pipeline] --> Demo[coach_demo.py]
    Topics --> Script[script.py]
    Demo --> Script
    Script --> Voice[voice.py · ElevenLabs]
    Script --> Scenes[scenes.py · HTML 1080x1920]
    Voice --> Render[render.py · Chrome frames + ffmpeg]
    Scenes --> Render
    Media[media.py · Valve animations and clips] --> Render
    Render --> QC[quality.py]
    QC --> Send[send.py]
    Send -->|video + buttons| TG[developer's Telegram]
    Send -->|package + media| Worker[Worker src/promo.js · D1 + R2]
    TG -->|button press| Worker
    Worker -->|✅| Channel[@wardlydota]
    Worker -->|✅ queue, cron */5| Direct[YouTube Data API · Instagram API · TikTok Content Posting API]
    Direct -->|daily numbers| Worker
    Worker -. optional .-> Metricool[Metricool]
    Worker -->|GET /v1/admin/promo| Weights[weights.py → data/promo/weights.json]
    Weights --> Topics
```

| Step | Where | What |
|---|---|---|
| Topic | `scripts/promo/topics.py` | A release not promoted yet first; the week's meta and its fact once per meta post; coach and hero videos rotate the 64 heroes with a site page (popular first, none of the last 20). Formats are drawn by weight, never the same twice in a row, seeded by the date. |
| Script | `scripts/promo/script.py` | Five formats. Every number comes from a listed source: OpenDota weekly stats (`data/news/posts`), hero profiles, release notes. |
| Real cards | `scripts/promo/coach_demo.py` | «What Wardly says on X»: a synthetic match runs through the real backend (`/gsi` → rules → scheduler → `/overlay/recommendation`) with two moments built from the hero's profile, HP falling fast with an escape ready, and a stun with BKB ready. The video shows exactly what the app shows. |
| Voice | `scripts/promo/voice.py` | ElevenLabs (`eleven_multilingual_v2` by default): the Ukrainian script with the English hero, ability and item names read as written. One request per scene, with the neighbouring scenes as context so the intonation carries across cuts; the character alignment gives every word its time. Percent words agree with the number. |
| Moving pictures | `scripts/promo/media.py` | Valve's own, from dota2.com's CDN: each hero's idle animation (VP9 with transparency) and in-game clips of abilities. Valve's hero data feed names the abilities, so a card that says «use Shackles» gets the Shackles clip; an item card gets the item's icon. A coach moment opens on an enemy's stun or burst. Clips are cropped to 9:16 where they move most, with the action above the overlay card, and decoded into frames once per run. |
| Picture | `scripts/promo/scenes.py`, `render.py` | One HTML page drawn frame by frame (`window.renderAt(t)`), 30 fps; frame sequences play frame-exact. Cuts punch in with a flash, a card hits with a shake, the advised ability or item follows. Site fonts and colours, the real overlay card CSS. Subtitles light up word by word with the voice. Content stays out of the platforms' button areas. |
| Check | `scripts/promo/quality.py` | 12 to 59 s, 1080x1920, a voice track, caption limits, no promises or cheat claims, no unfilled placeholders, sources present. |
| Approval | `scripts/promo/send.py` → Telegram | The video with buttons **✅ Всюди · 📣 Лише Telegram · ❌ Відхилити**, and a reply with captions per network, the YouTube title and the data sources. |
| Publish | `services/api/src/promo.js`, `src/social.js` | On a press from `TELEGRAM_CHAT_ID`: the channel post at once (by the approval message's file id), and one delivery per connected network. The five-minute cron works the queue: YouTube (one resumable upload), Instagram (a Reel container, polled until ready, then published), TikTok (an upload to the app's inbox as a draft, or a direct post). The result comes as a reply to the approval message. Networks that are not connected go through Metricool if it is configured, else they are listed as not connected. |
| Numbers | `promo.js` cron, `scripts/promo/weights.py` | Daily: views, likes, comments and shares straight from YouTube, Instagram and TikTok (and Metricool, if used). Mondays: a note to the developer. Before each video: format multipliers (median views per format over the median of all, at least 3 videos, bounded to 0.3–3×). |

Run locally, from the repository root (the backend venv plus `scripts/promo/requirements.txt`, `python -m playwright install chromium`):

```bash
PROMO_VOICE_MODEL=/path/uk_UA-ukrainian_tts-medium.onnx \
  python -m scripts.promo.package --out promo-out --format coach   # video.mp4, cover.jpg, package.json
python -m scripts.promo.package --out promo-out --format meta --no-video  # script and captions only
```

## Safety

- **Approval is the only way out.** A package is `pending` until a callback whose sender *and* chat are `TELEGRAM_CHAT_ID`. One conditional `UPDATE … WHERE status = 'pending'` moves it, so a double press or a Telegram redelivery publishes once (tested on real D1).
- **The webhook is signed.** Telegram sends `X-Telegram-Bot-Api-Secret-Token`, derived from the bot token (`sha256("wardly-promo-webhook:" + token)`), set by `api.yml`. Other requests get 404.
- **Accounts.** Only `TELEGRAM_CHAT_ID` gets `/connect` links. The OAuth `state` is random, lives 15 minutes and works once. Tokens are stored in D1 sealed with AES-GCM under a key derived from `ADMIN_TOKEN`; changing `ADMIN_TOKEN` means connecting again. `/disconnect <network>` deletes them.
- **Publishing once.** Each delivery keeps the network's id after the first call and only polls after that; a lease stops two cron runs from working the same delivery. Failed calls retry with back-off (2, 5, 15, 30, 60 minutes), six times at most.
- **Metricool (optional) starts as drafts.** `PROMO_METRICOOL_MODE = "draft"` (wrangler.toml).
- **Media.** R2 `promo/<random 128-bit key>/`, public only while the post is not rejected or expired (Instagram and Metricool fetch the video from there). Rejected media are deleted at once, undecided ones after 7 days, published ones after 30 days.
- **No personal data.** Videos use public aggregate statistics, the app's own rules and Valve's art; nothing from players' matches or reports.
- **Secrets** live only in GitHub and Worker secrets and are never printed.

## Setup

Everything is in place: the only thing left is each network's app keys. For
each network: create the app (below), put its two keys into the repository
secrets, run the **API** workflow (it copies them to the Worker), then send the
bot `/connect youtube` (or `instagram`, `tiktok`) and allow access on the page it
links. `/accounts` shows what is connected. Redirect URI for every app:
`https://api.luhovyimvp.dev/oauth/<network>/callback`.

### Voice → `ELEVENLABS_API_KEY`

1. An ElevenLabs Starter plan (or higher: the free plan forbids commercial use and wants attribution). Profile → API keys → a new key; repository secret `ELEVENLABS_API_KEY`.
2. Optional, a repository variable `ELEVENLABS_VOICE_ID`: a voice from the Voice Library (a native Ukrainian speaker sounds best; add it to your voices and copy its id). Without it a premade voice speaks. `ELEVENLABS_MODEL` switches the model (default `eleven_multilingual_v2`).
3. The Promo workflow stops with an annotation when the key is missing; it never sends a silent video.

### YouTube Shorts → `YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET`

1. [console.cloud.google.com](https://console.cloud.google.com): a new project, *APIs & Services → Library → YouTube Data API v3 → Enable*.
2. *OAuth consent screen*: External, app name Wardly, your e-mail. Scopes `youtube.upload` and `youtube.readonly`. Then **Publish app** (status *In production*): in *Testing* the refresh token dies after 7 days. The «unverified app» warning on sign-in is fine for your own channel.
3. *Credentials → Create credentials → OAuth client ID → Web application*, redirect URI `https://api.luhovyimvp.dev/oauth/youtube/callback`.
4. Until the project passes YouTube's API audit (*YouTube API Services — Audit and Quota Extension* form, free), uploads are locked as private; the bot says so after each upload. One upload uses 1,600 of the 10,000 daily quota units.

### Instagram Reels → `INSTAGRAM_APP_ID`, `INSTAGRAM_APP_SECRET`

1. The Instagram account must be professional (*Settings → Account type → Creator* or *Business*).
2. [developers.facebook.com](https://developers.facebook.com) → *Create app* → use case *Manage messaging & content on Instagram* (Instagram API with Instagram login).
3. *API setup with Instagram login*: add the account under *Roles → Instagram testers* and accept the invite in Instagram (*Settings → Website permissions → Apps and websites → Tester invites*); *Business login settings*: redirect URI `https://api.luhovyimvp.dev/oauth/instagram/callback`.
4. The *Instagram app ID* and *Instagram app secret* from the same page are the two secrets. The app can stay in development mode: it publishes to accounts that have a role in it.

### TikTok → `TIKTOK_CLIENT_KEY`, `TIKTOK_CLIENT_SECRET`

1. [developers.tiktok.com](https://developers.tiktok.com) → *Manage apps → Connect an app*. Platform *Web*, terms and privacy URL `https://luhovyimvp.dev/privacy.html`.
2. Products *Login Kit* (redirect URI `https://api.luhovyimvp.dev/oauth/tiktok/callback`) and *Content Posting API*; scopes `user.info.basic`, `video.list`, `video.upload` (and `video.publish` for direct posts).
3. Until TikTok reviews the app, use its *Sandbox* with your account as a target user. `TIKTOK_MODE = "inbox"` (wrangler.toml) sends each video to the TikTok app as a draft: open the notification and press *Post*. After TikTok's audit, `"direct"` posts at once.

### The rest

- `TELEGRAM_CHAT_ID` must be your chat with the bot: `/id` answers it.
- Metricool is optional (`METRICOOL_TOKEN`, `METRICOOL_USER_ID`, `METRICOOL_BLOG_ID`, the Advanced plan): it only takes the networks that are not connected directly.
- Without any network the buttons still publish to the Telegram channel, and the approval message carries the video and the captions for posting by hand.

## Costs

GitHub Actions (about 8 minutes per video on the free runners), the existing Cloudflare free tier (R2, D1 rows, two cron triggers), the networks' own free APIs and ElevenLabs Starter (commercial use; a video is about 700 characters, three a week fit the plan's monthly credits). Metricool is optional.

## Extending

- A new format: a builder in `script.py`, a branch in `topics.choose` and `package.build_script`, a weight in `topics.WEIGHTS`, a pill in `scenes.PILLS`, tests in `backend/tests/test_promo.py`.
- A word said wrong: rewrite it in the script (`script.py`) the way it should sound, or try another voice (`ELEVENLABS_VOICE_ID`).
- A new network: a client in `services/api/src/social.js` with `authUrl`, `exchange`, `fresh`, `step` and `stats`, its secrets in `NETWORK_SECRETS` and `api.yml`, a route in `index.js`.
- Tests: `backend/tests/test_promo.py`; `services/api/test/promo.test.js`, `test/social.test.js`, `test/integration/promo.test.js` and `test/integration/social.test.js` (real D1 and R2).
