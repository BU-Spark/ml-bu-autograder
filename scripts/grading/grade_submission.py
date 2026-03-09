#!/usr/bin/env python3
"""
grade_submission.py — Grade a student submission using retrieved lecture context.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

# Allow `from core.config import ...` regardless of where the script is run from.
SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from core.config import get_api_key, load_environment


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------

def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_student_content(
    chunks_jsonl: Path,
    student_path_filter: str | None,
) -> tuple[str, list[dict[str, Any]]]:
    """
    Return (assembled_text, student_chunks) sorted by document_order.
    If student_path_filter is given, only include chunks whose source_path
    contains that substring (case-insensitive).
    """
    all_chunks = read_jsonl(chunks_jsonl)
    student_chunks = [
        c for c in all_chunks
        if str(c.get("metadata", {}).get("source_type", "")).lower() == "student"
    ]
    if student_path_filter:
        filt = student_path_filter.lower()
        student_chunks = [
            c for c in student_chunks
            if filt in str(c.get("metadata", {}).get("source_path", "")).lower()
        ]

    student_chunks.sort(
        key=lambda c: (
            c.get("metadata", {}).get("document_order", 9999),
            c.get("metadata", {}).get("sort_key", ""),
        )
    )

    parts: list[str] = []
    seen: set[str] = set()
    for c in student_chunks:
        text = str(c.get("content", "")).strip()
        if text and text not in seen:
            seen.add(text)
            parts.append(text)

    return "\n\n".join(parts), student_chunks


def load_lecture_context(
    retrieval_jsonl: Path,
    student_path_filter: str | None,
    max_chars: int,
) -> str:
    """
    Collect unique lecture snippets from retrieval_results.jsonl,
    ordered by how often they appear (most-retrieved first).
    """
    rows = read_jsonl(retrieval_jsonl)
    if student_path_filter:
        filt = student_path_filter.lower()
        rows = [
            r for r in rows
            if filt in str(r.get("student_source_path", "")).lower()
        ]

    # Count how often each lecture document appears across all student chunks.
    doc_counts: dict[str, int] = {}
    for row in rows:
        results = row.get("results", {})
        docs = results.get("documents", [[]])[0]
        for doc in docs:
            doc = str(doc).strip()
            if doc:
                doc_counts[doc] = doc_counts.get(doc, 0) + 1

    # Sort most-retrieved first, then assemble up to max_chars.
    ranked = sorted(doc_counts.items(), key=lambda x: -x[1])
    parts: list[str] = []
    total = 0
    for doc, _ in ranked:
        if total + len(doc) > max_chars:
            break
        parts.append(doc)
        total += len(doc)

    return "\n\n---\n\n".join(parts)


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You are an expert academic grader for a graduate-level Health Informatics course.
You will receive:
  1. LECTURE CONTEXT — key concepts from the course lectures relevant to this assignment.
  2. STUDENT SUBMISSION — the student's extracted answers/work.

Your job:
  - Identify each distinct question or section in the student's submission.
  - For each question/section, evaluate the student's answer against the lecture concepts and rubric.
  - Assign a score from 0 to 10 (10 = excellent, fully correct and complete).
  - Provide concise, constructive feedback explaining the score.
  - Compute an overall grade (average of per-question scores, scaled to 100).
  - Ground feedback in lecture evidence only.

Return ONLY valid JSON in this exact structure (no markdown, no extra text):
{
  "student_file": "<filename or 'unknown'>",
  "overall_score": <float 0-100>,
  "overall_feedback": "<1-3 sentence summary>",
  "questions": [
    {
      "question_id": "<Q1 / Section 1 / etc.>",
      "question_summary": "<brief description of what this question asks>",
      "student_answer_summary": "<what the student said in 1-2 sentences>",
      "score": <float 0-10>,
      "feedback": "<what was correct, what was missing or incorrect>",
      "evidence_refs": ["<short quoted lecture phrase or concept used as evidence>"],
      "confidence": <float 0-1>
    }
  ]
}
"""


def build_user_message(
    student_text: str,
    lecture_context: str,
    student_file: str,
    rubric_text: str,
    max_student_chars: int,
) -> str:
    student_excerpt = student_text[:max_student_chars]
    if len(student_text) > max_student_chars:
        student_excerpt += "\n\n[... content truncated ...]"

    return (
        f"STUDENT FILE: {student_file}\n\n"
        "=== RUBRIC ===\n"
        f"{rubric_text or '(No rubric provided)'}\n\n"
        "=== LECTURE CONTEXT ===\n"
        f"{lecture_context}\n\n"
        "=== STUDENT SUBMISSION ===\n"
        f"{student_excerpt}"
    )


def read_text_file(path: Path | None) -> str:
    if path is None:
        return ""
    if not path.exists() or not path.is_file():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore").strip()


# ---------------------------------------------------------------------------
# OpenAI API call
# ---------------------------------------------------------------------------

