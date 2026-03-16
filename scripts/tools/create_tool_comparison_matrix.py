#!/usr/bin/env python3
"""
Create a structured matrix for comparing multiple AI tools on the same dataset.

This does not call cloud APIs directly. It prepares a consistent evaluation sheet
for manual testing (or later automation) across platforms.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

KIND_BY_EXTENSION = {
    ".xlsx": "excel",
    ".xlsm": "excel",
    ".xls": "excel",
    ".xlsb": "excel",
    ".csv": "csv",
    ".tsv": "csv",
    ".pdf": "pdf",
    ".png": "image",
    ".jpg": "image",
    ".jpeg": "image",
    ".bmp": "image",
    ".gif": "image",
    ".tif": "image",
    ".tiff": "image",
    ".docx": "docx",
    ".pptx": "pptx",
    ".txt": "text",
    ".md": "text",
    ".html": "text",
    ".htm": "text",
}


def guess_kind(path: Path) -> str:
    return KIND_BY_EXTENSION.get(path.suffix.lower(), "other")


def infer_data_bucket(relative_path: str, kind: str) -> str:
    low = relative_path.lower()

    # Project-specific naming patterns from your folder screenshots.
    if "lecture [pdf versions]" in low or "module" in low:
        return "lecture_material"
    if "lectures [html versions]" in low:
        return "lecture_material_html"
    if "assignment 2" in low or kind == "excel":
        return "assignment_excel"
    if "assignment 1" in low or "diagram" in low or kind == "image":
        return "assignment_diagram"
    if "slides [met eti]" in low:
        return "project_slides"
    if "student" in low:
        return "student_submission"
    return "other"


def rubric_for_kind(kind: str) -> str:
    if kind == "excel":
        return "Focus on formulas, tabular structure, and correctness extraction."
    if kind == "pdf":
        return "Focus on text + image interpretation and page-level completeness."
    if kind == "image":
        return "Focus on diagram/object interpretation and text in image."
    if kind in {"docx", "pptx", "text", "csv"}:
        return "Focus on text extraction quality and structure retention."
    return "Assess ingest, extraction quality, and relevance for grading/RAG."


def list_files(data_dir: Path) -> list[Path]:
    return sorted([p for p in data_dir.rglob("*") if p.is_file()])


def parse_tools(tools_arg: str) -> list[str]:
    raw = [t.strip() for t in tools_arg.split(",")]
    return [t for t in raw if t]


def write_matrix(
    matrix_path: Path,
    dataset_root: Path,
    files: list[Path],
    tools: list[str],
) -> dict[str, int]:
    fieldnames = [
        "tool",
        "file_path",
        "file_kind",
        "data_bucket",
        "file_size_kb",
        "ingest_success_0_1",
        "text_extraction_score_0_2",
        "image_understanding_score_0_2",
        "excel_structure_score_0_2",
        "rag_readiness_score_0_2",
        "grading_alignment_score_0_2",
        "hallucination_risk_score_0_2",
        "latency_seconds",
        "estimated_cost_usd",
        "overall_score_0_13",
        "notes",
        "rubric_hint",
    ]
    counts = Counter()

    with matrix_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for p in files:
            rel = str(p.relative_to(dataset_root))
            kind = guess_kind(p)
            bucket = infer_data_bucket(rel, kind)
            size_kb = round(p.stat().st_size / 1000.0, 2)
            hint = rubric_for_kind(kind)

            counts[f"kind::{kind}"] += 1
            counts[f"bucket::{bucket}"] += 1

            for tool in tools:
                writer.writerow(
                    {
                        "tool": tool,
                        "file_path": rel,
                        "file_kind": kind,
                        "data_bucket": bucket,
                        "file_size_kb": size_kb,
                        "ingest_success_0_1": "",
                        "text_extraction_score_0_2": "",
                        "image_understanding_score_0_2": "",
                        "excel_structure_score_0_2": "",
                        "rag_readiness_score_0_2": "",
                        "grading_alignment_score_0_2": "",
                        "hallucination_risk_score_0_2": "",
                        "latency_seconds": "",
                        "estimated_cost_usd": "",
                        "overall_score_0_13": "",
                        "notes": "",
                        "rubric_hint": hint,
                    }
                )
    return dict(counts)


def write_runbook(
    runbook_path: Path,
    dataset_root: Path,
    tools: list[str],
    total_files: int,
    stats: dict[str, int],
) -> None:
    lines: list[str] = []
    lines.append("# Tool Comparison Runbook")
    lines.append("")
    lines.append(f"- Dataset root: `{dataset_root}`")
    lines.append(f"- Total files: **{total_files}**")
    lines.append(f"- Tools in scope: **{', '.join(tools)}**")
    lines.append("")

    lines.append("## Objective")
    lines.append("")
    lines.append(
        "Compare AI tools on the same CS581 files to decide which platform best supports grading and RAG across Excel, PDF, and diagram/image submissions."
    )
    lines.append("")

    lines.append("## Scoring")
    lines.append("")
    lines.append("- `ingest_success_0_1`: 0 = failed upload/read, 1 = successful.")
    lines.append("- `text_extraction_score_0_2`: 0 = poor/missing, 1 = partial, 2 = accurate.")
    lines.append("- `image_understanding_score_0_2`: 0 = fails visuals, 1 = partial, 2 = strong.")
    lines.append("- `excel_structure_score_0_2`: 0 = misses sheet/formula/table logic, 1 = partial, 2 = strong.")
    lines.append("- `rag_readiness_score_0_2`: 0 = weak chunks/metadata, 1 = usable with fixes, 2 = strong.")
    lines.append("- `grading_alignment_score_0_2`: 0 = misaligned, 1 = somewhat aligned, 2 = strong alignment.")
    lines.append("- `hallucination_risk_score_0_2`: 0 = high risk, 1 = medium, 2 = low risk.")
    lines.append("- `overall_score_0_13`: sum of fields above.")
    lines.append("")

    lines.append("## Process")
    lines.append("")
    lines.append("1. Open `tool_comparison_matrix.csv` and filter one tool at a time.")
    lines.append("2. For each row, test the tool on the exact file and capture scores.")
    lines.append("3. Record latency and estimated cost where possible.")
    lines.append("4. Add concise notes for failure modes and surprises.")
    lines.append("5. Aggregate by `tool` and by `data_bucket` to pick a recommended platform.")
    lines.append("")

    lines.append("## Dataset Mix")
    lines.append("")
    lines.append("| Category | Count |")
    lines.append("|---|---:|")
    for k, v in sorted(stats.items()):
        lines.append(f"| {k} | {v} |")
    lines.append("")

    runbook_path.write_text("\n".join(lines), encoding="utf-8")


def write_metadata(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate tool comparison matrix CSV for multimodal grading evaluation.")
    parser.add_argument("--data-dir", required=True, help="Dataset root directory.")
    parser.add_argument("--output-dir", default="outputs/tool_comparison", help="Output directory.")
    parser.add_argument(
        "--tools",
        default="Azure AI Foundry,OpenAI,Gemini,Claude",
        help="Comma-separated tool names.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    data_dir = Path(args.data_dir).expanduser().resolve()
    out_dir = Path(args.output_dir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    if not data_dir.exists() or not data_dir.is_dir():
        raise SystemExit(f"Data directory not found or not a directory: {data_dir}")

    tools = parse_tools(args.tools)
    if not tools:
        raise SystemExit("No tools provided. Use --tools with at least one tool name.")

    files = list_files(data_dir)
    matrix_path = out_dir / "tool_comparison_matrix.csv"
    stats = write_matrix(matrix_path, data_dir, files, tools)

    runbook_path = out_dir / "tool_comparison_runbook.md"
    write_runbook(runbook_path, data_dir, tools, len(files), stats)

    metadata = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "dataset_root": str(data_dir),
        "file_count": len(files),
        "tools": tools,
        "outputs": {
            "matrix_csv": str(matrix_path),
            "runbook_md": str(runbook_path),
        },
        "stats": stats,
    }
    write_metadata(out_dir / "tool_comparison_metadata.json", metadata)

    print(f"Generated matrix: {matrix_path}")
    print(f"Generated runbook: {runbook_path}")
    print(f"Total files: {len(files)}")
    print(f"Tools: {', '.join(tools)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
