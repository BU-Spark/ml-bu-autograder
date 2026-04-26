# Features, Research & File Catalog

Companion to [`README.md`](README.md). Covers two things:

1. **What we built and researched** — feature list plus the research
   questions the eval harness was used to answer.
2. **What every Python file in the workspace does** — one-liner per
   module, grouped by role.

For architecture, data flow, and interface diagrams see
[`SYSTEM_DESIGN.md`](SYSTEM_DESIGN.md).

---

## Part 1 — Features & Research

### 1.1 Product features (`ml-bu-autograder/`)

| Feature | Where it lives | Notes |
| --- | --- | --- |
| Multimodal extraction (`pdf` / `pptx` / `xlsx` / `html`) | `app/scripts/extractors/`, `app/utils/extract_content.py` | Text, tables (Camelot), and embedded images with nearest-caption matching. |
| Diagram describer (vision-LLM → structured JSON) | `app/scripts/vision/` (`describer.py`, `prompts.py`, `tiling.py`, `output_normalizer.py`) | Supports OpenAI, Anthropic, Gemini. Tiles oversized images. Retries on invalid JSON. |
| Decorative-image filter | `app/scripts/image_utils/filtering.py` + `caption.py` | Drops logos/headers/icons by size, aspect ratio, and page position before the vision call. |
| OCR fallback | `app/scripts/image_utils/ocr.py` | Tesseract-based; used when vision mode is disabled. |
| RAG over lecture chunks | `app/scripts/retrieval/chroma_rag.py`, `app/scripts/storage/chroma_store.py`, `app/services/vector_db_service.py` | Chroma local per run; Azure Vector service as production option. |
| Rubric-aware grading (criterion-level evidence + scores) | `app/scripts/grading/grade_submission.py` | Returns per-criterion evidence, score, and overall total. |
| AI rubric refinement (critique → revise) | `app/services/rubric_refinement_service.py`, `app/routes/rubric_review.py` | Two-step LLM flow; enforces per-question point-sum constraint. |
| AI rubric generation from scratch | `app/scripts/rubric_gen/generate_rubric.py` | When no rubric exists yet. |
| Rubric test harness (Azure OpenAI E2E) | `rubric_test/rubric_test.py` | Used during the refinement validation. |
| Token + cost tracking | `app/scripts/core/token_budget.py`, `TokenTracker` | Per-call input/output/cache tokens + USD; pricing table per model. |
| Streamlit MVP app | `app/scripts/cli/mvp_web.py` | End-to-end grading UI with run-local Chroma. |
| Flask alt UI | `app/scripts/web/app.py` | Minimal demo UI. |
| FastAPI REST API + auth | `app/main.py`, `app/routes/*.py`, `app/utils/jwt_service.py` | Course / assignment / rubric / grading CRUD; JWT + PAT auth. |
| Next.js frontend | `frontend/src/` | Instructor UI: courses, assignments, rubrics, grading, materials, settings. |
| Azure Blob storage for course artifacts | `app/services/azure_blob_service.py` | Container layout documented in `ml-bu-autograder/README.md`. |
| Azure-hosted vector + speech clients | `app/services/azure_vector_service.py`, `app/services/azure_speech_client.py` | Production alternatives to local Chroma / local STT. |
| Cohere + Azure AI Inference embeddings | `app/services/azure_embedding_service.py` | `EmbeddingInputType.{SEARCH_QUERY,IMAGE,DOCUMENT}` with batching. |
| Background material processor | `app/services/bg_material_processor.py` | Off-thread RAG + grading pipeline so API calls don't block. |
| Unified pipeline CLI | `app/scripts/cli/run_pipeline.py` | Modes: `extract`, `describe`, `index`, `retrieve`, `grade`, `full`, `compare`. |

### 1.2 Research harness contributions (root-level scripts)

Built to answer concrete questions before changes are promoted into the
product. Everything here writes a JSON results file, so results are
reproducible and diffable.

