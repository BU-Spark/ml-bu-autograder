"""
blueprints/reports.py — /api/reports, /api/history, /api/export-csv, /api/status
"""
from __future__ import annotations

import csv
import io
import json
import re
from datetime import datetime
from pathlib import Path

from flask import Blueprint, Response, jsonify, send_file

from web.config import (
    DEFAULT_LECTURE_CHUNKS,
    OUTPUT_ROOT,
    REPORTS_DIR,
    REPORTS_INDEX,
)
from web.utils.pipeline import _embedding_provider, _shared_chroma_dir, _shared_chroma_ready

reports_bp = Blueprint("reports", __name__)


@reports_bp.route("/api/status")
def api_status():
    return jsonify({
        "lecture_chunks_exist": DEFAULT_LECTURE_CHUNKS.exists(),
        "shared_chroma_ready":  _shared_chroma_ready(),
        "shared_chroma_path":   str(_shared_chroma_dir()),
        "embedding_provider":   _embedding_provider(),
        "lecture_chunks_path":  str(DEFAULT_LECTURE_CHUNKS),
    })


@reports_bp.route("/api/history")
def api_history():
    runs: list[dict] = []
    if OUTPUT_ROOT.exists():
        for d in sorted(OUTPUT_ROOT.iterdir(), reverse=True):
            if d.is_dir() and d.name.startswith("web_"):
                gp = d / "grading" / "grades.json"
                if gp.exists():
                    try:
                        g     = json.loads(gp.read_text(encoding="utf-8"))
                        parts = d.name.split("_")
                        ts    = f"{parts[1]} {parts[2][:2]}:{parts[2][2:4]}:{parts[2][4:]}" if len(parts) >= 3 else d.name
                        runs.append({
                            "run_id":       d.name,
                            "student_file": g.get("student_file", "unknown"),
                            "score":        g.get("overall_score", 0),
                            "model":        g.get("grading_model", ""),
                            "timestamp":    ts,
                        })
                    except Exception:
                        pass
            if len(runs) >= 20:
                break
    return jsonify(runs)


@reports_bp.route("/api/export-csv")
def api_export_csv():
    rows: list[dict] = []
    if OUTPUT_ROOT.exists():
        for d in sorted(OUTPUT_ROOT.iterdir()):
            if not (d.is_dir() and d.name.startswith("web_")):
                continue
            gp = d / "grading" / "grades.json"
            if not gp.exists():
                continue
            try:
                g                = json.loads(gp.read_text(encoding="utf-8"))
                criterion_scores = g.get("criterion_scores", [])
                row: dict        = {
                    "run_id":           d.name,
                    "student_file":     g.get("student_file", ""),
                    "overall_score":    g.get("overall_score", ""),
                    "grading_model":    g.get("grading_model", ""),
                    "confidence":       g.get("confidence", ""),
                    "overall_feedback": g.get("overall_feedback", ""),
                }
                for cs in criterion_scores:
                    cid = cs.get("criterion_id", cs.get("criterion_name", "?"))
                    row[f"{cid}_awarded"] = cs.get("awarded_points", "")
                    row[f"{cid}_max"]     = cs.get("max_points", "")
                rows.append(row)
            except Exception:
                pass

    if not rows:
        return jsonify(success=False, error="No graded runs found to export."), 404

    fieldnames = list(rows[0].keys())
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


@reports_bp.route("/api/reports")
def api_reports():
    if not REPORTS_INDEX.exists():
        return jsonify(reports=[])
    try:
        index = json.loads(REPORTS_INDEX.read_text())
    except Exception:
        return jsonify(reports=[])
    valid = [e for e in index if (REPORTS_DIR / e["filename"]).exists()]
    return jsonify(reports=valid)


@reports_bp.route("/api/reports/<filename>")
def api_serve_report(filename):
    if not re.match(r"^[\w\-]+\.pdf$", filename):
        return "Invalid filename", 400
    path = REPORTS_DIR / filename
    if not path.exists():
        return "Report not found", 404
    return send_file(str(path), mimetype="application/pdf",
                     as_attachment=True, download_name=filename)
