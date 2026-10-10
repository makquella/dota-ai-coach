# Live tip ownership and prepared metadata

The 0.53.22 F10 slice moves map/role, skill and gold tip rendering behind
`MatchMemory.live_hints`. Their stateful calls run under the same memory owner
as observation/reset and the child snapshot. Two overlay requests cannot
interleave tip bookkeeping; neither can a live/demo observation or reset.
Main no longer calls mutable child trackers or tips directly.

PlayerService role/item/start/skill and lane-history lookups stay in main's
preparation phase before ownership. `GoldHintInputs` and `LiveHintInputs`
describe these prepared values. `live_hints.py` consumes them and observed
state without SQLite, provider, filesystem or network work. Timer settings
are warmed before ownership, including direct facade use. This extraction
keeps the existing tip priority, availability, timing, UK/EN copy and map-off
skill/gold/role behavior; it does not add a new advice rule or cache format.

Each core observation and reset advances an internal generation under its
owner. The detached tracker snapshot captures that generation. If observation
or reset ran while metadata was prepared, the facade returns no hint fields
and performs no tip calls. A later overlay poll prepares again; a slow metadata
lookup does not hold up reset. A generation advances before a potentially
failing mutation too, so an earlier prepared snapshot cannot survive a partial
observation. Rendering failures release ownership but do not roll back prior
tip mutations, matching the existing core memory exception contract.

Fifteen new functional cases use actual HTTP handlers, tips, SQLite/provider
methods, file reads and threads with traced pauses/Events: all three tip
operations against reset/live writes; parallel overlay requests; reset/new
observation during metadata preparation; carry/support and map-on/off metadata
outside ownership; an actual malformed item render exception followed by HTTP
reset; and direct cold timer preparation. Existing map/role, spacing, gold,
skill, enemy and objective tests verify the consuming behavior.

`live_hints` is a declared clean module in the whole-app gate and additionally
passes strict checking with imported modules' diagnostics silent in that
separate invocation. The whole-app baseline still checks those imported
modules; this does not claim they have become strictly typed.

Remaining F10 scope: the whole overlay response/GSI/metadata/scheduler is not
one atomic epoch; demo response-cache publication gains a separate guard in
0.53.23 ([DEMO_OVERLAY_CACHE.md](DEMO_OVERLAY_CACHE.md)). Demo execution and
PlayerService/history ownership remain separate. A main card can still finish computing after reset.
Legacy mutable attributes exist for internal code/tests and bypass ownership
if accessed directly. No new background history or recording worker is added.
