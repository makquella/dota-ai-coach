"""
Packaged backend entry point for Wardly.

This module is intentionally small: it starts the existing FastAPI app without
changing recommendation, scheduler, parser, GSI, or overlay behavior.

The desktop launcher starts it hidden, passes the port via
``DOTA_AI_BACKEND_PORT`` and sets ``DOTA_AI_BACKEND_STDIN_CONTROL=1``. In that
mode the server shuts down gracefully when the launcher writes ``shutdown`` to
stdin or when stdin reaches EOF (the launcher exited or crashed), so the
launcher never has to force-kill the process tree.
"""

from __future__ import annotations

import contextlib
import os
import sys
import threading
from pathlib import Path
from typing import Any, TextIO

import uvicorn

STDIN_CONTROL_ENV = "DOTA_AI_BACKEND_STDIN_CONTROL"
SHUTDOWN_COMMANDS = {"shutdown", "quit", "exit"}


def _runtime_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def _stdin_control_enabled() -> bool:
    return os.environ.get(STDIN_CONTROL_ENV, "").strip().lower() in {"1", "true", "yes"}


def watch_stdin_for_shutdown(server: Any, stream: TextIO | None) -> None:
    """Block until ``stream`` sends a shutdown command or closes, then stop ``server``."""
    reason = "stdin closed"
    if stream is not None:
        try:
            for line in stream:
                if line.strip().lower() in SHUTDOWN_COMMANDS:
                    reason = "shutdown command"
                    break
        except (OSError, ValueError):
            reason = "stdin unavailable"
    # Stop first: if the launcher died, stdout is a broken pipe and printing can fail.
    server.should_exit = True
    _log(f"[backend] Graceful shutdown requested ({reason}).")


def _log(message: str) -> None:
    with contextlib.suppress(OSError, ValueError):
        print(message, flush=True)


def main() -> int:
    runtime_dir = _runtime_dir()
    if str(runtime_dir) not in sys.path:
        sys.path.insert(0, str(runtime_dir))

    os.environ.setdefault("USE_LLM", "false")
    os.environ.setdefault("SIMULATION_USE_LLM", "false")
    os.environ.setdefault("LIVE_CONSERVATIVE_MODE", "true")

    log_level = os.environ.get("DOTA_AI_BACKEND_LOG_LEVEL", "info")

    # Import the app object directly. Import-string loading is more fragile in
    # frozen PyInstaller builds and can make startup failures harder to see.
    from app.config import BACKEND_HOST, BACKEND_PORT, DATA_DIR, WRITABLE_DIR
    from app.main import app  # noqa: WPS433

    if BACKEND_HOST not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("Wardly backend must bind to a loopback address.")

    _log(f"[backend] Starting Wardly backend on http://{BACKEND_HOST}:{BACKEND_PORT}")
    _log(f"[backend] Runtime directory: {runtime_dir}")
    _log(f"[backend] Data directory: {DATA_DIR}")
    _log(f"[backend] Writable directory: {WRITABLE_DIR}")
    config = uvicorn.Config(
        app,
        host=BACKEND_HOST,
        port=BACKEND_PORT,
        access_log=False,
        proxy_headers=False,
        log_level=log_level,
        loop="asyncio",
        timeout_graceful_shutdown=3,
    )
    server = uvicorn.Server(config)
    if _stdin_control_enabled():
        threading.Thread(
            target=watch_stdin_for_shutdown,
            args=(server, sys.stdin),
            name="stdin-shutdown-watch",
            daemon=True,
        ).start()
    server.run()
    _log("[backend] Stopped.")
    return 0 if server.started else 1


if __name__ == "__main__":
    raise SystemExit(main())