| Research question | Experiment | Result artifact |
| --- | --- | --- |
| Which chunking strategy (`semantic` / `fixed` / `hybrid`) gives the lowest MAE vs. professor scores on Quiz 1? | `eval_chunking_grading.py --strategies semantic fixed hybrid` | `chunking_eval_results*.json` |
| Does few-shot calibration help on each quiz, and by how much? | `run_fewshot_comparison.py` (baseline vs. few-shot across Quiz 1–4) | `fewshot_comparison_results.json` |
| Is OpenAI, Claude, or Gemini most aligned with the professor? | `--models openai claude gemini` | Per-model MAE in the same JSON |
| Does restricting retrieval to the relevant module (e.g. `module1` for Quiz 1) help? | `--filter-module module1` | MAE delta vs. unfiltered |
| Does the refined rubric (from our rubric-refinement effort) outperform the original? | Swap `--rubric` between original and `New Refined Rubrics/quiz_{N}.json` | Before/after MAE |
| Are we leaking few-shot examples into the eval set? | Built-in leakage guard (`run_eval`'s fingerprint filter) logs removed rows per run | `Leakage guard: removed N row(s)` in stdout |

### 1.3 Rubric refinement track

A cross-cutting effort that produced:

- **Refined rubric artifacts** under
  `fall 2025 cs 581 quiz and assignment data/New Refined Rubrics/quiz_{1..4}/`.
  Each folder has `rubric_refined.txt` (human) and `quiz_{N}.json`
  (machine-readable, consumed by both tracks).
- **Design principles** baked into each rubric:
  objective per-point-band mappings, anchor examples at low/mid/high
  credit, originality as a bounded separate criterion with numeric
  thresholds, explicit non-quality signals (e.g. sentence-count is
  administrative).
- **Automation**: `RubricRefinementService` (critique → revise) surfaced
  through `POST /ai_rubric_refine`, plus a standalone `rubric_gen`
  generator for cases with no prior rubric.
- **Validation**: `rubric_test/rubric_test.py` exercised the refined
  rubric end-to-end against real student answers using Azure OpenAI
  before the refinement was promoted into the product.

### 1.4 Data-leakage guard

- `eval_chunking_grading.py`'s `run_eval()` strips any eval row whose
  answer text matches a registered few-shot example (80-char
  fingerprint, stripped).
- Assignment ID is auto-inferred from path (`_infer_assignment_id`) so
  the guard runs in **both** baseline and few-shot conditions — the
  comparison is apples-to-apples.
- Provenance comments at the top of `FEW_SHOT_EXAMPLES` document the
  source semester for every anchor (Quiz 1 anchors come from Fall 2024
  → zero overlap; Quiz 2/3/4 use in-semester anchors but are stripped
  from eval rows).

### 1.5 Supporting research artifacts in `ml-bu-autograder/`

- `Proof_of_Concept.ipynb` — initial end-to-end demo.
- `CALIBRATION_ANALYSIS.md`, `CALIBRATION_ROOT_CAUSE.md`,
  `CALIBRATION_DATA_INVENTORY.md` — writeups on score-calibration
  findings.
- `PHASE_1_SUMMARY.md` — Phase 1 deliverables summary.
- `PROMPT_CHANGES_QUICK_REF.md` — prompt revision log.
- `fahim-model-recommendations.md`, `research.md`, `end-to-end.md`,
  `aseef-client-docs.md`, `frontend-documentation.md`,
  `Josh Yip - Azure Documentation.md`, `LLM-Use-Docs+Advice.md` —
  per-contributor writeups.
- Experiment sandboxes: `eval/`, `pdf-extraction-tests/`,
  `prompt-engineering-tests/`, `internet-search/`.

---

## Part 2 — Python File Catalog

### 2.1 Root of the workspace (research harness)

| File | Purpose |
| --- | --- |
| `eval_chunking_grading.py` | End-to-end research harness. Loads quiz Excel → builds RAG index → retrieves top-k chunks → grades with OpenAI/Claude/Gemini → compares to professor score (MAE). Hosts `FEW_SHOT_EXAMPLES`, `build_few_shot_block`, `load_rubric`, `load_eval_data`, `embed_chunks`, the data-leakage guard, and `run_eval` itself. Also exposes a CLI (`--strategies`, `--models`, `--filter-module`, `--assignment-id`, `--rubric-from-excel`, etc.). |
| `run_fewshot_comparison.py` | Driver for Quiz 1–4 baseline-vs-few-shot comparisons. Monkey-patches `build_few_shot_block` to `""` for the baseline condition so the only difference is the calibration block. Prints a combined MAE table and writes `fewshot_comparison_results.json`. |
| `chunking_strategies.py` | Three pure chunking functions: `chunk_by_semantic` (paragraph-boundary, size-capped), `chunk_by_fixed_tokens` (sliding window with overlap), `chunk_hybrid` (semantic first, sub-split large sections). Used by both the ingesters and `eval_chunking_grading.py`. |
| `html_lecture_ingest.py` | Parses `.html`/`.htm` lecture exports under `Spring 2026/Lectures [html versions]/` into RAG-ready chunks (with module metadata) and writes `cs581_lecture_html_index.jsonl`. |
| `pptx_lecture_ingest.py` | Walks `.pptx` decks and calls `pptx_text_extractor.extract_pptx_to_chunks` on each, producing `cs581_pptx_index.jsonl`. |
| `pptx_text_extractor.py` | Slide-level extractor. Returns one RAG chunk per slide: `{id, text (title+body+speaker-notes), metadata(course, lecture_id, source_file, slide_index, modality)}`. |

### 2.2 `ml-bu-autograder/app/` — FastAPI application

#### 2.2.1 Entry point

| File | Purpose |
| --- | --- |
| `app/main.py` | FastAPI app factory. Loads env, initializes Azure services (`AzureBlobService`, `LLMService`, `CohereEmbeddingService`, `ChromaDBService`, `BackgroundMaterialProcessor`), sets up CORS + validation handlers, registers all routers under `/api/v1`. |

#### 2.2.2 Routes (`app/routes/`)

| File | Endpoints |
| --- | --- |
| `auth.py` | Google OAuth + session endpoints (`/api/v1/auth/...`). |
| `course.py` | Course CRUD. |
| `assignment.py` | Assignment CRUD. |
| `rubric.py` | Rubric CRUD (upload, fetch, update). |
| `rubric_review.py` | `POST /ai_rubric_refine` — audits and revises a rubric via `RubricRefinementService`; optionally persists the critique and refined rubric to Azure Blob. |
| `student_response.py` | Student submission CRUD. |
| `grading.py` | Trigger grading on a student response; returns `Grade` / `GradedStudentResponse`. |
| `course_material.py` | Upload, list, and delete course materials (lectures, etc.). |
| `user.py` | User profile + Personal Access Token management. |
| `__init__.py` | Router package export. |

#### 2.2.3 Models (`app/models/`)

Pydantic models used for request/response bodies and Azure Blob
persistence. Each is one file:

`assignment.py`, `course.py`, `course_material.py`, `grade.py`,
`rubric.py`, `rubric_review.py` (`RubricCritique`, `RubricRefinementResponse`),
`student_response.py`, `token.py` (PAT), `uploaded_file.py`, `user.py`.

#### 2.2.4 Services (`app/services/`)

| File | Purpose |
| --- | --- |
| `azure_blob_service.py` | Singleton wrapper over Azure Blob Storage. Implements the container layout documented in the product README (`course/{semester}/{course_id}/assignment/...`). |
| `azure_embedding_service.py` | Two providers: `AzureEmbeddingService` (Azure AI Inference) and `CohereEmbeddingService` (Cohere v2). Exposes `EmbeddingInputType` (search query / document / image) and batches at 96 per request. |
| `azure_vector_service.py` | Azure-hosted vector index client (alternative to local Chroma for prod). |
| `azure_speech_client.py` | Azure AI Speech client (for audio-containing materials). |
| `vector_db_service.py` | Abstract `VectorDBService` + concrete `ChromaDBService` (singleton) for local/per-run vector storage. |
| `rubric_refinement_service.py` | `critique_rubric(...)` → `RubricCritique` then `refine_rubric(...)` → `Rubric`. Enforces per-question point-sum constraint in the prompt. |
| `bg_material_processor.py` | Polls a temp directory for queued grading/embedding jobs, processes them off-thread (safe against long-running LLM calls and FastAPI worker recycling). Handles both RAG ingestion and grading pipelines. |
| `__init__.py` | Service package exports (`AzureBlobService`, `AzureEmbeddingService`, ...). |

#### 2.2.5 Utilities (`app/utils/`)

| File | Purpose |
| --- | --- |
| `llm_service.py` | Unified LLM client (Azure OpenAI). `LLMService` singleton, `PromptBuilder`, `PromptRole`, multimodal `PromptType` (text / image / audio / file), `generate_structured_response()` for Pydantic-typed outputs. |
| `jwt_service.py` | JWT signing/verification; `from_authorization_header` dependency used across routes. |
| `env_var_util.py` | `get_str_var`, `get_bool_var`, `get_int_var` with required/optional semantics. |
| `logging_util.py` | `setup_loggers(production=...)` — configures formatters and log levels. |
| `error_handling_tpe.py` | `ErrorHandlingThreadPool` — thread pool that surfaces task exceptions instead of swallowing them. |
| `bytes_to_doc_util.py` | `Document` dataclass + `DataType` enum; converts raw bytes into a normalized document wrapper used by RAG/grading paths. |
| `extract_content.py` | PDF/table text+image extraction helpers (PyMuPDF + Camelot). Also has `df_to_text` table-to-readable-text converter. |
| `describe_content.py` | `describe_diagram_with_claude` — older, simpler Anthropic-only diagram describer returning plain text (used by legacy paths; the structured JSON version is in `app/scripts/vision/`). |
| `phase1_multimodal_extraction_util.py` | Full Phase 1 pipeline utility: PDF text-blocks + images + nearest caption, Excel sheets + embedded images, vision descriptions, optional OCR-first mode, JSONL chunks with metadata, optional direct Chroma ingestion. |
| `pdf_extraction_docx_export_util.py` | Exports PDF extraction results to `.docx` for reviewer inspection. |
| `pptx_text_extractor.py` | Same slide-level extractor as the root-level file (kept in-tree for the app to import without relative path hacks). |
| `pptx_lecture_ingest.py` | In-tree copy of the root-level `.pptx` → chunks ingester. |
| `__init__.py` | Utility package exports. |

#### 2.2.6 Tests (`app/tests/`)

| File | Purpose |
| --- | --- |
| `test_bytes_to_doc_util.py` | Round-trip tests for `Document` / `DataType` conversion. |

#### 2.2.7 Deprecated (`app/to_remove/`)

| File | Purpose |
| --- | --- |
| `rag_orchestrator.py` | Earlier RAG wrapper. |
| `langchain_rag_service.py` | Earlier LangChain-based retrieval layer. |
| `azure_ai_search_retriever.py` | Earlier Azure AI Search retriever. |

These are superseded by `vector_db_service.py` + `bg_material_processor.py`.

---

### 2.3 `ml-bu-autograder/app/scripts/` — Pipeline scripts

There is a near-identical copy at `ml-bu-autograder/scripts/` (repo
root); the `app/scripts/` version is the canonical one that the app
imports. Duplication is intentional so the CLI can run with or without
the full FastAPI stack installed.

#### 2.3.1 CLI (`scripts/cli/`)

| File | Purpose |
| --- | --- |
| `run_pipeline.py` | Unified multimodal pipeline entry point. Modes: `extract`, `describe`, `full`, `compare`, `index`, `retrieve`, `grade`. Handles vision-provider / vision-model / prompt-version flags. |
| `mvp_web.py` | Streamlit MVP app. Uploads a submission + rubric + assignment, runs `extract → describe → index → retrieve → grade` in a run-local working directory, and displays per-criterion results + total score. |

#### 2.3.2 Core (`scripts/core/`)

| File | Purpose |
| --- | --- |
| `config.py` | Central config. `SUPPORTED_EXTENSIONS`, `get_api_key()`, `load_environment()`, `merged_config()` (CLI args + defaults + env). |
| `pipeline.py` | Top-level pipeline orchestration. `now_utc_iso`, `list_target_files`, extract/describe/index/retrieve/grade driver functions; wires together extractors, `VisionDescriber`, storage, and chunking. |
| `chunking.py` | `clean_text`, `chunk_text` (character-level with word-boundary snapping), `make_sort_key`, `sha1_id` (deterministic chunk IDs). |
| `token_budget.py` | `TokenTracker` + `MODEL_PRICING` table (USD per 1M tokens, per model, with cache rates). Handles OpenAI / Anthropic / Gemini usage schemas uniformly. Exposes helpers to compute `grading_call_cost_usd`. |
| `__init__.py` | Core package re-exports. |

#### 2.3.3 Extractors (`scripts/extractors/`)

| File | Purpose |
| --- | --- |
| `pptx_extractor.py` | Slide → text blocks + images. Pulls captions from nearby text boxes; filters decorative images via `image_utils.filtering.is_diagram_image`; runs OCR when enabled. |
| `pdf_extractor.py` | Page → text blocks + images + detected tables. Uses PyMuPDF for layout, Camelot for tables, and the same image-filtering / OCR path. |
| `html_extractor.py` | Parses lecture HTML. Extracts headings, paragraphs, images (with captions), and emits `ExtractedHTML` with consistent metadata. |
| `excel_extractor.py` | Sheet → tables + embedded images. |
| `__init__.py` | Exports `extract_{excel,html,pdf,pptx}` and `extracted_*_to_jsonable` helpers used by `pipeline.py`. |

#### 2.3.4 Vision (`scripts/vision/`)

| File | Purpose |
| --- | --- |
| `describer.py` | `VisionDescriber` class (OpenAI / Anthropic / Gemini). `describe_image_with_strategy` — handles resolution classification, tiling for oversized images, JSON-retry path, per-tile output merge, token accounting. |
| `prompts.py` | `build_prompt()` — resolution-aware preamble + strict JSON schema (`image_type`, `all_visible_text`, `description`, `structural_elements`, `spatial_layout`, `completeness`, `unclear_parts`, `quality_warning`). Also `classify_image_quality` and `quality_warning_from_band`. |
| `tiling.py` | `compute_tile_grid` (minimize aspect-ratio distortion, cap tile count) + `split_image_into_tiles` for oversized images. |
| `output_normalizer.py` | `extract_json_object` (handles messy LLM output), `normalize_vision_output` (fills defaults), `merge_vision_tile_outputs`, `build_image_text_content` (flatten structured JSON into retrievable text). |
| `__init__.py` | Vision package export. |

#### 2.3.5 Image utilities (`scripts/image_utils/`)

| File | Purpose |
| --- | --- |
| `filtering.py` | `is_diagram_image` — rejects images by area / side length / aspect ratio / page position so decorative icons never hit the vision LLM. |
| `caption.py` | `find_best_caption_for_image` — spatial heuristic to attach the nearest text block as a caption hint. |
| `ocr.py` | `compute_ocr` — Tesseract wrapper used when vision mode is off or as an extra signal. |
| `__init__.py` | Package export. |

#### 2.3.6 Storage (`scripts/storage/`)

| File | Purpose |
| --- | --- |
| `chroma_store.py` | `try_store_chroma` — builds a run-local Chroma DB from JSONL chunks with metadata. |
| `jsonl_writer.py` | `write_jsonl`, `write_json`, `write_per_file_json` — atomic JSONL and JSON writers. |
| `__init__.py` | Storage package re-exports. |

#### 2.3.7 Retrieval (`scripts/retrieval/`)

| File | Purpose |
| --- | --- |
| `chroma_rag.py` | `read_jsonl`, `filter_chunks_by_source_type`, `ChromaRAG` dataclass for top-k retrieval with metadata filters. |

#### 2.3.8 Grading (`scripts/grading/`)

| File | Purpose |
| --- | --- |
| `grade_submission.py` | Given retrieved lecture chunks + student submission + rubric + assignment, calls the grading LLM and returns a `Grade` with per-criterion evidence, per-criterion score, and overall total. Drives the `TokenTracker`. |
| `quiz_1_brp_prompt.py` | Quiz-1-specific grading prompt (BPR question). |
| `regrade_quiz1_with_new_prompt.py` | One-off script to re-grade quiz 1 submissions with an updated prompt, for A/B comparison. |
| `demo_phase1_calibration.py` | Demo/validation script for the Phase 1 calibration work. |
| `analyze_expected_improvement.py` | Analyzes per-question expected improvement from a prompt/rubric change. |

#### 2.3.9 Rubric generation (`scripts/rubric_gen/`)

| File | Purpose |
| --- | --- |
| `generate_rubric.py` | Generate a rubric from scratch for an assignment when none exists. Companion to the refinement service (which expects an existing rubric). |

#### 2.3.10 Exporters (`scripts/exporters/`)

| File | Purpose |
| --- | --- |
| `export_pdf_extraction_docx.py` | PDF-extraction result → `.docx` for reviewer inspection. |
| `export_pdf_layout_docx.py` | PDF layout dump (blocks + bounding boxes) → `.docx`. |
| `export_excel_extraction_docx.py` | Excel extraction result → `.docx`. |

#### 2.3.11 Visuals, tools, web, legacy

| File | Purpose |
| --- | --- |
| `scripts/visuals/generate_phase1_visuals.py` | Builds the Phase 1 report visualizations. |
| `scripts/tools/create_tool_comparison_matrix.py` | Builds a per-tool capability matrix (extraction/vision/grading). |
| `scripts/web/app.py` | Flask alternative demo UI. |
| `scripts/legacy/phase1_multimodal_pipeline.py` | Older monolithic pipeline kept for reference; superseded by `scripts/core/pipeline.py`. |

### 2.4 `ml-bu-autograder/` repo-root extras

| File | Purpose |
| --- | --- |
| `generate_jwt_secret.py` | Generates the JWT encryption secret file referenced by `JWT_ENCRYPTION_SECRET_FILE`. |
| `rubric_test/rubric_test.py` | Azure-OpenAI-backed E2E test: parses a Quiz 1 rubric from Excel (criterion ID, rule, points, bracketed levels-of-achievement), grades the workbook's student answers, and writes `quiz1_scores.csv`. Includes `LENIENT_PERSONA` and `ROUNDING_MODE` knobs. |
| `design/workflow_diagram.py` | Renders the project workflow diagram. |

Not Python but worth flagging: `chroma.db/`, `outputs/final_phase1/…/chunks.jsonl`, `frontend/src/` (Next.js), `dataset-documentation/EDA.ipynb`, and the various `*.md` writeups referenced in Part 1.

---

## Conventions

- Every pipeline stage writes a JSON or JSONL artifact so runs are
  reproducible and diffable.
- Vector storage is per-run in local mode (`chroma.db/` or
  `outputs/.../chroma_db/`), persistent in Azure mode.
- Grading prompts return **criterion-level** evidence + scores, never
  just a single number.
- Cost tracking is on by default; every grading call logs a
  `grading_call_cost_usd` line to the persistent token log.
- The rubric refinement flow is strictly two-step (audit → revise) and
  the audit step is forbidden from proposing rewrites, so blame for
  point-sum drift is localized to the revise step.

---

## See also

- [`README.md`](README.md) — setup, quickstart, and repo tour.
- [`SYSTEM_DESIGN.md`](SYSTEM_DESIGN.md) — architecture, data flow,
  and interface diagrams.
- `ml-bu-autograder/README.md` — product-side quickstart.
- `ml-bu-autograder/MANIFEST.md` — full product-repo inventory.
- `ml-bu-autograder/PLAN.md` — roadmap.
