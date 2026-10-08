# Acceptance against the audit of 7 October 2026

Source: the user's “Глубокий аудит Wardly / dota-ai-coach”, audited `dd5a83c`.
“Prepared” means implementation plus relevant checks in patch PRs; “merged” is
reserved for main. Version numbers and PR quantity do not measure completion.
The core acceptance scope follows the original F01–F17 table and initial slices.
Additional engineering/product work is tracked separately, not silently dropped.

## Core findings

| ID | Original acceptance | Status / evidence |
|---|---|---|
| F01 | Durable finish until DB ack, idempotent retry/restart, failure tests | Prepared 0.53.4; MATCH_RECOVERY.md |
| F02 | Running dedupe, bounded stop/join, safe store lifetime, real threads | Prepared 0.53.5; JOB_QUEUE_LIFECYCLE.md |
| F03 | Validate backup before writes, atomic restore/link, corruption/rollback | Prepared 0.53.6; HISTORY_BACKUP.md |
| F04 | Structured evidence and semantic AI verification, start with 3 valuable findings | Prepared 0.53.38: vision, LH10, early deaths; FINDING_EVIDENCE.md and test_finding_evidence.py. Arbitrary prose/career remains outside this first boundary. |
| F05 | Recommendation log OSError preserves HTTP response and records diagnosis | Merged #100, 0.53.1 |
| F06 | Loopback/GSI tokens, Origin/Host and body bounds, real configuration/smoke | Prepared 0.53.7; LOCAL_API_SECURITY.md |
| F07 | Locked Python runtime/dev/build with shared installation path | Merged #103, 0.53.3 |
| F08 | Advisory triage, compatible upgrades, clean install and Windows checks | Merged #102, 0.53.2; DEPENDENCIES.md lists residual build-only advisory |
| F09 | Short AGENTS/CLAUDE adapter, scoped explicit checks, preserve useful docs | Merged #101 |
| F10 | One coherent published runtime revision and ownership/reset, no I/O under locks; concurrent endpoints | Partial through 0.53.41: GSI/demo off the ASGI loop and bounded phase timings; finish whole-overlay/demo execution/history boundary |
| F11 | Atomic transfer claims/inserts and real local D1 concurrency | Prepared 0.53.11; TRANSFER_ATOMICITY.md |
| F12 | Typed NormalizedState, MatchFacts, Finding + important I/O/detail DTO and consumers | Prepared 0.53.39: actual NormalizedState/MatchFacts producers, Finding core and evidence/coverage/detail DTOs; DOMAIN_CONTRACTS.md and test_domain_contracts.py. Open tracker/event/params extensions are explicit. |
| F13 | Extract locales, JobQueue, transfer orchestration and match-detail slice; preserve exports/behavior and 2 actual UI scenarios | Prepared 0.53.40: history-transfer, app-texts and match-detail modules plus prior JobQueue/match-locales extraction; real RU/EN file/full-review/missing-review scenarios, DESKTOP_BOUNDARIES.md |
| F14 | Pinned mypy, reviewed debt cannot grow, clean-module blocking gate | Prepared 0.53.9, baseline pruned later; TYPE_CHECKING.md |
| F15 | Release validation on the same tag SHA before publication | Prepared 0.53.10; RELEASE_VALIDATION.md |
| F16 | Canonical npm check, CI concurrency, meaningful Windows scope/stable required summary | Prepared 0.53.12; WINDOWS_CI_SCOPE.md |
| F17 | Trusted sender/frame, navigation/popup guards, CSP and actual UI checks | Prepared 0.53.8; DESKTOP_SECURITY.md |

## Additional tasks from sections 15–18 and 22

These are acceptance tasks too. They are not included in the 17-finding percentage.

- [ ] Portable `scripts/dev.py` with profiles and `check --changed` across staged,
  unstaged and untracked paths; optional thin hook adapter; explicit argv/cwd,
  Windows venv discovery; no deploy/publish/paid AI.
- [ ] Version consistency script and generated site/changelog checks in the runner.
- [ ] Remove F841 unused assignment while preserving the state-changing call;
  remove the global lint exemption.
- [ ] Pure abilities normalization helper to break the documented GSI/skills cycle,
  with compatibility re-export.
- [ ] Incremental live-message translation by ID/params rather than retranslating
  full historical copies.
- [x] Measure GSI phase p50/p95 and persistence time, move synchronous GSI/demo work off the ASGI event loop (0.53.41, LIVE_EVENT_LOOP.md; real same-loop requests).
- [ ] Bound remaining census/recorder/settings I/O failures and retain diagnostics.
- [ ] Async AI questions with request IDs/status, total deadline/attempt cap,
  duplicate retry protection, stale/cancel guards and atomic history append.
- [ ] Local operations health: job age/running/pending, persistence ack/error,
  queue depth, bounded latency observations and source freshness in developer UI.
- [ ] More sanitized support/mid role replay acceptance cases and a fixed-clock
  compact regression runner over the existing simulation tools.
- [ ] Patch/source/rules/input versions, as-of/sample count where relevant, rebuild
  reason and comparable Progress metrics across changed rules.
- [ ] Automatic bounded rotating local backups, opt-in configuration/disk budget,
  migration/import backup and restore preview → validated atomic apply.
- [ ] Local post-match advice feedback (useful/irrelevant/repeated), keyed by advice
  ID; begin with a local experiment. Any future cloud aggregation remains opt-in
  with explicit allowlist/privacy changes.
- [ ] Canonical hero identity regression coverage and shared minimal public/local
  profile appearance catalog/styles.
- [ ] Review repeated main response builders and remaining AI/detail orchestration
  after concrete boundaries; retain distinct status semantics.
- [ ] Mark retained browser entrypoints debug-only and fix routing/docs; deletion
  requires evidence that they have no remaining users.

Deliberately excluded by the audit: generic SaaS, new event bus/task broker,
plugin marketplace, deletion of replay fixtures or Java parser, merging live and
post-match LLM policies, and an unsolicited Pages publication workflow.
