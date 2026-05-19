"""
utils/pdf_generator.py — PDF grade report generation using fpdf2.
"""
from __future__ import annotations

import json
import re
import traceback
from datetime import datetime
from pathlib import Path

from web.config import MAX_REPORTS, REPORTS_DIR, REPORTS_INDEX


def _safe_ascii(text: str) -> str:
    """Replace common Unicode chars so fpdf2 (latin-1) never raises encoding errors."""
    _UNICODE_MAP = {
        "\u2014": "--",   "\u2013": "-",    "\u2022": "*",
        "\u2019": "'",    "\u2018": "'",    "\u201c": '"',
        "\u201d": '"',    "\u2026": "...",  "\u00b7": "-",
        "\u00a9": "(c)",  "\u00ae": "(R)",  "\u2122": "(TM)",
        "\u2212": "-",    "\u00d7": "x",    "\u2265": ">=",
        "\u2264": "<=",   "\u2260": "!=",   "\u25b6": ">",
        "\u2192": "->",   "\u2190": "<-",
    }
    for ch, repl in _UNICODE_MAP.items():
        text = text.replace(ch, repl)
    return text.encode("latin-1", errors="replace").decode("latin-1")


def _generate_grade_pdf(grades: dict, run_id: str) -> Path | None:
    """Build PDF report. Returns saved Path or None — never raises."""
    try:
        from fpdf import FPDF
    except ImportError:
        return None
    try:
        return _build_grade_pdf(FPDF, grades, run_id)
    except Exception as exc:
        print(f"[PDF] generation failed (non-fatal): {exc}\n{traceback.format_exc()}")
        return None


