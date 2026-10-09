# Cold timer settings before state ownership

0.53.20 closes another F10 I/O boundary. `RoshanTimer.observe` can consult
`map_hints.timers()` on the first Aegis pickup to check the configured duration.
That lazy cache reads `data/meta/map_timers.json`. A cold read used to happen
inside core MatchMemory ownership and, for live GSI, the register writer owner.

`_prepare_gsi_prior` now warms timer settings in the standard ASGI thread pool
before role preparation and either state owner. Direct `update_latest_gsi`
also warms timers before entering the register. Public `MatchMemory.observe_state`
warms the same cache before calling its owned `_observe_state`, covering demo
and direct observations. Inside observation, Roshan/Aegis uses the cached data;
no timer rules, event offsets or default settings change. The cache remains
stable during normal runtime; no concurrent configuration reload is introduced.

The actual observation body is preserved. Core ownership is still reentrant
and protects reset, annotation and tracker updates. The concurrency test traces
the actual owned body under its new private name. Recordings/history remain
on their existing path; this slice does not move those writers into concurrent
workers or introduce a new ingestion queue.

Five functional cases clear the real timer cache and trace actual Path.read_text:
live GSI, demo and direct memory reads must occur outside both state owners;
direct register enrichment has the same guarantee. Real Aegis pickup still
records its observed clock. A paused cold read on one persistent ASGI loop
lets HTTP reset finish before the incoming GSI packet resumes and commits.
The file reader, timers and policy are not replaced by mocks.

Remaining F10 work is the child tracker/tip facade, whole-overlay/demo-cache
ownership and the wider history/recording concurrency boundary. CPU work and
existing post-publication disk writes on the async GSI path are not promised to
be entirely off the event loop. Missing/invalid timer-file behavior is unchanged.
