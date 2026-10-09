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

## Match table

0.53.27 adds `MatchListResponse` to authenticated `GET /player/matches`. Its
three required fields are `linked`, `items` and `total`; an unlinked account
still returns exactly those fields with an empty list and zero total. Linked
responses keep stats, hero counts, filters, sync and nullable skipped-mode
counts. Nested models use the same strict/extensible and exclude-unset policy.
Pagination does not change the filtered total; hero choices count all stored
heroes. The existing query clamps, sort whitelist, order and SQL behavior stay.

List rows validate the stored match ID, optional nullable hero/result and K/D/A,
source strings, nullable parse state, analysis/timeline booleans, optional
nullable inventory and note. Stats validate nonnegative game/win counts,
nullable 0–100 integer winrate and nullable integer average score. Hero and
skipped counts use nonnegative safe integers; filters retain nullable hero/win,
extensible sort string and a strict ascending flag. Other row metrics and future
nested fields are preserved but not yet validated. Combat counters remain
independent measurements, and item/note text is not rendered as HTML.

Functional HTTP/SQLite cases compare full responses with the actual service for
empty/unlinked/filtered/paged tables, sorting, unknown results, zero/partial K/D/A,
notes, inventory and skipped modes. Existing sort/filter/history consumers run
alongside them; OpenAPI and malformed nested values are checked. JS JSDoc
describes this shape without changing consumer behavior.

Source and packaged Windows Electron smoke restores 32 fixture matches through
the actual backup API into a dedicated temporary `PLAYER_DATA_DIR`, with
OpenDota disabled. The genuine preload/IPC and table render load the next page,
toggle GPM sorting, select/clear a hero filter and preserve partial K/D/A,
unknown results and literal notes in RU/EN. The smoke restores the saved sort
and language, and removes its fixture DB after backend exit; it never imports
fixture history into the user's/developer's normal store. This covers the linked
table flow; full linked-review/analysis consumer scenarios remain future work.

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

## Progress in 0.53.32

`GET /player/career` now publishes `CareerResponse`. Required `linked` is a
strict boolean. Optional nullable counts, percentage, streak, hero filter,
hero choices, hero rows and series preserve the exact unlinked response
`{"linked": false}` through exclude-unset. Linked empty history retains known
zero counts with unknown winrate/streak; unknown match results stay nullable
booleans. Counts are nonnegative safe integers; percentages are 0–100 integers.
Series match IDs keep the same stored int64 wire format. All heroes remain
available as choices when filtering to one hero.

Nested `CareerHero`, `CareerStreak` and `CareerSeriesItem` validate their core
fields and retain extensions. Averages, trends, findings, focus, coach/Q&A,
rank, builds and other blocks remain unvalidated extensions. The existing
analysis, known-result denominator, averages, filters and cache/AI policy are
unchanged; this does not close F12. Malformed core output is a server validation
failure, not numeric coercion. JS JSDoc mirrors the core.

Functional cases compare complete decoded HTTP output with the actual service
for unlinked/empty and filtered SQLite history plus parsed reviews in RU/EN,
unknown results, zero/partial averages and nested extension retention. Schema
and malformed values are checked. Source/Windows Electron smoke opens genuine
Progress for the isolated 32-match fixture, checks unknown KDA and 52% from
16 wins/15 losses/one unknown, filters Juggernaut and clears it in RU/EN.

## Profile in 0.53.37

`ProfileResponse` validates the success responses of `GET /player/profile`,
`POST`/`DELETE /player/profile/mmr` and both shop actions. Required nullable
`profile` retains exactly `{"profile": null}` for an unlinked player. Nested
player, level, stats, sparks, rating and rating-point models validate their
core and preserve extensions. Achievements, cosmetics and shop rows remain
unvalidated extensions; the public friends-card contract is a separate boundary.

Player name/avatar/rank remain nullable. Level/XP, match/win counts and sparks
are nonnegative safe integers; level and next-level cost are positive. Unknown
winrate stays null and known percentage is a 0–100 integer. Hours are finite
nonnegative numbers. Rating source retains manual/medal, nullable rating stays
unknown, and estimated MMR and changes use signed safe integers: the existing
graph can extrapolate below zero. This validates its wire values without
changing rating calculations. Point time is an integer; optional nullable game,
hero, result and anchor keys retain their exact presence with exclude-unset.
Match IDs keep the existing stored int64 format.

Malformed core output raises server validation failure instead of numeric
coercion. Complete HTTP responses are compared with actual SQLite/service
output for unlinked/empty, unknown results, manual zero/positive MMR, medal
estimates, signed graphs and RU/EN. Real MMR save/clear and funded cosmetic
purchase/equip exercise every success endpoint; normal error responses remain.
Validation checks cover invalid nested numbers/booleans/strings, nonfinite
hours, extension retention and the five published OpenAPI schemas. JS JSDoc
mirrors the core. Source/Windows smoke retains actual Profile/friends IPC,
MMR save/clear, locale and account transitions from 0.53.36.

Analysis/coach/cache versions and stored history do not change. F12 remains
partial: nested achievements/shop, public card, other mutations, facts and
overlay responses still require their own contracts.

## Domain/finding cores in 0.53.39

Actual normalized-state and source-facts producers return typed domain shapes.
The match-detail response validates finding/source/coverage cores and binds each
measurement to its own finding params. Legacy extensions and unset fields remain
intact. See [DOMAIN_CONTRACTS.md](DOMAIN_CONTRACTS.md) for scope, static negative
fixtures and remaining open tracker/event/params extensions.
