"""Explicit portable checks for Wardly; commands use argv/cwd without a shell."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCOPES = ("backend", "live", "history", "ai", "desktop", "worker", "site", "tooling")
BACKEND_SCOPES = {"backend", "live", "history", "ai", "tooling"}
TEST_PATTERNS = {
    "live": (
        "test_gsi*",
        "test_advice*",
        "test_evaluate*",
        "test_scheduler*",
        "test_live*",
        "test_match_memory*",
        "test_demo*",
        "test_signal*",
        "test_decision*",
        "test_hero_safety*",
        "test_laning*",
        "test_replay*",
        "test_fuzz*",
        "test_supports*",
    ),
    "history": (
        "test_player*",
        "test_match*",
        "test_history*",
        "test_backup*",
        "test_cache*",
        "test_domain*",
        "test_finding*",
        "test_personal*",
        "test_focus*",
        "test_profile*",
        "test_cosmetics*",
        "test_friend*",
        "test_support_review*",
        "test_death_review*",
    ),
    "ai": (
        "test_coach*",
        "test_llm*",
        "test_diagnostics*",
        "test_finding*",
        "test_share_review*",
    ),
    "tooling": (
        "test_dev_runner.py",
        "test_version_consistency.py",
        "test_type_checking.py",
        "test_windows_checks.py",
        "test_release_validation.py",
    ),
}
SHARED_BACKEND = {
    "main.py",
    "config.py",
    "schemas.py",
    "player_store.py",
    "player_contracts.py",
    "domain_contracts.py",
    "history_backup.py",
    "player_api.py",
    "player_service.py",
}
SHARED_DESKTOP = {"main.js", "preload.js", "overlay-preload.js", "local-api.js"}


@dataclass(frozen=True)
class Command:
    argv: tuple[str, ...]
    cwd: Path
    reason: str


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
    ).stdout


def changed_paths(root: Path, base: str | None = None) -> list[str]:
    commands = [
        ("diff", "--name-only", "--no-renames", "-z", "--"),
        ("diff", "--cached", "--name-only", "--no-renames", "-z", "--"),
        ("ls-files", "--others", "--exclude-standard", "-z"),
    ]
    if base:
        commit = _git(
            root, "rev-parse", "--verify", "--end-of-options", f"{base}^{{commit}}"
        ).strip()
        commands.append(("diff", "--name-only", "--no-renames", "-z", commit, "HEAD", "--"))
    return sorted({p for args in commands for p in _git(root, *args).split("\0") if p})


def profiles_for(paths: Sequence[str]) -> set[str]:
    profiles: set[str] = set()
    for raw in paths:
        name = raw.replace("\\", "/")
        leaf = name.rsplit("/", 1)[-1]
        if name.startswith("backend/app/"):
            if leaf in SHARED_BACKEND:
                profiles.add("backend")
            elif leaf.startswith(("coach", "llm")):
                profiles.update(("ai", "history"))
            elif (
                leaf.startswith(
                    ("gsi", "advice", "live", "decision", "recommender", "match_memory")
                )
                or "/scheduler/" in name
            ):
                profiles.add("live")
            else:
                profiles.add("backend")  # unknown boundary: complete subsystem
        elif name.startswith("backend/tests/"):
            profiles.add("tooling" if leaf in TEST_PATTERNS["tooling"] else "backend")
        elif name.startswith("backend/"):
            profiles.add("backend")
        elif name.startswith("frontend/launcher/"):
            profiles.add("desktop")
            if leaf in SHARED_DESKTOP:
                profiles.add("backend")
        elif name.startswith("services/api/"):
            profiles.add("worker")
        elif name.startswith(("site/", "docs/", ".agents/", ".claude/")) or name in {
            "AGENTS.md",
            "CLAUDE.md",
            "README.md",
        }:
            profiles.add("site")
        elif name.startswith("data/"):
            profiles.update(("live", "history", "site"))
        elif name.startswith("scripts/"):
            profiles.update(("tooling", "site"))
            if leaf not in {
                "dev.py",
                "bump_version.py",
                "check_hook.py",
                "windows_checks.py",
                "verify_source.py",
                "build_site.py",
                "build_changelog.py",
            }:
                profiles.update(("backend", "desktop"))
        elif name.startswith(".github/"):
            profiles.update(SCOPES)
        else:
            profiles.update(SCOPES)  # new root/build input needs conservative checks
    return profiles


def backend_python(root: Path) -> str:
    for relative in ("backend/.venv/Scripts/python.exe", "backend/.venv/bin/python"):
        candidate = root / relative
        if candidate.is_file():
            return str(candidate)
    raise ValueError("Backend venv missing. Run setup explicitly with a Python 3.11+ interpreter.")


def executable(name: str) -> str:
    if found := shutil.which(name):
        return found
    raise ValueError(f"Required executable not found: {name}")


def npm_argv(*args: str) -> tuple[str, ...]:
    # Launch npm's JS entrypoint with Node. npm.cmd needs a shell on Windows;
    # avoiding it keeps filenames and user paths out of cmd expansion.
    node = executable("node")
    npm = Path(executable("npm")).resolve()
    candidates = (
        npm,
        npm.parent / "node_modules/npm/bin/npm-cli.js",
        Path(node).parent / "node_modules/npm/bin/npm-cli.js",
    )
    for cli in candidates:
        if cli.is_file() and cli.suffix == ".js":
            return (node, str(cli), *args)
    raise ValueError(
        "Cannot locate npm-cli.js next to Node/npm; install a standard Node distribution."
    )


def test_paths(root: Path, scopes: set[str]) -> list[str]:
    if "backend" in scopes:
        return ["tests"]
    files = {
        p
        for scope in scopes
        for pattern in TEST_PATTERNS.get(scope, ())
        for p in (root / "backend/tests").glob(pattern)
    }
    # Every profile includes actual API and packaging boundary checks.
    if scopes & BACKEND_SCOPES:
        files.update(
            root / "backend/tests" / p for p in ("test_api_smoke.py", "test_packaging_runtime.py")
        )
    return sorted(str(p.relative_to(root / "backend")) for p in files if p.is_file())


def checked_path(root: Path, raw: str) -> Path:
    path = (root / raw).resolve()
    if not path.is_relative_to(root.resolve()) or not path.is_file():
        raise ValueError(f"Expected an existing file inside repository: {raw}")
    return path


def plan(root: Path, args: argparse.Namespace) -> tuple[list[str], set[str], list[Command]]:
    paths = changed_paths(root, args.base) if args.changed else []
    scopes = set(SCOPES) if args.full else set(args.scope or ())
    if args.changed:
        scopes.update(profiles_for(paths))
    if not scopes and not args.changed:
        raise ValueError("Choose --changed, --scope or --full; no implicit full suite.")
    commands: list[Command] = []

    def add(argv: Sequence[str], cwd: Path, reason: str) -> None:
        command = Command(tuple(argv), cwd, reason)
        if command not in commands:
            commands.append(command)

    python = (
        backend_python(root) if scopes & BACKEND_SCOPES or scopes & {"site"} else sys.executable
    )
    backend = root / "backend"
    existing_python = [
        str(checked_path(root, p)) for p in paths if p.endswith(".py") and (root / p).is_file()
    ]
    if not args.changed and scopes & BACKEND_SCOPES:
        existing_python = ["."] if args.full else ["app"]
        if args.full:
            existing_python.extend(
                str(root / "scripts" / name)
                for name in (
                    "dev.py",
                    "bump_version.py",
                    "check_hook.py",
                    "check_types.py",
                    "windows_checks.py",
                    "verify_source.py",
                    "lock_python_dependencies.py",
                )
            )
    if existing_python:
        if args.mode == "format":
            add(
                [
                    python,
                    "-m",
                    "ruff",
                    "format",
                    "--config",
                    str(backend / "pyproject.toml"),
                    *existing_python,
                ],
                backend,
                "explicit formatting of selected Python files",
            )
        elif args.mode in {"check", "lint"}:
            add(
                [
                    python,
                    "-m",
                    "ruff",
                    "check",
                    "--config",
                    str(backend / "pyproject.toml"),
                    *existing_python,
                ],
                backend,
                "selected Python lint",
            )
            add(
                [
                    python,
                    "-m",
                    "ruff",
                    "format",
                    "--check",
                    "--config",
                    str(backend / "pyproject.toml"),
                    *existing_python,
                ],
                backend,
                "selected Python formatting (read only)",
            )
    if "desktop" in scopes and args.mode in {"check", "lint"}:
        add(
            npm_argv("run", "check"),
            root / "frontend/launcher",
            "canonical desktop syntax",
        )
        for selected in paths:
            if (
                selected.startswith("frontend/launcher/")
                and selected.endswith(".js")
                and (root / selected).is_file()
            ):
                add(
                    [executable("node"), "--check", str(checked_path(root, selected))],
                    root / "frontend/launcher",
                    "changed desktop syntax, including new modules",
                )
    if "worker" in scopes and args.mode in {"check", "lint"}:
        js_paths = [
            checked_path(root, p)
            for p in paths
            if p.startswith("services/api/") and p.endswith(".js") and (root / p).is_file()
        ]
        if not args.changed:
            js_paths = sorted((root / "services/api/src").rglob("*.js"))
        for path in js_paths:
            add(
                [executable("node"), "--check", str(path)],
                root / "services/api",
                "selected Worker syntax",
            )
    if args.mode == "check":
        if scopes & BACKEND_SCOPES:
            add(
                [python, str(root / "scripts/check_types.py")],
                backend,
                "whole app type debt and clean modules",
            )
        if tests := test_paths(root, scopes):
            add(
                [python, "-m", "pytest", *tests],
                backend,
                "consumer profiles: " + ", ".join(sorted(scopes & BACKEND_SCOPES)),
            )
        if "desktop" in scopes:
            add(npm_argv("test"), root / "frontend/launcher", "desktop behavior tests")
        if "worker" in scopes:
            add(
                npm_argv("test"),
                root / "services/api",
                "Worker unit and genuine local D1 integration",
            )
        if scopes:
            add(
                [python, str(root / "scripts/bump_version.py"), "--check"],
                root,
                "backend/package/lock/UK-EN versions",
            )
            add(
                [python, str(root / "scripts/build_site.py"), "--check"],
                root,
                "generated site",
            )
            add(
                [python, str(root / "scripts/build_changelog.py"), "--check"],
                root,
                "generated release history",
            )
        add(["git", "diff", "--check"], root, "changed-tree whitespace")
        if args.package:
            if os.name != "nt":
                raise ValueError(
                    "--package requires Windows; use actual Windows CI on other systems."
                )
            powershell = executable("powershell")
            add(
                [
                    powershell,
                    "-NoProfile",
                    "-File",
                    str(root / "scripts/build-windows.ps1"),
                ],
                root,
                "actual Windows build",
            )
            add(
                [
                    powershell,
                    "-NoProfile",
                    "-File",
                    str(root / "scripts/smoke-windows.ps1"),
                ],
                root,
                "actual Windows installer smoke",
            )
    return paths, scopes, commands


def special_plan(root: Path, args: argparse.Namespace) -> list[Command]:
    scope = set(args.scope or ())
    if args.mode == "typecheck":
        return [
            Command(
                (backend_python(root), str(root / "scripts/check_types.py")),
                root / "backend",
                "type gate",
            )
        ]
    if args.mode == "test":
        if args.target:
            path = checked_path(root, args.target)
            relative = path.relative_to(root).as_posix()
            if relative.startswith("backend/tests/") and path.suffix == ".py":
                return [
                    Command(
                        (backend_python(root), "-m", "pytest", str(path)),
                        root / "backend",
                        "explicit backend target",
                    )
                ]
            for prefix in ("frontend/launcher/", "services/api/"):
                if relative.startswith(prefix + "test/") and path.suffix == ".js":
                    return [
                        Command(
                            (executable("node"), "--test", str(path)),
                            root / prefix,
                            "explicit Node target",
                        )
                    ]
            raise ValueError("--target must be a backend/launcher/Worker test file.")
        if not scope:
            raise ValueError("test requires --target or --scope")
        commands = []
        if tests := test_paths(root, scope):
            commands.append(
                Command(
                    (backend_python(root), "-m", "pytest", *tests),
                    root / "backend",
                    "backend consumer tests",
                )
            )
        if "desktop" in scope:
            commands.append(Command(npm_argv("test"), root / "frontend/launcher", "launcher tests"))
        if "worker" in scope:
            commands.append(
                Command(
                    npm_argv("run", "test:integration") if args.integration else npm_argv("test"),
                    root / "services/api",
                    "Worker local tests",
                )
            )
        if not commands:
            raise ValueError("No test suite for selected scope.")
        return commands
    if args.mode == "dev":
        if scope == {"backend"}:
            return [
                Command(
                    (backend_python(root), "-m", "uvicorn", "app.main:app", "--reload"),
                    root / "backend",
                    "explicit standalone backend",
                )
            ]
        if scope and scope != {"desktop"}:
            raise ValueError("dev supports desktop (default) or explicit backend")
        return [
            Command(
                npm_argv("run", "dev"),
                root / "frontend/launcher",
                "launcher owns its backend",
            )
        ]
    if args.mode == "setup":
        if scope - {"backend", "desktop", "worker"}:
            raise ValueError("setup supports backend/desktop/worker")
        scope = scope or {"backend", "desktop"}
        commands = []
        if "backend" in scope:
            try:
                python = backend_python(root)
            except ValueError:
                python = str(
                    root
                    / "backend/.venv"
                    / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
                )
                commands.append(
                    Command(
                        (args.python, "-m", "venv", str(root / "backend/.venv")),
                        root,
                        "explicit venv creation",
                    )
                )
            commands.append(
                Command(
                    (
                        python,
                        "-m",
                        "pip",
                        "install",
                        "--disable-pip-version-check",
                        "--require-hashes",
                        "--only-binary=:all:",
                        "-r",
                        "requirements-dev.txt",
                    ),
                    root / "backend",
                    "locked dev dependencies",
                )
            )
        for selected, directory in (
            ("desktop", "frontend/launcher"),
            ("worker", "services/api"),
        ):
            if selected in scope:
                commands.append(
                    Command(
                        npm_argv("ci"),
                        root / directory,
                        "locked " + selected + " dependencies",
                    )
                )
        return commands
    if args.mode == "build":
        if os.name != "nt":
            raise ValueError("build requires Windows")
        return [
            Command(
                (
                    executable("powershell"),
                    "-NoProfile",
                    "-File",
                    str(root / "scripts/build-windows.ps1"),
                    *(("-SkipBackend",) if args.skip_backend else ()),
                ),
                root,
                "explicit Windows build",
            )
        ]
    raise ValueError("Unsupported command")


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument(
        "mode",
        choices=(
            "check",
            "lint",
            "format",
            "typecheck",
            "test",
            "setup",
            "dev",
            "build",
        ),
    )
    result.add_argument(
        "--changed",
        action="store_true",
        help="Union staged, unstaged and untracked paths",
    )
    result.add_argument("--base", help="Also include committed changes since this ref")
    result.add_argument("--scope", action="append", choices=SCOPES)
    result.add_argument(
        "--full",
        action="store_true",
        help="All check profiles; package remains explicit",
    )
    result.add_argument(
        "--dry-run",
        action="store_true",
        help="Print JSON plan without executing checks",
    )
    result.add_argument("--target", help="Repository-relative test file")
    result.add_argument("--integration", action="store_true", help="Worker local D1 suite")
    result.add_argument("--package", action="store_true", help="Include actual Windows build/smoke")
    result.add_argument(
        "--skip-backend",
        action="store_true",
        help="Explicit build with existing backend executable",
    )
    result.add_argument(
        "--python",
        default=sys.executable,
        help="Interpreter for explicit setup venv creation",
    )
    return result


def fingerprint(root: Path, paths: Sequence[str]) -> str:
    digest = hashlib.sha256()
    for raw in sorted(paths):
        digest.update(raw.encode("utf-8") + b"\0")
        path = root / raw
        if path.is_symlink():
            digest.update(os.readlink(path).encode("utf-8"))
        elif path.is_file():
            with path.open("rb") as source:
                while chunk := source.read(65536):
                    digest.update(chunk)
        else:
            digest.update(b"deleted")
        digest.update(b"\0")
    # Include index status even when staged/working copies end with the same bytes.
    digest.update(_git(root, "status", "--porcelain=v1", "-z").encode("utf-8"))
    return digest.hexdigest()


def receipt_path(root: Path) -> Path:
    key = hashlib.sha256(str(root.resolve()).encode("utf-8")).hexdigest()[:24]
    return Path(tempfile.gettempdir()) / f"wardly-check-{key}.json"


def save_receipt(root: Path, token: str, scopes: set[str]) -> None:
    destination = receipt_path(root)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=destination.parent,
        prefix="wardly-check-",
        delete=False,
    ) as output:
        temporary = Path(output.name)
        json.dump({"format": 1, "fingerprint": token, "profiles": sorted(scopes)}, output)
    try:
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


def receipt_matches(root: Path, paths: Sequence[str]) -> bool:
    try:
        content = receipt_path(root).read_text(encoding="utf-8")
        if len(content) > 8192:
            return False
        saved = json.loads(content)
        return (
            saved.get("format") == 1
            and saved.get("fingerprint") == fingerprint(root, paths)
            and profiles_for(paths).issubset(set(saved.get("profiles", [])))
        )
    except (OSError, ValueError, TypeError, AttributeError):
        return False


def main() -> int:
    args = parser().parse_args()
    try:
        if args.base and not args.changed:
            raise ValueError("--base requires --changed")
        if (args.changed or args.full) and args.mode not in {"check", "lint", "format"}:
            raise ValueError("--changed/--full apply to check, lint or format")
        if args.package and args.mode != "check":
            raise ValueError("--package applies to check")
        if args.skip_backend and args.mode != "build":
            raise ValueError("--skip-backend applies to build")
        if args.integration and (args.mode != "test" or set(args.scope or ()) != {"worker"}):
            raise ValueError("--integration applies to test --scope worker")
        if args.target and args.mode != "test":
            raise ValueError("--target applies to test")
        if args.mode in {"check", "lint", "format"}:
            paths, scopes, commands = plan(ROOT, args)
        else:
            paths, scopes, commands = (
                [],
                set(args.scope or ()),
                special_plan(ROOT, args),
            )
        print(
            json.dumps(
                {
                    "paths": paths,
                    "profiles": sorted(scopes),
                    "commands": [
                        {"argv": c.argv, "cwd": str(c.cwd), "reason": c.reason} for c in commands
                    ],
                },
                ensure_ascii=False,
            ),
            flush=True,
        )
        if args.dry_run:
            return 0
        env = dict(os.environ)
        if args.mode in {"check", "test"}:
            env.update(USE_LLM="false", OPENDOTA_ENABLED="false")
        token = fingerprint(ROOT, paths) if args.mode == "check" and args.changed else None
        for command in commands:
            subprocess.run(command.argv, cwd=command.cwd, env=env, check=True)
        if token is not None and token == fingerprint(ROOT, paths):
            save_receipt(ROOT, token, scopes)
        return 0
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
