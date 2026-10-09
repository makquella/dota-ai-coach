# Finding measurements (0.53.38)

F04's first three groups are observer/sentry vision (`wards_low/high`), last hits at
10:00 (`lh10_low/great`) and early deaths (`lane_deaths`). A measurement has
`field`, `source`, `precision`, `value`, `observed_at` and nullable recording
`coverage` (`start`, `end`, gaps >30 seconds, full-match flag). Bounded native
integer counts preserve measured zero; unknown, malformed or conflicting data
cannot license quantified claims.

`finding_evidence.py` owns source construction/validation. Parsed `obs_log` /
`sen_log` counts precede OpenDota totals. GSI inventory decreases remain estimates
because giving a ward away can also decrease the inventory. Incomplete GSI does
not score whole-match vision. Only a sample at second 600 licenses an exact LH10
finding; a carried sample keeps its real observation time. Death counts describe
recorded nonnegative events through second 600, not proof of every death or its
cause. An absent kill log does not mean zero.

Per-minute GSI series preserve unknown time before the first sample and beyond
30 seconds of staleness. Farm stalls cannot bridge unknown intervals. Renderer
charts break paths/areas at those intervals. Coverage remains visible in the
review header even when no supported finding can be produced.

Analysis version **21** rebuilds old reviews through the existing read path.
`evidence_findings` retains the three groups' `{id, params, evidence}` before deduplication and the
visible finding cap, so presentation priority cannot remove verification data.
AI compaction revalidates field/parameter/source consistency. An exact LH10 source
can fill the player's sample when lane/peer measurements are absent, retaining
its real source. Existing opponent comparisons still require their own sample.

`coach_finding_evidence.py` checks explicit RU/EN numeric observer/sentry and
first-ten-minute death claims. Inventory claims require an estimate qualifier
and full recording; early-death claims require a recorded-event qualifier.
Other heroes, team counts, other time slices and metric swaps fail. The generic
number whitelist cannot bypass these bindings. Next-game/plan/fix goals retain
the existing policy. Backend attaches verification refs after checking the
answer; model-provided refs are ignored.

Coach verification version **5** hides obsolete match reviews until regeneration,
including offline states, without deleting storage. Saved Q&A is rechecked on
read with no provider call. Shared review payloads continue excluding questions
and evidence. No live/paid provider is needed for these checks.

`renderer/finding-evidence.js` validates whitelisted metadata and uses textContent.
Finding disclosures show measured value, method, source and recording intervals
in RU/EN; AI disclosures use the same renderer. Functional HTTP/SQLite tests cover
producer → analysis → prompt → review → saved answers. Electron smoke opens the
actual disclosure and renders charts with gaps.

The first boundary does not verify arbitrary natural-language paraphrases,
spelled-out counts, causality, every remaining metric or career claims. Those
limits are explicit; F04's audit criterion was to start with three valuable
finding groups, not to prove every possible generated sentence.
