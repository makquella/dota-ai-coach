# Dependency and generated-data maintenance (0.53.47)

`.node-version` (Node 22) and `.python-version` (Python 3.11) are the CI/build/tooling
version sources. Workflows read them after checkout; the backend CI explicitly
installs Node for actual RU/EN catalog validation. Electron's embedded runtime
remains its own packaged dependency. Local newer Node versions may work, but
validation on the declared CI version remains required. Workflow syntax and
expressions are checked by pinned actionlint 1.7.9.

Dependabot requests weekly launcher/Worker npm updates, including development and
build dependencies. Compatible minor/patch updates are grouped; majors remain
individual reviewable PRs. Actions updates are monthly. There is no auto-merge.

The monthly/manual Python refresh uses the existing pinned compiler to regenerate
all three universal/hash profiles. Changes stay in a dependency PR. It calls the
full reusable CI directly on the generated head, including actual Windows
packaging. A future compiler/mypy contract change may require deliberate review;
automation never grows type allowances or silently overrides failing tests.

Weekly/manual dependency audits retain complete npm reports and Python dev/build
profile reports on Linux and Windows (platform markers matter). The latter
includes the runtime graph and uses isolated pip-audit 2.9.0. Build dependencies
are included. JSON artifacts last 30 days; the scan outcome remains visible.
Advisory return codes do not suppress report retention. A green report-producing
workflow is not an assertion of zero advisories: reports require triage against
`DEPENDENCIES.md`, which already documents residual build-only advisories.
Refresh PRs also produce these reports for their proposed immutable head.

Dota/Stratz refreshes keep their existing targeted pre-PR checks and add an exact
diff summary. Hero validation now happens before opening the Dota-data PR. The
workflow token cannot trigger ordinary PR CI, so each refresh calls
`refresh-validation.yml` with create-pull-request's actual head SHA. This wrapper
calls full reusable CI, which verifies its checkout SHA. Only after that result
does it publish `Generated refresh functional validation` on the same head.
Failure/cancellation/skipping cannot become success. The check links the original
run and explicitly separates functional validation from advisory triage.

Generation gets contents/PR write permission; validation is read-only except the
separate result publisher's checks permission. No new deployment, release,
provider-paid call or auto-merge is introduced. Existing scheduled data fetching
and secrets remain in their original generation jobs; validators inherit none.

Local actionlint verifies all workflows. Final PR CI verifies the declared Node
version, consumer suites and actual Windows package path. The scheduled registry
refresh itself is prospective; it requires the repository's existing Actions
permission to create PRs. Live STRATZ fetching is not needed to validate these
workflow changes and was not invoked for this patch.
