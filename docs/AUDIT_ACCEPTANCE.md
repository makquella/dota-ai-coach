# Acceptance against the audit of 7 October 2026

Source: the user's “Глубокий аудит Wardly / dota-ai-coach”, audited `dd5a83c`.
“Prepared” means implementation plus relevant checks in patch PRs; “merged” is
reserved for main. The 0.53.4–0.53.46 stack was integrated through #146, merge
`0d7ef29c7475b9b984921b969fdbda7fc31cc9ba`; individual stacked reviews were
closed as included. Their code is in main, rather than separately re-merged. Version numbers and PR quantity do not measure completion.
The core acceptance scope follows the original F01–F17 table and initial slices.
Additional engineering/product work is tracked separately, not silently dropped.

## Core findings

| ID | Original acceptance | Status / evidence |
|---|---|---|
| F01 | Durable finish until DB ack, idempotent retry/restart, failure tests | Merged through #146, 0.53.4; MATCH_RECOVERY.md |
| F02 | Running dedupe, bounded stop/join, safe store lifetime, real threads | Merged through #146, 0.53.5; JOB_QUEUE_LIFECYCLE.md |
| F03 | Validate backup before writes, atomic restore/link, corruption/rollback | Merged through #146, 0.53.6; HISTORY_BACKUP.md |
| F04 | Structured evidence and semantic AI verification, start with 3 valuable findings | Merged through #146, 0.53.38: vision, LH10, early deaths; FINDING_EVIDENCE.md and test_finding_evidence.py. Arbitrary prose/career remains outside this first boundary. |
| F05 | Recommendation log OSError preserves HTTP response and records diagnosis | Merged #100, 0.53.1 |
| F06 | Loopback/GSI tokens, Origin/Host and body bounds, real configuration/smoke | Merged through #146, 0.53.7; LOCAL_API_SECURITY.md |
| F07 | Locked Python runtime/dev/build with shared installation path | Merged #103, 0.53.3 |
| F08 | Advisory triage, compatible upgrades, clean install and Windows checks | Merged #102, 0.53.2; DEPENDENCIES.md lists residual build-only advisory |
| F09 | Short AGENTS/CLAUDE adapter, scoped explicit checks, preserve useful docs | Merged #101 |
| F10 | One coherent published runtime revision and ownership/reset, no I/O under locks; concurrent endpoints | Partial in main through 0.53.46: GSI/demo off the ASGI loop, bounded timings and generation-guarded owned history; finish whole-overlay/demo execution/history boundary |
| F11 | Atomic transfer claims/inserts and real local D1 concurrency | Merged through #146, 0.53.11; TRANSFER_ATOMICITY.md |
| F12 | Typed NormalizedState, MatchFacts, Finding + important I/O/detail DTO and consumers | Merged through #146, 0.53.39: actual NormalizedState/MatchFacts producers, Finding core and evidence/coverage/detail DTOs; DOMAIN_CONTRACTS.md and test_domain_contracts.py. Open tracker/event/params extensions are explicit. |
| F13 | Extract locales, JobQueue, transfer orchestration and match-detail slice; preserve exports/behavior and 2 actual UI scenarios | Merged through #146, 0.53.40: history-transfer, app-texts and match-detail modules plus prior JobQueue/match-locales extraction; real RU/EN file/full-review/missing-review scenarios, DESKTOP_BOUNDARIES.md |
| F14 | Pinned mypy, reviewed debt cannot grow, clean-module blocking gate | Merged through #146, 0.53.9, baseline pruned later; TYPE_CHECKING.md |
| F15 | Release validation on the same tag SHA before publication | Merged through #146, 0.53.10; RELEASE_VALIDATION.md |
| F16 | Canonical npm check, CI concurrency, meaningful Windows scope/stable required summary | Merged through #146, 0.53.12; WINDOWS_CI_SCOPE.md |
| F17 | Trusted sender/frame, navigation/popup guards, CSP and actual UI checks | Merged through #146, 0.53.8; DESKTOP_SECURITY.md |

## Additional tasks from sections 8–10, 15–18 and 22

These are acceptance tasks too. They are not included in the 17-finding percentage.

- [x] Portable `scripts/dev.py` with profiles and `check --changed` across staged,
  unstaged and untracked paths; optional thin hook adapter; explicit argv/cwd,
  Windows venv discovery; no deploy/publish/paid AI (0.53.42, DEV_RUNNER.md).
