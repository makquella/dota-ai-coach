# Match navigation boundary

0.53.28 extracts the browser-like back/forward history from `renderer/matches.js`
into `renderer/match-navigation.js`. A viewer owns one factory instance with
`current`/`visit` callbacks; arrays and the synchronous movement guard stay
private. Retained places are copied, so caller mutation and another viewer
cannot alter that history. `samePlace` preserves string/number match-ID equality.

Normal navigation keeps the newest 30 prior places and clears the forward
branch. Equal places and disabled notes do not record a new entry. Back/forward
visits suppress recording their own synchronous transition. `finally` releases
the guard after a rendering callback throws; travel is not transactional and
does not undo the popped/pushed entries on failure, preserving prior behavior.
The callback is deliberately synchronous, as in the existing controller: this
module does not cancel or order asynchronous match requests.

The parent retains route selection, review origin, tab scroll memory, the
return button, row focus, keyboard/mouse guards, DOM and IPC. Returning from a
review previously focused a row that the subsequent async table reload replaced.
The parent now retains that focused match ID across table rendering and restores
focus only if its row still exists. Module loading is
before matches.js and included by the existing renderer packaging glob; the
canonical syntax and test commands include it. No new renderer privileges or
visible translations are introduced.

Five module scenarios exercise the public interface: tab/review round trips,
equal places and forward branching, the 30-place limit, detached/independent
history, and movement-guard recovery/disabled notes. Source and Windows Electron
smoke opens a real stored match row through preload/IPC, uses Alt+Left/Right and
the actual return button, and verifies the tab and keyboard focus after the real
API response replaces the old row in UK/EN. The
fixture uses the dedicated temporary player DB from 0.53.27; it is a linked
review navigation scenario with no analysis, not a complete analysis-rendering
test. Other review/actions/state boundaries remain F13 work.
