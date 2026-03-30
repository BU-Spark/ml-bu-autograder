#!/usr/bin/env python3
"""
Generate presentation-ready visuals from Phase 1 pipeline outputs.

Inputs:
- summary.json
- chunks.jsonl

Outputs (PNG files):
- chunk_type_distribution.png
- per_file_chunk_breakdown.png
- vision_pipeline_metrics.png
- sample_image_extraction_comparison.png
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    import matplotlib.pyplot as plt
except Exception as exc:  # pragma: no cover
    raise SystemExit(
        "matplotlib is required. Install with: pip install matplotlib (or pip install -r requirements.txt)"
    ) from exc

try:
    from PIL import Image
except Exception as exc:  # pragma: no cover
    raise SystemExit(
        "Pillow is required. Install with: pip install Pillow (or pip install -r requirements.txt)"
    ) from exc


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate visuals from phase1 summary/chunks.")
    parser.add_argument("--summary-json", required=True, help="Path to phase1 summary.json")
    parser.add_argument("--chunks-jsonl", required=True, help="Path to phase1 chunks.jsonl")
    parser.add_argument("--output-dir", required=True, help="Directory to write PNG files")
    parser.add_argument(
        "--max-text-preview-chars",
        type=int,
        default=1200,
        help="Max chars shown in sample extraction text panel.",
    )
    return parser.parse_args()


def safe_mkdir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def clean_text(text: str) -> str:
    return " ".join(str(text).replace("\x00", " ").split()).strip()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            rows.append(json.loads(line))
    return rows


def plot_chunk_type_distribution(summary: dict[str, Any], out_path: Path) -> None:
    counts = summary.get("counts_by_content_type", {})
    labels = list(counts.keys())
    values = [counts[k] for k in labels]

    plt.figure(figsize=(10, 5.5))
    bars = plt.bar(labels, values)
    plt.title("Chunk Type Distribution")
    plt.ylabel("Count")
    plt.xlabel("Content Type")
    for b, v in zip(bars, values):
        plt.text(b.get_x() + b.get_width() / 2, v + max(values) * 0.02 if values else 0, str(v), ha="center")
    plt.tight_layout()
    plt.savefig(out_path, dpi=160)
    plt.close()


def plot_per_file_breakdown(summary: dict[str, Any], out_path: Path) -> None:
    per_file = summary.get("per_file_stats", [])
    labels = [Path(x.get("source_path", "")).name for x in per_file]
    text_vals = [int(x.get("text_chunks", 0)) for x in per_file]
    table_vals = [int(x.get("table_chunks", 0)) for x in per_file]
    image_vals = [int(x.get("vision_chunks", 0)) + int(x.get("ocr_chunks", 0)) for x in per_file]

    x = list(range(len(labels)))
    plt.figure(figsize=(12, 6))
    plt.bar(x, text_vals, label="Text chunks")
    plt.bar(x, table_vals, bottom=text_vals, label="Table chunks")
    bottoms = [text_vals[i] + table_vals[i] for i in range(len(x))]
    plt.bar(x, image_vals, bottom=bottoms, label="Image chunks")
    plt.xticks(x, labels, rotation=20, ha="right")
    plt.ylabel("Chunk Count")
    plt.title("Per-File Chunk Breakdown")
    plt.legend()
    plt.tight_layout()
    plt.savefig(out_path, dpi=160)
    plt.close()


def plot_vision_metrics(summary: dict[str, Any], out_path: Path) -> None:
    vu = summary.get("vision_usage", {})
    metrics = {
        "images_extracted": int(vu.get("total_images_extracted", 0)),
        "images_routed": int(vu.get("total_images_sent_to_vision", 0)),
        "api_calls": int(vu.get("total_vision_api_calls", 0)),
        "calls_succeeded": int(vu.get("vision_calls_succeeded", 0)),
        "errors": int(vu.get("vision_errors", 0)),
        "tiled_images": int(vu.get("tiled_images", 0)),
        "json_fallbacks": int(vu.get("vision_json_fallbacks", 0)),
        "retries": int(vu.get("vision_retries", 0)),
    }
    labels = list(metrics.keys())
    values = list(metrics.values())

    plt.figure(figsize=(11, 6))
    bars = plt.barh(labels, values)
    plt.title("Vision Pipeline Metrics")
    plt.xlabel("Count")
    for b, v in zip(bars, values):
        plt.text(v + max(values) * 0.01 if values else 0, b.get_y() + b.get_height() / 2, str(v), va="center")
    plt.tight_layout()
    plt.savefig(out_path, dpi=160)
    plt.close()


def get_first_image_chunk(chunks: list[dict[str, Any]]) -> dict[str, Any] | None:
    for c in chunks:
        md = c.get("metadata", {})
        if md.get("content_type") == "image_description":
            return c
    return None


def plot_sample_extraction_comparison(
    sample_chunk: dict[str, Any] | None,
    out_path: Path,
    max_text_chars: int,
) -> None:
    if sample_chunk is None:
        plt.figure(figsize=(12, 6))
        plt.text(0.5, 0.5, "No image_description chunk found.", ha="center", va="center")
        plt.axis("off")
        plt.tight_layout()
        plt.savefig(out_path, dpi=160)
        plt.close()
        return

    md = sample_chunk.get("metadata", {})
    image_path = md.get("image_path")
    content = clean_text(sample_chunk.get("content", ""))[:max_text_chars]
    title = f"Sample Extraction: {md.get('filename', '')} (page {md.get('page', '')})"

    fig, axes = plt.subplots(1, 2, figsize=(16, 8))
    fig.suptitle(title, fontsize=14)

    if image_path and Path(image_path).exists():
        img = Image.open(image_path).convert("RGB")
        axes[0].imshow(img)
        axes[0].set_title("Original Extracted Image")
    else:
        axes[0].text(0.5, 0.5, "Image not found", ha="center", va="center")
    axes[0].axis("off")

    left_text = md.get("extracted_text") or "[no extracted_text]"
    desc = md.get("description") or "[no description]"
    panel = (
        "Extracted Text (from image):\n"
        + str(left_text)[: max_text_chars // 2]
        + "\n\nSummary:\n"
        + str(desc)[: max_text_chars // 2]
        + "\n\nChunk Content Preview:\n"
        + content[: max_text_chars // 3]
    )
    axes[1].text(0.01, 0.99, panel, ha="left", va="top", wrap=True, fontsize=10, family="monospace")
    axes[1].set_title("What AI Stored")
    axes[1].axis("off")

    plt.tight_layout()
    plt.savefig(out_path, dpi=160)
    plt.close()


def main() -> int:
    args = parse_args()
    summary_path = Path(args.summary_json).expanduser().resolve()
    chunks_path = Path(args.chunks_jsonl).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()

    if not summary_path.exists():
        raise SystemExit(f"Missing summary json: {summary_path}")
    if not chunks_path.exists():
        raise SystemExit(f"Missing chunks jsonl: {chunks_path}")

    safe_mkdir(output_dir)
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    chunks = load_jsonl(chunks_path)

    out1 = output_dir / "chunk_type_distribution.png"
    out2 = output_dir / "per_file_chunk_breakdown.png"
    out3 = output_dir / "vision_pipeline_metrics.png"
    out4 = output_dir / "sample_image_extraction_comparison.png"

    plot_chunk_type_distribution(summary, out1)
    plot_per_file_breakdown(summary, out2)
    plot_vision_metrics(summary, out3)
    plot_sample_extraction_comparison(get_first_image_chunk(chunks), out4, args.max_text_preview_chars)

    print("Generated visuals:")
    for p in (out1, out2, out3, out4):
        print(str(p))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

