"""
Packaged backend entry point for Dota AI Coach.

This module is intentionally small: it starts the existing FastAPI app without
changing recommendation, scheduler, parser, GSI, or overlay behavior.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import uvicorn


def _runtime_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def main() -> int:
    runtime_dir = _runtime_dir()
    if str(runtime_dir) not in sys.path:
        sys.path.insert(0, str(runtime_dir))

    os.environ.setdefault("USE_LLM", "false")
    os.environ.setdefault("SIMULATION_USE_LLM", "false")
    os.environ.setdefault("LIVE_CONSERVATIVE_MODE", "true")

    host = os.environ.get("DOTA_AI_BACKEND_HOST", "127.0.0.1")
    port = int(os.environ.get("DOTA_AI_BACKEND_PORT", "8000"))
    log_level = os.environ.get("DOTA_AI_BACKEND_LOG_LEVEL", "info")

    # Import the app object directly. Import-string loading is more fragile in
    # frozen PyInstaller builds and can make startup failures harder to see.
    from app.main import app  # noqa: WPS433

    print(f"[backend] Starting Dota AI Coach backend on http://{host}:{port}", flush=True)
    print(f"[backend] Runtime directory: {runtime_dir}", flush=True)
    config = uvicorn.Config(
        app,
        host=host,
        port=port,
        access_log=False,
        log_level=log_level,
        loop="asyncio",
    )
    server = uvicorn.Server(config)
    server.run()
    if server.started and not server.should_exit:
        return 0
    return 0 if server.started else 1


if __name__ == "__main__":
    raise SystemExit(main())
