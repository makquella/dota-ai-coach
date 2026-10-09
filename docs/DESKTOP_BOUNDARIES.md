# Initial desktop extraction (0.53.40, F13)

The audit's initial moves were JobQueue, renderer locales, history-transfer
orchestration and a match-detail slice after boundary tests. JobQueue and match
catalogs were extracted earlier; this patch completes the concrete desktop moves:

- `history-transfer.js` owns backup file export/import and encrypted one-time
  transfer orchestration (gzip, native crypto, size bounds, collision retry,
  claim/import/delete). `main.js` supplies window/dialog/backend/cloud/log ports
  and retains trusted IPC handlers and code input bounds. The installer explicitly
  includes the new main-process module. Existing result shapes remain intact.
- `renderer/app-texts.js` creates independent RU/EN control-panel catalogs, with
  the update-history provider supplied explicitly. `app.js` consumes the catalog;
  locale tests import the actual desktop catalogs rather than evaluating copied
  source literals. The small overlay catalog remains a separate future slice.
- `renderer/match-detail.js` composes loading/error/complete review, navigation,
  share/PDF controls, section zones, hydration and chart initialization from
  explicit card/DOM/action ports. `matches.js` retains accepted-response ownership,
  navigation state and card implementations; career/profile do not live in the
  detail controller. The renderer script is shipped under `renderer/**/*`.

Behavior tests use genuine filesystem/gzip/crypto/fetch with scripted external
backend/Worker HTTP boundaries: gzipped/plain JSON, damaged input, cancellation,
missing window, backend failure, code collision cap/size limit, encrypted roundtrip,
claim/import/delete and invalid/expired codes. Catalog tests verify functional copy
and detached nested/update tables. Existing installer module checks apply.

Source/Windows Electron smoke drives RU/EN settings, backup buttons through trusted
IPC, actual temporary file export/import and an isolated real SQLite backend.
Only the OS chooser/reveal ports select the dedicated smoke file; production uses
Electron dialogs/shell normally. No transfer is published during GUI smoke.
The smoke fixture supplies real recorded timelines; opening a row rebuilds and
renders the actual complete analysis, evidence and charts. Missing-record navigation
uses the same existing exposed view action and backend IPC. Back/forward/focus,
latest-response ownership, paging/filter/sort, Profile/MMR and CSP/sender checks
continue over this fixture.

The dedicated smoke directory contains both DB and backup and is removed after
backend shutdown. User history, friend publication/consent and account settings
are not used for the fixture. Language/sort are restored. Raw share/transfer/key
material is not printed by transfer tests.

This completes F13's first concrete extraction and actual UI acceptance. It does
not claim that every card or main-process feature has been decomposed. Further
slices should preserve these boundaries rather than create a generic event bus
or renderer framework.
