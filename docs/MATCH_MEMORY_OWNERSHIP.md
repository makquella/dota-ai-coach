# Core MatchMemory ownership

The second F10 slice, 0.53.18, gives core `MatchMemory` operations a per-instance
RLock. `observe_state`, `reset`, `summary`, `overlay_context`, death-decision
reads and `note_advice` share that owner. Live GSI and demo replay use the same
observation method; session reset no longer interleaves with a demo's memory
write. A summary waits until the core observation completes instead of seeing
a changed hero beside an unfinished state/death/farm update.

The `_owned` decorator preserves each method's signature with ParamSpec and
wraps. Reentrancy is required: observation can reset on a session/hero change
and annotate its state through the death-decision method. The context manager
releases ownership on exceptions. Failure does not roll back earlier memory
mutations; this is serialization, not transactional recovery.

All work inside these core methods is in memory: tracker observation,
classification, time reads and detached JSON state copies. The methods do not
call PlayerService, scheduler, logging, filesystem or network operations.
Summary/context lists are freshly constructed and cannot mutate the stored
death patterns. The main callback uses the owned advice setter. The legacy
death fallback's session check and decision now execute as one owned method,
with the same availability/session behavior.

GSI update acquires its register writer owner before entering a core memory
method. Core methods do not acquire the GSI register, so the order does not
reverse. They release memory ownership before main calls role metadata,
scheduler, history or recorder work; reset releases it before scheduler and
coach reset. A slow role/history/provider path therefore does not hold this
memory lock. Core readers can wait for an observation; the existing GSI packet
readers still capture the previous/next published snapshot without that wait.

Five functional checks use real HTTP, threads and Events/Barrier, with standard
thread tracing to pause the actual code rather than replace it: summary during
an unfinished live observation, reset during a demo write, simultaneous live
and demo observation with serialized previous state, owner release on exception
and reentrant reset, detached death/advice reads. Existing GSI concurrency,
replay, spacing, death/role/timer and policy tests cover the consuming paths.

Narrowing now reads raw extra/laning context once before checking its type. This
preserves runtime rules and resolves the module's eleven baseline diagnostics;
their allowances are pruned. MatchMemory joins the regular whole-app gate's
named clean modules. This is not a claim of strict typing for all imported
policy modules or arbitrary Any payloads.

Remaining F10 boundaries:
- Direct access to mutable child trackers/tips and legacy public attributes
  still needs a facade; this lock does not protect code that bypasses it.
- The whole overlay response, demo response cache, scheduler, PlayerService
  trackers and GSI register do not form one atomic epoch. A demo can publish its
  response after a reset; core memory itself remains serialized.
- The role-prior metadata lookup was moved outside the separate GSI writer
  owner in 0.53.19; role reads now use an owned snapshot method. See
  [GSI_ROLE_PREPARATION.md](GSI_ROLE_PREPARATION.md).
