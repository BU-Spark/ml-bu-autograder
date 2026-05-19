"""
utils/pipeline.py — Subprocess runner and Chroma/embedding helpers.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from web.config import (
    DEFAULT_LECTURE_CHUNKS,
    OUTPUT_ROOT,
    PROJECT_ROOT,
    RUN_PIPELINE,
    SHARED_LECTURE_COLLECTION,
)


def _embedding_provider() -> str:
    """
    Resolve which embedding provider to use.

    Priority:
      1. CHROMA_EMBEDDING_PROVIDER env var (if the required API key is also present)
      2. Auto-detect from available API keys
      3. Fall back to local sentence-transformers (free, no key needed)
    """
    explicit = os.getenv("CHROMA_EMBEDDING_PROVIDER", "").strip().lower()

    # Validate that the requested provider actually has a key; fall back if not.
    if explicit == "google":
        if os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"):
            return "google"
        # Configured as google but no key → fall back silently
        explicit = ""
    if explicit == "openai":
        if os.getenv("OPENAI_API_KEY"):
            return "openai"
        explicit = ""
    if explicit == "default":
        return "default"

    # Auto-detect from whichever key is present
    if os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"):
        return "google"
    if os.getenv("OPENAI_API_KEY"):
        return "openai"

    # No API keys at all → local embeddings, always works
    return "default"


def _shared_chroma_dir() -> Path:
    return OUTPUT_ROOT / f"shared_lecture_chroma_{_embedding_provider()}"


def _embedding_env() -> dict[str, str]:
    return {"CHROMA_EMBEDDING_PROVIDER": _embedding_provider()}


def _adaptive_top_k() -> int:
    try:
        chunks_path = DEFAULT_LECTURE_CHUNKS
        if not chunks_path.exists():
            return 6
        count = sum(1 for line in chunks_path.read_text(encoding="utf-8").splitlines() if line.strip())
        if count <= 100:
            return 4
        if count <= 500:
            return 6
        return 8
    except Exception:
        return 6


def _shared_chroma_ready() -> bool:
    chroma_dir = _shared_chroma_dir()
    return chroma_dir.exists() and (chroma_dir / "chroma.sqlite3").exists()


def _run(args: list[str], extra_env: dict | None = None) -> tuple[int, str]:
    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)
    try:
        proc = subprocess.run(
            args,
            cwd=str(PROJECT_ROOT),
            env=env,
            text=True,
            capture_output=True,
            timeout=600,
        )
    except subprocess.TimeoutExpired:
        return 1, "Pipeline step timed out after 10 minutes."
    return proc.returncode, ((proc.stdout or "") + "\n" + (proc.stderr or "")).strip()


def _cli() -> list[str]:
    return [sys.executable, str(RUN_PIPELINE)]
