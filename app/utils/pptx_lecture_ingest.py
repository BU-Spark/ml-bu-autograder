from pathlib import Path
import json
from .pptx_text_extractor import extract_pptx_to_chunks


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
    root = Path(root_dir)

    with open(output_index_path, "w", encoding="utf-8") as index_f:
        for pptx_path in root.rglob("*.pptx"):
            category = categorize_pptx(pptx_path)
            try:
                chunks = extract_pptx_to_chunks(
                    pptx_path,
                    course=course,
                    lecture_id=pptx_path.stem,
                )
            except Exception as exc:
                print(f"Skipping {pptx_path}: {exc}")
                continue

            for c in chunks:
                c["metadata"]["category"] = category
                c["metadata"]["abs_path"] = str(pptx_path)
                index_f.write(json.dumps(c, ensure_ascii=False) + "\n")

            print(f"Processed {pptx_path} as {category}")


if __name__ == "__main__":
    extract_and_categorize_all_pptx(
        "/Users/dereklee/Desktop/DS549/BU MET",
        "cs581_pptx_index.jsonl",
        course="CS 581",
    )
