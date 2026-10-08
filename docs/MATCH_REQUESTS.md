# Review request ownership

0.53.29 adds a private generation owner in `renderer/match-requests.js`.
Foreground review loads and quiet refreshes use the same instance. A request
captures view, match ID and locale before calling the real player API. Only the
latest generation in the still-visible match/locale may synchronously apply its
result. Leaving the review increments generation and clears its pending refresh
timer; returning to the same ID cannot revive a response from an earlier visit.
Changing locale also prevents an older response from applying. Rejected stale
results cannot render or schedule another poll.

The owner performs validation and the parent callback in one JS turn. It does
not abort the underlying IPC/HTTP request or change backend cache/network work.
Current normalized errors retain the normal error UI. Quiet refresh keeps the
existing input/AI form protection and 4/30-second polling policy. Locale-change
rendering occurs only after an applied response. Other table/career/question/
action requests still have their own state handling; F13 remains partial.

Five public module scenarios use controlled asynchronous external requests to
verify out-of-order completion, same-ID leave/return, changed match/locale/view,
skipped hidden loads and error recovery. Source and packaged Windows Electron
smoke starts actual A/B/A review requests through preload/IPC with a tab change,
awaits all of them and verifies that only the latest applies, on RU/EN. It uses
the isolated history fixture from 0.53.27. Navigation/focus, table and security
checks continue. No new renderer privileges, API routes or dependencies are added.

## Match list and pagination

0.53.30 adds `renderer/match-list-requests.js`. The table's replacement request
owns a generation before awaiting player-status preparation. Superseded
preparations cannot start a list fetch. The request captures the prepared
account/link state and filter/sort; only the latest still-visible selection may
apply its result. Leaving the table or successfully linking/unlinking cancels
pending table work, including A/B/A returns. Status preparation itself still
uses the existing shared player-status loader; this is not a status controller
refactor. The first preparation may discover the selected account.

Pagination permits one pending page and blocks paging during replacement. A
page captures selection, account and offset; replacement, cancellation, changed
account or changed row count rejects it. Current errors preserve the previous
UI behavior and release ownership for retries. Validation and the parent
callback are synchronous in one JS turn. Underlying IPC/HTTP is not aborted.
Table strings remain localized at render time; no locale-dependent list
response is cached. Periodic/sync refresh and return-row focus are preserved.

Ten module scenarios exercise controlled external completion order, preparation,
filter/sort/account changes, replacement/page races, duplicate clicks, tab
return, offset and error recovery. Source/Windows smoke double-clicks More,
starts a page then switches filters A/B/A, and checks leave/return generations
through actual preload/IPC in RU/EN using the isolated SQLite fixture. F13
remains partial: career/profile/status/question/action controllers remain.
