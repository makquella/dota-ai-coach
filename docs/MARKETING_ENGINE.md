# Wardly Marketing Engine

Short vertical videos (TikTok, Instagram Reels, YouTube Shorts) and Telegram
posts, made three times a week from the project's own data, with no gameplay
recording, editing or screen capture. Every video goes to the developer's
Telegram first; nothing is published without a button press there.

## Pipeline

```mermaid
flowchart LR
    Data[(hero profiles · weekly meta · release notes)] --> Topics[topics.py]
    Backend[real live pipeline] --> Demo[coach_demo.py]
    Topics --> Script[script.py]
    Demo --> Script
    Script --> Voice[voice.py · Piper uk]
    Script --> Scenes[scenes.py · HTML 1080x1920]
    Voice --> Render[render.py · Chrome frames + ffmpeg]
    Scenes --> Render
    Render --> QC[quality.py]
    QC --> Send[send.py]
    Send -->|video + buttons| TG[developer's Telegram]
    Send -->|package + media| Worker[Worker src/promo.js · D1 + R2]
    TG -->|button press| Worker
    Worker -->|✅| Channel[@wardlydota]
    Worker -->|✅| Metricool[Metricool → TikTok · Reels · Shorts]
    Metricool -->|daily numbers| Worker
    Worker -->|GET /v1/admin/promo| Weights[weights.py → data/promo/weights.json]
    Weights --> Topics
```

| Step | Where | What |
|---|---|---|
| Topic | `scripts/promo/topics.py` | A release not promoted yet first; the week's meta and its fact once per meta post; coach and hero videos rotate the 64 heroes with a site page (popular first, none of the last 20). Formats are drawn by weight, never the same twice in a row, seeded by the date. |
| Script | `scripts/promo/script.py` | Five formats. Every number comes from a listed source: OpenDota weekly stats (`data/news/posts`), hero profiles, release notes. |
| Real cards | `scripts/promo/coach_demo.py` | «What Wardly says on X»: a synthetic match runs through the real backend (`/gsi` → rules → scheduler → `/overlay/recommendation`) with two moments built from the hero's profile, HP falling fast with an escape ready, and a stun with BKB ready. The video shows exactly what the app shows. |
| Voice | `scripts/promo/voice.py`, `pronounce.py` | Piper (offline, MIT), Ukrainian voice `uk_UA-ukrainian_tts-medium`. Dota names are said through `data/promo/pronounce.json`; words read by fallback rules are listed in the quality report. Percent words agree with the number. |
| Picture | `scripts/promo/scenes.py`, `render.py` | One HTML page drawn frame by frame (`window.renderAt(t)`), 30 fps. Site fonts and colours, Valve hero renders, the real overlay card CSS, in-game screenshots. Burned-in subtitles. Content stays out of the platforms' button areas. |
| Check | `scripts/promo/quality.py` | 12 to 59 s, 1080x1920, a voice track, caption limits, no promises or cheat claims, no unfilled placeholders, sources present. |
| Approval | `scripts/promo/send.py` → Telegram | The video with buttons **✅ Всюди · 📣 Лише Telegram · ❌ Відхилити**, and a reply with captions per network, the YouTube title and the data sources. |
| Publish | `services/api/src/promo.js` | On a press from `TELEGRAM_CHAT_ID`: the channel post (by the approval message's file id), then one Metricool post for Instagram, TikTok and YouTube. |
| Numbers | `promo.js` cron, `scripts/promo/weights.py` | Daily: views, likes, comments and shares per network from Metricool analytics. Mondays: a note to the developer. Before each video: format multipliers (median views per format over the median of all, at least 3 videos, bounded to 0.3–3×). |

Run locally, from the repository root (the backend venv plus `scripts/promo/requirements.txt`, `python -m playwright install chromium`):

```bash
PROMO_VOICE_MODEL=/path/uk_UA-ukrainian_tts-medium.onnx \
  python -m scripts.promo.package --out promo-out --format coach   # video.mp4, cover.jpg, package.json
python -m scripts.promo.package --out promo-out --format meta --no-video  # script and captions only
```

## Safety

- **Approval is the only way out.** A package is `pending` until a callback whose sender *and* chat are `TELEGRAM_CHAT_ID`. One conditional `UPDATE … WHERE status = 'pending'` moves it, so a double press or a Telegram redelivery publishes once (tested on real D1).
- **The webhook is signed.** Telegram sends `X-Telegram-Bot-Api-Secret-Token`, derived from the bot token (`sha256("wardly-promo-webhook:" + token)`), set by `api.yml`. Other requests get 404.
- **Metricool starts as drafts.** `PROMO_METRICOOL_MODE = "draft"` (wrangler.toml) puts approved videos into Metricool as drafts. Switch it to `"publish"` once the first drafts look right on every network.
- **Media.** R2 `promo/<random 128-bit key>/`, public only while the post is not rejected or expired (Metricool fetches the video from there). Rejected media are deleted at once, undecided ones after 7 days, published ones after 30 days.
- **No personal data.** Videos use public aggregate statistics, the app's own rules and Valve's art; nothing from players' matches or reports.
- **Secrets** live only in GitHub and Worker secrets and are never printed.

## Setup

1. Metricool: the API needs the **Advanced** plan. Connect Instagram (business or creator account), TikTok and YouTube to one brand. From *Account settings → API* take the token; `userId` and `blogId` are in the brand's URL.
2. Repository secrets: `METRICOOL_TOKEN`, `METRICOOL_USER_ID`, `METRICOOL_BLOG_ID` (with the existing `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `API_ADMIN_TOKEN`, `CLOUDFLARE_*`).
3. Run the **API** workflow: it deploys the Worker, applies `0008_promo.sql`, sets the secrets and registers the bot's webhook.
4. Write `/id` to the bot in a private chat: it answers your chat id. It must equal `TELEGRAM_CHAT_ID`.
5. Run **Promo** by hand (*Actions → Promo → Run workflow*), approve the video, check the Metricool drafts, then set `PROMO_METRICOOL_MODE = "publish"`.

Without Metricool the buttons still publish to the Telegram channel. Without the Telegram secrets the video is only built and kept as an artifact for 7 days.

## Costs

GitHub Actions (about 5 minutes per video on the free runners), the existing Cloudflare free tier (R2 and D1 rows), Piper (offline, free) and the Metricool plan. No paid AI APIs.

## Extending

- A new format: a builder in `script.py`, a branch in `topics.choose` and `package.build_script`, a weight in `topics.WEIGHTS`, a pill in `scenes.PILLS`, tests in `backend/tests/test_promo.py`.
- A word said wrong: add it to `data/promo/pronounce.json` (the approval message lists every guessed word).
- Tests: `backend/tests/test_promo.py`; `services/api/test/promo.test.js` and `test/integration/promo.test.js` (real D1 and R2).
