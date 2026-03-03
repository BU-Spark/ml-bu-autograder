# describe_content.py
import base64
import io
import json
import os
import time
from typing import Any, Dict, List

from PIL import Image
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()


def get_anthropic_client() -> Anthropic:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set. Export it first:\n"
            "  export ANTHROPIC_API_KEY='your_key_here'\n"
        )
    return Anthropic(api_key=api_key)


def _extract_first_text_block(response: Any) -> str:
    """
    Anthropic SDK returns a Message with a list of typed content blocks.
    Safely return the first non-empty text block.
    """
    blocks = getattr(response, "content", None) or []
    for block in blocks:
        if getattr(block, "type", None) == "text":
            text = getattr(block, "text", None)
            if text:
                return text
    raise RuntimeError("Claude response did not contain a text block")


def describe_diagram_with_claude(client: Anthropic, image_path: str, caption: str) -> str:
    """Describe a diagram/image"""
    image = Image.open(image_path).convert("RGB")

    buffered = io.BytesIO()
    image.save(buffered, format="PNG")
    image_b64 = base64.b64encode(buffered.getvalue()).decode()

    prompt = f"""
Analyze this diagram.

Caption: "{caption}"

Provide a comprehensive description including:
1. Type of diagram (flowchart, process diagram, etc.)
2. Main concept illustrated
3. Key components and labels
4. Flow or sequence
5. Relationships between elements

Be specific and detailed.
""".strip()

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {"type": "base64", "media_type": "image/png", "data": image_b64},
                    },
                    {"type": "text", "text": prompt},
                ],
            }
        ],
    )
    return _extract_first_text_block(response)


def describe_table_with_claude(client: Anthropic, table_text: str, page: Any) -> str:
    """Describe a table using Claude"""
    prompt = f"""
Analyze this table extracted from a document.

{table_text}

Provide a summary that includes:
1. What this table represents
2. Key data points or patterns
3. Column meanings and relationships
4. Any notable observations
5. Purpose of the table

Be concise but thorough.
""".strip()

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    return _extract_first_text_block(response)


def safe_write(path: str, content: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def process_all_content(metadata_path: str, output_dir: str) -> List[Dict[str, Any]]:
    """
    Process both tables and diagrams for ONE metadata file.
    Writes summaries to output_dir.
    """
    start_time = time.time()
    client = get_anthropic_client()
    os.makedirs(output_dir, exist_ok=True)

    with open(metadata_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    all_summaries: List[Dict[str, Any]] = []

    # Process tables
    print(f"\n{'='*60}")
    print(f"PROCESSING TABLES: {metadata_path}")
    print(f"{'='*60}")

    for table in metadata.get("tables", []):
        page = table.get("page")
        idx = table.get("index")
        print(f"\nTable {idx + 1} (Page {page})...")

        try:
            description = describe_table_with_claude(client, table["text"], page)

            summary = f"""TABLE SUMMARY:
Source PDF: {metadata.get('source_pdf')}
Page: {page}
Table Index: {idx}

Extracted Data:
{table['text']}

Description:
{description}

---
"""
            summary_path = os.path.join(output_dir, f"table_page{page}_idx{idx}_summary.txt")
            safe_write(summary_path, summary)
            print(f"✅ Saved to {summary_path}")

            all_summaries.append(
                {
                    "type": "table",
                    "source_pdf": metadata.get("source_pdf"),
                    "page": page,
                    "index": idx,
                    "summary_path": summary_path,
                    "description": description,
                }
            )

        except Exception as e:
            print(f"❌ Error describing table page {page} idx {idx}: {e}")

    # Process diagrams
    print(f"\n{'='*60}")
    print(f"PROCESSING DIAGRAMS: {metadata_path}")
    print(f"{'='*60}")

    for diagram in metadata.get("diagrams", []):
        page = diagram.get("page")
        idx = diagram.get("index")
        image_path = diagram.get("image_path")
        caption = diagram.get("caption", "No caption found")

        print(f"\nDiagram page {page}, index {idx}...")

        try:
            if not image_path or not os.path.exists(image_path):
                raise FileNotFoundError(f"Image not found at {image_path}")

            description = describe_diagram_with_claude(client, image_path, caption)

            summary = f"""DIAGRAM SUMMARY:
Source PDF: {metadata.get('source_pdf')}
Page: {page}
Diagram Index: {idx}
Caption: {caption}
Image Path: {image_path}

Description:
{description}

---
"""
            summary_path = os.path.join(output_dir, f"diagram_page{page}_idx{idx}_summary.txt")
            safe_write(summary_path, summary)
            print(f"✅ Saved to {summary_path}")

            all_summaries.append(
                {
                    "type": "diagram",
                    "source_pdf": metadata.get("source_pdf"),
                    "page": page,
                    "index": idx,
                    "summary_path": summary_path,
                    "description": description,
                    "image_path": image_path,
                    "caption": caption,
                }
            )

        except Exception as e:
            print(f"❌ Error describing diagram page {page} idx {idx}: {e}")

    # Save master index for this student
    index_path = os.path.join(output_dir, "summaries_index.json")
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(all_summaries, f, indent=2, ensure_ascii=False)

    total_tables = len(metadata.get("tables", []))
    total_diagrams = len(metadata.get("diagrams", []))
    total_api_calls = total_tables + total_diagrams

    elapsed = time.time() - start_time

    print(f"\n{'='*60}")
    print(f"✅ Processed {len(all_summaries)} items total")
    print(f"📊 Tables: {total_tables}, Diagrams: {total_diagrams}")
    print(f"⏱️  Total time: {elapsed:.2f} seconds ({elapsed/60:.2f} minutes)")
    print(f"🤖 API calls: {total_api_calls}")
    print(f"📋 Index saved to {index_path}")
    print(f"{'='*60}")

    return all_summaries


def default_output_dir_for_pdf(pdf_path: str) -> str:
    return os.path.splitext(os.path.basename(pdf_path))[0]


if __name__ == "__main__":
    PDF_PATHS = [
        "../data/Spring 2026/Assignment Examples Fall 2025 /Assignment 1_ Diagram & Text/Student 1 - Good Example/Student 1.pdf",
        "../data/Spring 2026/Assignment Examples Fall 2025 /Assignment 1_ Diagram & Text/Student 2 - Good Example/Student 2.pdf",
        "../data/Spring 2026/Assignment Examples Fall 2025 /Assignment 1_ Diagram & Text/Student 3 - Bad Example/Student 3.pdf",
    ]

    for pdf_path in PDF_PATHS:
        student_dir = default_output_dir_for_pdf(pdf_path)
        metadata_path = os.path.join(student_dir, "content_metadata.json")

        if not os.path.exists(metadata_path):
            print(f"\nMetadata not found for: {pdf_path}")
            print(f"   Expected: {metadata_path}")
            print("   Run extract_content.py first for this PDF.")
            continue

        summaries_out = os.path.join("content_summaries", student_dir)
        process_all_content(metadata_path, output_dir=summaries_out)