# Dependency maintenance — 0.53.2

Checked on 7 October 2026 against the public npm advisory API. Baseline: the
0.53.1 branch (`bbc6151`). These are package/range matches, not a count of
exploitable Wardly vulnerabilities.

| Component | Previous | Updated | Scope |
|---|---|---|---|
| Electron | 42.4.0 | 42.11.12 | Bundled desktop runtime; stays on 42.x |
| electron-builder | 26.15.2 | 26.17.0 | Packaging tools |
| js-yaml | 4.2.0 | 4.3.2 | Updater YAML parsing and build tools |
| tar | 7.5.16 | 7.5.22 | Build tools |
| Wrangler | 4.142.0 | 4.148.0 | Worker development/deployment tools |
| sharp | 0.35.4 | 0.35.5 | Local Miniflare image tooling |
| Worker undici | 7.29.0 | 7.29.1 | Local Miniflare HTTP client |

Other compatible launcher transitives were refreshed within their parent
constraints. `electron-updater` stays at 6.8.10, the latest published 6.x
version at the check date; its YAML dependency now resolves to 4.3.2.

Wrangler 4.148.0 pins Miniflare's `sharp` to 0.35.4. A scoped
`overrides["sharp@0.35.4"] = "0.35.5"` applies the available patch to this
version without changing unrelated dependencies. Remove the override when
upstream pins a fixed version. The native package was checked by converting a tiny SVG to PNG
with sharp 0.35.5 / librsvg 2.63.2.

## Advisory results

| npm audit result | Before | After |
|---|---|---|
| Launcher package entries | 17: 1 critical, 8 high, 8 moderate | 8 moderate, 0 high/critical |
| Launcher unique advisory URLs | 63 | 1 |
| Launcher `--omit=dev` package entries | — | 0 |
| Worker tooling package entries | 4 high | 0 |
| Worker unique advisory URLs | 11 | 0 |

`--omit=dev` excludes Electron even though Electron is shipped in the app;
the full audit and its six Electron advisory ranges were checked separately.
42.11.12 is outside all six reported ranges, including
[the compromised-renderer preload-cache advisory](https://github.com/advisories/GHSA-qmv3-fv6v-rmhq)
fixed in 42.10.0. Protocol/webview/sandbox advisories have additional
conditions; this update does not establish that Wardly was exploitable.

The remaining
[sprintf-js precision DoS advisory](https://github.com/advisories/GHSA-hp3w-g68c-fv3c)
matches all published versions; the latest is still 1.1.3. It is reached via
the development chain `app-builder-lib → @electron/get 3.1.0 → global-agent
3.0.0 → roarr 2.15.4 → sprintf-js 1.1.3`. npm propagates this one advisory
through eight package entries. It is a build-tool logging dependency, absent
from the production dependency graph. An exploitable Wardly path has not
been established. Do not force npm's suggested builder downgrade or override
roarr/@electron/get across major versions to hide the report. Follow up when
the sprintf-js advisory is fixed or the upstream download chain is replaced.
Audit F08 therefore retains this explicit build-tool follow-up.

## Verification

From each npm package directory:

```bash
npm ci --no-audit --no-fund
npm test
npm audit --json
```

Launcher also uses `npm run check`, a current Electron smoke result, and the
Windows CI package/build smoke. Full launcher audit currently returns exit
status 1 for the documented moderate advisory; `npm audit --omit=dev` and
Worker audit return 0. The override uses a version selector so the same
lockfile installs with npm 10 and npm 11. Clean install, tests, bundling and
migrations were checked with Node 22.23.3/npm 10.9.9; the cloud environment's
Node 24.19.0/npm 11.9.0 clean install was checked as well.
Audit results describe the registry snapshot, not a permanent guarantee.

Worker CI installs the exact lockfile, bundles with
`npx --no-install wrangler deploy --dry-run` and applies all six migrations
with `wrangler d1 migrations apply dota-ai-coach --local`. Local workerd
health/config requests and two statistics writes were also checked against
real local D1: one row was updated and only allowlisted fields persisted.
These checks validate the dependency update; they do not resolve audit F11's
concurrent transfer-claim defect or constitute a full D1 regression harness.

The Worker CLI validation uses local bindings and temporary output. It does
not publish a Worker or contact the production database.
