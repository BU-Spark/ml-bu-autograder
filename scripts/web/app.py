#!/usr/bin/env python3
"""
app.py  —  Flask web application for the AI Auto Grader.

Run:
    cd "Final AI Auto Grader"
    python scripts/web/app.py

Then open:  http://localhost:5000
"""
from __future__ import annotations

import csv
import io
import json
import os
import re
import subprocess
import sys
import uuid
from datetime import datetime
from pathlib import Path

from flask import Flask, render_template, request, jsonify, Response
from dotenv import load_dotenv
from werkzeug.utils import secure_filename

# ── project paths ──────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
RUN_PIPELINE = SCRIPTS_DIR / "cli" / "run_pipeline.py"
OUTPUT_ROOT = PROJECT_ROOT / "outputs" / "final_phase1"
DEFAULT_LECTURE_CHUNKS = (
    OUTPUT_ROOT
    / "run_01"
    / "describe_openai_gpt-4o-2024-11-20_v2_semantic"
    / "chunks.jsonl"
)
DEFAULT_ASSIGNMENT = PROJECT_ROOT / "assignments" / "assignment1_instructions.txt"
DEFAULT_RUBRIC_DIR = Path(
    os.getenv("AUTO_GRADER_RUBRIC_DIR", "/Users/sai/Downloads/Spring 2026 2/Assignment Rubrics")
).expanduser()

# Shared Chroma DB for lecture content — built once, reused across all grading runs.
# This avoids re-indexing lectures for every student submission.
SHARED_LECTURE_CHROMA = OUTPUT_ROOT / "shared_lecture_chroma"
SHARED_LECTURE_COLLECTION = "lecture_v1"

STUDENT_ALLOWED_EXTS = {".pdf", ".pptx", ".xlsx"}
SUPPORT_ALLOWED_EXTS = {".docx", ".pdf", ".txt", ".md"}

# Load environment from project .env so web app can access API keys without manual exports.
load_dotenv(PROJECT_ROOT / ".env")

# ── provider config ────────────────────────────────────────────────────────
PROVIDERS = {
    "openai": {
        "label": "OpenAI GPT-4o",
        "model": "gpt-4o-2024-11-20",
        "color": "#10a37f",
        "icon": "openai",
    },
    "gemini": {
        "label": "Google Gemini",
        "model": "gemini-2.5-flash",
        "color": "#4285f4",
        "icon": "gemini",
    },
    "anthropic": {
        "label": "Anthropic Claude",
        "model": "claude-sonnet-4-20250514",
        "color": "#7c3aed",
        "icon": "anthropic",
    },
}

PROVIDER_API_KEY_ENV = {
    "openai": "OPENAI_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
}


# ── Flask app ──────────────────────────────────────────────────────────────
app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 200 * 1024 * 1024  # 200 MB max


def _safe(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]+", "_", name)


def _is_allowed_ext(filename: str, allowed_exts: set[str]) -> bool:
    ext = Path(filename or "").suffix.lower()
    return ext in allowed_exts


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
            root_resolved = root.expanduser().resolve()
            p.relative_to(root_resolved)
            return p
        except Exception:
            continue
    return None


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


# ── Discover available rubric / assignment files ───────────────────────────
def _discover_files(root: Path, exts: set[str] | None = None) -> list[dict]:
    if not root.exists():
        return []
    exts = exts or {".pdf", ".docx", ".txt", ".md"}
    out: list[dict] = []
    for p in sorted(root.rglob("*")):
        if p.is_file() and p.suffix.lower() in exts and not p.name.startswith("~$"):
            out.append({"path": str(p), "name": p.name, "rel": str(p.relative_to(root))})
    return out


def _shared_chroma_ready() -> bool:
    """True if the shared lecture Chroma DB has been built and contains data."""
    chroma_sqlite = SHARED_LECTURE_CHROMA / "chroma.sqlite3"
    return SHARED_LECTURE_CHROMA.exists() and chroma_sqlite.exists()


# ── API routes ─────────────────────────────────────────────────────────────
@app.route("/")
def index():
    rubrics = _discover_files(DEFAULT_RUBRIC_DIR)
    assignments = _discover_files(PROJECT_ROOT / "assignments")
    return render_template(
        "index.html",
        providers=PROVIDERS,
        rubrics=rubrics,
        assignments=assignments,
        lecture_chunks_exist=DEFAULT_LECTURE_CHUNKS.exists(),
        shared_chroma_ready=_shared_chroma_ready(),
    )


