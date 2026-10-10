"""Real Git path selection and the summary CLI cannot hide a failed build."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
import yaml
from test_release_validation import _git

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/windows_checks.py"


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=15,
        check=False,
    )


@pytest.fixture
def repo(tmp_path: Path) -> tuple[Path, str]:
    repo = tmp_path / "git"
    (repo / "backend/app").mkdir(parents=True)
    _git(repo, "init", "--initial-branch=main")
    (repo / "backend/app/main.py").write_text("# source\n")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "base")
    return repo, _git(repo, "rev-parse", "HEAD")


def _scope(repo: Path, base: str) -> subprocess.CompletedProcess[str]:
    return _run(
        "scope",
        "--source",
        _git(repo, "rev-parse", "HEAD"),
        "--base",
        base,
        "--repository",
        str(repo),
    )


def test_only_known_non_desktop_paths_skip_windows(repo: tuple[Path, str]) -> None:
    root, base = repo
    for name in ("docs/Перевірка з пробілами.md", "site/index.html", "services/api/src/index.js"):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# changed\n")
    _git(root, "add", ".")
    _git(root, "commit", "-m", "non desktop")
    result = _scope(root, base)
    assert result.returncode == 0 and "windows_required=false" in result.stdout
    (root / "unknown-build-input").write_text("unknown\n")
    _git(root, "add", ".")
    _git(root, "commit", "-m", "unknown input")
    assert "windows_required=true" in _scope(root, base).stdout


def test_removed_or_renamed_desktop_source_requires_windows(repo: tuple[Path, str]) -> None:
    root, base = repo
    (root / "docs").mkdir()
    _git(root, "mv", "backend/app/main.py", "docs/example.py")
    _git(root, "commit", "-m", "move from packaged source")
    assert "windows_required=true" in _scope(root, base).stdout


@pytest.mark.parametrize("base", ["", "0" * 40, "f" * 40])
def test_missing_base_is_conservative(repo: tuple[Path, str], base: str) -> None:
    root, _ = repo
    result = _scope(root, base)
    assert result.returncode == 0 and "windows_required=true" in result.stdout


@pytest.mark.parametrize(
    ("changes", "build", "required", "caller", "code"),
    [
        ("success", "success", "true", "false", 0),
        ("success", "skipped", "false", "false", 0),
        ("success", "skipped", "true", "true", 0),
        ("success", "skipped", "true", "false", 1),
        ("failure", "skipped", "false", "false", 1),
        ("cancelled", "success", "true", "false", 1),
        ("success", "failure", "false", "false", 1),
        ("success", "cancelled", "true", "true", 1),
        ("skipped", "skipped", "false", "false", 1),
    ],
)
def test_summary_accepts_only_success_or_a_justified_skip(
    changes: str, build: str, required: str, caller: str, code: int
) -> None:
    result = _run(
        "summary",
        "--changes",
        changes,
        "--build",
        build,
        "--required",
        required,
        "--caller-builds-windows",
        caller,
    )
    assert result.returncode == code


def test_windows_required_context_remains_stable_and_always_checks_results() -> None:
    ci = yaml.load((ROOT / ".github/workflows/ci.yml").read_text(), Loader=yaml.BaseLoader)
    jobs = ci["jobs"]
    summary = jobs["windows-package"]
    assert summary["name"] == "Windows package (PyInstaller + NSIS, /health smoke)"
    assert summary["if"] == "${{ always() }}"
    assert set(summary["needs"]) == {"changes", "windows-build"}
    assert "needs.changes.outputs.windows_required == 'true'" in jobs["windows-build"]["if"]
    assert "!inputs.skip_windows" in jobs["windows-build"]["if"]
    assert jobs["changes"]["steps"][0]["with"]["fetch-depth"] == "0"