def _build_grade_pdf(FPDF, grades: dict, run_id: str) -> Path | None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    student_raw = grades.get("student_file", "unknown")
    student     = re.sub(r"^[0-9a-f]{8}_", "", student_raw)
    score       = round(grades.get("overall_score", 0))
    total_max   = grades.get("total_max_points", 100) or 100
    feedback    = _safe_ascii(grades.get("overall_feedback", ""))
    criteria    = grades.get("criterion_details", [])
    section_cov = grades.get("section_coverage", [])
    ctx         = grades.get("_grading_context", {})

    def _score_rgb(s: float, mx: float = 100.0):
        pct = s / mx * 100 if mx else 0
        if pct >= 90: return (34, 197, 94)
        if pct >= 80: return (20, 184, 166)
        if pct >= 70: return (245, 158, 11)
        if pct >= 60: return (249, 115, 22)
        return (239, 68, 68)

    CRIT_COLORS = [
        (99, 102, 241), (16, 185, 129), (245, 158, 11),
        (239, 68, 68),  (20, 184, 166), (139, 92, 246),
        (236, 72, 153), (14, 165, 233),
    ]

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    def _cell(w, h, txt, **kw):
        pdf.set_x(pdf.l_margin)
        pdf.cell(w, h, _safe_ascii(str(txt)), **kw)
        pdf.ln(h)

    def _row(h, txt, **kw):
        pdf.set_x(pdf.l_margin)
        pdf.cell(0, h, _safe_ascii(str(txt)), **kw)
        pdf.ln(h)

    def _mcell(h, txt, **kw):
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(0, h, _safe_ascii(str(txt)), **kw)

    # Header band
    pdf.set_fill_color(30, 27, 75)
    pdf.rect(0, 0, 210, 32, "F")
    pdf.set_font("Helvetica", "B", 17)
    pdf.set_text_color(255, 255, 255)
    pdf.set_xy(12, 7)
    _row(10, "GradeAI Pro -- Grade Report")
    pdf.set_font("Helvetica", "", 9)
    pdf.set_xy(12, 20)
    pdf.cell(0, 7, _safe_ascii(
        f"Student: {student}   |   Run: {run_id}   |   {datetime.now().strftime('%B %d, %Y  %H:%M')}"
    ))
    pdf.set_text_color(0, 0, 0)
    pdf.ln(18)

    # Score hero
    sr, sg, sb = _score_rgb(score, total_max)
    pdf.set_fill_color(sr, sg, sb)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 38)
    pdf.cell(48, 22, str(score), fill=True, align="C")
    pdf.set_font("Helvetica", "", 13)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(20, 22, f"/ {int(total_max)}", align="L")
    pdf.ln(26)

    # Context row
    if ctx:
        pdf.set_fill_color(248, 249, 251)
        pdf.set_draw_color(226, 232, 240)
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(71, 85, 105)
        ctx_line = (
            f"Assignment: {ctx.get('assignment_file','?')}   |   "
            f"Rubric: {ctx.get('rubric_file','?')}   |   "
            f"Describe: {ctx.get('describe_provider','')}/{ctx.get('describe_model','')}   |   "
            f"Grade: {ctx.get('grade_provider','')}/{ctx.get('grade_model','')}"
        )
        _row(7, ctx_line, fill=True, border=1)
        pdf.ln(4)

    # Overall Feedback
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", "B", 11)
    _row(8, "Overall Feedback")
    pdf.set_font("Helvetica", "", 9)
    _mcell(5, feedback or "N/A")
    pdf.ln(4)

    # Section Coverage
    if section_cov:
        pdf.set_font("Helvetica", "B", 11)
        _row(8, "Section Coverage")
        pdf.set_font("Helvetica", "", 9)
        STATUS_COLORS = {"addressed": (34,197,94), "partial": (245,158,11), "missing": (239,68,68)}
        for s in section_cov:
            sid    = _safe_ascii(str(s.get("section_id", "")))
            status = str(s.get("status", "")).lower()
            cr, cg, cb = STATUS_COLORS.get(status, (148, 163, 184))
            pdf.set_fill_color(cr, cg, cb)
            pdf.set_text_color(255, 255, 255)
            pdf.cell(60, 6, f"  {sid}: {status}", fill=True, border=0)
            pdf.set_text_color(0, 0, 0)
            pdf.ln(7)
        pdf.ln(3)

    # Score Breakdown table
    if criteria:
        pdf.set_font("Helvetica", "B", 11)
        _row(8, "Score Breakdown")
        pdf.set_fill_color(30, 27, 75)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Helvetica", "B", 8.5)
        pdf.cell(105, 7, "  Criterion", fill=True, border=0)
        pdf.cell(25,  7, "Awarded",    fill=True, border=0, align="C")
        pdf.cell(20,  7, "Max",        fill=True, border=0, align="C")
        pdf.cell(40,  7, "Score %",    fill=True, border=0, align="C")
        pdf.ln(7)
        pdf.set_font("Helvetica", "", 8.5)
        for i, c in enumerate(criteria):
            awarded  = c.get("awarded_points", 0)
            max_pts  = c.get("max_points", 0)
            pct      = f"{round(awarded/max_pts*100)}%" if max_pts else "?"
            cname    = _safe_ascii(str(c.get("criterion_name", ""))[:52])
            row_fill = (248, 249, 251) if i % 2 == 0 else (255, 255, 255)
            pdf.set_fill_color(*row_fill)
            pdf.set_text_color(30, 41, 59)
            pdf.cell(105, 6, f"  {cname}", fill=True, border="B")
            pdf.cell(25,  6, str(awarded), fill=True, border="B", align="C")
            pdf.cell(20,  6, str(max_pts), fill=True, border="B", align="C")
            pdf.cell(40,  6, pct,          fill=True, border="B", align="C")
            pdf.ln(6)
        pdf.ln(6)

    # Criterion Evidence Details
    if criteria:
        pdf.set_font("Helvetica", "B", 11)
        _row(8, "Criterion Evidence Details")
        pdf.ln(2)
        for i, c in enumerate(criteria):
            cr, cg, cb = CRIT_COLORS[i % len(CRIT_COLORS)]
            pdf.set_fill_color(cr, cg, cb)
            pdf.set_text_color(255, 255, 255)
            pdf.set_font("Helvetica", "B", 9.5)
            cname   = _safe_ascii(str(c.get("criterion_name", ""))[:60])
            awarded = c.get("awarded_points", 0)
            max_pts = c.get("max_points", 0)
            _row(7, f"  {cname}   [{awarded} / {max_pts} pts]", fill=True)
            pdf.set_text_color(30, 41, 59)
            pdf.set_fill_color(250, 251, 252)
            just = str(c.get("justification", "")).strip()
            if just:
                pdf.set_font("Helvetica", "B", 8)
                _row(5, "  Justification:", fill=True)
                pdf.set_font("Helvetica", "", 8)
                _mcell(4.5, "    " + just, fill=True)
            evidence = [_safe_ascii(e) for e in (c.get("evidence_refs") or [])[:4] if e]
            if evidence:
                pdf.set_font("Helvetica", "B", 8)
                _row(5, "  Evidence:", fill=True)
                pdf.set_font("Helvetica", "", 8)
                for ev in evidence:
                    _mcell(4.5, f"    * {ev}", fill=True)
            missing = [_safe_ascii(m) for m in (c.get("missing_items") or [])[:4] if m]
            if missing:
                pdf.set_font("Helvetica", "B", 8)
                _row(5, "  Missing / Gaps:", fill=True)
                pdf.set_font("Helvetica", "", 8)
                for m in missing:
                    _mcell(4.5, f"    * {m}", fill=True)
            pdf.ln(4)

    # Footer
    pdf.set_y(-14)
    pdf.set_font("Helvetica", "I", 7.5)
    pdf.set_text_color(148, 163, 184)
    pdf.cell(0, 6, _safe_ascii(
        f"Generated by GradeAI Pro  |  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    ), align="C")

    # Save & update FIFO index
    safe_name    = re.sub(r"[^\w\-]", "_", student)[:40]
    pdf_filename = f"{run_id}_{safe_name}.pdf"
    pdf_path     = REPORTS_DIR / pdf_filename
    try:
        pdf.output(str(pdf_path))
    except Exception:
        return None

    try:
        index: list[dict] = json.loads(REPORTS_INDEX.read_text()) if REPORTS_INDEX.exists() else []
    except Exception:
        index = []

    index.insert(0, {
        "run_id":    run_id,
        "filename":  pdf_filename,
        "student":   student,
        "score":     score,
        "total_max": int(total_max),
        "timestamp": datetime.now().isoformat(),
    })
    while len(index) > MAX_REPORTS:
        old = index.pop()
        old_path = REPORTS_DIR / old["filename"]
        if old_path.exists():
            try:
                old_path.unlink()
            except Exception:
                pass

    REPORTS_INDEX.write_text(json.dumps(index, indent=2), encoding="utf-8")
    return pdf_path
