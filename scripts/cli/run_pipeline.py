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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Unified multimodal extraction pipeline")
    parser.add_argument(
        "--mode",
        choices=["extract", "describe", "full", "compare", "index", "retrieve", "grade"],
        required=True,
    )

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

    # Vector DB utilities
    parser.add_argument("--chunks-jsonl", help="Path to chunks.jsonl for index/retrieve/grade modes")
    parser.add_argument("--retrieval-out-jsonl", default="outputs/retrieval_results.jsonl")
    parser.add_argument("--retrieval-top-k", type=int, default=6)
    parser.add_argument("--student-path", default=None, help="Filter to one student source path substring")
    parser.add_argument("--rubric-file", default=None, help="Optional rubric text file for grading")
    parser.add_argument("--assignment-file", default=None, help="Text file with the actual assignment instructions/questions for grading")
    parser.add_argument("--grading-provider", default="openai", choices=["openai", "gemini", "anthropic"],
                        help="LLM provider for grading (openai, gemini, anthropic)")
    parser.add_argument("--grading-model", default=None, help="Model name for grading (default: provider default)")
    parser.add_argument("--max-lecture-chars", type=int, default=12000)
    parser.add_argument("--max-student-chars", type=int, default=20000)

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
        from core.pipeline import run_extract

        if not args.data_dir:
            raise SystemExit("--data-dir is required for extract mode")
        data_dir = Path(args.data_dir).expanduser().resolve()
        manifest = run_extract(data_dir=data_dir, run_root=run_root, cfg=cfg)
        print(f"Extract complete: {run_root / 'extract' / 'manifest.json'}")
        print(f"Processed files: {manifest.get('processed_file_count')} / {manifest.get('file_count')}")
        return 0

    if args.mode == "describe":
        from core.pipeline import run_describe

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
        from core.pipeline import run_describe, run_extract

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
        from core.pipeline import run_compare

        if len(args.compare_summaries) < 2:
            raise SystemExit("--compare-summaries requires at least two summary.json paths")
        compare_inputs = [Path(p).expanduser().resolve() for p in args.compare_summaries]
        compare_dir = run_root / "comparison"
        run_compare(compare_inputs=compare_inputs, output_dir=compare_dir)
        print(f"Comparison written to: {compare_dir}")
        return 0

    if args.mode == "index":
        from retrieval.chroma_rag import index_lecture_chunks_to_chroma

        if not args.chunks_jsonl:
            raise SystemExit("--chunks-jsonl is required for index mode")
        chunks_jsonl = Path(args.chunks_jsonl).expanduser().resolve()
        if not chunks_jsonl.exists():
            raise SystemExit(f"chunks.jsonl not found: {chunks_jsonl}")

        # Default to indexing into the run_root unless an explicit chroma path was provided.
        chroma_path = args.chroma_path or str(run_root / "chroma_db")
        res = index_lecture_chunks_to_chroma(
            chunks_jsonl=chunks_jsonl,
            chroma_path=chroma_path,
            chroma_collection=args.chroma_collection,
            chroma_batch_size=args.chroma_batch_size,
        )
        if not res.ok:
            raise SystemExit(f"Chroma index failed: {res.error}")
        print(
            f"Indexed lecture chunks to Chroma: {res.records_indexed}/{res.records_total} "
            f"({args.chroma_collection} at {chroma_path})"
        )
        return 0

    if args.mode == "retrieve":
        from retrieval.chroma_rag import retrieve_lecture_context_for_student_chunks

        if not args.chunks_jsonl:
            raise SystemExit("--chunks-jsonl is required for retrieve mode")
        chunks_jsonl = Path(args.chunks_jsonl).expanduser().resolve()
        if not chunks_jsonl.exists():
            raise SystemExit(f"chunks.jsonl not found: {chunks_jsonl}")

        chroma_path = args.chroma_path or str(run_root / "chroma_db")
        out_jsonl = Path(args.retrieval_out_jsonl).expanduser().resolve()
        stats = retrieve_lecture_context_for_student_chunks(
            chroma_path=chroma_path,
            chroma_collection=args.chroma_collection,
            student_chunks_jsonl=chunks_jsonl,
            top_k=args.retrieval_top_k,
            out_jsonl=out_jsonl,
        )
        print(f"Retrieval written: {stats['out_jsonl']}")
        print(f"Student queries written: {stats['queries_written']}")
        return 0

    if args.mode == "grade":
        from grading.grade_submission import run_grading

        if not args.chunks_jsonl:
            raise SystemExit("--chunks-jsonl is required for grade mode")
        chunks_jsonl = Path(args.chunks_jsonl).expanduser().resolve()
        if not chunks_jsonl.exists():
            raise SystemExit(f"chunks.jsonl not found: {chunks_jsonl}")

        retrieval_jsonl = Path(args.retrieval_out_jsonl).expanduser().resolve()
        if not retrieval_jsonl.exists():
            raise SystemExit(f"retrieval jsonl not found: {retrieval_jsonl}")

        from grading.grade_submission import DEFAULT_GRADING_MODELS

        out_dir = run_root / "grading"
        rubric_file = Path(args.rubric_file).expanduser().resolve() if args.rubric_file else None
        assignment_file = Path(args.assignment_file).expanduser().resolve() if args.assignment_file else None
        grading_provider = args.grading_provider
        grading_model = args.grading_model or DEFAULT_GRADING_MODELS.get(grading_provider, "gpt-4o-2024-11-20")
        out_path = run_grading(
            retrieval_jsonl=retrieval_jsonl,
            chunks_jsonl=chunks_jsonl,
            student_path_filter=args.student_path,
            out_dir=out_dir,
            model=grading_model,
            grading_provider=grading_provider,
            max_lecture_chars=int(args.max_lecture_chars),
            max_student_chars=int(args.max_student_chars),
            rubric_file=rubric_file,
            assignment_file=assignment_file,
        )
        print(f"Grading written: {out_path}")
        return 0

    raise SystemExit(f"Unsupported mode: {args.mode}")


if __name__ == "__main__":
    raise SystemExit(main())