- [x] Version consistency script and generated site/changelog checks in the runner and CI (0.53.42).
- [x] Remove F841 unused assignment while preserving the state-changing call;
  remove the global lint exemption (0.53.43).
- [x] Pure abilities normalization helper to break the documented GSI/skills cycle,
  with compatibility re-export (0.53.43, PURE_ABILITIES.md).
- [x] Cache Markdown knowledge-base parsing at startup with dev mtime invalidation;
  defer retrieval until scheduler needs a candidate (0.53.45, KNOWLEDGE_BASE_CACHE.md).
- [ ] Profile large-history read models and EXPLAIN QUERY PLAN; avoid repeated
  analysis JSON parsing with revision-invalidated projections/caches.
- [x] Protect local secrets with OS-backed storage and migrate existing keys without
  logs/backups; backend receives credentials in memory (0.53.53, SECRETS_AT_REST.md:
  the backend seals its keys itself with DPAPI for the same Windows user instead of
  a launcher handoff; the launcher seals tokens/webhook with safeStorage).
- [ ] Device/transfer deletion capabilities with stored hashes and explicit legacy
  compatibility; preserve public share/profile ownership.
- [x] Scheduled dependency refresh/audit for runtime and build locks plus tests
  and actual Windows package checks (0.53.47, MAINTENANCE_VALIDATION.md).
- [x] Validate data-update PRs directly before merge even when workflow-token PRs
  do not trigger ordinary CI; include a change summary
  (0.53.47, immutable SHA validation and published functional check).
- [x] Canonical Node 22/Python 3.11 tooling version files consumed by workflows
  (0.53.47).
- [ ] Optional parser wrapper/build guidance where its maintained use warrants it.
- [x] Incremental live-message translation by ID/params rather than retranslating
  full historical copies (0.53.46, LIVE_MESSAGE_HISTORY.md; bounded selection/render
  caches and generation-guarded history; F10 whole-operation ownership remains).
- [x] Measure GSI phase p50/p95 and persistence time, move synchronous GSI/demo work off the ASGI event loop (0.53.41, LIVE_EVENT_LOOP.md; real same-loop requests).
- [x] Bound remaining census/recorder/settings I/O failures and retain diagnostics
  (0.53.44, LOCAL_IO_HEALTH.md; bounded retry/disable, not a filesystem timeout).
- [x] Async AI questions with request IDs/status, total deadline/attempt cap,
  duplicate retry protection, stale/cancel guards and atomic history append
  (0.53.52, AI_QUESTIONS.md; the request stays synchronous, bounded under the
  launcher's wait, with `GET /player/asks/{id}` for a lost answer).
- [x] Local operations health: job age/running/pending, persistence ack/error,
  queue depth, bounded latency observations and source freshness in developer UI
  (0.53.51, OPERATIONS_HEALTH.md; `/operations/health`, «Состояние операций»).
- [x] Investigate and fix the observed nightly fuzz seed-12 dead-hero phase
  container regression (0.53.48); preserve unknown signals and normal phases.
- [ ] More sanitized support/mid role replay acceptance cases and a fixed-clock
  compact regression runner over the existing simulation tools.
- [ ] Patch/source/rules/input versions, as-of/sample count where relevant, rebuild
  reason and comparable Progress metrics across changed rules.
- [ ] Automatic bounded rotating local backups, opt-in configuration/disk budget,
  migration/import backup and restore preview → validated atomic apply.
- [ ] Local post-match advice feedback (useful/irrelevant/repeated), keyed by advice
  ID; begin with a local experiment. Any future cloud aggregation remains opt-in
  with explicit allowlist/privacy changes.
- [x] Canonical hero identity regression coverage and shared minimal public/local
  profile appearance catalog/styles (0.53.50: `dota_constants.HEROES` + `hero_id_from_any`
  / `hero_key` for every spelling, `tests/test_hero_identity.py`; the Worker test
  compares every `cos-` rule of the public profile with the launcher's).
- [ ] Review repeated main response builders and remaining AI/detail orchestration
  after concrete boundaries; retain distinct status semantics.
- [x] Mark retained browser entrypoints debug-only and fix routing/docs; deletion
  requires evidence that they have no remaining users (0.53.49: `frontend/debug/`,
  `/debug/` from a source checkout only, the rest of `frontend/` no longer served or public).

Deliberately excluded by the audit: generic SaaS, new event bus/task broker,
plugin marketplace, deletion of replay fixtures or Java parser, merging live and
post-match LLM policies, and an unsolicited Pages publication workflow.
