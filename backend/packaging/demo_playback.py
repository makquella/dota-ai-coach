"""
Packaged replay-demo playback entry point.

This wraps scripts/run_overlay_demo.py so the Windows launcher can replay bundled
GSI-like JSONL files without requiring a Python venv.
"""

from __future__ import annotations

import sys
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from scripts.run_overlay_demo import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
