"""The real pinned checker rejects regressions and only prunes resolved debt."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from importlib.metadata import version
from pathlib import Path
from typing import Any

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts/check_types.py"
SPEC = importlib.util.spec_from_file_location("wardly_check_types", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
GATE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = GATE
SPEC.loader.exec_module(GATE)


def _invoke(backend: Path, baseline: Path, *options: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--backend-dir",
            str(backend),
            "--baseline",
            str(baseline),
            *options,
        ],
        cwd=backend.parent,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
        check=False,
    )


@pytest.fixture
def project(tmp_path: Path) -> tuple[Path, Path]:
    backend = tmp_path / "backend"
    app = backend / "app"
    app.mkdir(parents=True)
    (app / "__init__.py").write_text("")
    (app / "clean.py").write_text('value: str = "valid"\n')
    (app / "debt.py").write_text('value: int = "existing error"\n')
    (backend / "pyproject.toml").write_text('[tool.mypy]\npython_version = "3.11"\n')
    errors = GATE.run_mypy(backend)
    assert errors.total() == 1
    baseline = backend / "type-baseline.json"
    baseline.write_text(
        json.dumps(
            {
                "format": 1,
                "mypy_version": version("mypy"),
                "python_target": "3.11",
                "clean_modules": ["app/clean.py"],
                "errors": GATE.entries(errors),
            }
        )
    )
    return backend, baseline


def test_gate_accepts_reviewed_debt_after_line_shifts_and_rejects_more_occurrences(
    project: tuple[Path, Path],
) -> None:
    backend, baseline = project
    debt = backend / "app/debt.py"
    debt.write_text('\n\n# Harmless edit\nvalue: int = "existing error"\n')
    result = _invoke(backend, baseline)
    assert result.returncode == 0 and "1 reviewed errors" in result.stdout
    before = baseline.read_bytes()
    debt.write_text(debt.read_text() + 'another: int = "same error"\n')
    result = _invoke(backend, baseline, "--prune-baseline")
    assert result.returncode == 1 and "1 new type errors" in result.stdout
    assert baseline.read_bytes() == before


def test_same_total_cannot_hide_a_message_or_module_swap_and_new_modules_are_checked(
    project: tuple[Path, Path],
) -> None:
    backend, baseline = project
    before = baseline.read_bytes()
    (backend / "app/debt.py").write_text("def value() -> str:\n    return 1\n")
    result = _invoke(backend, baseline)
    assert result.returncode == 1 and "1 new type errors" in result.stdout
    assert "[return-value]" in result.stdout
    (backend / "app/debt.py").write_text("value: int = 1\n")
    clean = backend / "app/clean.py"
    clean.write_text('value: int = "new clean-module error"\n')
    result = _invoke(backend, baseline)
    assert result.returncode == 1 and "app/clean.py" in result.stdout
    clean.write_text('value: str = "valid"\n')
    (backend / "app/new_module.py").write_text('value: int = "new module error"\n')
    result = _invoke(backend, baseline, "--prune-baseline")
    assert result.returncode == 1 and "app/new_module.py" in result.stdout
    assert baseline.read_bytes() == before


def test_resolved_errors_must_be_pruned_and_the_allowance_cannot_return(
    project: tuple[Path, Path],
) -> None:
    backend, baseline = project
    debt = backend / "app/debt.py"
    debt.write_text("value: int = 1\n")
    result = _invoke(backend, baseline)
    assert result.returncode == 1 and "resolved baseline errors" in result.stdout
    result = _invoke(backend, baseline, "--prune-baseline")
    assert result.returncode == 0 and json.loads(baseline.read_text())["errors"] == []
    debt.write_text('value: int = "regression"\n')
    result = _invoke(backend, baseline)
    assert result.returncode == 1 and "1 new type errors" in result.stdout


@pytest.mark.parametrize("fault", ["version", "format", "missing_module", "clean_allowance"])
def test_invalid_baseline_fails_closed(project: tuple[Path, Path], fault: str) -> None:
    backend, baseline = project
    data: dict[str, Any] = json.loads(baseline.read_text())
    if fault == "version":
        data["mypy_version"] = "wrong-version"
    elif fault == "format":
        data["format"] = True
    elif fault == "missing_module":
        data["clean_modules"] = ["app/missing.py"]
    else:
        data["clean_modules"] = ["app/debt.py"]
    baseline.write_text(json.dumps(data))
    result = _invoke(backend, baseline)
    assert result.returncode == 1 and "FAIL:" in result.stderr


def test_diagnostic_parser_preserves_counts_and_rejects_unknown_formats() -> None:
    output = (
        "app/debt.py:3: error: Incompatible types in assignment [assignment]\n"
        "app/debt.py:19:5: error: Incompatible types in assignment [assignment]\n"
        "app/debt.py:19: note: A useful note\n"
    )
    errors = GATE.parse_errors(output)
    assert errors.total() == 2 and len(errors) == 1
    with pytest.raises(ValueError, match="Unrecognized"):
        GATE.parse_errors("app/debt.py:3: error: Missing error code")
