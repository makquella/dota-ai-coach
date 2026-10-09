"""Replace a small local JSON file after a complete unique temporary write."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from app.diagnostics import record_error


def write_json_atomic(path: Path, data: object, *, indent: int | None = None) -> None:
    text = json.dumps(data, ensure_ascii=False, allow_nan=False, indent=indent) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=".wardly-",
            suffix=".tmp",
            delete=False,
        ) as output:
            temporary = Path(output.name)
            output.write(text)
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except OSError as error:
                record_error("local-file-cleanup", error, with_trace=False)
