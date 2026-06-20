"""
config.py — paths and global settings for the application.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Root of the repository (app/ -> backend/ -> dota-ai-coach/)
REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"

load_dotenv(BACKEND_DIR / ".env", override=False)
load_dotenv(REPO_ROOT / ".env", override=False)

# Where Markdown knowledge-base files live
KNOWLEDGE_BASE_DIR = REPO_ROOT / "data" / "knowledge_base"

# Where per-request log files are written
LOGS_DIR = Path(__file__).resolve().parents[1] / "logs"

# How many RAG paragraphs to return
RAG_TOP_K = 3

# Optional runtime LLM provider settings
USE_LLM = os.getenv("USE_LLM", "false").lower() == "true"
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "disabled").strip().lower()

try:
    LLM_TIMEOUT = max(1.0, min(float(os.getenv("LLM_TIMEOUT", "6")), 30.0))
except ValueError:
    LLM_TIMEOUT = 6.0

try:
    LLM_MAX_TOKENS = max(1, min(int(os.getenv("LLM_MAX_TOKENS", "350")), 2000))
except ValueError:
    LLM_MAX_TOKENS = 350

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b").strip()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openai/gpt-oss-120b:free").strip()

LLAMACPP_BASE_URL = os.getenv("LLAMACPP_BASE_URL", "http://127.0.0.1:8080").strip().rstrip("/")
LLAMACPP_MODEL = os.getenv("LLAMACPP_MODEL", "local-gpt-oss-20b").strip()

# Optional live GSI payload inspection. Raw samples can be noisy and should stay local.
GSI_DEBUG_LOG = os.getenv("GSI_DEBUG_LOG", "false").strip().lower() == "true"
GSI_DEBUG_SAMPLES_DIR = BACKEND_DIR / "gsi_debug_samples"

# Live Dota GSI readiness and recording.
LIVE_CONSERVATIVE_MODE = os.getenv("LIVE_CONSERVATIVE_MODE", "true").strip().lower() != "false"
try:
    GSI_STALE_SECONDS = max(1.0, float(os.getenv("GSI_STALE_SECONDS", "5")))
except ValueError:
    GSI_STALE_SECONDS = 5.0
SESSION_RECORDS_DIR = Path(os.getenv("SESSION_RECORDS_DIR", str(BACKEND_DIR / "session_records")))
