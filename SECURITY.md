# Security policy

## Reporting a vulnerability

Please report security issues privately through GitHub: **[Report a vulnerability](https://github.com/makquella/dota-ai-coach/security/advisories/new)**. Do not open a public issue for them.

Include what you found, how to reproduce it, and the version (shown in Settings, or the release tag). You will get an answer within a week. Fixes ship as a patch release, and the advisory is published once players have the update.

## Supported versions

Only the latest release gets security fixes. The app updates itself (never while Dota is running), so most players are on it within days.

## Scope

In scope:

- **Local API** (`backend/`). It listens on `127.0.0.1` only, with separate control and GSI tokens, Origin and Host checks, and bounded request bodies ([docs/LOCAL_API_SECURITY.md](docs/LOCAL_API_SECURITY.md)). A web page or another local user reaching it is a vulnerability.
- **Desktop app** (`frontend/launcher/`): IPC sender checks, navigation and popup guards, CSP ([docs/DESKTOP_SECURITY.md](docs/DESKTOP_SECURITY.md)); keys at rest ([docs/SECRETS_AT_REST.md](docs/SECRETS_AT_REST.md)).
- **Cloud API** (`services/api/`, `api.luhovyimvp.dev`): problem reports, opt-in statistics, shared reviews, history transfer and device deletion.
- **Updates and the installer**: the release pipeline and the auto-update feed.

Out of scope: third-party services Wardly talks to (OpenDota, Valve's CDN, AI providers), denial of service by volume, and reports that need a compromised computer.

## Data we never want to see

Keys, deletion tokens, Steam IDs and match data must never appear in logs, problem reports or backups. If you find a path where they do, that is a vulnerability too.
