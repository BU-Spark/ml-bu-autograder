# Phase 1 Plan: Unified Extraction Architecture

## Problem
Two separate codebases exist for the same project:
- **Sai's code** (`scripts/phase1_multimodal_pipeline.py`) — 2,300-line monolith handling PDF+XLSX+HTML extraction, multi-model vision (OpenAI/Anthropic/Gemini), tiling, OCR, chunking, ChromaDB
- **Friend's code** (`pdf_pipeline.py` + `describe_content.py` + `run_pipeline.py`) — modular 3-file design with Camelot table extraction, better image filtering heuristics, caption scoring, and Claude-based diagram description

Need: One merged architecture that both contributors work from.

## What Each Side Brings (Best Ideas to Keep)

### From Sai's code (KEEP):
- Multi-provider `VisionDescriber` class (OpenAI, Anthropic, Gemini) — client needs all models tested
- Quality-aware vision prompting (clear/low_res/unreadable preambles)
- Structured JSON vision output schema (image_type, structural_elements, visible_text, etc.)
- JSON retry with increased token limit when first response fails parsing
- Tile grid computation (aspect-ratio-aware, configurable max tiles)
- Excel processing (header detection, sheet iteration, embedded images)
- HTML processing (BeautifulSoup, tag filtering)
- ChromaDB ingestion with metadata flattening
- Rich summary.json with cost tracking, token usage, ordering validation
- Per-file JSON output for debugging
- `chunks.jsonl` vector-ready output format with consistent metadata schema

### From Friend's code (KEEP):
- **Camelot table extraction** — lattice + stream detection, much better than no table extraction in Sai's PDF pipeline
- **Image filtering heuristics** (`is_diagram_image`) — min area, min side, aspect ratio, page margin filtering to skip icons/logos/banners
- **Caption scoring system** — column-aware, multi-line merging, regex boost for "Figure N" / "Diagram N", length penalties
- **Modular 3-file architecture** — extraction separate from description separate from orchestration
- **Batch orchestrator** with per-student status tracking and batch_summary.json
- **describe_content.py pattern** — separate pass that sends extracted images/tables to LLM for rich descriptions

## New Unified Architecture

```
scripts/
├── config.py                    # Shared config, .env loading, constants
├── extractors/
│   ├── __init__.py
│   ├── pdf_extractor.py         # PyMuPDF text + images + Camelot tables
│   ├── excel_extractor.py       # openpyxl tables + embedded images
│   └── html_extractor.py        # BeautifulSoup text extraction
├── vision/
│   ├── __init__.py
│   ├── describer.py             # VisionDescriber class (OpenAI/Anthropic/Gemini)
│   ├── prompts.py               # Quality-aware prompts, JSON schema
│   ├── output_normalizer.py     # JSON parsing, normalization, tile merging
│   └── tiling.py                # Tile grid computation, image splitting
├── image_utils/
│   ├── __init__.py
│   ├── ocr.py                   # Tesseract OCR with confidence scoring
│   ├── filtering.py             # Image filtering heuristics (from friend)
│   └── caption.py               # Caption detection + scoring (from friend)
├── chunking.py                  # Text chunking with overlap
├── storage/
│   ├── __init__.py
│   ├── jsonl_writer.py          # chunks.jsonl + per-file JSON output
│   └── chroma_store.py          # ChromaDB ingestion
├── pipeline.py                  # Main pipeline: extract → describe → chunk → store
└── run_pipeline.py              # CLI orchestrator (batch + single file)
```

## Detailed File Breakdown

### 1. `config.py` (~80 lines)
Source: New file combining constants from both codebases
```
- Load .env (dotenv)
- DEFAULT_CONFIG dict (merge both configs):
    Image filtering: min_area, min_side, max_aspect_ratio, page_margin_pct (from friend)
    Caption: vertical_window, overlap_bonus, prefix_bonus, regex_boost, length_penalty (from friend)
    Tiling: tile_max_pixels, tile_target_max_pixels, max_tiles (from Sai)
    Chunking: chunk_size=1800, chunk_overlap=140 (from Sai)
    Vision: max_tokens=1800, retry_max_tokens=2500 (from Sai)
    OCR: word_threshold=45, char_threshold=280, min_confidence=55.0 (from Sai)
    Table: rows_per_chunk=35 (from Sai)
- SUPPORTED_EXTENSIONS = {".pdf", ".xlsx", ".html", ".htm"}
- API key loading helpers
```

