"""
config.py — Paths, constants, and provider definitions for the web app.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# ── project paths ──────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR  = PROJECT_ROOT / "scripts"
RUN_PIPELINE = SCRIPTS_DIR / "cli" / "run_pipeline.py"
OUTPUT_ROOT  = PROJECT_ROOT / "outputs" / "final_phase1"

DEFAULT_LECTURE_CHUNKS = (
    OUTPUT_ROOT / "lecture_chunks_hybrid.jsonl"
)
DEFAULT_RUBRIC_DIR = Path(
    os.getenv("AUTO_GRADER_RUBRIC_DIR", str(PROJECT_ROOT / "data" / "library" / "rubrics"))
).expanduser()

# Library dirs — professor uploads here once; files persist across sessions
LIBRARY_DIR             = PROJECT_ROOT / "data" / "library"
LIBRARY_ASSIGNMENTS_DIR = LIBRARY_DIR / "assignments"
LIBRARY_QUIZZES_DIR     = LIBRARY_DIR / "quizzes"
LIBRARY_RUBRICS_DIR     = LIBRARY_DIR / "rubrics"
LIBRARY_LECTURES_DIR    = LIBRARY_DIR / "lectures"

# PDF reports
REPORTS_DIR   = PROJECT_ROOT / "data" / "reports"
REPORTS_INDEX = REPORTS_DIR / "index.json"
MAX_REPORTS   = 10

# Shared Chroma collection name
SHARED_LECTURE_COLLECTION = "lecture_v1"

# Allowed file extensions
STUDENT_ALLOWED_EXTS = {".pdf", ".pptx", ".xlsx"}
SUPPORT_ALLOWED_EXTS = {".docx", ".pdf", ".txt", ".md"}
RUBRIC_ALLOWED_EXTS  = SUPPORT_ALLOWED_EXTS | {".json"}

# ── provider config ────────────────────────────────────────────────────────
PROVIDERS = {
    "anthropic": {
        "label": "Anthropic Claude",
        "model": "claude-sonnet-4-6",
        "color": "#7c3aed",
        "icon":  "anthropic",
    },
    "openai": {
        "label": "OpenAI GPT-4o",
        "model": "gpt-4o-mini",
        "color": "#10a37f",
        "icon":  "openai",
    },
    "gemini": {
        "label": "Google Gemini",
        "model": "gemini-2.5-flash",
        "color": "#4285f4",
        "icon":  "gemini",
    },
}

PROVIDER_API_KEY_ENV = {
    "openai":    "OPENAI_API_KEY",
    "gemini":    "GEMINI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
}

# Load .env once at import time
load_dotenv(PROJECT_ROOT / ".env", override=True)
