#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
import sys

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from core.config import load_environment, merged_config
from core.pipeline import run_compare, run_describe, run_extract


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Unified multimodal extraction pipeline")
    parser.add_argument("--mode", choices=["extract", "describe", "full", "compare"], required=True)

    parser.add_argument("--data-dir", help="Input root directory for extract/full")
    parser.add_argument("--output-root", default="outputs/final_phase1", help="Root output directory")
    parser.add_argument("--run-id", default=None, help="Run id; default timestamp")

    parser.add_argument("--extract-dir", help="Existing extract directory for describe mode")
    parser.add_argument("--describe-dir", help="Output directory for describe mode")

    parser.add_argument("--vision-provider", default="openai", choices=["none", "openai", "anthropic", "gemini"])
    parser.add_argument("--vision-model", default="gpt-4o-2024-11-20")
    parser.add_argument("--prompt-version", default="verbose_v2")

    parser.add_argument("--vector-db", default="none", choices=["none", "chroma"])
    parser.add_argument("--chroma-path", default="")
    parser.add_argument("--chroma-collection", default="phase1_chunks")
    parser.add_argument("--chroma-batch-size", type=int, default=100)

    parser.add_argument("--vision-input-cost-per-1m", type=float, default=0.0)
    parser.add_argument("--vision-output-cost-per-1m", type=float, default=0.0)

    parser.add_argument("--compare-summaries", nargs="*", default=[])

    # Config overrides
    parser.add_argument("--max-pdf-pages", type=int)
    parser.add_argument("--max-sheet-rows", type=int)
    parser.add_argument("--max-sheet-cols", type=int)
    parser.add_argument("--table-rows-per-chunk", type=int)
    parser.add_argument("--text-chunk-chars", type=int)
    parser.add_argument("--text-chunk-overlap", type=int)
    parser.add_argument("--min-text-chars", type=int)
    parser.add_argument("--image-large-pixels-threshold", type=int)
    parser.add_argument("--image-tile-target-max-pixels", type=int)
    parser.add_argument("--image-max-tiles", type=int)
    parser.add_argument("--vision-max-tokens", type=int)
    parser.add_argument("--vision-retry-max-tokens", type=int)
    parser.add_argument("--vision-max-visible-text-items", type=int)

    # friend-derived extraction heuristics
    parser.add_argument("--min-area", type=int)
    parser.add_argument("--min-side", type=int)
    parser.add_argument("--max-aspect-ratio", type=float)
    parser.add_argument("--min-aspect-ratio", type=float)
    parser.add_argument("--page-margin-pct", type=float)

    return parser.parse_args()


def default_run_id() -> str:
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def build_overrides(args: argparse.Namespace) -> dict[str, object]:
    override_keys = [
        "max_pdf_pages",
        "max_sheet_rows",
        "max_sheet_cols",
        "table_rows_per_chunk",
        "text_chunk_chars",
        "text_chunk_overlap",
        "min_text_chars",
        "image_large_pixels_threshold",
        "image_tile_target_max_pixels",
        "image_max_tiles",
        "vision_max_tokens",
        "vision_retry_max_tokens",
        "vision_max_visible_text_items",
        "min_area",
        "min_side",
        "max_aspect_ratio",
        "min_aspect_ratio",
        "page_margin_pct",
    ]
    out: dict[str, object] = {}
    for k in override_keys:
        out[k] = getattr(args, k)
    return out


def main() -> int:
    load_environment()
    args = parse_args()

    run_id = args.run_id or default_run_id()
    output_root = Path(args.output_root).expanduser().resolve()
    run_root = output_root / run_id

    cfg = merged_config(build_overrides(args))

    if args.mode == "extract":
        if not args.data_dir:
            raise SystemExit("--data-dir is required for extract mode")
        data_dir = Path(args.data_dir).expanduser().resolve()
        manifest = run_extract(data_dir=data_dir, run_root=run_root, cfg=cfg)
        print(f"Extract complete: {run_root / 'extract' / 'manifest.json'}")
        print(f"Processed files: {manifest.get('processed_file_count')} / {manifest.get('file_count')}")
        return 0

    if args.mode == "describe":
        extract_dir = Path(args.extract_dir).expanduser().resolve() if args.extract_dir else (run_root / "extract")
        describe_dir = (
            Path(args.describe_dir).expanduser().resolve()
            if args.describe_dir
            else run_root / f"describe_{args.vision_provider}_{args.vision_model}"
        )
        chroma_path = args.chroma_path or str(describe_dir / "chroma_db")
        summary = run_describe(
            extract_dir=extract_dir,
            describe_dir=describe_dir,
            cfg=cfg,
            vision_provider=args.vision_provider,
            vision_model=args.vision_model,
            prompt_version=args.prompt_version,
            vector_db=args.vector_db,
            chroma_path=chroma_path,
            chroma_collection=args.chroma_collection,
            chroma_batch_size=args.chroma_batch_size,
            vision_input_cost_per_1m=args.vision_input_cost_per_1m,
            vision_output_cost_per_1m=args.vision_output_cost_per_1m,
        )
        print(f"Describe complete: {describe_dir / 'summary.json'}")
        print(f"Generated chunks: {summary.get('chunk_count')}")
        return 0

    if args.mode == "full":
        if not args.data_dir:
            raise SystemExit("--data-dir is required for full mode")
        data_dir = Path(args.data_dir).expanduser().resolve()
        manifest = run_extract(data_dir=data_dir, run_root=run_root, cfg=cfg)
        extract_dir = run_root / "extract"
        describe_dir = run_root / f"describe_{args.vision_provider}_{args.vision_model}"
        chroma_path = args.chroma_path or str(describe_dir / "chroma_db")
        summary = run_describe(
            extract_dir=extract_dir,
            describe_dir=describe_dir,
            cfg=cfg,
            vision_provider=args.vision_provider,
            vision_model=args.vision_model,
            prompt_version=args.prompt_version,
            vector_db=args.vector_db,
            chroma_path=chroma_path,
            chroma_collection=args.chroma_collection,
            chroma_batch_size=args.chroma_batch_size,
            vision_input_cost_per_1m=args.vision_input_cost_per_1m,
            vision_output_cost_per_1m=args.vision_output_cost_per_1m,
        )
        print(f"Full run complete under: {run_root}")
        print(f"Extracted files: {manifest.get('processed_file_count')} / {manifest.get('file_count')}")
        print(f"Generated chunks: {summary.get('chunk_count')}")
        return 0

    if args.mode == "compare":
        if len(args.compare_summaries) < 2:
            raise SystemExit("--compare-summaries requires at least two summary.json paths")
        compare_inputs = [Path(p).expanduser().resolve() for p in args.compare_summaries]
        compare_dir = run_root / "comparison"
        run_compare(compare_inputs=compare_inputs, output_dir=compare_dir)
        print(f"Comparison written to: {compare_dir}")
        return 0

    raise SystemExit(f"Unsupported mode: {args.mode}")


if __name__ == "__main__":
    raise SystemExit(main())
