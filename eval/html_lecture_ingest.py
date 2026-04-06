"""
Extract and ingest HTML lecture files from 'Lectures [html versions]' directories.
Outputs RAG-ready JSONL with text chunks and metadata.
"""

from pathlib import Path
import argparse
import hashlib
import json
import re

try:
    from bs4 import BeautifulSoup
except ImportError:
    raise ImportError("Install beautifulsoup4: pip install beautifulsoup4")


LECTURE_HTML_DIR = "Lectures [html versions]"


def iter_lecture_html(root_dir: str):
    """Yield only HTML/HTM files under any 'Lectures [html versions]' directory."""
    root = Path(root_dir)
    for ext in ("*.html", "*.htm"):
        for html_path in root.rglob(ext):
            if LECTURE_HTML_DIR in html_path.parts:
                yield html_path


def _chunk_id_from_path(course: str, resolved_path: Path, chunk_idx: int) -> str:
    """Deterministic, collision-resistant ID for a chunk."""
    path_str = str(resolved_path)
    h = hashlib.sha256(path_str.encode()).hexdigest()[:12]
    safe_course = "".join(c if c.isalnum() else "_" for c in course).strip("_") or "course"
    return f"{safe_course}_{h}_chunk_{chunk_idx}"


def extract_text_from_html(html_path: Path) -> str:
    """Extract visible text from an HTML file."""
    with open(html_path, "r", encoding="utf-8", errors="replace") as f:
        soup = BeautifulSoup(f.read(), "html.parser")
    # Remove script/style
    for tag in soup(["script", "style"]):
        tag.decompose()
    text = soup.get_text(separator="\n", strip=True)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def chunk_by_semantic_sections(text: str, max_chunk_chars: int = 4000) -> list[str]:
    """
    Split text into chunks by paragraph/section boundaries.
    If a section exceeds max_chunk_chars, split it further.
    """
    sections = [s.strip() for s in text.split("\n\n") if s.strip()]
    chunks = []
    current = []
    current_len = 0

    for sec in sections:
        sec_len = len(sec) + 2  # +2 for \n\n
        if current_len + sec_len > max_chunk_chars and current:
            chunks.append("\n\n".join(current))
            current = []
            current_len = 0
        current.append(sec)
        current_len += sec_len

    if current:
        chunks.append("\n\n".join(current))
    return chunks


def extract_and_ingest_lecture_html(
    root_dir: str,
    output_path: str = "cs581_lecture_html_index.jsonl",
    course: str = "CS 581",
    max_chunk_chars: int = 4000,
):
    """Scan 'Lectures [html versions]' dirs, extract text, chunk, and write JSONL."""
    root = Path(root_dir).resolve()

    with open(output_path, "w", encoding="utf-8") as out_f:
        for html_path in iter_lecture_html(root):
            resolved = html_path.resolve()
            try:
                text = extract_text_from_html(html_path)
            except Exception as exc:
                print(f"Skipping {html_path}: {exc}")
                continue

            if not text.strip():
                print(f"Skipping {html_path}: no text extracted")
                continue

            chunks = chunk_by_semantic_sections(text, max_chunk_chars=max_chunk_chars)
            abs_path_str = str(resolved)

            for idx, chunk_text in enumerate(chunks):
                chunk_id = _chunk_id_from_path(course, resolved, idx)
                record = {
                    "id": chunk_id,
                    "text": chunk_text,
                    "metadata": {
                        "course": course,
                        "source_file": html_path.name,
                        "abs_path": abs_path_str,
                        "chunk_index": idx,
                        "total_chunks": len(chunks),
                        "source_type": "lecture_html",
                    },
                }
                out_f.write(json.dumps(record, ensure_ascii=False) + "\n")

            print(f"Processed {html_path} -> {len(chunks)} chunks")


def _parse_args():
    parser = argparse.ArgumentParser(
        description="Extract HTML lectures from 'Lectures [html versions]' to RAG-ready JSONL.",
    )
    parser.add_argument(
        "input_dir",
        nargs="?",
        default=".",
        help="Root directory to scan (default: current directory)",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="cs581_lecture_html_index.jsonl",
        dest="output_file",
        help="Output JSONL path (default: cs581_lecture_html_index.jsonl)",
    )
    parser.add_argument(
        "-c",
        "--course",
        default="CS 581",
        help="Course label (default: CS 581)",
    )
    parser.add_argument(
        "--max-chunk-chars",
        type=int,
        default=4000,
        help="Max characters per chunk (default: 4000)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    extract_and_ingest_lecture_html(
        root_dir=args.input_dir,
        output_path=args.output_file,
        course=args.course,
        max_chunk_chars=args.max_chunk_chars,
    )
