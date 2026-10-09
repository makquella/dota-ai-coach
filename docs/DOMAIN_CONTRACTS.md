# Initial domain contracts (0.53.39, F12)

`domain_contracts.py` defines:

- **NormalizedState**: the ten normalized core fields returned by the actual GSI
  normalizer. Canonical hero, legacy role, minute/level/gold/HP, item names,
  game/team state and an explicitly open tracker context. Unknown observed
  signals remain absent; existing normalization defaults are unchanged.
- **MatchFacts**: the complete common source shape from OpenDota and GSI, including
  nullable totals, per-minute values, provenance and recording coverage. Both
  producers and the merger return this type. Event/detail extensions are open
  dictionaries; inventory is explicitly IDs/names, not arbitrary objects.
- **Finding**: required `id`, `params`, `evidence`, plus typed optional presentation
  metadata. The deterministic builder constructs this core; localized text stays
  separate. Finding-specific heterogeneous params remain explicitly open.

The mutable enrichment port adapts a normalized mapping to a dictionary once.
Snapshot detachment and enrichment/reset ownership are unchanged. Read-only
analysis/inventory consumers accept mappings, preserving compatibility with
existing dictionaries. `merge_facts` has one documented cast after copying fields
between two complete typed source shapes; raw provider JSON is not cast into the
contract. Producer literals and update fields remain checked.

`player_contracts.py` additionally validates finding, evidence and coverage cores
at the actual `/player/matches/{id}` response boundary. Source/field/precision/time
pairs use the existing source validator; counts are native bounded integers;
intervals are ordered and a complete record cannot declare gaps. Evidence must
match the finding ID and its own numeric param. Legacy unset evidence stays
unset under `exclude_unset`; extension/title/text/drill fields are retained.
The schema is exposed in OpenAPI, and JS consumers have matching JSDoc shapes.
Import rejects invalid modern analysis cores before SQL writes; invalid stored
cores are rebuilt from source records on detail/career reads while retaining
notes and account selection.

Functional tests use real source transformations and HTTP/SQLite reviews in both
languages, including full response equality, missing signals, native inventory
IDs/names, legacy extensions and malformed field/source/interval/value cases.
A real mypy subprocess checks the actual producer return annotations; a separate
negative fixture must fail for five key/None/value mistakes. It never becomes a
production lint allowance.

The blocking whole-app gate removes three resolved GSI allowances and adds no new
debt: **176 reviewed errors in 30 files**. Domain contracts and MatchFacts join the
strictly clean source modules. Ruff/type/behavior/source Electron/Windows checks
are still required on the final PR SHA.

This fulfills the audit's initial domain types + important detail/I/O boundary.
It does not claim that every tracker context, event log, finding params variant,
AI schema or renderer function has been completely typed. Those extensions are
named explicitly rather than silently treating unknown metrics as measured zero.
