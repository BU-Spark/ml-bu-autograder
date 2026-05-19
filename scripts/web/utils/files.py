"""
utils/files.py — File validation, upload handling, and discovery helpers.
"""
from __future__ import annotations

import json
import re
import uuid
from pathlib import Path

from flask import request
from werkzeug.utils import secure_filename

from web.config import (
    DEFAULT_RUBRIC_DIR,
    LIBRARY_ASSIGNMENTS_DIR,
    LIBRARY_QUIZZES_DIR,
    LIBRARY_RUBRICS_DIR,
    PROJECT_ROOT,
    RUBRIC_ALLOWED_EXTS,
    SUPPORT_ALLOWED_EXTS,
)


def _safe(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]+", "_", name)


def _is_allowed_ext(filename: str, allowed_exts: set[str]) -> bool:
    return Path(filename or "").suffix.lower() in allowed_exts


def _safe_upload_name(filename: str) -> str:
    base = secure_filename(filename or "") or "upload.bin"
    return f"{uuid.uuid4().hex[:8]}_{base}"


def _resolve_selected_path(selected: str, *, allowed_roots: list[Path], allowed_exts: set[str]) -> Path | None:
    if not selected:
        return None
    try:
        p = Path(selected).expanduser().resolve()
    except Exception:
        return None
    if not p.exists() or not p.is_file():
        return None
    if p.suffix.lower() not in allowed_exts:
        return None
    for root in allowed_roots:
        try:
            p.relative_to(root.expanduser().resolve())
            return p
        except Exception:
            continue
    return None


def _resolve_project_file(selected: str, *, allowed_exts: set[str]) -> Path | None:
    if not selected:
        return None
    try:
        p = Path(selected).expanduser().resolve()
    except Exception:
        return None
    if not p.exists() or not p.is_file():
        return None
    if p.suffix.lower() not in allowed_exts:
        return None
    try:
        p.relative_to(PROJECT_ROOT.resolve())
    except Exception:
        return None
    return p


def _collect_supporting_files(run_root: Path) -> tuple[Path | None, Path | None, str | None]:
    rubric_file     = request.files.get("rubric")
    assignment_file = request.files.get("assignment")
    selected_rubric     = request.form.get("selected_rubric", "")
    selected_assignment = request.form.get("selected_assignment", "")

    if rubric_file and rubric_file.filename and not _is_allowed_ext(rubric_file.filename, RUBRIC_ALLOWED_EXTS):
        return None, None, "Invalid rubric file type. Allowed: DOCX, PDF, TXT, MD, JSON."
    if assignment_file and assignment_file.filename and not _is_allowed_ext(assignment_file.filename, SUPPORT_ALLOWED_EXTS):
        return None, None, "Invalid assignment file type. Allowed: DOCX, PDF, TXT, MD."

    support_dir   = run_root / "supporting"
    rubric_path   = None
    assignment_path = None

    generated_rubric_json = request.form.get("generated_rubric_json", "").strip()
    if generated_rubric_json:
        try:
            json.loads(generated_rubric_json)
        except Exception:
            return None, None, "generated_rubric_json is not valid JSON."
        support_dir.mkdir(parents=True, exist_ok=True)
        rubric_path = support_dir / "generated_rubric.json"
        rubric_path.write_text(generated_rubric_json, encoding="utf-8")
    elif rubric_file and rubric_file.filename:
        support_dir.mkdir(parents=True, exist_ok=True)
        rubric_path = support_dir / _safe_upload_name(rubric_file.filename)
        rubric_file.save(str(rubric_path))
    elif selected_rubric:
        rubric_path = _resolve_selected_path(
            selected_rubric,
            allowed_roots=[DEFAULT_RUBRIC_DIR, PROJECT_ROOT / "assignments",
                           LIBRARY_RUBRICS_DIR, LIBRARY_ASSIGNMENTS_DIR, LIBRARY_QUIZZES_DIR],
            allowed_exts=RUBRIC_ALLOWED_EXTS,
        )

    if assignment_file and assignment_file.filename:
        support_dir.mkdir(parents=True, exist_ok=True)
        assignment_path = support_dir / _safe_upload_name(assignment_file.filename)
        assignment_file.save(str(assignment_path))
    elif selected_assignment:
        assignment_path = _resolve_selected_path(
            selected_assignment,
            allowed_roots=[PROJECT_ROOT / "assignments", DEFAULT_RUBRIC_DIR,
                           LIBRARY_ASSIGNMENTS_DIR, LIBRARY_QUIZZES_DIR, LIBRARY_RUBRICS_DIR],
            allowed_exts=SUPPORT_ALLOWED_EXTS,
        )

    if not rubric_path:
        return None, None, (
            "No rubric selected. Please choose a rubric from the library "
            "or upload one before grading."
        )
    if not assignment_path:
        return None, None, (
            "No assignment description selected. Please choose an assignment "
            "from the library or upload one before grading."
        )

    return rubric_path, assignment_path, None


def _display_name(filename: str, kind: str = "description") -> str:
    stem = Path(filename).stem
    is_rubric = bool(re.search(r"(?i)rubric", stem))
    label = "Rubric" if (is_rubric or kind == "rubric") else "Description"
    m_a = re.match(r"(?i)assignment[_\-\s]*(\d+)", stem)
    if m_a:
        return f"Assignment - {m_a.group(1)} - {label}"
    m_q = re.match(r"(?i)quiz[_\-\s]*(\d+)", stem)
    if m_q:
        return f"Quiz - {m_q.group(1)} - {label}"
    name = re.sub(r"[-_]+", " ", stem).strip()
    return " ".join(w.capitalize() for w in name.split())


def _assignment_number(filename: str) -> str | None:
    m = re.match(r"(?i)assignment[_\-\s]*(\d+)", Path(filename).stem)
    return m.group(1) if m else None


def _quiz_number(filename: str) -> str | None:
    m = re.match(r"(?i)quiz[_\-\s]*(\d+)", Path(filename).stem)
    return m.group(1) if m else None


def _discover_files(root: Path, exts: set[str] | None = None, kind: str = "description") -> list[dict]:
    if not root.exists():
        return []
    exts = exts or {".pdf", ".docx", ".txt", ".md"}
    out: list[dict] = []
    for p in sorted(root.rglob("*")):
        if p.is_file() and p.suffix.lower() in exts and not p.name.startswith("~$"):
            out.append({
                "path":              str(p),
                "name":              p.name,
                "rel":               str(p.relative_to(root)),
                "display_name":      _display_name(p.name, kind=kind),
                "assignment_number": _assignment_number(p.name),
                "quiz_number":       _quiz_number(p.name),
            })
    return out