def call_openai(
    *,
    model: str,
    api_key: str,
    system: str,
    user: str,
) -> dict[str, Any]:
    try:
        import openai
    except ImportError as exc:
        raise RuntimeError("openai package not installed. Run: pip install openai") from exc

    client = openai.OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        max_tokens=2048,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        response_format={"type": "json_object"},
    )
    raw = response.choices[0].message.content.strip()

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        parsed = {"raw_response": raw, "parse_error": True}

    return {
        "result": parsed,
        "usage": {
            "input_tokens": response.usage.prompt_tokens,
            "output_tokens": response.usage.completion_tokens,
        },
        "model": response.model,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Grade a student submission via OpenAI")
    parser.add_argument("--retrieval-jsonl", required=True, help="Path to retrieval_results.jsonl")
    parser.add_argument("--chunks-jsonl", required=True, help="Path to chunks.jsonl")
    parser.add_argument(
        "--student-path",
        default=None,
        help="Substring to filter to a single student file (e.g. 'Student 1')",
    )
    parser.add_argument("--out-dir", default=None, help="Output directory (default: alongside retrieval-jsonl)")
    parser.add_argument("--model", default="gpt-4o-2024-11-20", help="OpenAI model to use")
    parser.add_argument("--max-lecture-chars", type=int, default=6000)
    parser.add_argument("--max-student-chars", type=int, default=8000)
    parser.add_argument(
        "--rubric-file",
        default=None,
        help="Optional rubric text file used to anchor scoring.",
    )
    return parser.parse_args()


def run_grading(
    *,
    retrieval_jsonl: Path,
    chunks_jsonl: Path,
    student_path_filter: str | None,
    out_dir: Path,
    model: str,
    max_lecture_chars: int,
    max_student_chars: int,
    rubric_file: Path | None = None,
) -> Path:
    api_key = get_api_key("openai")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set. Add it to your .env file.")

    if not retrieval_jsonl.exists():
        raise RuntimeError(f"retrieval_results.jsonl not found: {retrieval_jsonl}")
    if not chunks_jsonl.exists():
        raise RuntimeError(f"chunks.jsonl not found: {chunks_jsonl}")

    print(f"Loading student content from: {chunks_jsonl}")
    student_text, student_chunks = load_student_content(chunks_jsonl, student_path_filter)
    if not student_text:
        raise RuntimeError("No student content found. Check --student-path filter or chunks.jsonl.")

    # Determine the student filename for the report.
    student_file = "unknown"
    if student_chunks:
        student_file = student_chunks[0].get("metadata", {}).get("filename", "unknown")

    print(f"Student file: {student_file}  |  {len(student_text):,} chars  |  {len(student_chunks)} chunks")

    print(f"Loading lecture context from: {retrieval_jsonl}")
    lecture_context = load_lecture_context(retrieval_jsonl, student_path_filter, max_lecture_chars)
    print(f"Lecture context: {len(lecture_context):,} chars")

    if not lecture_context:
        print("WARNING: No lecture context found. Grading without lecture reference.")
        lecture_context = "(No lecture context available)"

    rubric_text = read_text_file(rubric_file)
    if rubric_file and not rubric_text:
        print(f"WARNING: rubric file not found/empty: {rubric_file}")

    user_msg = build_user_message(
        student_text=student_text,
        lecture_context=lecture_context,
        student_file=student_file,
        rubric_text=rubric_text,
        max_student_chars=max_student_chars,
    )

    print(f"Calling OpenAI ({model}) ...")
    response = call_openai(
        model=model,
        api_key=api_key,
        system=SYSTEM_PROMPT,
        user=user_msg,
    )

    usage = response["usage"]
    print(f"Tokens used — input: {usage['input_tokens']:,}  output: {usage['output_tokens']:,}")

    output = {
        "grading_model": response["model"],
        "student_path_filter": student_path_filter,
        "chunks_jsonl": str(chunks_jsonl),
        "retrieval_jsonl": str(retrieval_jsonl),
        "rubric_file": str(rubric_file) if rubric_file else None,
        "token_usage": usage,
        **response["result"],
    }

    out_path = out_dir / "grades.json"
    write_json(out_path, output)
    print(f"\nGrades written to: {out_path}")

    # Print a quick summary.
    result = response["result"]
    if not result.get("parse_error"):
        print(f"\nOverall score: {result.get('overall_score', 'N/A')} / 100")
        print(f"Overall feedback: {result.get('overall_feedback', '')}")
        questions = result.get("questions", [])
        if questions:
            print(f"\nPer-question breakdown ({len(questions)} questions):")
            for q in questions:
                print(f"  [{q.get('question_id')}] {q.get('score')}/10 — {q.get('feedback', '')[:80]}")
    else:
        print("\nWARNING: Could not parse JSON from OpenAI response. Raw output saved in grades.json.")

    return out_path


def main() -> int:
    load_environment()
    args = parse_args()

    retrieval_jsonl = Path(args.retrieval_jsonl).expanduser().resolve()
    chunks_jsonl = Path(args.chunks_jsonl).expanduser().resolve()
    out_dir = Path(args.out_dir).expanduser().resolve() if args.out_dir else retrieval_jsonl.parent
    rubric_file = Path(args.rubric_file).expanduser().resolve() if args.rubric_file else None

    run_grading(
        retrieval_jsonl=retrieval_jsonl,
        chunks_jsonl=chunks_jsonl,
        student_path_filter=args.student_path,
        out_dir=out_dir,
        model=args.model,
        max_lecture_chars=int(args.max_lecture_chars),
        max_student_chars=int(args.max_student_chars),
        rubric_file=rubric_file,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
