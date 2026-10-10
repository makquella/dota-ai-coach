"""Real Git trees and real argv plans for the portable developer interface."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

REPOSITORY = Path(__file__).resolve().parents[2]


def _module(name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, REPOSITORY / "scripts" / f"{name}.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


dev = _module("dev")
hook = _module("check_hook")


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=root, check=True, capture_output=True, text=True, encoding="utf-8"
    ).stdout.strip()


@pytest.fixture
def tree(tmp_path: Path) -> Path:
    root = tmp_path / "Репозиторій з пробілами"
    root.mkdir()
    _git(root, "init")
    _git(root, "config", "user.name", "Local test")
    _git(root, "config", "user.email", "test@example.invalid")
    for name in (
        "backend/app/decision_points.py",
        "backend/app/main.py",
        "backend/tests/test_api_smoke.py",
        "backend/tests/test_packaging_runtime.py",
        "backend/tests/test_gsi_samples_and_advice.py",
        "backend/tests/test_dev_runner.py",
        "frontend/launcher/main.js",
        "services/api/src/index.js",
        "docs/example.md",
    ):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# initial\n", encoding="utf-8")
    (root / ".gitignore").write_text(".venv/\nignored.local\n", encoding="utf-8")
    _git(root, "add", ".")
    _git(root, "commit", "-m", "initial")
    return root


def _venv(root: Path, windows: bool = False) -> Path:
    path = root / "backend/.venv" / ("Scripts/python.exe" if windows else "bin/python")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"fixture path for argv discovery")
    return path


def test_real_git_union_includes_staged_unstaged_untracked_and_optional_base(tree: Path) -> None:
    base = _git(tree, "rev-parse", "HEAD")
    (tree / "docs/example.md").write_text("committed change\n")
    _git(tree, "add", "docs/example.md")
    _git(tree, "commit", "-m", "docs")
    (tree / "backend/app/decision_points.py").write_text("# staged\n")
    _git(tree, "add", "backend/app/decision_points.py")
    (tree / "frontend/launcher/main.js").write_text("// unstaged\n")
    (tree / "backend/tests/test_new case.py").write_text("# untracked\n")
    (tree / "ignored.local").write_text("ignored\n")
    expected = {
        "backend/app/decision_points.py",
        "frontend/launcher/main.js",
        "backend/tests/test_new case.py",
    }
    assert set(dev.changed_paths(tree)) == expected
    assert set(dev.changed_paths(tree, base)) == expected | {"docs/example.md"}
    assert dev.profiles_for(dev.changed_paths(tree)) == {"live", "desktop", "backend"}


def test_rename_delete_and_unknown_boundary_cannot_hide_consumer_checks(tree: Path) -> None:
    _git(tree, "mv", "frontend/launcher/main.js", "docs/moved.js")
    (tree / "backend/app/decision_points.py").unlink()
    paths = dev.changed_paths(tree)
    assert set(paths) == {
        "frontend/launcher/main.js",
        "docs/moved.js",
        "backend/app/decision_points.py",
    }
    assert dev.profiles_for(paths) == {"desktop", "backend", "live", "site"}
    assert dev.profiles_for(["new-build-input"]) == set(dev.SCOPES)
    assert dev.profiles_for(["backend/app/unknown.py"]) == {"backend"}
    assert dev.profiles_for(["scripts/new-build.py"]) >= {"backend", "desktop"}


@pytest.mark.parametrize(
    ("paths", "expected"),
    [
        (["backend/app/advice_scheduler.py"], {"live"}),
        (["backend/app/coach_review.py"], {"ai", "history"}),
        (["backend/app/player_store.py"], {"backend"}),
        (["frontend/launcher/renderer/matches.js"], {"desktop"}),
        (["frontend/launcher/preload.js"], {"desktop", "backend"}),
        (["services/api/migrations/001.sql"], {"worker"}),
        (["docs/release-notes/v0.53.42.md"], {"site"}),
        (["data/gsi_samples/packet.json"], {"live", "history", "site"}),
    ],
)
def test_explicit_profiles_cover_critical_and_data_paths(
    paths: list[str], expected: set[str]
) -> None:
    assert dev.profiles_for(paths) == expected


def test_read_only_changed_plan_uses_explicit_cwd_argv_and_includes_new_js(tree: Path) -> None:
    python = _venv(tree)
    source = tree / "backend/app/decision_points.py"
    source.write_text("# changed\n")
    js = tree / "frontend/launcher/new module.js"
    js.write_text("'use strict';\n")
    args = dev.parser().parse_args(["check", "--changed", "--dry-run"])
    paths, scopes, commands = dev.plan(tree, args)
    assert paths == ["backend/app/decision_points.py", "frontend/launcher/new module.js"]
    assert scopes == {"live", "desktop"}
    assert any(c.argv[:4] == (str(python), "-m", "ruff", "check") for c in commands)
    assert any(str(source) in c.argv and "--check" in c.argv for c in commands)
    assert any(c.argv[1:] == ("--check", str(js)) for c in commands)
    tests = next(c for c in commands if "pytest" in c.argv)
    assert tests.cwd == tree / "backend"
    assert "tests/test_gsi_samples_and_advice.py" in tests.argv
    assert any("build_site.py" in c.argv[1] and "--check" in c.argv for c in commands)
    assert any("bump_version.py" in c.argv[1] for c in commands)
    assert all("deploy" not in c.argv and "publish" not in c.argv for c in commands)
    assert not any("fix" in c.argv or "--fix" in c.argv for c in commands)


def test_empty_tree_has_only_whitespace_check_and_windows_venv_is_discovered(tree: Path) -> None:
    python = _venv(tree, windows=True)
    assert dev.backend_python(tree) == str(python)
    _, scopes, commands = dev.plan(tree, dev.parser().parse_args(["check", "--changed"]))
    assert scopes == set() and len(commands) == 1 and commands[0].argv == ("git", "diff", "--check")


def test_actual_npm_entrypoint_avoids_cmd_shell_and_supports_real_installation() -> None:
    argv = dev.npm_argv("run", "check")
    assert Path(argv[0]).is_file() and Path(argv[1]).is_file()
    assert argv[1].endswith("npm-cli.js") and argv[2:] == ("run", "check")
    assert all("cmd.exe" not in arg.lower() for arg in argv)


def test_target_and_hook_paths_are_confined_even_with_shell_metacharacters(tree: Path) -> None:
    _venv(tree)
    file = tree / "backend/tests/test_$(private) & space.py"
    file.write_text("# actual argv fixture\n")
    args = dev.parser().parse_args(["test", "--target", str(file)])
    commands = dev.special_plan(tree, args)
    assert commands[0].argv[-1] == str(file) and commands[0].cwd == tree / "backend"
    commands = hook.edit_commands(tree, {"tool_input": {"file_path": str(file)}}, formatting=False)
    assert len(commands) == 1 and commands[0].argv[-1] == str(file)
    assert "format" not in commands[0].argv
    outside = tree.parent / "outside.py"
    outside.write_text("# outside\n")
    with pytest.raises(ValueError, match="inside repository"):
        dev.special_plan(tree, dev.parser().parse_args(["test", "--target", str(outside)]))
    with pytest.raises(ValueError, match="inside repository"):
        hook.edit_commands(tree, {"tool_input": {"file_path": str(outside)}}, formatting=True)
    assert (
        hook.edit_commands(tree, {"tool_input": {"file_path": "docs/example.md"}}, formatting=False)
        == []
    )
    assert hook.edit_commands(tree, {}, formatting=False) == []


def test_only_explicit_formatting_changes_the_hook_plan(tree: Path) -> None:
    _venv(tree)
    commands = hook.edit_commands(
        tree, {"tool_input": {"file_path": "backend/app/main.py"}}, formatting=True
    )
    assert len(commands) == 2 and commands[0].argv[3] == "format" and commands[1].argv[3] == "check"


def test_success_receipt_requires_same_real_tree_and_covered_profiles(tree: Path) -> None:
    path = tree / "backend/app/decision_points.py"
    path.write_text("# first\n")
    paths = dev.changed_paths(tree)
    receipt = dev.receipt_path(tree)
    try:
        assert not dev.receipt_matches(tree, paths)
        dev.save_receipt(tree, dev.fingerprint(tree, paths), {"site"})
        assert not dev.receipt_matches(tree, paths)
        dev.save_receipt(tree, dev.fingerprint(tree, paths), dev.profiles_for(paths))
        assert dev.receipt_matches(tree, paths)
        path.write_text("# second\n")
        assert not dev.receipt_matches(tree, paths)
        dev.save_receipt(tree, dev.fingerprint(tree, paths), dev.profiles_for(paths))
        _git(tree, "add", "backend/app/decision_points.py")
        assert not dev.receipt_matches(tree, paths)  # index changed despite same file bytes
        receipt.write_text("not JSON")
        assert not dev.receipt_matches(tree, paths)
    finally:
        receipt.unlink(missing_ok=True)


def test_actual_cli_help_and_optional_hook_leave_hooks_disabled() -> None:
    result = subprocess.run(
        [sys.executable, str(REPOSITORY / "scripts/dev.py"), "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0 and "--changed" in result.stdout and "--dry-run" in result.stdout
    result = subprocess.run(
        [sys.executable, str(REPOSITORY / "scripts/check_hook.py"), "stop"],
        input=json.dumps({"stop_hook_active": True}),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0 and result.stdout == ""
    assert json.loads((REPOSITORY / ".claude/settings.json").read_text())["hooks"] == {}
