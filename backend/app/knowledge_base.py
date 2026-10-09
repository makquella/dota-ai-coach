"""One immutable parsed Markdown catalog; development refreshes by file metadata."""

from __future__ import annotations

import threading
import time
from pathlib import Path

from app.diagnostics import record_error

Signature = tuple[tuple[Path, int, int], ...]


def _signature(directory: Path) -> Signature:
    files = []
    for path in sorted(directory.glob("*.md")):
        stat = path.stat()
        files.append((path, stat.st_mtime_ns, stat.st_size))
    return tuple(files)


class KnowledgeBaseCache:
    """Load outside the owner; readers may keep a previous complete catalog.

    The first concurrent readers wait for one initial load. Later refreshes do
    not block readers of the previous catalog. Packaged resources are immutable
    for the process lifetime; source checkouts inspect mtime/size on lookup.
    """

    def __init__(self, directory: Path, *, watch_changes: bool) -> None:
        self.directory = directory
        self.watch_changes = watch_changes
        self._condition = threading.Condition()
        self._paragraphs: tuple[str, ...] | None = None
        self._signature: Signature | None = None
        self._loading = False
        self._loads = 0
        self._files_read = 0
        self._failures = 0
        self._last_error: str | None = None
        self._retry_at = 0.0

    def paragraphs(self) -> tuple[str, ...]:
        while True:
            with self._condition:
                if self._loading:
                    if self._paragraphs is not None:
                        return self._paragraphs
                    self._condition.wait()
                    continue
                if self._paragraphs is not None and not self.watch_changes:
                    return self._paragraphs
                if time.monotonic() < self._retry_at:
                    return self._paragraphs or ()
            try:
                signature = _signature(self.directory)
            except OSError as error:
                return self._failed(error)
            with self._condition:
                if self._loading:
                    continue  # Reinspect after the other loader publishes.
                if self._signature == signature:
                    return self._paragraphs or ()
                self._loading = True
            try:
                # A file changing during its read cannot publish a mixed catalog.
                # Retry once; repeated changes defer to a later lookup.
                for _attempt in range(2):
                    paragraphs: list[str] = []
                    for path, _mtime, _size in signature:
                        text = path.read_text(encoding="utf-8")
                        with self._condition:
                            self._files_read += 1
                        paragraphs.extend(p.strip() for p in text.split("\n\n") if p.strip())
                    verified = _signature(self.directory)
                    if verified == signature:
                        break
                    signature = verified
                else:
                    raise OSError("Knowledge base changed during both read attempts")
                private = tuple(paragraphs)
                with self._condition:
                    self._paragraphs = private
                    self._signature = signature
                    self._loads += 1
                    self._last_error = None
                    self._retry_at = 0.0
                return private
            except (OSError, UnicodeError) as error:
                return self._failed(error)
            finally:
                with self._condition:
                    self._loading = False
                    self._condition.notify_all()

    def _failed(self, error: OSError | UnicodeError) -> tuple[str, ...]:
        # Do not retain file names or document contents in health/diagnostics.
        with self._condition:
            self._failures += 1
            self._last_error = type(error).__name__
            self._retry_at = time.monotonic() + 1
            previous = self._paragraphs or ()
        record_error("knowledge-base", type(error).__name__, with_trace=False)
        return previous

    def health(self) -> dict[str, object]:
        with self._condition:
            return {
                "loaded": self._paragraphs is not None,
                "loading": self._loading,
                "paragraphs": len(self._paragraphs or ()),
                "loads": self._loads,
                "files_read": self._files_read,
                "failures": self._failures,
                "last_error": self._last_error,
                "watch_changes": self.watch_changes,
            }
