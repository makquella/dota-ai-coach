"""Secrets at rest under the operating system's protection.

On Windows the AI coach key and the OpenDota key are sealed with DPAPI
(CryptProtectData, current user) before they go into SQLite, so a copied
database or backup of the data folder does not carry usable keys. A sealed
value reads `dpapi:v1:<base64>`. Elsewhere (development, CI) there is no OS
sealing and values stay as they were; a value sealed on Windows that cannot be
opened here or by another Windows user reads as missing ("locked") and the
player enters the key again. Nothing here logs a value.
"""

from __future__ import annotations

import base64
import binascii
import ctypes
import os
from collections.abc import Callable
from typing import Any

PREFIX = "dpapi:v1:"
# Ties the sealed blobs to this app (DPAPI optional entropy).
_ENTROPY = b"Wardly local secret v1"
_UI_FORBIDDEN = 0x1

Transform = Callable[[bytes], bytes]


def _blob(data: bytes) -> tuple[Any, Any]:
    class DataBlob(ctypes.Structure):
        _fields_ = [("cbData", ctypes.c_uint32), ("pbData", ctypes.POINTER(ctypes.c_char))]

    buffer = ctypes.create_string_buffer(data, len(data))
    return DataBlob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_char))), buffer


def _dpapi(protect: bool) -> Transform:
    windll: Any = getattr(ctypes, "windll")  # noqa: B009 - Windows only, absent elsewhere
    crypt32, kernel32 = windll.crypt32, windll.kernel32

    def run(data: bytes) -> bytes:
        blob_in, keep_in = _blob(data)
        entropy, keep_entropy = _blob(_ENTROPY)
        blob_out, _ = _blob(b"")
        call = crypt32.CryptProtectData if protect else crypt32.CryptUnprotectData
        args = (
            (ctypes.byref(blob_in), "Wardly", ctypes.byref(entropy))
            if protect
            else (ctypes.byref(blob_in), None, ctypes.byref(entropy))
        )
        if not call(*args, None, None, _UI_FORBIDDEN, ctypes.byref(blob_out)):
            raise OSError("DPAPI refused the value")
        try:
            return ctypes.string_at(blob_out.pbData, blob_out.cbData)
        finally:
            kernel32.LocalFree(blob_out.pbData)
            del keep_in, keep_entropy

    return run


class SecretBox:
    """`seal` before writing a secret, `open` after reading one."""

    def __init__(
        self, protect: Transform | None = None, unprotect: Transform | None = None
    ) -> None:
        if protect is None and unprotect is None and os.name == "nt":
            protect, unprotect = _dpapi(True), _dpapi(False)
        self._protect = protect
        self._unprotect = unprotect

    @property
    def available(self) -> bool:
        return self._protect is not None and self._unprotect is not None

    @property
    def kind(self) -> str:
        return "dpapi" if self.available else "none"

    @staticmethod
    def is_sealed(value: str | None) -> bool:
        return bool(value) and str(value).startswith(PREFIX)

    def seal(self, text: str) -> str:
        """Sealed when the OS can and the seal opens again to the same text; the
        plain value otherwise, so a sealing fault never loses a key."""
        if not self.available or self._protect is None:
            return text
        try:
            sealed = PREFIX + base64.b64encode(self._protect(text.encode("utf-8"))).decode("ascii")
        except OSError:
            return text
        return sealed if self.open(sealed) == text else text

    def open(self, value: str | None) -> str | None:
        """The plain value; None for nothing stored or a seal this user cannot open."""
        if not value:
            return None
        if not self.is_sealed(value):
            return value
        if self._unprotect is None:
            return None
        try:
            return self._unprotect(base64.b64decode(value[len(PREFIX) :], validate=True)).decode(
                "utf-8"
            )
        except (OSError, ValueError, binascii.Error, UnicodeDecodeError):
            return None