@app.route("/api/providers")
def api_providers():
    return jsonify(PROVIDERS)


@app.route("/api/index-lectures", methods=["POST"])
def api_index_lectures():
    """Pre-index lecture chunks into the shared Chroma DB.
    Call this once before grading any students. Subsequent grading runs
    reuse this DB instead of rebuilding it from scratch every time.
    """
    if not DEFAULT_LECTURE_CHUNKS.exists():
        return jsonify(success=False, error=f"Lecture chunks not found at: {DEFAULT_LECTURE_CHUNKS}"), 404

    SHARED_LECTURE_CHROMA.mkdir(parents=True, exist_ok=True)
    code, out = _run(
        _cli() + [
            "--mode", "index",
            "--chunks-jsonl", str(DEFAULT_LECTURE_CHUNKS),
            "--chroma-path", str(SHARED_LECTURE_CHROMA),
            "--chroma-collection", SHARED_LECTURE_COLLECTION,
            "--output-root", str(OUTPUT_ROOT),
            "--run-id", "shared_lecture_index",
        ],
        extra_env={"CHROMA_USE_OPENAI_EMBEDDINGS": "0"},
    )
    if code != 0:
        return jsonify(success=False, error="Lecture indexing failed.", log=out[-3000:]), 500
    return jsonify(success=True, message="Lecture index built successfully.", log=out[-1000:])


@app.errorhandler(413)
def payload_too_large(_err):
    return jsonify(success=False, error="Uploaded file is too large (max 200 MB)."), 413


