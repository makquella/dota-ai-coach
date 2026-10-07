"""Credentials for trusted local tools and the separate Dota GSI capability."""

from __future__ import annotations

import contextlib
import json
import os
import re
import secrets
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

from app.config import BACKEND_PORT, WRITABLE_DIR

TOKEN_RE = re.compile(r"[a-f0-9]{64}")
AUTH_FILE = "local-api-auth.json"


@dataclass(frozen=True)
class LocalApiAuth:
    control: str = field(repr=False)
    gsi: str = field(repr=False)

    @property
    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.control}"}


def _credentials(control: object, gsi: object) -> LocalApiAuth:
    if (
        not isinstance(control, str)
        or not isinstance(gsi, str)
        or not TOKEN_RE.fullmatch(control)
        or not TOKEN_RE.fullmatch(gsi)
        or control == gsi
    ):
        raise ValueError("Invalid local API credentials; two distinct 256-bit tokens are required.")
    return LocalApiAuth(control, gsi)


def load_auth(directory: Path, environment: Mapping[str, str] | None = None) -> LocalApiAuth:
    """Use launcher-provided credentials, or atomically create a private local file."""
    env = os.environ if environment is None else environment
    control, gsi = env.get("DOTA_AI_CONTROL_TOKEN"), env.get("DOTA_AI_GSI_TOKEN")
    if control is not None or gsi is not None:
        return _credentials(control, gsi)
    path = directory / AUTH_FILE
    directory.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        raise ValueError("The local API credentials file must not be a symlink.")
    if not path.exists():
        auth = _credentials(secrets.token_hex(32), secrets.token_hex(32))
        temporary: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", dir=directory, delete=False, encoding="utf-8"
            ) as handle:
                temporary = Path(handle.name)
                os.chmod(temporary, 0o600)
                json.dump({"version": 1, "control": auth.control, "gsi": auth.gsi}, handle)
                handle.flush()
                os.fsync(handle.fileno())
            with contextlib.suppress(FileExistsError):
                os.link(temporary, path)  # Publish a complete file without replacing a winner.
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
    if path.stat().st_size > 4096:
        raise ValueError("Invalid local API credentials file.")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, UnicodeError):
        raise ValueError("Invalid local API credentials file.") from None
    if not isinstance(data, dict) or type(data.get("version")) is not int or data["version"] != 1:
        raise ValueError("Invalid local API credentials file.")
    os.chmod(path, 0o600)
    return _credentials(data.get("control"), data.get("gsi"))


LOCAL_API_AUTH = load_auth(WRITABLE_DIR)
LOCAL_API_URL = f"http://127.0.0.1:{BACKEND_PORT}"
