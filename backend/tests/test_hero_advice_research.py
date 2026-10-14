"""Research CLI with real files: wrong facts/availability must block publication."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "hero_advice_research.py"


def _run(data: Path, docs: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args, "--data", str(data), "--docs", str(docs)],
        cwd=ROOT,
        env={**os.environ, "PYTHONUTF8": "1"},
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
        check=False,
    )


@pytest.fixture
def research(tmp_path: Path) -> Path:
    dest = tmp_path / "research"
    shutil.copytree(ROOT / "data" / "hero_advice_research", dest)
    return dest


def test_five_hero_research_renders_and_checks_real_documents(
    research: Path, tmp_path: Path
) -> None:
    docs = tmp_path / "docs"
    result = _run(research, docs, "render")
    assert result.returncode == 0, result.stdout + result.stderr
    assert len(list(docs.glob("*.md"))) == 6
    assert "5 heroes" in result.stdout
    checked = _run(research, docs, "render", "--check")
    assert checked.returncode == 0, checked.stdout
    ember = (docs / "ember_spirit.md").read_text(encoding="utf-8")
    assert "ember_spirit.consume_all" in ember
    assert "Контрпример:" in ember
    assert "не включены в приложение" in ember


def test_stale_document_is_reported_without_rewriting(research: Path, tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    assert _run(research, docs, "render").returncode == 0
    path = docs / "ember_spirit.md"
    path.write_text("old research\n", encoding="utf-8")
    result = _run(research, docs, "render", "--check")
    assert result.returncode == 1
    assert "stale research docs" in result.stdout
    assert path.read_text() == "old research\n"


@pytest.mark.parametrize(
    ("mutation", "diagnostic"),
    [
        ("fact", "differs from source"),
        ("source", "checksum mismatch"),
        ("readiness", "live readiness overclaims"),
        ("evidence", "unknown evidence"),
        ("translation", "missing translation"),
        ("length", "exceeds overlay limit"),
        ("scenario", "missing counterexample"),
        ("path", "unsafe source path"),
        ("patch", "patch mismatch"),
    ],
)
def test_invalid_research_is_rejected_by_cli(
    research: Path, tmp_path: Path, mutation: str, diagnostic: str
) -> None:
    path = research / "catalogs" / "ember_spirit.json"
    item = json.loads(path.read_text(encoding="utf-8"))
    if mutation == "fact":
        fact = next(f for f in item["mechanics"] if "equals" in f)
        fact["equals"] = [999]
    elif mutation == "source":
        source = research / item["source"]
        snapshot = json.loads(source.read_text(encoding="utf-8"))
        snapshot["hero"]["name"] = "Wrong hero"
        source.write_text(json.dumps(snapshot), encoding="utf-8")
    elif mutation == "readiness":
        item["advice"][0]["readiness"] = "existing"
    elif mutation == "evidence":
        item["advice"][0]["evidence"] = ["invented-mechanic"]
    elif mutation == "translation":
        del item["advice"][0]["action"]["uk"]
    elif mutation == "length":
        item["advice"][0]["action"]["uk"] = "x" * 101
    elif mutation == "scenario":
        del item["advice"][0]["scenarios"]["unknown"]
    elif mutation == "path":
        item["source"] = "../outside.json"
    else:
        manifest = research / "manifest.json"
        data = json.loads(manifest.read_text(encoding="utf-8"))
        data["patch"] = "old-patch"
        manifest.write_text(json.dumps(data), encoding="utf-8")
    path.write_text(json.dumps(item), encoding="utf-8")
    result = _run(research, tmp_path / "docs", "validate")
    assert result.returncode == 1, result.stdout + result.stderr
    assert diagnostic in result.stdout


def test_committed_research_documents_match_catalogs() -> None:
    result = _run(
        ROOT / "data" / "hero_advice_research", ROOT / "docs" / "hero-advice", "render", "--check"
    )
    assert result.returncode == 0, result.stdout + result.stderr
