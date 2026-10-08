"""Scope costly Windows builds and keep their required CI status trustworthy."""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

from verify_source import REPOSITORY, verify_source

# These trees do not ship in the desktop installer. Unknown paths require it.
NON_DESKTOP = ("docs/", "site/", "services/api/", ".agents/", ".claude/")
NON_DESKTOP_FILES = {"AGENTS.md", "CLAUDE.md", ".github/workflows/api.yml"}


def needs_windows(repository: Path, source: str, base: str) -> tuple[bool, str]:
    verify_source(source, repository)
    if re.fullmatch(r"[0-9a-f]{40}", base) is None or base == "0" * 40:
        return True, "No usable base commit; require Windows validation."
    result = subprocess.run(
        ["git", "diff", "--name-only", "--no-renames", "-z", base, source, "--"],
        cwd=repository,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
        check=False,
    )
    if result.returncode != 0:
        return True, "Base unavailable; require Windows validation."
    paths = [name for name in result.stdout.split("\0") if name]
    relevant = [
        name for name in paths if name not in NON_DESKTOP_FILES and not name.startswith(NON_DESKTOP)
    ]
    return bool(relevant), f"{len(relevant)} desktop/unknown paths in {len(paths)} changed paths."


def check_result(changes: str, build: str, *, required: bool, caller_builds_windows: bool) -> int:
    if changes != "success":
        print(f"FAIL: source/path determination {changes}.")
        return 1
    if build == "success":
        print("PASS: Windows build and smoke completed.")
        return 0
    if build == "skipped" and (not required or caller_builds_windows):
        reason = (
            "caller performs its own Windows build"
            if caller_builds_windows
            else "no desktop changes"
        )
        print(f"PASS: Windows build skipped because {reason}.")
        return 0
    print(f"FAIL: Windows build {build}; required={required}.")
    return 1


def boolean(value: str) -> bool:
    if value not in {"true", "false"}:
        raise argparse.ArgumentTypeError("Expected true or false.")
    return value == "true"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_subparsers(dest="mode", required=True)
    scope = modes.add_parser("scope")
    scope.add_argument("--source", required=True)
    scope.add_argument("--base", default="")
    scope.add_argument("--repository", type=Path, default=REPOSITORY)
    summary = modes.add_parser("summary")
    summary.add_argument("--changes", required=True)
    summary.add_argument("--build", required=True)
    summary.add_argument("--required", type=boolean, required=True)
    summary.add_argument("--caller-builds-windows", type=boolean, required=True)
    args = parser.parse_args()
    try:
        if args.mode == "summary":
            return check_result(
                args.changes,
                args.build,
                required=args.required,
                caller_builds_windows=args.caller_builds_windows,
            )
        required, reason = needs_windows(args.repository, args.source, args.base)
        print(reason)
        print(f"windows_required={str(required).lower()}")
        if output := os.environ.get("GITHUB_OUTPUT"):
            with Path(output).open("a", encoding="utf-8") as handle:
                handle.write(f"windows_required={str(required).lower()}\n")
        return 0
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
