"""Compile the three Python dependency profiles with the pinned uv tool."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / "backend"
PROFILES = ("requirements-dev", "requirements", "requirements-build")
COMPILE_COMMAND = "python scripts/lock_python_dependencies.py"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    options = parser.add_mutually_exclusive_group()
    options.add_argument(
        "--check", action="store_true", help="Fail if a lockfile needs regeneration"
    )
    options.add_argument(
        "--upgrade", action="store_true", help="Refresh allowed dependency versions"
    )
    args = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix="wardly-python-locks-") as temporary:
        output = Path(temporary)
        constraints = {}
        for profile in PROFILES:
            existing = BACKEND / f"{profile}.txt"
            if existing.exists() and not args.upgrade:
                # Reuse versions, not hashes: recompiling an existing output can
                # preserve its hashes without checking the registry metadata.
                versions = [
                    line.rstrip(" \\")
                    for line in existing.read_text(encoding="utf-8").splitlines()
                    if line and line[0].isalnum()
                ]
                constraint = output / f"{profile}.versions.txt"
                constraint.write_text("\n".join(versions) + "\n", encoding="utf-8")
                constraints[profile] = constraint

        for profile in PROFILES:
            command = [
                sys.executable,
                "-m",
                "uv",
                "pip",
                "compile",
                f"{profile}.in",
                "--universal",
                "--python-version",
                "3.11",
                "--generate-hashes",
                "--no-annotate",
                "--custom-compile-command",
                COMPILE_COMMAND,
                "--output-file",
                str(output / f"{profile}.txt"),
                "--quiet",
                "--cache-dir",
                str(os.environ.get("UV_CACHE_DIR") or output / "uv-cache"),
            ]
            if profile != "requirements-dev":
                command.extend(["--constraints", str(output / "requirements-dev.txt")])
            if profile != "requirements" and profile in constraints:
                command.extend(["--constraints", str(constraints[profile])])
            if args.upgrade:
                command.append("--upgrade")
            subprocess.run(command, cwd=BACKEND, check=True)

        changed = [
            profile
            for profile in PROFILES
            if not (BACKEND / f"{profile}.txt").exists()
            or (BACKEND / f"{profile}.txt").read_text(encoding="utf-8")
            != (output / f"{profile}.txt").read_text(encoding="utf-8")
        ]
        if args.check:
            if changed:
                print("Stale Python lockfiles: " + ", ".join(changed), file=sys.stderr)
                print("Run " + COMPILE_COMMAND, file=sys.stderr)
                return 1
            print("Python lockfiles are up to date")
            return 0

        for profile in changed:
            shutil.copyfile(output / f"{profile}.txt", BACKEND / f"{profile}.txt")
        print("Updated Python lockfiles: " + (", ".join(changed) or "none"))
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