### 2. `extractors/pdf_extractor.py` (~350 lines)
Source: Merge Sai's `process_pdf()` + friend's `pdf_pipeline.py`
```
What it does:
- Opens PDF with PyMuPDF (fitz)
- Extracts text blocks with bbox (from Sai's pdf_text_blocks)
- Extracts images with bbox (from Sai's image extraction loop)
- Applies friend's is_diagram_image() filter to skip icons/logos
- Applies friend's caption scoring (column-aware, multi-line merge, regex boost)
- Extracts tables via Camelot (from friend's extract_tables_from_pdf)
- Runs OCR on each image (from Sai's compute_ocr)
- Returns: ExtractedPDF dataclass containing:
    - text_blocks: List[TextBlock]
    - images: List[ImageItem] (with paths, bbox, caption, ocr_text)
    - tables: List[TableItem] (with text representation, rows, page)
    - page_count: int

Key merge decisions:
- Image filtering: USE FRIEND'S is_diagram_image() — it has min_area, aspect ratio,
  page margin checks that Sai's code lacks
- Caption detection: USE FRIEND'S score_caption_candidate() — it has column binning,
  regex boost, multi-line merge. Sai's match_nearest_caption is simpler (distance-only)
- Table extraction: USE FRIEND'S Camelot — Sai's PDF pipeline has NO table extraction
  (only Excel has tables)
- Text blocks: USE SAI'S pdf_text_blocks() — cleaner, includes block ID
- Image saving: USE SAI'S pattern — saves to organized images_dir with rel_path structure
```

### 3. `extractors/excel_extractor.py` (~200 lines)
Source: Sai's `process_excel()` (friend has no Excel support)
```
- Opens XLSX with openpyxl
- Header detection with find_header_row()
- Sheet iteration with row/column limits
- Embedded image extraction
- Returns: ExtractedExcel dataclass
```

### 4. `extractors/html_extractor.py` (~80 lines)
Source: Sai's `process_html()` (friend has no HTML support)
```
- BeautifulSoup parsing
- Script/style/nav stripping
- Kept tags: p, h1, h2, h3, li
- Returns: ExtractedHTML dataclass
```

### 5. `vision/describer.py` (~200 lines)
Source: Sai's `VisionDescriber` class
```
- Multi-provider support: OpenAI, Anthropic, Gemini
- Each provider's API call logic
- Returns: raw text + token usage dict
- No changes needed — Sai's implementation is solid
```

### 6. `vision/prompts.py` (~60 lines)
Source: Sai's prompt construction from `describe()` method
```
- Quality-aware preamble (clear/low_res/unreadable)
- Structured JSON schema prompt
- Retry prompt construction
- Max visible text items cap
```

### 7. `vision/output_normalizer.py` (~200 lines)
Source: Sai's `normalize_vision_output()` + `merge_vision_tile_outputs()`
```
- extract_json_object() — robust JSON extraction from LLM responses
- normalize_vision_output() — standardize all fields
- merge_vision_tile_outputs() — combine tiled image results
- build_image_text_content() — create readable text from structured output
```

### 8. `vision/tiling.py` (~100 lines)
Source: Sai's `compute_tile_grid()` + `split_image_into_tiles()`
```
- Aspect-ratio-aware grid computation
- Image splitting into tiles
- Configurable max tiles safety cap
```

### 9. `image_utils/ocr.py` (~50 lines)
Source: Sai's `compute_ocr()`
```
- Tesseract OCR with word-level confidence
- Returns OCRResult dataclass
```

### 10. `image_utils/filtering.py` (~80 lines)
Source: Friend's `is_diagram_image()`
```
- Min area check
- Min side check
- Aspect ratio bounds
- Page margin position filter
- Returns (keep: bool, reason: str)
```

### 11. `image_utils/caption.py` (~180 lines)
Source: Friend's caption system
```
- assign_column_bin() — column detection
- merge_caption_lines() — multi-line caption merging
- score_caption_candidate() — scoring with overlap/prefix/regex bonuses
- find_best_caption_for_image() — full pipeline
```

### 12. `chunking.py` (~60 lines)
Source: Sai's `chunk_text()`
```
- Character-based chunking with overlap
- Word-boundary-aware splitting
- Configurable chunk size and overlap
```

### 13. `storage/jsonl_writer.py` (~80 lines)
Source: Sai's `write_jsonl()` + `write_per_file_json()`
```
- Write chunks.jsonl
- Write per-file extraction JSON for debugging
- SHA1 chunk ID generation
```

