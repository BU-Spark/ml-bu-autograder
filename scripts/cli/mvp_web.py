#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RUN_PIPELINE = PROJECT_ROOT / "scripts" / "cli" / "run_pipeline.py"
DEFAULT_OUTPUT_ROOT = PROJECT_ROOT / "outputs" / "final_phase1"
DEFAULT_LECTURE_CHUNKS = (
    PROJECT_ROOT
    / "outputs"
    / "final_phase1"
    / "run_01"
    / "describe_openai_gpt-4o-2024-11-20_v2_semantic"
    / "chunks.jsonl"
)
DEFAULT_RUBRIC_ROOT = Path(
    os.getenv("AUTO_GRADER_RUBRIC_DIR", str(PROJECT_ROOT / "data" / "library" / "rubrics"))
)

MODEL_BY_PROVIDER = {
    "openai": "gpt-4o-2024-11-20",
    "gemini": "gemini-2.5-flash",
    "anthropic": "claude-sonnet-4-6",
}

NOISY_PATTERNS = [
    "Could not get FontBBox from font descriptor",
    "Data-loss while decompressing corrupted data",
]


def _style() -> None:
    st.markdown(
        """
<style>
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@400;600;700;800&family=Manrope:wght@400;600;700&display=swap');

:root {
  --bg0: #f2f6fb;
  --bg1: #e8f2ff;
  --ink: #13253f;
  --muted: #4f647f;
  --line: #d3e1f3;
  --card: #ffffff;
  --brand: #0ea5a0;
  --brand2: #f59e0b;
}

.stApp {
  background:
    radial-gradient(1200px 650px at 95% -20%, #d8f5f3 0%, rgba(216,245,243,0) 60%),
    radial-gradient(1200px 650px at -5% 10%, #dfe8ff 0%, rgba(223,232,255,0) 55%),
    linear-gradient(145deg, var(--bg0), var(--bg1));
}

h1, h2, h3, h4 { font-family: 'Sora', sans-serif; color: var(--ink); }
p, label, .stCaption, .stMarkdown, .stTextInput, .stSelectbox, .stFileUploader {
  font-family: 'Manrope', sans-serif;
  color: var(--ink);
}

.hero {
  border: 1px solid var(--line);
  border-radius: 20px;
  padding: 1.2rem 1.4rem;
  background: linear-gradient(135deg, rgba(14,165,160,.14), rgba(245,158,11,.12));
  box-shadow: 0 10px 30px rgba(22,53,86,.08);
}

.panel {
  border: 1px solid var(--line);
  border-radius: 16px;
  padding: 1rem 1rem;
  background: var(--card);
  box-shadow: 0 6px 18px rgba(22,53,86,.05);
}

.kpi {
  border: 1px solid var(--line);
  border-radius: 14px;
  background: #f8fbff;
  padding: .8rem .9rem;
}
</style>
""",
        unsafe_allow_html=True,
    )


def _discover_rubric_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    out: list[Path] = []
    for p in sorted(root.rglob("*")):
        if p.is_file() and p.suffix.lower() in {".pdf", ".docx", ".txt", ".md"}:
            out.append(p)
    return out


def _run_cmd(args: list[str], cwd: Path, extra_env: dict[str, str] | None = None) -> tuple[int, str]:
    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)
    proc = subprocess.run(
        args,
        cwd=str(cwd),
        env=env,
        text=True,
        capture_output=True,
    )
    out = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")
    return proc.returncode, out.strip()


def _sanitize_log(text: str) -> tuple[str, int]:
    lines = text.splitlines()
    clean_lines: list[str] = []
    removed = 0
    for line in lines:
        if any(pattern in line for pattern in NOISY_PATTERNS):
            removed += 1
            continue
        clean_lines.append(line)
    return "\n".join(clean_lines).strip(), removed


def _cli_base_args() -> list[str]:
    return [sys.executable, str(RUN_PIPELINE)]


