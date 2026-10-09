"""Require the checked-out commit to be the immutable SHA selected by CI."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[1]


def verify_source(expected: str, repository: Path) -> str:
    if re.fullmatch(r"[0-9a-f]{40}", expected) is None:
        raise ValueError("Expected a full lowercase commit SHA, not a branch or tag.")
    actual = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repository,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=10,
        check=True,
    ).stdout.strip()
    if actual != expected:
        raise ValueError(f"Source mismatch: selected {expected}, checked out {actual}.")
    unchanged = subprocess.run(
        ["git", "diff", "--quiet", "HEAD", "--"], cwd=repository, timeout=10, check=False
    )
    if unchanged.returncode != 0:
        raise ValueError("Tracked source changed since the selected checkout.")
    return actual


def verify_tag(tag: str, expected: str, repository: Path, *, allow_missing: bool) -> None:
    if re.fullmatch(r"v\d+\.\d+\.\d+", tag) is None:
        raise ValueError("Invalid release tag.")
    ref = f"refs/tags/{tag}"
    output = subprocess.run(
        ["git", "ls-remote", "--tags", "origin", ref, f"{ref}^{{}}"],
        cwd=repository,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
        check=True,
    ).stdout
    refs: dict[str, str] = {}
    for line in output.splitlines():
        sha, name = line.split()
        if name not in {ref, f"{ref}^{{}}"} or name in refs:
            raise ValueError("Ambiguous release tag.")
        refs[name] = sha
    commit = refs.get(f"{ref}^{{}}") or refs.get(ref)
    if commit is None:
        if not allow_missing:
            raise ValueError("Release tag disappeared after validation.")
    elif commit != expected:
        raise ValueError("Release tag points to a commit that was not validated.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sha")
    parser.add_argument("--repository", type=Path, default=REPOSITORY)
    parser.add_argument(
        "--release-tag", help="Also verify the current origin tag before publishing"
    )
    parser.add_argument(
        "--allow-missing-tag", action="store_true", help="Manual release creates the tag"
    )
    args = parser.parse_args()
    try:
        actual = verify_source(args.sha, args.repository)
        if args.release_tag:
            verify_tag(
                args.release_tag, actual, args.repository, allow_missing=args.allow_missing_tag
            )
        print(f"Verified source commit: {actual}")
        return 0
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
