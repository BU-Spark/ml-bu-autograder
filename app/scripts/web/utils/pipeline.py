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
    explicit = os.getenv("CHROMA_EMBEDDING_PROVIDER", "").strip().lower()
    if explicit in {"openai", "google", "default"}:
        return explicit
    if os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"):
        return "google"
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
