from pathlib import Path
import json
from pptx_text_extractor import extract_pptx_to_chunks


def categorize_pptx(path: Path) -> str:
    """Heuristic categorization based on folder/file names."""
    parts = [p.lower() for p in path.parts]
    name = path.name.lower()

    if "submission" in parts or "submissions" in parts or "student" in parts:
        return "student_submission"
    if "quiz" in parts or "assignment" in parts or "rubric" in parts:
        return "assessment_material"
    if "lecture" in parts or "slides" in parts or "presentation" in parts:
        return "lecture"
    if "meeting" in parts:
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
            chunks = extract_pptx_to_chunks(
                pptx_path,
                course=course,
                lecture_id=pptx_path.stem,
            )

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
