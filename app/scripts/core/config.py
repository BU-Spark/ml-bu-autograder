from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover
    load_dotenv = None


SUPPORTED_EXTENSIONS = {".pdf", ".pptx", ".xlsx", ".html", ".htm"}


DEFAULT_CONFIG: dict[str, Any] = {
    # PDF extraction backend — PyMuPDF is the right default for student assignment PDFs
    # (simple single-column text, fast). Set use_docling=True for course materials with
    # complex layouts (multi-column lab reports, slides with dense figures/tables).
    # Requires `pip install docling`. Can also be set via USE_DOCLING=true env var.
    "use_docling": False,
    # image filtering (friend)
    "min_area": 30_000,
    "min_side": 80,
    "max_aspect_ratio": 15.0,   # allow tall flowcharts and wide Gantt charts (was 8.0)
    "min_aspect_ratio": 0.067,  # 1:15 — very tall diagrams still accepted (was 0.1)
    "page_margin_pct": 0.07,
    # caption scoring (friend)
    "caption_vertical_window": 120,
    "caption_overlap_bonus": 50.0,
    "caption_below_bonus": 20.0,
    "caption_prefix_bonus": 35.0,
    "caption_regex_boost": 25.0,
    "caption_length_penalty_start": 120,
    "caption_length_penalty_scale": 15.0,
    "caption_max_length": 400,
    "caption_max_line_gap": 18,
    "caption_max_candidates": 2,
    "column_bins": 3,
    # tiling (sai)
    "image_large_pixels_threshold": 1_000_000,
    "image_tile_target_max_pixels": 1_000_000,
    "image_max_tiles": 9,
    # chunking (sai)
    "text_chunk_chars": 1800,
    "text_chunk_overlap": 140,
    "min_text_chars": 30,
    # vision (sai)
    "vision_max_tokens": 1800,
    "vision_retry_max_tokens": 2500,
    "vision_max_visible_text_items": 120,
    # OCR (sai)
    "ocr_word_threshold": 45,
    "ocr_char_threshold": 280,
    "ocr_min_confidence_for_scanned": 70.0,  # raised from 55% — rejects low-confidence gibberish
    # excel table chunking (sai)
    "table_rows_per_chunk": 35,
    # bounds
    "max_pdf_pages": 120,
    "max_sheet_rows": 600,
    "max_sheet_cols": 60,
}


@dataclass
class RunConfig:
    data_dir: str
    output_dir: str
    run_id: str
    mode: str
    vision_provider: str
    vision_model: str
    prompt_version: str = "verbose_v2"
    vector_db: str = "none"
    chroma_path: str = ""
    chroma_collection: str = "phase1_chunks"
    chroma_batch_size: int = 100
    vision_input_cost_per_1m: float = 0.0
    vision_output_cost_per_1m: float = 0.0


def load_environment() -> None:
    if load_dotenv is not None:
        load_dotenv()


def merged_config(overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    cfg = dict(DEFAULT_CONFIG)
    if overrides:
        cfg.update({k: v for k, v in overrides.items() if v is not None})
    return cfg


def get_api_key(provider: str) -> str | None:
    low = provider.lower()
    if low == "openai":
        return os.getenv("OPENAI_API_KEY")
    if low == "anthropic":
        return os.getenv("ANTHROPIC_API_KEY")
    if low == "gemini":
        return os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    return None
