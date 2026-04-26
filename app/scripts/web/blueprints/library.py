"""
blueprints/library.py — /api/library/* (CRUD for assignments, quizzes, rubrics)
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from flask import Blueprint, jsonify, request

from web.config import (
    DEFAULT_RUBRIC_DIR,
    LIBRARY_ASSIGNMENTS_DIR,
    LIBRARY_QUIZZES_DIR,
    LIBRARY_RUBRICS_DIR,
    PROJECT_ROOT,
    RUBRIC_ALLOWED_EXTS,
    SUPPORT_ALLOWED_EXTS,
)
from web.utils.files import (
    _assignment_number,
    _discover_files,
    _display_name,
    _is_allowed_ext,
    _quiz_number,
)

library_bp = Blueprint("library", __name__)


@library_bp.route("/api/library/save-assignment", methods=["POST"])
def api_library_save_assignment():
    f = request.files.get("file")
    if not f or not f.filename:
        return jsonify(success=False, error="No file uploaded."), 400
    ext = Path(f.filename).suffix.lower()
    if ext not in SUPPORT_ALLOWED_EXTS:
        return jsonify(success=False, error=f"Invalid file type. Allowed: {', '.join(sorted(SUPPORT_ALLOWED_EXTS))}"), 400
    if not re.match(r"(?i)^assignment[_\-]?\d+\.", f.filename):
        return jsonify(success=False, error="Filename must follow: assignment_1.pdf, assignment_2.docx, etc."), 400
    num      = _assignment_number(f.filename)
    canonical = f"assignment_{num}{ext}"
    LIBRARY_ASSIGNMENTS_DIR.mkdir(parents=True, exist_ok=True)
    dest = LIBRARY_ASSIGNMENTS_DIR / canonical
    if dest.exists():
        return jsonify(success=False,
                       error=f"Assignment - {num} - Description already exists. Delete it first to replace."), 409
    f.save(str(dest))
    return jsonify(success=True,
                   display_name=_display_name(dest.name, kind="description"),
                   assignment_number=num, filename=dest.name, path=str(dest))


@library_bp.route("/api/library/save-quiz", methods=["POST"])
def api_library_save_quiz():
    f = request.files.get("file")
    if not f or not f.filename:
        return jsonify(success=False, error="No file uploaded."), 400
    ext = Path(f.filename).suffix.lower()
    if ext not in SUPPORT_ALLOWED_EXTS:
        return jsonify(success=False, error=f"Invalid file type. Allowed: {', '.join(sorted(SUPPORT_ALLOWED_EXTS))}"), 400
    if not re.match(r"(?i)^quiz[_\-]?\d+\.", f.filename):
        return jsonify(success=False, error="Filename must follow: quiz_1.pdf, quiz_2.docx, etc."), 400
    num      = _quiz_number(f.filename)
    canonical = f"quiz_{num}{ext}"
    LIBRARY_QUIZZES_DIR.mkdir(parents=True, exist_ok=True)
    dest = LIBRARY_QUIZZES_DIR / canonical
    if dest.exists():
        return jsonify(success=False,
                       error=f"Quiz - {num} - Description already exists. Delete it first to replace."), 409
    f.save(str(dest))
    return jsonify(success=True,
                   display_name=_display_name(dest.name, kind="description"),
                   quiz_number=num, filename=dest.name, path=str(dest))


@library_bp.route("/api/library/save-rubric", methods=["POST"])
def api_library_save_rubric():
    f = request.files.get("file")
    if not f or not f.filename:
        return jsonify(success=False, error="No file uploaded."), 400
    ext = Path(f.filename).suffix.lower()
    if ext not in RUBRIC_ALLOWED_EXTS:
        return jsonify(success=False, error=f"Invalid file type. Allowed: {', '.join(sorted(RUBRIC_ALLOWED_EXTS))}"), 400
    num = _assignment_number(f.filename)
    if num:
        canonical = f"assignment_{num}_rubric{ext}"
    elif (qnum := _quiz_number(f.filename)):
        canonical = f"quiz_{qnum}_rubric{ext}"
    else:
        safe      = re.sub(r"[^\w\-]", "_", Path(f.filename).stem).strip("_") or "rubric"
        canonical = f"{safe}{ext}"
    LIBRARY_RUBRICS_DIR.mkdir(parents=True, exist_ok=True)
    dest = LIBRARY_RUBRICS_DIR / canonical
    if dest.exists():
        return jsonify(success=False,
                       error=f"'{_display_name(canonical, kind='rubric')}' already exists. Delete it first."), 409
    f.save(str(dest))
    return jsonify(success=True,
                   display_name=_display_name(dest.name, kind="rubric"),
                   assignment_number=num, filename=dest.name, path=str(dest))


@library_bp.route("/api/library/delete", methods=["POST"])
def api_library_delete():
    data      = request.get_json(force=True, silent=True) or {}
    file_type = data.get("type", "")
    filename  = data.get("filename", "")
    if not filename or ".." in filename or "/" in filename or "\\" in filename:
        return jsonify(success=False, error="Invalid filename."), 400
    if file_type == "assignment":
        path = LIBRARY_ASSIGNMENTS_DIR / filename
    elif file_type == "quiz":
        path = LIBRARY_QUIZZES_DIR / filename
    elif file_type == "rubric":
        path = LIBRARY_RUBRICS_DIR / filename
    else:
        return jsonify(success=False, error="Unknown type. Use 'assignment', 'quiz', or 'rubric'."), 400
    if not path.exists():
        return jsonify(success=False, error="File not found."), 404
    path.unlink()
    return jsonify(success=True)


@library_bp.route("/api/library/list")
def api_library_list():
    rubrics = (
        _discover_files(DEFAULT_RUBRIC_DIR, kind="rubric") +
        _discover_files(LIBRARY_RUBRICS_DIR, exts=RUBRIC_ALLOWED_EXTS, kind="rubric")
    )
    assignments = (
        _discover_files(PROJECT_ROOT / "assignments") +
        _discover_files(LIBRARY_ASSIGNMENTS_DIR)
    )
    quizzes = _discover_files(LIBRARY_QUIZZES_DIR)
    return jsonify(rubrics=rubrics, assignments=assignments, quizzes=quizzes)


@library_bp.route("/api/library/preview")
def api_library_preview():
    file_type = request.args.get("type", "")
    filename  = request.args.get("filename", "")
    if not filename or ".." in filename or "/" in filename or "\\" in filename:
        return jsonify(success=False, error="Invalid filename."), 400
    if file_type == "rubric":
        path = LIBRARY_RUBRICS_DIR / filename
    elif file_type == "assignment":
        path = LIBRARY_ASSIGNMENTS_DIR / filename
    elif file_type == "quiz":
        path = LIBRARY_QUIZZES_DIR / filename
    else:
        return jsonify(success=False, error="Unknown type. Use 'rubric', 'assignment', or 'quiz'."), 400
    if not path.exists():
        return jsonify(success=False, error="File not found in library."), 404

    ext = path.suffix.lower()
    if ext == ".json":
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return jsonify(success=True, content_type="json", data=data)
        except Exception as e:
            return jsonify(success=False, error=f"Invalid JSON: {e}"), 400
    elif ext in {".txt", ".md"}:
        return jsonify(success=True, content_type="text",
                       preview=path.read_text(encoding="utf-8", errors="ignore")[:4000])
    elif ext == ".docx":
        try:
            from docx import Document as _DocxDoc
            doc   = _DocxDoc(str(path))
            parts = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
            for table in doc.tables:
                for row in table.rows:
                    cells = [c.text.strip() for c in row.cells if c.text.strip()]
                    if cells:
                        parts.append(" | ".join(cells))
            return jsonify(success=True, content_type="text", preview="\n".join(parts)[:4000])
        except Exception as e:
            return jsonify(success=True, content_type="binary", preview=f"DOCX preview unavailable: {e}")
    elif ext == ".pdf":
        try:
            import fitz as _fitz
            doc  = _fitz.open(str(path))
            text = "\n\n".join(page.get_text() for page in doc).strip()
            return jsonify(success=True, content_type="text", preview=text[:4000])
        except Exception:
            try:
                from pypdf import PdfReader as _PdfReader
                reader = _PdfReader(str(path))
                text   = "\n\n".join((page.extract_text() or "").strip() for page in reader.pages).strip()
                return jsonify(success=True, content_type="text", preview=text[:4000])
            except Exception as e2:
                return jsonify(success=True, content_type="binary", preview=f"PDF preview unavailable: {e2}")
    return jsonify(success=True, content_type="binary",
                   preview=f"Inline preview is not available for {ext} files.")