@app.route("/api/grade", methods=["POST"])
def api_grade():
    student = (
        request.files.get("student_pdf")
        or request.files.get("student_submission")
        or request.files.get("student_file")
    )
    if not student or not student.filename:
        return jsonify(success=False, error="Please upload a student submission file."), 400
    if not _is_allowed_ext(student.filename, STUDENT_ALLOWED_EXTS):
        return jsonify(success=False, error="Invalid student file type. Allowed: PDF, PPTX, XLSX."), 400

    rubric_file = request.files.get("rubric")
    assignment_file = request.files.get("assignment")
    if rubric_file and rubric_file.filename and not _is_allowed_ext(rubric_file.filename, SUPPORT_ALLOWED_EXTS):
        return jsonify(success=False, error="Invalid rubric file type. Allowed: DOCX, PDF, TXT, MD."), 400
    if assignment_file and assignment_file.filename and not _is_allowed_ext(assignment_file.filename, SUPPORT_ALLOWED_EXTS):
        return jsonify(success=False, error="Invalid assignment file type. Allowed: DOCX, PDF, TXT, MD."), 400

    provider = request.form.get("provider", "openai")
    model = request.form.get("model") or PROVIDERS.get(provider, {}).get("model", "gpt-4o-2024-11-20")

    key_env_name = PROVIDER_API_KEY_ENV.get(provider)
    if key_env_name and not os.getenv(key_env_name):
        return jsonify(
            success=False,
            error=f"{key_env_name} is not set. Add it to the project .env file or export it before starting Flask.",
        ), 400

    # Pre-selected files from dropdowns
    selected_rubric = request.form.get("selected_rubric", "")
    selected_assignment = request.form.get("selected_assignment", "")

    # ── create run directory ──
    run_id = f"web_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:4]}"
    run_root = OUTPUT_ROOT / run_id
    upload_dir = run_root / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)

    student_path = upload_dir / _safe_upload_name(student.filename)
    student.save(str(student_path))

    support_dir = run_root / "supporting"
    rubric_path = assignment_path = None

    # Uploaded rubric takes precedence over selected
    if rubric_file and rubric_file.filename:
        support_dir.mkdir(parents=True, exist_ok=True)
        rubric_path = support_dir / _safe_upload_name(rubric_file.filename)
        rubric_file.save(str(rubric_path))
    elif selected_rubric:
        rubric_path = _resolve_selected_path(
            selected_rubric,
            allowed_roots=[DEFAULT_RUBRIC_DIR, PROJECT_ROOT / "assignments"],
            allowed_exts=SUPPORT_ALLOWED_EXTS,
        )

    if assignment_file and assignment_file.filename:
        support_dir.mkdir(parents=True, exist_ok=True)
        assignment_path = support_dir / _safe_upload_name(assignment_file.filename)
        assignment_file.save(str(assignment_path))
    elif selected_assignment:
        assignment_path = _resolve_selected_path(
            selected_assignment,
            allowed_roots=[PROJECT_ROOT / "assignments", DEFAULT_RUBRIC_DIR],
            allowed_exts=SUPPORT_ALLOWED_EXTS,
        )
    elif DEFAULT_ASSIGNMENT.exists():
        assignment_path = DEFAULT_ASSIGNMENT

    safe_model = _safe(model)
    extract_dir = run_root / "extract"
    describe_dir = run_root / f"describe_student_{provider}_{safe_model}"
    retrieval_out = run_root / "retrieval.jsonl"

    # Use shared Chroma DB if it exists; otherwise fall back to per-run DB
    use_shared_chroma = _shared_chroma_ready() and DEFAULT_LECTURE_CHUNKS.exists()
    chroma_path = SHARED_LECTURE_CHROMA if use_shared_chroma else run_root / "chroma_db"

    steps: list[dict] = []

    # ── 1. Extract ──
    code, out = _run(
        _cli() + [
            "--mode", "extract",
            "--data-dir", str(upload_dir),
            "--output-root", str(OUTPUT_ROOT),
            "--run-id", run_id,
        ]
    )
    steps.append({"step": "Extract PDF", "ok": code == 0, "log": out[-2000:]})
    if code != 0:
        return jsonify(success=False, error="PDF extraction failed.", steps=steps, log=out[-1000:])

    # ── 2. Describe ──
    code, out = _run(
        _cli() + [
            "--mode", "describe",
            "--extract-dir", str(extract_dir),
            "--describe-dir", str(describe_dir),
            "--vision-provider", provider,
            "--vision-model", model,
            "--prompt-version", "verbose_v2",
        ]
    )
    steps.append({"step": "Analyze Content", "ok": code == 0, "log": out[-2000:]})
    if code != 0:
        return jsonify(success=False, error="Content analysis failed.", steps=steps, log=out[-1000:])

    # ── 3. Index lectures (only if shared DB not ready) ──
    has_lectures = DEFAULT_LECTURE_CHUNKS.exists()
    if has_lectures:
        if not use_shared_chroma:
            # No shared DB yet — build it now (also saves it as shared for future runs)
            SHARED_LECTURE_CHROMA.mkdir(parents=True, exist_ok=True)
            code, out = _run(
                _cli() + [
                    "--mode", "index",
                    "--chunks-jsonl", str(DEFAULT_LECTURE_CHUNKS),
                    "--output-root", str(OUTPUT_ROOT),
                    "--run-id", run_id,
                    "--chroma-path", str(SHARED_LECTURE_CHROMA),
                    "--chroma-collection", SHARED_LECTURE_COLLECTION,
                ],
                extra_env={"CHROMA_USE_OPENAI_EMBEDDINGS": "0"},
            )
            steps.append({"step": "Index Lectures", "ok": code == 0, "log": out[-2000:]})
            if code != 0:
                return jsonify(success=False, error="Lecture indexing failed.", steps=steps)
        else:
            steps.append({"step": "Index Lectures", "ok": True, "log": "Reusing shared lecture index (skipped rebuild)."})

        # ── 4. Retrieve ──
        code, out = _run(
            _cli() + [
                "--mode", "retrieve",
                "--chunks-jsonl", str(describe_dir / "chunks.jsonl"),
                "--output-root", str(OUTPUT_ROOT),
                "--run-id", run_id,
                "--chroma-path", str(chroma_path),
                "--chroma-collection", SHARED_LECTURE_COLLECTION,
                "--retrieval-top-k", "6",
                "--retrieval-out-jsonl", str(retrieval_out),
            ],
            extra_env={"CHROMA_USE_OPENAI_EMBEDDINGS": "0"},
        )
        steps.append({"step": "Retrieve Context", "ok": code == 0, "log": out[-2000:]})
        if code != 0:
            return jsonify(success=False, error="Context retrieval failed.", steps=steps)
    else:
        # No lectures — create empty retrieval file so grading can proceed
        retrieval_out.parent.mkdir(parents=True, exist_ok=True)
        retrieval_out.write_text("")
        steps.append({"step": "Lectures", "ok": True, "log": "No lecture chunks found; grading without RAG context."})

    # ── 5. Grade ──
    grade_args = _cli() + [
        "--mode", "grade",
        "--chunks-jsonl", str(describe_dir / "chunks.jsonl"),
        "--retrieval-out-jsonl", str(retrieval_out),
        "--output-root", str(OUTPUT_ROOT),
        "--run-id", run_id,
        "--grading-provider", provider,
        "--grading-model", model,
        "--student-path", student_path.name,
    ]
    if assignment_path and assignment_path.exists():
        grade_args += ["--assignment-file", str(assignment_path)]
    if rubric_path and rubric_path.exists():
        grade_args += ["--rubric-file", str(rubric_path)]

    code, out = _run(grade_args)
    steps.append({"step": "Grade Submission", "ok": code == 0, "log": out[-2000:]})
    if code != 0:
        return jsonify(success=False, error="Grading failed.", steps=steps, log=out[-1000:])

    # ── Load result ──
    grades_path = run_root / "grading" / "grades.json"
    if not grades_path.exists():
        return jsonify(success=False, error="grades.json not produced.", steps=steps)

    grades = json.loads(grades_path.read_text(encoding="utf-8"))
    return jsonify(success=True, grades=grades, run_id=run_id, steps=steps)


