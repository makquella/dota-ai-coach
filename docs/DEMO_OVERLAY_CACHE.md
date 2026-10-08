# Demo response publication

The 0.53.23 F10 slice replaces two separately assigned globals with a
`DemoOverlayCache` frame containing a private response and its expiry.
Publication, expiry removal and invalidation share a short lock. Each caller
receives a detached response; language translation or caller mutation cannot
change the cached value. Copies happen outside publication ownership, like
the GSI snapshot, because published values are never mutated.

A valid demo request reserves a generation/sequence token before observation
and response processing. Publication rechecks it after copying. An old request
cannot overwrite a later published request, even if it finishes later. A clear
invalidates pending requests; expiry alone does not invalidate pending work.
A request can publish only once. Malformed requests do not clear valid demo
output. Tokens are internal and do not change the public response format.

Session reset invalidates at both ends of its whole reset window. Publication
is disabled throughout overlapping reset windows, including tokens reserved
during them. The context manager releases the window on reset exceptions.
The cache lock is not held while GSI, MatchMemory, scheduler or coach history
reset runs; their ownership order is preserved.

The existing eight-second lifetime now uses elapsed monotonic time. A response
at exactly its expiry remains available, as before; it is removed after that
boundary. Wall-clock adjustments cannot extend/shorten the elapsed lifetime.

Eight functional cases cover actual delayed demo HTTP requests across reset
and newer demo publication, invalid HTTP/reader mutations, detached nested
data and exact expiry, overlapping/exceptional resets, actual slow deepcopy
across clear/new publication, and expiration versus concurrent replacement.
HTTP interleaving cases use distinct TestClient portals. They do not claim to
prove ASGI event-loop responsiveness while synchronous demo processing runs.
Existing replay and scheduler tests verify sequential demo behavior.

This owner protects cached publication only. An HTTP read that already captured
the old frame may finish after invalidation. An in-flight demo still receives
its computed POST response even when that response is no longer publishable.
Demo processing can still update scheduler/coach after reset; the entire
overlay, demo execution and PlayerService/history do not form one atomic epoch.
No background history or recording worker is introduced.
