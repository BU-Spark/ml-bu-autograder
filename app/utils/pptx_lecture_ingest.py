from pathlib import Path
import argparse
import hashlib
import json

from .pptx_text_extractor import extract_pptx_to_chunks


def _lecture_id_from_path(course: str, resolved_path: Path) -> str:
    """Deterministic, collision-resistant ID from course + resolved path."""
    path_str = str(resolved_path)
    h = hashlib.sha256(path_str.encode()).hexdigest()[:16]
    safe_course = "".join(c if c.isalnum() else "_" for c in course).strip("_") or "course"
    return f"{safe_course}_{h}"


def categorize_pptx(path: Path) -> str:
    """Heuristic categorization based on folder/file names."""
    haystack = " / ".join(p.lower() for p in path.parts)

    if any(k in haystack for k in ("submission", "submissions", "student")):
        return "student_submission"
    if any(k in haystack for k in ("quiz", "assignment", "rubric")):
        return "assessment_material"
    if any(k in haystack for k in ("lecture", "slides", "presentation")):
        return "lecture"
    if "meeting" in haystack:
        return "meeting"
    return "other"


def extract_and_categorize_all_pptx(
    root_dir: str,
    output_index_path: str = "cs581_pptx_index.jsonl",
    course: str = "CS 581",
):
    root = Path(root_dir).resolve()

    with open(output_index_path, "w", encoding="utf-8") as index_f:
        for pptx_path in root.rglob("*.pptx"):
            resolved = pptx_path.resolve()
            lecture_id = _lecture_id_from_path(course, resolved)
            category = categorize_pptx(pptx_path)
            try:
                chunks = extract_pptx_to_chunks(
                    pptx_path,
                    course=course,
                    lecture_id=lecture_id,
                )
            except Exception as exc:
                print(f"Skipping {pptx_path}: {exc}")
                continue

            abs_path_str = str(resolved)
            for c in chunks:
                c["metadata"]["category"] = category
                c["metadata"]["abs_path"] = abs_path_str
                index_f.write(json.dumps(c, ensure_ascii=False) + "\n")

            print(f"Processed {pptx_path} as {category}")


def _parse_args():
    parser = argparse.ArgumentParser(
        description="Extract and categorize PPTX files to RAG-ready JSONL.",
    )
    parser.add_argument(
        "input_dir",
        nargs="?",
        default=".",
        help="Root directory to scan for .pptx files (default: current directory)",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="cs581_pptx_index.jsonl",
        dest="output_file",
        help="Output JSONL file path (default: cs581_pptx_index.jsonl)",
    )
    parser.add_argument(
        "-c",
        "--course",
        default="CS 581",
        help="Course label for metadata (default: CS 581)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    extract_and_categorize_all_pptx(
        root_dir=args.input_dir,
        output_index_path=args.output_file,
        course=args.course,
    )
