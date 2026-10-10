# Update history boundary

The 0.53.24 F13 slice extracts 758 lines of UK/EN What's New history from
`renderer/app.js` into `renderer/whats-new.js`, together with the existing
numeric skipped-version selection. The I18N table obtains detached locale
tables from the module; main retains its DOM rendering/dismissal and IPC flow.
All historical bullets were compared as actual evaluated objects before/after
extraction and preserved exactly. No history entry is removed.

`texts(language)` returns copied arrays, with English for an unknown language.
`versions(table, current, from)` keeps the existing behavior: show current
notes and skipped versions newer than the previous installation, newest first,
at most four. An installation with no prior version gets only current notes.
Missing/empty current notes keep the DOM card hidden. The selector does not
change updater versioning, release publication, seen-version settings or consent.

The module is loaded before app.js in the panel and included by the existing
`renderer/**/*` packaging glob. Canonical syntax checking includes it. Existing
i18n checks still check both language tables and duplicate keys, with the real
module supplied when evaluating panel I18N. Four module cases cover skipped
patch ordering/limit, initial/missing notes, detached bilingual tables/fallback,
and current version consistency across launcher lock, both backend versions
and bilingual release notes.

Source and packaged Electron smoke renders the actual What's New card in UK
and EN, including skipped-version labels and the current bullets, then restores
real status. The test uses synchronous DOM reads because smoke windows can be
hidden and animation frames may be suspended. It leaves CSP, sandbox and IPC
guards active. This extraction does not close other detail/controller/state
boundaries in F13 or introduce a general UI harness.
