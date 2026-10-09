"""Real Git checkouts/tags and the workflow graph enforce release provenance."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/verify_source.py"


def _git(repository: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", *args],
        cwd=repository,
        text=True,
        encoding="utf-8",
        env={
            **os.environ,
            "GIT_AUTHOR_NAME": "Wardly test",
            "GIT_COMMITTER_NAME": "Wardly test",
            "GIT_AUTHOR_EMAIL": "checks@example.invalid",
            "GIT_COMMITTER_EMAIL": "checks@example.invalid",
        },
        stderr=subprocess.PIPE,
        timeout=10,
    ).strip()


def _verify(repository: Path, sha: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), sha, "--repository", str(repository), *args],
        cwd=repository.parent,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=15,
        check=False,
    )


@pytest.fixture
def repository(tmp_path: Path) -> tuple[Path, str]:
    repository = tmp_path / "source"
    repository.mkdir()
    _git(repository, "init", "--initial-branch=main")
    (repository / "source.txt").write_text("first commit\n")
    _git(repository, "add", "source.txt")
    _git(repository, "commit", "-m", "first")
    return repository, _git(repository, "rev-parse", "HEAD")


def test_source_guard_requires_the_selected_immutable_commit(repository: tuple[Path, str]) -> None:
    repo, first = repository
    assert _verify(repo, first).returncode == 0
    for mutable in ("main", "v0.53.10", first[:12]):
        assert _verify(repo, mutable).returncode == 1
    (repo / "source.txt").write_text("second commit\n")
    _git(repo, "commit", "-am", "second")
    result = _verify(repo, first)
    assert result.returncode == 1 and "Source mismatch" in result.stderr
    assert _verify(repo, _git(repo, "rev-parse", "HEAD")).returncode == 0


def test_same_head_with_changed_tracked_source_is_rejected(repository: tuple[Path, str]) -> None:
    repo, sha = repository
    (repo / "source.txt").write_text("unvalidated edit\n")
    assert "Tracked source changed" in _verify(repo, sha).stderr
    _git(repo, "add", "source.txt")
    assert _verify(repo, sha).returncode == 1
    _git(repo, "reset", "--hard", sha)
    assert _verify(repo, sha).returncode == 0


@pytest.mark.parametrize("annotated", [False, True])
def test_remote_tag_movement_or_deletion_cannot_publish_another_commit(
    repository: tuple[Path, str], tmp_path: Path, annotated: bool
) -> None:
    repo, first = repository
    origin = tmp_path / "origin.git"
    _git(repo, "init", "--bare", str(origin))
    _git(repo, "remote", "add", "origin", str(origin))
    tag = "v0.53.10"
    tag_args = ("-a", "-m", "test tag") if annotated else ()
    _git(repo, "tag", *tag_args, tag)
    _git(repo, "push", "origin", tag)
    assert _verify(repo, first, "--release-tag", tag).returncode == 0
    (repo / "source.txt").write_text("another release commit\n")
    _git(repo, "commit", "-am", "second")
    _git(repo, "tag", "-f", *tag_args, tag)
    _git(repo, "push", "--force", "origin", tag)
    _git(repo, "checkout", "--detach", first)
    result = _verify(repo, first, "--release-tag", tag)
    assert result.returncode == 1 and "not validated" in result.stderr
    _git(repo, "push", "origin", f":refs/tags/{tag}")
    result = _verify(repo, first, "--release-tag", tag)
    assert result.returncode == 1 and "disappeared" in result.stderr
    assert _verify(repo, first, "--release-tag", tag, "--allow-missing-tag").returncode == 0


def test_release_workflow_cannot_build_or_publish_before_shared_validation() -> None:
    release = yaml.load(
        (ROOT / ".github/workflows/release.yml").read_text(), Loader=yaml.BaseLoader
    )
    ci = yaml.load((ROOT / ".github/workflows/ci.yml").read_text(), Loader=yaml.BaseLoader)
    jobs = release["jobs"]
    selected = "${{ needs.source.outputs.sha }}"
    assert jobs["validation"]["uses"] == "./.github/workflows/ci.yml"
    assert jobs["validation"]["needs"] == "source"
    assert jobs["validation"]["with"]["source_sha"] == selected
    assert jobs["validation"]["permissions"]["contents"] == "read"
    windows = jobs["windows"]
    assert set(windows["needs"]) == {"source", "validation"}
    assert "if" not in windows  # GitHub's default success gate must remain in effect.
    assert windows["env"]["RELEASE_SHA"] == selected
    checkout = next(
        step
        for step in windows["steps"]
        if str(step.get("uses", "")).startswith("actions/checkout@")
    )
    assert checkout["with"]["ref"] == selected
    publish = next(
        step for step in windows["steps"] if step.get("name") == "Publish GitHub release"
    )
    assert publish["run"].index("verify_source.py") < publish["run"].index("gh release create")
    assert "--target $env:RELEASE_SHA" in publish["run"]
    assert ci["on"]["workflow_call"]["inputs"]["source_sha"]["required"] == "true"
    assert ci["permissions"]["contents"] == "read"
    for job in ci["jobs"].values():
        checkout = next(
            step
            for step in job["steps"]
            if str(step.get("uses", "")).startswith("actions/checkout@")
        )
        assert checkout["with"]["ref"] == "${{ inputs.source_sha || github.sha }}"
        assert any("verify_source.py" in step.get("run", "") for step in job["steps"])
