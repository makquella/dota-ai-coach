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
