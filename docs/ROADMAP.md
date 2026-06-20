# Roadmap

## Current Status

Coursework MVP / v0.1.0.

The project demonstrates a local real-time Dota 2 coaching loop using live GSI, deterministic rule-based advice, scheduler-based anti-spam, an Electron overlay, an Electron launcher, replay demo playback, and live session recording.

For the analogue/comparison analysis, see [Analogues and Differentiation](ANALOGS.md).

## Implemented

- FastAPI backend.
- Dota 2 GSI endpoint.
- Rule-based recommender.
- Advice scheduler / anti-spam.
- Game-time spacing.
- Heartbeat long-silence nudge.
- Electron launcher.
- Electron overlay.
- Replay demo playback.
- Live GSI recorder.
- Coach session summary export.
- Windows live GSI validation.
- Pytest tests.
- Node dependency hardening with high-severity npm audit result at zero for launcher and overlay.

## Packaging Status

Windows packaging is Phase 1 / partially validated.

What works:

- development launcher;
- backend start/stop from launcher;
- overlay start/stop from launcher;
- replay demo playback;
- live GSI validation through the normal development stack.

Still to validate:

- final portable Windows build on a clean machine;
- final resource paths inside the packaged app;
- optional code signing or installer workflow.

## Future Work

- Improve and fully validate packaged Windows portable build.
- Run longer real-match validation beyond Demo Hero mode.
- Expand hero-specific safety rules and hero profiles.
- Add optional semantic review/RAG mode for post-session analysis.
- Add optional offline OpenDota/OpenDota-like replay enrichment.
- Polish launcher and overlay UI.
- Add more sanitized session reports for coursework evaluation.

## Not Current Scope

- STRATZ live integration.
- Live scraping.
- Game-process hooks.
- Account/auth system.
- Database-backed user history.
- Automated input.
- Production-grade signed installer.
