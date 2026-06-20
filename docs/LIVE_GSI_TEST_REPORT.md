# Live GSI Test Report

This report is a sanitized summary of a completed Windows live GSI validation.

## Environment

- OS: Windows 11
- Game mode: Dota 2 Demo Hero
- Backend mode: `live_gsi`
- Hero: Juggernaut
- Session: `live_session_20260610T090212_534960_0000`

Private account fields, player nickname, local Windows user paths, and full raw GSI payloads are intentionally excluded.

## Collected Data

- Raw GSI states: `165`
- Shown advice cards: `6`
- Approximate game-time range: `299-488` seconds

Advice categories observed:

- `LOW_HP`
- `LOW_MANA`
- `HERO_SURVIVABILITY_RISK`
- `ABILITY_SAFETY_COOLDOWN`

## Validated Pipeline

```text
Dota 2 -> GSI config -> FastAPI backend -> live state parser -> recommender/scheduler -> recorder -> shown_advice.jsonl
```

## Result

The live GSI pipeline was validated successfully. Dota 2 posted states to the local backend, the backend normalized those states, the recommender and scheduler produced advice, and the live recorder saved shown advice evidence.

## Notes

- This was a demo-hero validation, not a full ranked-match evaluation.
- Advice remained based on available GSI fields only.
- The test did not require game-process hooks, screen capture, input automation, STRATZ, a database, or account authentication.
