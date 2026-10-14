# Manual Ukrainian voice comparisons

PRs #188 and #189 introduced ElevenLabs scene narration and the draft video
format. The code defaults to `eleven_multilingual_v2` and the premade Liam;
repository variables may override them. `/v1/` is the API route version, rather
than the speech model version. The voice lab checks the authenticated model
catalog and chooses `eleven_v4` when available, otherwise `eleven_v3`; it refuses
to silently fall back to an older model.

Run the existing **Promo** workflow on this branch with `voice_lab=catalog`,
`send=false`. It reads the account/library catalogs without synthesizing audio
and saves `voice-catalog.json`. Only explicitly Ukrainian male voices qualify;
an English voice's multilingual capability is insufficient. Public library
voices are added to the account on first use if needed, using the same API key.

Then dispatch A, B, C, D with the verified catalog JSON in `voice_catalog` and
`send=true`. The first three catalog candidates are used consistently:

| Variant | Voice | Delivery |
|---|---|---|
| A | First native male voice | Natural, stability 0.5, speed 1.0 |
| B | Same first voice | Creative, stability 0.0, speed 1.04 |
| C | Second native male voice | Natural, stability 0.5, speed 1.0 |
| D | Third native male voice | Natural, stability 0.5, speed 1.0 |

All variants use the same Phantom Lancer → counter-item script, verified from
Wardly's rules, and the same render seed/assets. One continuous TTS request gives
prosody across the whole script; aligned words split the recording for existing
scene rendering and karaoke captions. New models omit legacy previous/next text
context. Every output records the actual model, voice, stability and speed.

Comparisons go directly to the configured developer Telegram chat, with variant
labels. They are absent from the publishing queue, have no publication callbacks
and do not alter production voice variables or rotation history. Scheduled
videos retain their existing approval/publishing flow. Manual checkout uses the
actual dispatched commit so a branch experiment cannot silently run main code.

Local validation: `backend/.venv/bin/python -m pytest
backend/tests/test_promo.py backend/tests/test_promo_voice_experiments.py` and
Ruff/actionlint. New functional checks use a real local HTTP provider, WAV files
and Telegram multipart delivery. Live account/model availability, rendered audio
and delivery require the authenticated workflow; unit checks alone cannot prove
them. No secret values are placed in catalog artifacts, arguments or logs.
