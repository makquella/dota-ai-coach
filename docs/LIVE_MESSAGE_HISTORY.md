# Owned history and incremental advice messages (0.53.46)

`CoachSessionHistory` owns append/deduplication/reset with a short lock. Record
construction, message selection and defensive copying run outside it. Prepared
appends carry the captured generation; reset rejects an older append. Published
records are private and never mutated. Each accepted record has a session-scoped
ID, distinct after reset, even if advice counts restart. This is a local record
identity, not a device/account identifier or authorization token.

`records(limit)` selects only the requested suffix under ownership and deep-copies
those records after release. `/advice/recent` requests at most 20 instead of
copying all 200 retained records and then slicing. Full coach-summary export keeps
the complete bounded history. Simultaneous identical appends add one record.

Live recommendation/last-visible/history DTOs retain canonical English action and
reason and add `action_message` / `reason_message`: `{id, params}`. IDs derive from
the exact canonical catalog entry or regex source/flags; they do not change when
entries are inserted/reordered. Pattern values become named parameters. Consider
and multi-sentence messages reference structured child messages in `params.parts`.
Unknown text has an explicit fallback descriptor and stays English; mixed
known/unknown sentences are never partly translated.

Selection and RU rendering use separate bounded 512-entry caches. Rendering looks
up the message ID and formats parameters instead of rescanning historical English
through regexes. Legacy callers and records lacking descriptors retain translation
fallback. DTO shape/depth/parameter limits and invalid descriptors cannot break
the response. Locale selection never mutates canonical history. Status text uses
the same bounded message cache internally; no new external translation service.

Real thread tests prove deduplication, private records and reset during a paused
prepared append. A deepcopy trace verifies only the selected suffix is copied.
Actual GSI → overlay → RU/EN recent HTTP requests prove stable IDs and zero parser
or renderer cache misses on unchanged repeat reads. Catalog equivalence, unknown
fallback, dynamic params and cache bounds supplement existing replay translation
coverage. All existing review and advice text policies remain unchanged.

This completes the incremental translation task and the history-owner portion of
F10. GSI/MatchMemory/scheduler/demo/overlay still need one whole-operation runtime
boundary; independently safe owners are not that boundary.
