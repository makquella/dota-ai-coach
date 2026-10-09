# GSI role metadata preparation

F10's 0.53.19 slice moves the role-prior lookup out of the GSI enrichment
callback. `PlayerService.role_prior` reads the primary account on every call
and can read review history/hero metadata from SQLite when its cache is cold.
Previously, the GSI register writer owner was already held and MatchMemory
already observed the new state when that lookup ran.

The HTTP GSI path now selects the hero through the same `hero_from_gsi`
function used by normalization, then prepares the prior before acquiring
either GSI or core memory ownership. SQLite lookup runs in the standard ASGI
thread pool so it cannot block the event loop while other requests arrive.
In 0.53.20 that preparer also warms the cold timer settings cache; see
[GSI_TIMER_PREPARATION.md](GSI_TIMER_PREPARATION.md).
The hero/profile lookup also warms the
same lazy profile cache outside ownership. The prior is requested only for
full-coverage cores, matching the former callback condition; support/safety
heroes do not gain extra metadata reads.

Inside the callback, actual memory observation still runs first. Coverage
then uses an owned `MatchMemory.role_snapshot(prior)` with those prepared
facts, so freshly observed lane/selected-role data remains authoritative.
The shared support-role predicate preserves the existing rule: a full core
played as support receives support coverage except when the role came only
from the hero prior. Ordinary overlay role reads use the same owned method
after their metadata lookup. No PlayerService call remains in GSI enrichment.

A blocked metadata lookup leaves the previous packet and memory intact and
does not reserve the GSI writer. Reset can complete; once preparation finishes,
the resumed incoming packet may commit after reset. Ownership orders completed
updates, not packet arrival. Metadata failures retain the existing error
behavior, but happen before any new packet/memory observation. This slice does
not silently substitute guessed history facts or add provider requests.

Functional checks trace actual PlayerStore method calls through a real HTTP
GSI request and verify that none run under the GSI update/core memory owners,
for both automatic and selected-support roles. A paused real role lookup lets
HTTP reset finish before it resumes, with both requests on one persistent ASGI
event loop. Closing the actual SQLite store proves
failure preserves the previous packet and memory. Hero fixtures exercise
override precedence, string/NPC forms, aliases and unknown values, comparing
preparation with the real normalizer. Existing empty-string override behavior
is retained. Full role/policy/GSI/replay consumers cover the unchanged rules.

F10 still needs the remaining child tracker/tip facade, an overlay response
epoch and demo-cache ownership. Role priors can reflect the account/history
at preparation time rather than at commit; moving the lookup does not promise
an atomic account/SQLite/GSI transaction. No disk/network work is introduced
inside the core memory or GSI enrichment owners.
