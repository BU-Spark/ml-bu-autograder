# extract_content.py
import fitz
from PIL import Image
import io
import os
import json
import camelot
import re
from typing import Any, Dict, List


def normalize_cell(s: Any) -> str:
    """Clean up cell text"""
    s = re.sub(r"\s+", " ", str(s)).strip()
    # Camelot sometimes emits "nan" as string-like values; normalize those.
    if s.lower() == "nan":
        return ""
    return s


def df_to_text(df, title="Table") -> str:
    """Convert dataframe to readable text for LLM"""
    if df is None or len(df) == 0:
        return f"TABLE: {title}\n\n(Empty table)\n"

    # Many Camelot tables come with header row embedded as row 0
    headers = [normalize_cell(h) for h in df.iloc[0].tolist()]
    rows_text = [f"TABLE: {title}\n"]
    rows_text.append("Columns: " + " | ".join(headers) + "\n")

    # Add rows
    for i in range(1, len(df)):
        row = [normalize_cell(x) for x in df.iloc[i].tolist()]

        # Skip empty rows
        if all(not c for c in row):
            continue

        rows_text.append(f"\nRow {i}:")
        for h, c in zip(headers, row):
            if not h or not c:
                continue
            rows_text.append(f"  {h}: {c}")

    return "\n".join(rows_text)


def extract_tables_from_pdf(pdf_path: str) -> List[Dict[str, Any]]:
    """Extract all tables from PDF using Camelot"""
    print(f"\nExtracting tables from {pdf_path}...")

    all_tables: List[Dict[str, Any]] = []

    try:
        # Try lattice method first (for tables with borders)
        tables = camelot.read_pdf(pdf_path, pages="all", flavor="lattice")

        if tables.n == 0:
            # Try stream method (for tables without borders)
            print("  No lattice tables found, trying stream method...")
            tables = camelot.read_pdf(pdf_path, pages="all", flavor="stream")

        print(f"  Found {tables.n} tables")

        for i, table in enumerate(tables):
            table_text = df_to_text(table.df, title=f"Table {i+1} (Page {table.page})")

            # Store dataframe as list-of-lists for JSON safety and portability
            df_as_rows = table.df.values.tolist()

            all_tables.append(
                {
                    "index": i,
                    "page": int(table.page) if str(table.page).isdigit() else table.page,
                    "text": table_text,
                    "rows": df_as_rows,
                }
            )

            print(f"  Extracted table {i+1} from page {table.page}")

    except Exception as e:
        print(f"Error extracting tables: {e}")

    return all_tables


def find_caption_near_image(page_blocks, img_rect, threshold=60) -> str:
    """
    Find text near image that looks like a caption.
    Uses a relaxed threshold and keyword heuristic.
    """
    captions = []

    img_x0, img_y0, img_x1, img_y1 = img_rect.x0, img_rect.y0, img_rect.x1, img_rect.y1

    for block in page_blocks:
        if len(block) < 5:
            continue

        x0, y0, x1, y1, text, *_ = block
        if not text or not str(text).strip():
            continue

        text_str = str(text).strip()
        if not text_str:
            continue

        # distance to image vertically (either below or above)
        vertical_distance = min(abs(y0 - img_y1), abs(img_y0 - y1))
        horizontal_overlap = not (x1 < img_x0 or img_x1 < x0)

        if vertical_distance < threshold and horizontal_overlap:
            low = text_str.lower()
            if any(kw in low for kw in ["figure", "fig.", "fig ", "diagram", "image", "workflow", "step"]):
                captions.append(text_str)

    return " ".join(captions) if captions else "No caption found"


def extract_diagrams_from_pdf(pdf_path: str, output_dir: str) -> List[Dict[str, Any]]:
    """Extract diagrams (images) from PDF"""
    print(f"\nExtracting diagrams from {pdf_path}...")

    os.makedirs(output_dir, exist_ok=True)
    doc = fitz.open(pdf_path)
    diagrams: List[Dict[str, Any]] = []

    for page_idx in range(len(doc)):
        page = doc[page_idx]
        images = page.get_images(full=True)
        if not images:
            continue

        # For caption detection
        page_blocks = page.get_text("blocks")

        for img_idx, image in enumerate(images):
            try:
                xref = image[0]
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]

                pil_image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

                # In some cases get_image_bbox can fail; guard it
                try:
                    img_rect = page.get_image_bbox(image)
                except Exception:
                    img_rect = None

                caption = "No caption found"
                position = None
                if img_rect is not None:
                    caption = find_caption_near_image(page_blocks, img_rect)
                    position = {"x0": img_rect.x0, "y0": img_rect.y0, "x1": img_rect.x1, "y1": img_rect.y1}

                img_filename = f"page{page_idx + 1}_img{img_idx}.png"
                img_path = os.path.join(output_dir, img_filename)
                pil_image.save(img_path)

                diagrams.append(
                    {
                        "page": page_idx + 1,
                        "index": img_idx,
                        "image_path": img_path,
                        "caption": caption,
                        "position": position,
                    }
                )

                print(f"  Extracted diagram from page {page_idx + 1} -> {img_filename}")

            except Exception as e:
                print(f"  Error on page {page_idx + 1}, image {img_idx}: {e}")
                continue

    doc.close()
    return diagrams


def extract_all_content(pdf_path: str, output_dir: str) -> Dict[str, Any]:
    """Extract both tables and diagrams from PDF"""
    print(f"\n{'='*60}")
    print(f"EXTRACTING ALL CONTENT FROM PDF")
    print(f"{'='*60}")

    os.makedirs(output_dir, exist_ok=True)

    tables = extract_tables_from_pdf(pdf_path)
    diagrams = extract_diagrams_from_pdf(pdf_path, output_dir)

    metadata = {
        "pdf_path": pdf_path,
        "output_dir": output_dir,
        "tables": tables,
        "diagrams": diagrams,
    }

    metadata_path = os.path.join(output_dir, "content_metadata.json")
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    print(f"\n{'='*60}")
    print(f"EXTRACTION COMPLETE")
    print(f"{'='*60}")
    print(f"Tables extracted: {len(tables)}")
    print(f"Diagrams extracted: {len(diagrams)}")
    print(f"Metadata saved to: {metadata_path}")

    return metadata


def default_output_dir_for_pdf(pdf_path: str) -> str:
    """Stable naming: folder name = PDF filename without extension"""
    return os.path.splitext(os.path.basename(pdf_path))[0]


if __name__ == "__main__":
    PDF_PATHS = [
        "../data/Spring 2026/Assignment Examples Fall 2025 /Assignment 1_ Diagram & Text/Student 1 - Good Example/Student 1.pdf",
        "../data/Spring 2026/Assignment Examples Fall 2025 /Assignment 1_ Diagram & Text/Student 2 - Good Example/Student 2.pdf",
        "../data/Spring 2026/Assignment Examples Fall 2025 /Assignment 1_ Diagram & Text/Student 3 - Bad Example/Student 3.pdf",
    ]

    for pdf_path in PDF_PATHS:
        out_dir = default_output_dir_for_pdf(pdf_path)
        extract_all_content(pdf_path, out_dir)