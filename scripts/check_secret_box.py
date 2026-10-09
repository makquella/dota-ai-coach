"""Windows CI: DPAPI seals and opens a value for the current user (secret_box.py).

Run from the repository root with the backend's Python; exits non-zero when
sealing is unavailable or does not round-trip.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.secret_box import PREFIX, SecretBox  # noqa: E402


def main() -> int:
    box = SecretBox()
    if not box.available:
        print("secret_box: no OS sealing on this platform")
        return 1
    value = "wardly-check-Ключ-0123456789"
    sealed = box.seal(value)
    if not sealed.startswith(PREFIX) or value in sealed or box.open(sealed) != value:
        print("secret_box: DPAPI round trip failed")
        return 1
    if box.open(PREFIX + "AAAA") is not None:
        print("secret_box: a damaged seal opened")
        return 1
    print("secret_box: DPAPI seals and opens for this user")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
