"""Optional scoped hook; disabled by default. Stop offers a hint, never full tests."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from dev import (
    ROOT,
    Command,
    backend_python,
    changed_paths,
    checked_path,
    receipt_matches,
)


def edit_commands(root: Path, payload: dict[str, Any], *, formatting: bool) -> list[Command]:
    tool_input = payload.get("tool_input")
    raw = tool_input.get("file_path") if isinstance(tool_input, dict) else None
    if not isinstance(raw, str):
        return []
    path = checked_path(root, raw)
    relative = path.relative_to(root).as_posix()
    if path.suffix != ".py" or not relative.startswith(("backend/", "scripts/")):
        return []
    commands = []
    python = backend_python(root)
    config = str(root / "backend/pyproject.toml")
    if formatting:
        commands.append(
            Command(
                (python, "-m", "ruff", "format", "--config", config, str(path)),
                root / "backend",
                "explicit single-file formatting",
            )
        )
    commands.append(
        Command(
            (python, "-m", "ruff", "check", "--config", config, str(path)),
            root / "backend",
            "single edited Python file",
        )
    )
    return commands


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("event", choices=("edit", "stop"))
    parser.add_argument(
        "--format", action="store_true", help="Explicitly enable single-file formatting"
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    try:
        raw = sys.stdin.read(1_048_577)
        if len(raw) > 1_048_576:
            raise ValueError("Hook input exceeds 1 MiB")
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            raise ValueError("Hook input must be an object")
        if args.event == "stop":
            if payload.get("stop_hook_active") is True:
                return 0
            paths = changed_paths(ROOT)
            if paths and not receipt_matches(ROOT, paths):
                print(
                    "Changed tree has no matching successful check receipt. Review: python scripts/dev.py check --changed --dry-run; then run selected checks."
                )
            return 0
        commands = edit_commands(ROOT, payload, formatting=args.format)
        if args.dry_run:
            print(json.dumps([{"argv": c.argv, "cwd": str(c.cwd)} for c in commands]))
            return 0
        for command in commands:
            subprocess.run(command.argv, cwd=command.cwd, check=True)
        return 0
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        print(f"Hook check failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
