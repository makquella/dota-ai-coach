# Detached live tracker reads

The F10 slice in 0.53.21 adds `MatchMemory.tracker_snapshot`: enemy heroes,
lane opponents/missing calls, skill-bar size, TP signal and Roshan/Aegis
reads share the core memory RLock. Observation or reset cannot replace or
partially update child trackers between those reads. The returned frozen
dataclass contains detached lists/dictionaries; freezing does not make nested
containers immutable, but caller changes cannot change the trackers.

The overlay captures this snapshot before item/skill/history metadata lookup.
It uses the captured enemies for both save-item lookup and map hints, and the
captured opponents for lane history. Counter-item advice uses the separately
owned `enemy_heroes` read. Main no longer reads these child trackers directly.
Missing coordinates/dead players still suppress missing calls. Existing event,
TP, lane, timer and objective rules and translated copy are preserved.

Cold timer configuration is warmed before snapshot ownership, as for
observation in [GSI_TIMER_PREPARATION.md](GSI_TIMER_PREPARATION.md). No metadata,
SQLite, file or network work runs inside the capture. Normal runtime keeps the
timer cache stable; concurrent manual cache invalidation is not supported.

Five functional cases use actual HTTP observations/reset, child methods and
thread traces/Events: reading while child observation is unfinished, reset and
live writes during a partial capture, detached values/observed Aegis/unknown
signals, and actual cold timer file reads outside ownership. Existing map/lane/
counter/timer tests cover the public overlay consumers.

This is one snapshot of child reads, not an atomic epoch for the entire overlay.
GSI state, role, metadata and later rendering can still belong to different
updates. Mutable role/skill/gold tip calls gain an owned facade and stale
preparation guard in 0.53.22; see [LIVE_HINT_OWNERSHIP.md](LIVE_HINT_OWNERSHIP.md). Demo cache,
scheduler and PlayerService/history ownership remain separate. Legacy child
attributes remain available internally/tests and should not be new API consumers.
