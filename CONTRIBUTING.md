# Contributing to Wardly

Thanks for taking the time. Wardly is a small project with a few firm rules; reading this page first saves a review round.

## Ground rules

- **Valve's GSI only.** Nothing that reads game memory, captures the screen, sends input or injects into Dota is accepted, whatever it would enable.
- **Rules decide, AI explains.** Live advice (what, when, how urgent, how often) comes from deterministic local rules. AI may only phrase or review, on facts the code computed.
- **Unknown stays unknown.** If GSI does not show it (an enemy out of vision, team readiness), the coach does not guess it.
- **Local-first and opt-in.** Player history, notes and keys stay on the player's computer. A new upload needs consent, an allowlist on the server, redaction, a retention limit and an entry on [`site/privacy.html`](site/privacy.html).
- **Two languages.** Every visible text has Ukrainian and English. Live advice is English inside the backend and translated at the API edge (`advice_i18n.py`); post-match findings are ids plus parameters (`analysis_texts.py`).

The full list, with the owning modules, is in [AGENTS.md](AGENTS.md).

## Setup

```bash
cd backend
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
python -m pip install --require-hashes --only-binary=:all: -r requirements-dev.txt

cd ../frontend/launcher && npm ci                       # the desktop app
cd ../../services/api && npm ci                         # the Worker (only if you touch it)
```

`npm run dev` in `frontend/launcher/` starts the whole app: it runs its own backend on a free port. Do not start a second `uvicorn` for it. Without Dota, use the replay demo: [docs/REPLAY_DEMO.md](docs/REPLAY_DEMO.md).

## Before you open a pull request

```bash
python scripts/dev.py check --changed --dry-run   # what runs for your diff
python scripts/dev.py check --changed
```

The runner picks the checks from the paths you changed: Ruff and format for the changed Python, the backend tests and the mypy gate (no new type debt), the desktop syntax check and tests, the Worker tests with a real local D1, and the site, changelog and version checks. [docs/TESTING.md](docs/TESTING.md) maps each area to its tests.

- **Tests come with behaviour.** Live-advice changes get a replay or fixed-clock test; lifecycle changes get real thread and lifespan tests; UI changes get a DOM or IPC scenario.
- **Versions.** A fix is the next patch of the current minor (`0.56.1`); a new feature starts the next minor. Sync the launcher `package.json` and lock, both backend version strings, add UK and EN notes in `docs/release-notes/` and «What's new» (`renderer/whats-new.js`), then run `python scripts/build_changelog.py`. `python scripts/bump_version.py --check` verifies it.
- **Rules and formats.** Changing analysis rules or stored formats means reviewing `ANALYSIS_VERSION` / `TRIM_VERSION`, cache invalidation and old data. Never lose notes, history, the linked account or consent.
- **Never commit** local databases, recordings, `.env` files, keys or build outputs.

## Commits and pull requests

- One topic per pull request. Small, reviewable diffs merge faster.
- Commit subject: imperative, under ~72 characters, with the area first when it helps (`Site: …`, `0.56.0: …`). The body says what changed and why.
- The pull request description lists what changed and the checks you ran (and what you could not run, such as a real Windows install).

## Reporting bugs and ideas

- **Bugs:** «Report a problem» in the app's Settings sends the log with keys removed. Or [open an issue](https://github.com/makquella/dota-ai-coach/issues/new/choose).
- **Security issues:** please do not open a public issue; see [SECURITY.md](SECURITY.md).
- **Ideas:** open an issue, or write in [t.me/wardlydota](https://t.me/wardlydota).
