"""Check pinned mypy without permitting growth of the reviewed type debt."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tomllib
from collections import Counter
from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

BACKEND = Path(__file__).resolve().parents[1] / "backend"
DIAGNOSTIC = re.compile(r"^(.+?):\d+(?::\d+)?: error: (.+) \[([a-z0-9-]+)\]$")


@dataclass(frozen=True, order=True)
class Error:
    path: str
    message: str
    code: str


def parse_errors(output: str) -> Counter[Error]:
    errors: Counter[Error] = Counter()
    for line in output.splitlines():
        if ": error:" not in line:
            continue
        match = DIAGNOSTIC.fullmatch(line)
        if match is None:
            raise ValueError(f"Unrecognized mypy diagnostic: {line}")
        path, message, code = match.groups()
        path = path.replace("\\", "/")
        if not path.startswith("app/") or ".." in Path(path).parts:
            raise ValueError(f"Unexpected mypy source path: {path}")
        errors[Error(path, message.rstrip(), code)] += 1
    return errors


def run_mypy(backend: Path) -> Counter[Error]:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "mypy",
            "--config-file",
            "pyproject.toml",
            "--show-error-codes",
            "--hide-error-context",
            "--no-pretty",
            "--no-color-output",
            "--no-error-summary",
            "--no-incremental",
            "app",
        ],
        cwd=backend,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
        check=False,
    )
    if result.returncode not in {0, 1}:
        raise ValueError(f"mypy failed ({result.returncode}): {result.stdout}{result.stderr}")
    errors = parse_errors(result.stdout)
    if (result.returncode == 1) != bool(errors):
        raise ValueError(f"mypy exit status does not match its diagnostics: {result.stderr}")
    return errors


def entries(errors: Counter[Error]) -> list[dict[str, Any]]:
    return [
        {"path": error.path, "message": error.message, "code": error.code, "count": count}
        for error, count in sorted(errors.items())
    ]


def read_baseline(path: Path, backend: Path) -> tuple[dict[str, Any], Counter[Error]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or type(data.get("format")) is not int or data["format"] != 1:
        raise ValueError("Invalid type baseline format.")
    if data.get("mypy_version") != version("mypy"):
        raise ValueError("mypy version differs from the baseline; install requirements-dev.txt.")
    config = tomllib.loads((backend / "pyproject.toml").read_text(encoding="utf-8"))
    if data.get("python_target") != config["tool"]["mypy"]["python_version"]:
        raise ValueError("mypy Python target differs from the baseline.")
    clean = data.get("clean_modules")
    if not isinstance(clean, list) or not clean or any(not isinstance(p, str) for p in clean):
        raise ValueError("The baseline must declare clean modules.")
    if len(set(clean)) != len(clean):
        raise ValueError("Duplicate clean module in baseline.")
    for module in clean:
        if (
            not module.startswith("app/")
            or ".." in Path(module).parts
            or not (backend / module).is_file()
        ):
            raise ValueError(f"Missing or invalid clean module: {module}")
    known: Counter[Error] = Counter()
    rows = data.get("errors")
    if not isinstance(rows, list):
        raise ValueError("Invalid baseline diagnostics.")
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Invalid baseline diagnostic.")
        source, message, code, count = (row.get(k) for k in ("path", "message", "code", "count"))
        if (
            not isinstance(source, str)
            or not source.startswith("app/")
            or ".." in Path(source).parts
            or not isinstance(message, str)
            or not message
            or not isinstance(code, str)
            or re.fullmatch(r"[a-z0-9-]+", code) is None
            or type(count) is not int
            or count <= 0
        ):
            raise ValueError("Invalid baseline diagnostic fields.")
        error = Error(source, message, code)
        if source in clean or error in known:
            raise ValueError(
                "Clean modules cannot have allowances; duplicate diagnostics are invalid."
            )
        known[error] = count
    return data, known


def check(backend: Path, baseline: Path, *, prune: bool = False) -> int:
    data, known = read_baseline(baseline, backend)
    actual = run_mypy(backend)
    added, removed = actual - known, known - actual
    if added:
        print(f"FAIL: {added.total()} new type errors; baseline additions are not automatic.")
        for error, count in sorted(added.items()):
            print(f"{error.path}: {error.message} [{error.code}] (new occurrences: {count})")
        return 1
    if removed:
        if not prune:
            print(
                f"FAIL: {removed.total()} resolved baseline errors still have allowances. "
                "Run check_types.py --prune-baseline and review its diff."
            )
            return 1
        data["errors"] = entries(actual)
        baseline.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Pruned {removed.total()} resolved baseline errors; no allowances added.")
    files = {error.path for error in actual}
    print(
        f"PASS: no new errors; {actual.total()} reviewed errors in {len(files)} files; "
        f"{len(data['clean_modules'])} declared clean modules and all other sources checked."
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend-dir", type=Path, default=BACKEND)
    parser.add_argument("--baseline", type=Path, default=BACKEND / "type-baseline.json")
    parser.add_argument(
        "--prune-baseline", action="store_true", help="Only remove resolved allowances"
    )
    args = parser.parse_args()
    try:
        return check(args.backend_dir, args.baseline, prune=args.prune_baseline)
    except (
        OSError,
        ValueError,
        KeyError,
        TypeError,
        PackageNotFoundError,
        subprocess.TimeoutExpired,
    ) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
