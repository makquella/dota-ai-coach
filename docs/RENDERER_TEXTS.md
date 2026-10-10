# Match-screen copy boundary

F13, second slice in 0.53.16, moves the 1,386-line UK/EN `TEXT` literal out of
`renderer/matches.js` into `renderer/match-texts.js`. Text values and functions
are preserved; the literal is only reindented. The controller keeps view state,
actions and DOM rendering, reducing it from 6,853 to 5,468 lines at extraction.

`WardlyMatchTexts.create({ number, decimal, clock, plural })` returns both
language tables. These functions are explicitly supplied by the view: copy no
longer implicitly depends on its lexical scope. The view's number/decimal
formatters continue reading the current locale after language switching; copy
is not frozen to the startup language. Translation lookup/fallback stays in the
view. The Node export exposes the same factory without DOM/Electron imports.

`index.html` loads the factory before the controller under the existing self
CSP. `renderer/**/*` already includes it in the installer, and `npm run check`
checks its syntax explicitly. The factory has no IPC, network or storage access.

Existing duplicate-key and UK/EN key-coverage checks now read the canonical
literal. Three factory tests exercise section metric/time formatter bindings,
Ukrainian plural delegation and changing locale behind the formatter. Source
and packaged Windows smoke switch UK/EN, navigate to the real Matches view and
verify rendered copy plus the authenticated API/preload/security checks. These
DOM checks catch missing scripts, load order and broken view initialization.

Remaining F13 work includes launcher locale extraction, splitting match detail
from profile/career/actions, and main-process history-transfer orchestration.
This slice changes the copy boundary only; it does not introduce a new UI/data
framework or claim that the remaining large controllers are refactored.