def _load_grade(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _save_uploaded(uploaded_file, target_dir: Path) -> Path | None:
    if uploaded_file is None:
        return None
    target_dir.mkdir(parents=True, exist_ok=True)
    out = target_dir / uploaded_file.name
    out.write_bytes(uploaded_file.getbuffer())
    return out


def _safe_model_name(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]+", "_", name)


def main() -> None:
    st.set_page_config(page_title="AI Auto-Grader MVP", page_icon="AG", layout="wide")
    _style()

    st.markdown(
        """
<div class="hero">
  <h2 style="margin:0 0 .25rem 0;">AI Auto-Grader MVP</h2>
  <p style="margin:0;color:#274462;">
    Upload student submission + rubric + assignment, retrieve lecture context via RAG, and generate model-specific grading.
  </p>
</div>
""",
        unsafe_allow_html=True,
    )

    rubric_candidates = _discover_rubric_files(DEFAULT_RUBRIC_ROOT)
    candidate_labels = ["(none)"] + [str(p) for p in rubric_candidates]

    with st.sidebar:
        st.header("Pipeline Setup")
        output_root = Path(st.text_input("Output Root", str(DEFAULT_OUTPUT_ROOT))).expanduser().resolve()
        run_prefix = st.text_input("Run ID Prefix", "web_mvp")

        st.subheader("Model Selection")
        provider = st.selectbox("Provider", ["openai", "gemini", "anthropic"], index=0)
        model = st.text_input("Model", MODEL_BY_PROVIDER[provider])

        st.subheader("RAG Source")
        lecture_chunks = Path(st.text_input("Lecture Chunks JSONL", str(DEFAULT_LECTURE_CHUNKS))).expanduser().resolve()
        chroma_collection = st.text_input("Chroma Collection", "lecture_context_v1")
        retrieval_top_k = st.slider("Retrieval Top-K", 2, 12, 6, 1)
        always_reindex = st.checkbox("Always re-index lecture context per run", value=True)

        with st.expander("Optional Preselected Files"):
            selected_assignment = st.selectbox("Assignment file (from Spring 2026 2)", candidate_labels, index=0)
            selected_rubric = st.selectbox("Rubric file (from Spring 2026 2)", candidate_labels, index=0)

    c1, c2, c3 = st.columns([1.2, 1.2, 1])
    with c1:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.subheader("Student Submission")
        student_upload = st.file_uploader(
            "Upload Student Submission",
            type=["pdf", "xlsx"],
            key="student_submission",
            help="Supported formats: PDF (Assignment 1) and XLSX (Assignment 2).",
        )
        st.markdown("</div>", unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.subheader("Rubric + Assignment")
        rubric_upload = st.file_uploader("Upload Rubric", type=["txt", "md", "pdf", "docx"], key="rubric_file")
        assignment_upload = st.file_uploader("Upload Assignment", type=["txt", "md", "pdf", "docx"], key="assignment_file")
        st.caption("Uploaded files override preselected files in sidebar.")
        st.markdown("</div>", unsafe_allow_html=True)
    with c3:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.subheader("Execution")
        run_btn = st.button("Run Full Grading", type="primary", use_container_width=True)
        st.caption("Flow: extract -> describe -> index -> retrieve -> grade")
        st.markdown("</div>", unsafe_allow_html=True)

    if not run_btn:
        return

    if student_upload is None:
        st.error("Upload a student submission file (.pdf or .xlsx).")
        return
    if not lecture_chunks.exists():
        st.error(f"Lecture chunks file not found: {lecture_chunks}")
        return

    # Build run paths
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_id = f"{run_prefix}_{timestamp}"
    run_root = output_root / run_id
    upload_dir = run_root / "uploads"
    support_dir = run_root / "supporting_inputs"
    extract_dir = run_root / "extract"
    describe_dir = run_root / f"describe_student_{provider}_{_safe_model_name(model)}"
    retrieval_out = run_root / "retrieval.jsonl"
    chroma_path = run_root / "chroma_db"

    # Save uploads
    student_submission_path = _save_uploaded(student_upload, upload_dir)
    rubric_upload_path = _save_uploaded(rubric_upload, support_dir)
    assignment_upload_path = _save_uploaded(assignment_upload, support_dir)

    # Resolve rubric + assignment sources
    rubric_path: Path | None = rubric_upload_path
    if rubric_path is None and selected_rubric != "(none)":
        rubric_path = Path(selected_rubric)

    assignment_path: Path | None = assignment_upload_path
    if assignment_path is None and selected_assignment != "(none)":
        assignment_path = Path(selected_assignment)

    log_tab, results_tab, raw_tab = st.tabs(["Pipeline Logs", "Results", "Raw JSON"])
    with log_tab:
        log_box = st.empty()
        logs: list[str] = []

    def push_log(title: str, body: str) -> None:
        cleaned, removed = _sanitize_log(body)
        note = f"\n\n(filtered noisy lines: {removed})" if removed else ""
        with log_tab:
            logs.append(f"### {title}\n```\n{cleaned or body}\n```{note}")
            log_box.markdown("\n\n".join(logs))

    with st.status("Running pipeline...", expanded=True) as status:
        # 1) Extract student
        code, out = _run_cmd(
            _cli_base_args()
            + [
                "--mode", "extract",
                "--data-dir", str(upload_dir),
                "--output-root", str(output_root),
                "--run-id", run_id,
            ],
            cwd=PROJECT_ROOT,
        )
        push_log("Extract", out)
        if code != 0:
            status.update(label="Extract failed", state="error")
            st.error("Extract failed. Check logs.")
            return

        # 2) Describe student
        code, out = _run_cmd(
            _cli_base_args()
            + [
                "--mode", "describe",
                "--extract-dir", str(extract_dir),
                "--describe-dir", str(describe_dir),
                "--vision-provider", provider,
                "--vision-model", model,
                "--prompt-version", "verbose_v2",
            ],
            cwd=PROJECT_ROOT,
        )
        push_log("Describe", out)
        if code != 0:
            status.update(label="Describe failed", state="error")
            st.error("Describe failed. Check logs.")
            return

        # 3) Index lecture chunks for this run (isolated chroma db)
        if always_reindex or not chroma_path.exists():
            code, out = _run_cmd(
                _cli_base_args()
                + [
                    "--mode", "index",
                    "--chunks-jsonl", str(lecture_chunks),
                    "--output-root", str(output_root),
                    "--run-id", run_id,
                    "--chroma-path", str(chroma_path),
                    "--chroma-collection", chroma_collection,
                ],
                cwd=PROJECT_ROOT,
                # local embeddings by default to avoid OpenAI embedding permission failures
                extra_env={"CHROMA_USE_OPENAI_EMBEDDINGS": "0"},
            )
            push_log("Index Lecture Context", out)
            if code != 0:
                status.update(label="Index failed", state="error")
                st.error("Index failed. Check logs.")
                return

        # 4) Retrieve
        code, out = _run_cmd(
            _cli_base_args()
            + [
                "--mode", "retrieve",
                "--chunks-jsonl", str(describe_dir / "chunks.jsonl"),
                "--output-root", str(output_root),
                "--run-id", run_id,
                "--chroma-path", str(chroma_path),
                "--chroma-collection", chroma_collection,
                "--retrieval-top-k", str(retrieval_top_k),
                "--retrieval-out-jsonl", str(retrieval_out),
            ],
            cwd=PROJECT_ROOT,
            extra_env={"CHROMA_USE_OPENAI_EMBEDDINGS": "0"},
        )
        push_log("Retrieve", out)
        if code != 0:
            status.update(label="Retrieve failed", state="error")
            st.error("Retrieve failed. Check logs.")
            return

        # 5) Grade
        grade_args = _cli_base_args() + [
            "--mode", "grade",
            "--chunks-jsonl", str(describe_dir / "chunks.jsonl"),
            "--retrieval-out-jsonl", str(retrieval_out),
            "--output-root", str(output_root),
            "--run-id", run_id,
            "--grading-provider", provider,
            "--grading-model", model,
            "--student-path", student_submission_path.name if student_submission_path else student_upload.name,
        ]
        if assignment_path and assignment_path.exists():
            grade_args += ["--assignment-file", str(assignment_path)]
        if rubric_path and rubric_path.exists():
            grade_args += ["--rubric-file", str(rubric_path)]

        code, out = _run_cmd(grade_args, cwd=PROJECT_ROOT)
        push_log("Grade", out)
        if code != 0:
            status.update(label="Grade failed", state="error")
            st.error("Grade failed. Check logs.")
            return

        status.update(label="Completed", state="complete")

    grades_path = run_root / "grading" / "grades.json"
    if not grades_path.exists():
        st.error(f"grades.json not found: {grades_path}")
        return

    grade = _load_grade(grades_path)
    with results_tab:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        top_left, top_mid, top_right = st.columns([1, 1, 1.2])
        with top_left:
            st.markdown('<div class="kpi">', unsafe_allow_html=True)
            st.metric("Overall Score", f"{grade.get('overall_score', 0)} / 100")
            st.markdown("</div>", unsafe_allow_html=True)
        with top_mid:
            st.markdown('<div class="kpi">', unsafe_allow_html=True)
            st.metric("Model", str(grade.get("grading_model", model)))
            st.markdown("</div>", unsafe_allow_html=True)
        with top_right:
            st.markdown('<div class="kpi">', unsafe_allow_html=True)
            st.metric("Student File", str(grade.get("student_file", student_upload.name)))
            st.markdown("</div>", unsafe_allow_html=True)

        st.subheader("Overall Feedback")
        st.write(grade.get("overall_feedback", "No feedback generated."))

        breakdown = grade.get("score_breakdown", {}) or {}
        if breakdown:
            st.subheader("Score Breakdown")
            bcols = st.columns(len(breakdown))
            for idx, (k, v) in enumerate(breakdown.items()):
                with bcols[idx]:
                    st.metric(k.replace("_", " ").title(), f"{v}")

        caps = grade.get("policy_caps_applied", []) or []
        if caps:
            st.subheader("Policy Caps Applied")
            for cap in caps:
                st.write(f"- {cap}")

        details = grade.get("criterion_details", []) or []
        if details:
            st.subheader("Criterion Evidence")
            st.dataframe(
                [
                    {
                        "criterion_id": d.get("criterion_id"),
                        "criterion_name": d.get("criterion_name"),
                        "awarded_points": d.get("awarded_points"),
                        "max_points": d.get("max_points"),
                        "evidence_match_count": d.get("evidence_match_count"),
                    }
                    for d in details
                ],
                use_container_width=True,
                hide_index=True,
            )

        strengths = grade.get("strengths", []) or []
        gaps = grade.get("gaps", []) or []
        actions = grade.get("action_items", []) or []
        c1, c2, c3 = st.columns(3)
        with c1:
            st.subheader("Strengths")
            for item in strengths:
                st.write(f"- {item}")
        with c2:
            st.subheader("Gaps")
            for item in gaps:
                st.write(f"- {item}")
        with c3:
            st.subheader("Action Items")
            for item in actions:
                st.write(f"- {item}")
        st.markdown("</div>", unsafe_allow_html=True)

        st.success(f"Run complete: {run_root}")
        st.caption(f"Rubric used: {rubric_path if rubric_path else '(none)'}")
        st.caption(f"Assignment used: {assignment_path if assignment_path else '(none)'}")

    with raw_tab:
        st.json(grade)


if __name__ == "__main__":
    main()
