from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app import gsi_state  # noqa: E402
from app.coach_summary import COACH_SESSION_HISTORY  # noqa: E402
from app.main import _clear_demo_overlay_response, app  # noqa: E402
from app.match_memory import MATCH_MEMORY  # noqa: E402
from app.advice_scheduler import ADVICE_SCHEDULER  # noqa: E402


@pytest.fixture(autouse=True)
def reset_runtime_state():
    MATCH_MEMORY.reset()
    ADVICE_SCHEDULER.reset()
    COACH_SESSION_HISTORY.reset()
    _clear_demo_overlay_response()
    gsi_state._latest_raw_payload = None
    gsi_state._latest_normalized_state = None
    gsi_state._latest_timestamp = None
    gsi_state._previous_extra_context = None
    yield
    MATCH_MEMORY.reset()
    ADVICE_SCHEDULER.reset()
    COACH_SESSION_HISTORY.reset()
    _clear_demo_overlay_response()
    gsi_state._latest_raw_payload = None
    gsi_state._latest_normalized_state = None
    gsi_state._latest_timestamp = None
    gsi_state._previous_extra_context = None


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def repo_root() -> Path:
    return REPO_ROOT
