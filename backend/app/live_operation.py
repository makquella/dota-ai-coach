"""One live operation at a time over the in-memory live owners (audit F10).

The GSI snapshot (gsi_snapshot.py), MatchMemory, the advice scheduler and the
coach session history each guard themselves, but a whole operation spans
several of them: a GSI packet is enriched by MatchMemory and then published;
an overlay poll reads the published snapshot, asks MatchMemory and lets the
scheduler decide; a demo state goes through all of them; a session reset
clears them together. Interleaved, an overlay poll could pair packet N's
snapshot with MatchMemory already moved to packet N+1, or a reset could land
between the two halves of a packet.

`live_operation()` is the outermost lock of those operations (taken first,
before any owner's own lock, never while holding one), so each runs whole.
Disk and network work stays outside it: SQLite role/lane reads are prepared
before, and persistence, recordings and advice logs run after.
"""

from __future__ import annotations

import threading
from collections.abc import Iterator
from contextlib import contextmanager

_LOCK = threading.RLock()


@contextmanager
def live_operation() -> Iterator[None]:
    with _LOCK:
        yield
