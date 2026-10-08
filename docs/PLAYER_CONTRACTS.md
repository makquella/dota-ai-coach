# Player response contracts

## Player polling status

0.53.25 extends the same runtime boundary to authenticated `GET /player` with
`PlayerStatusResponse` and nested `PlayerSyncResponse` / `PlayerAIResponse`
schemas in OpenAPI. Strict booleans cover linking, provider enablement and key
configuration; nullable account/source values preserve an unlinked account.
Account IDs retain the existing nonnegative SQLite int64 wire format. Match,
pending-job and optional fetched counts are nonnegative safe integers. Running
work still counts as pending work. A fetched count of zero is a measured value.

Sync state remains an extensible string; timestamps, errors and error codes
remain nullable strings. `fetched` is optional: `exclude_unset=True` keeps it
absent before fetching, and preserves an explicitly supplied null. The response
retains undeclared player, detected-account, live, review, today, goals and tilt
extensions, including future nested sync/AI fields. Those extensions are not yet
validated. Link/unlink/sync mutation endpoints are outside this polling slice.

Functional checks compare complete HTTP responses with actual service output
for unlinked, manual and GSI linking, SQLite profile/match data and provider
errors. A real queue thread paused at an external OpenDota fixture verifies
queued/running/completed states, pending counts and zero fetched results. The
published schema and rejection of malformed core values are also checked.
`renderer/match-contract.js` documents this core for existing JS consumers;
their behavior and IPC privileges are unchanged.

## Match detail

F12 starts in 0.53.17 at `GET /player/matches/{match_id}`. The canonical runtime
contract is `backend/app/player_contracts.py`, used as the FastAPI response model
and published in `/openapi.json` (200 `MatchDetailResponse`, 404
`MatchNotFoundResponse`). Authentication remains required for OpenAPI and player
data. An absent match still returns `{"status":"error","code":"match_not_found"}`.

The core validates the nonnegative SQLite int64 match ID, summary object,
nullable source list, parse-status string, nullable analysis and strict loading
boolean. Both summary and analysis headline validate kills/deaths/assists as
nonnegative integers up to JavaScript's safe-integer limit. Booleans, numeric
strings, fractions and negative values are rejected rather than coerced.
Null/absent counters are unknown; zero is a valid measured total. A loading
response has `analysis: null`; analysis with partial counters remains a review.

Extensible models retain every undeclared field, including notes, analysis
sections, curves, findings, scoreboard, focus, baselines, coach and question
evidence. `response_model_exclude_unset=True` preserves absent optional counters
instead of adding null keys to older responses. This slice validates the core,
not the full shape of each extension. Invalid core output is a server validation
failure; it is not silently converted into invented measurements. SQLite cache
recovery and backup validation remain separate responsibilities.

`renderer/match-contract.js` describes the core in JSDoc and supplies the shared
`combatScore` consumer. Each counter is checked independently; `0 / — / 5` and
`— / 4 / 9` retain partial observations. All unknowns collapse to `—`; compact
cards omit that empty score. The review header, match rows, scoreboard, Home
summary, recent cards and command-palette results use the same function. Text
still enters DOM via textContent. No new renderer network/IPC privileges are
introduced; the helper loads before matches.js and ships through renderer/**/*.

HTTP/SQLite checks cover parsed/unparsed reviews in RU/EN, notes, GSI-only
partial/zero counts, loading/missing responses, and cached coach/question
evidence. Complete decoded responses are compared with the actual service
output to detect dropped extension fields. Contract checks reject coercion and
inspect the published OpenAPI schema. Node checks exercise unknown, partial,
zero and malformed inputs; real source/Windows Electron smoke loads the module,
checks partial-counter DOM text and navigates the actual RU/EN Matches screen.
The counter smoke checks the shared formatter, not a full linked-match UI flow.

Remaining F12 work: type the other analysis/facts/career/player mutations/overlay
response boundaries and nested extensions, and add full linked-match consumer
scenarios. Match/account IDs retain the existing SQLite int64 numeric wire
format: IDs beyond JavaScript's safe integer range need a separate string-format
migration. These slices do not change analysis rules, ANALYSIS_VERSION,
COACH_VERSION or caches.