### 14. `storage/chroma_store.py` (~60 lines)
Source: Sai's `try_store_chroma()`
```
- PersistentClient setup
- Metadata flattening for Chroma compatibility
- Batch insertion
- Returns status dict
```

### 15. `pipeline.py` (~300 lines)
Source: New file combining Sai's `main()` orchestration + friend's modular pattern
```
def run_pipeline(file_path, output_dir, config, vision_provider, vision_model):
    """Process a single file through the full pipeline."""

    ext = file_path.suffix.lower()

    # Stage 1: Extract content
    if ext == ".pdf":
        extracted = extract_pdf(file_path, images_dir, config)
    elif ext == ".xlsx":
        extracted = extract_excel(file_path, images_dir, config)
    elif ext in {".html", ".htm"}:
        extracted = extract_html(file_path, config)

    # Stage 2: Describe images/diagrams with vision API
    vision = VisionDescriber(provider, model, max_tokens)
    for image in extracted.images:
        result = describe_with_strategy(vision, image, config)
        # includes tiling, retry, OCR fallback

    # Stage 3: Describe tables with vision API (for complex tables)
    for table in extracted.tables:
        # Simple tables: use text representation directly
        # Complex tables with images: send to vision

    # Stage 4: Chunk all content
    chunks = []
    chunks.extend(chunk_text_blocks(extracted.text_blocks, config))
    chunks.extend(create_image_chunks(extracted.images, vision_results))
    chunks.extend(create_table_chunks(extracted.tables))

    # Stage 5: Write outputs
    write_jsonl(chunks)
    write_per_file_json(chunks, stats)

    return chunks, stats
```

### 16. `run_pipeline.py` (~200 lines)
Source: Friend's orchestrator pattern + Sai's CLI args
```
- CLI with argparse (all of Sai's existing flags)
- --input_dir or --pdfs for batch mode
- --vision-provider (openai/anthropic/gemini/none)
- --vision-model
- --output-dir
- --vector-db chroma
- Batch processing with per-student folders
- batch_summary.json output
- Final summary.json with cost/token tracking
```

## Output Structure (unchanged from Sai's current output)
```
outputs/<run_name>/
├── chunks.jsonl              # Vector-ready chunks (same schema as now)
├── summary.json              # Run metadata, costs, stats
├── extracted_images/         # All extracted images organized by source
├── per_file_json/            # Per-file extraction details
└── chroma_db/                # ChromaDB persistent store (if --vector-db chroma)
```

## Chunk Schema (unchanged)
```json
{
    "id": "<sha1_hash>",
    "content": "<text or image description>",
    "metadata": {
        "filename": "...",
        "source_path": "...",
        "source_type": "lecture|student",
        "format": "pdf|xlsx|html",
        "page": 1,
        "content_type": "text|image_description|table",
        "sort_key": "0001-0003",
        "document_order": 5,
        "vision_provider": "openai|anthropic|gemini",
        "vision_model": "...",
        ...
    }
}
```

## New Dependency
```
camelot-py[base]>=0.11.0    # Friend's table extraction (needs ghostscript installed)
python-dotenv>=1.0.0         # .env file loading
```

## Migration Steps (in order)

1. Create `scripts/config.py` — merge configs from both codebases
2. Create `scripts/extractors/` — move+refactor extraction logic
3. Create `scripts/vision/` — move VisionDescriber + prompts + normalizer + tiling
4. Create `scripts/image_utils/` — move OCR + friend's filtering + caption scoring
5. Create `scripts/chunking.py` — move chunk_text
6. Create `scripts/storage/` — move JSONL writer + ChromaDB
7. Create `scripts/pipeline.py` — new orchestration combining both flows
8. Create `scripts/run_pipeline.py` — CLI entry point
9. Update `requirements.txt` — add camelot-py, python-dotenv
10. Test: run on Student 1 PDF with each vision provider
11. Test: run on all 6 lecture PDFs
12. Verify: output matches existing chunks.jsonl schema

## What Gets Deleted After Migration
- `scripts/phase1_multimodal_pipeline.py` (replaced by modular files)
- Downloaded `pdf_pipeline.py`, `describe_content.py`, `run_pipeline.py` (merged in)
- Keep existing `scripts/run_eda.py`, `scripts/generate_phase1_visuals.py` etc. as-is

## What Does NOT Change
- Output format (chunks.jsonl schema stays identical)
- Existing outputs in `outputs/` are preserved
- Other scripts (run_eda.py, evaluate_student_extraction.py, etc.) untouched
- requirements.txt only gets additions, no removals