# ── History endpoint — list past runs ──────────────────────────────────────
@app.route("/api/history")
def api_history():
    runs: list[dict] = []
    if OUTPUT_ROOT.exists():
        for d in sorted(OUTPUT_ROOT.iterdir(), reverse=True):
            if d.is_dir() and d.name.startswith("web_"):
                gp = d / "grading" / "grades.json"
                if gp.exists():
                    try:
                        g = json.loads(gp.read_text(encoding="utf-8"))
                        # run_id format: web_YYYYMMDD_HHMMSS_xxxx
                        # Extract readable timestamp from dir name
                        parts = d.name.split("_")  # ['web', 'YYYYMMDD', 'HHMMSS', 'xxxx']
                        if len(parts) >= 3:
                            ts = f"{parts[1]} {parts[2][:2]}:{parts[2][2:4]}:{parts[2][4:]}"
                        else:
                            ts = d.name
                        runs.append({
                            "run_id": d.name,
                            "student_file": g.get("student_file", "unknown"),
                            "score": g.get("overall_score", 0),
                            "model": g.get("grading_model", ""),
                            "timestamp": ts,
                        })
                    except Exception:
                        pass
            if len(runs) >= 20:
                break
    return jsonify(runs)


# ── Export grades as CSV ────────────────────────────────────────────────────
@app.route("/api/export-csv")
def api_export_csv():
    """Export all graded runs as a CSV file for LMS submission."""
    rows: list[dict] = []
    if OUTPUT_ROOT.exists():
        for d in sorted(OUTPUT_ROOT.iterdir()):
            if not (d.is_dir() and d.name.startswith("web_")):
                continue
            gp = d / "grading" / "grades.json"
            if not gp.exists():
                continue
            try:
                g = json.loads(gp.read_text(encoding="utf-8"))
                criterion_scores = g.get("criterion_scores", [])
                row: dict = {
                    "run_id": d.name,
                    "student_file": g.get("student_file", ""),
                    "overall_score": g.get("overall_score", ""),
                    "grading_model": g.get("grading_model", ""),
                    "confidence": g.get("confidence", ""),
                    "overall_feedback": g.get("overall_feedback", ""),
                }
                for cs in criterion_scores:
                    cid = cs.get("criterion_id", cs.get("criterion_name", "?"))
                    row[f"{cid}_awarded"] = cs.get("awarded_points", "")
                    row[f"{cid}_max"] = cs.get("max_points", "")
                rows.append(row)
            except Exception:
                pass

    if not rows:
        return jsonify(success=False, error="No graded runs found to export."), 404

    # Build CSV in memory
    fieldnames = list(rows[0].keys())
    # Make sure all rows have same keys
    for r in rows[1:]:
        for k in r:
            if k not in fieldnames:
                fieldnames.append(k)

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)

    filename = f"grades_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# ── Status endpoint ─────────────────────────────────────────────────────────
@app.route("/api/status")
def api_status():
    return jsonify({
        "lecture_chunks_exist": DEFAULT_LECTURE_CHUNKS.exists(),
        "shared_chroma_ready": _shared_chroma_ready(),
        "shared_chroma_path": str(SHARED_LECTURE_CHROMA),
        "lecture_chunks_path": str(DEFAULT_LECTURE_CHUNKS),
    })


if __name__ == "__main__":
    print("\n  AI Auto Grader — Web Interface")
    print("  http://localhost:5000\n")
    debug = str(os.getenv("FLASK_DEBUG", "0")).strip().lower() in {"1", "true", "yes"}
    host = os.getenv("FLASK_HOST", "127.0.0.1")
    port = int(os.getenv("FLASK_PORT", "5000"))
    app.run(debug=debug, host=host, port=port)
