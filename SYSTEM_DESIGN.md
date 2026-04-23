# System Design

Companion to [`README.md`](README.md) and
[`FEATURES_AND_FILES.md`](FEATURES_AND_FILES.md). This document covers
architecture, data flow, component responsibilities, interfaces, and
deployment topology for the BU MET autograder project.

---

## 1. Architecture Overview

Two code tracks, one shared data set.

```
                        ┌──────────────────────────────────────┐
                        │           Course Data (shared)       │
                        │  · Lectures (Spring 2026)            │
                        │  · Graded quizzes (Fall 2025)        │
                        │  · Refined rubrics                   │
                        └───────────┬─────────────┬────────────┘
                                    │             │
              ┌─────────────────────┘             └────────────────────┐
              │                                                         │
              ▼                                                         ▼
┌────────────────────────────────────────┐      ┌────────────────────────────────────────┐
│  Research harness  (root of workspace) │      │  Product  (`ml-bu-autograder/`)        │
│                                        │      │                                        │
│  eval_chunking_grading.py              │      │  FastAPI  +  Next.js  +  Streamlit     │
│  run_fewshot_comparison.py             │      │  Pipeline CLI  (extract → describe →   │
│  chunking_strategies.py                │ ───▶ │   index → retrieve → grade)            │
│  html_lecture_ingest.py                │      │  Chroma (local)  /  Azure (prod)       │
│  pptx_lecture_ingest.py                │      │  Azure Blob storage                    │
│                                        │      │  JWT auth                              │
│  Output: MAE per (model × strategy ×   │      │  Output: per-criterion grades +        │
│          few-shot × rubric variant)    │      │          token/cost logs               │
└────────────────────────────────────────┘      └────────────────────────────────────────┘
              │                                                         ▲
              │      calibration signals, refined rubrics,              │
              └────▶ prompt variants, few-shot anchors ──────────────── ┘
```

Principles:

1. **Two tracks, one data set.** The harness informs product decisions;
   the product is the deliverable.
2. **Stage-first pipeline.** Every stage writes a JSON or JSONL
   artifact, so any stage is re-runnable in isolation and runs are
   diffable.
3. **Provider-agnostic LLM layer.** Any grading / vision step accepts
   OpenAI, Anthropic, or Gemini behind a common interface.
4. **Run-local by default, Azure-backed in production.** Same code paths,
   different storage and auth backends.

---

## 2. End-to-End Data Flow (Product)

```
 ┌──────────────┐
 │  Submission  │  (.pdf / .pptx / .xlsx / .html)
 └──────┬───────┘
        │
        ▼
 ┌────────────────────────┐     scripts/extractors/
 │  EXTRACT               │     · text blocks
 │  (per file type)       │     · tables (Camelot for PDF, openpyxl for xlsx)
 │                        │     · images + nearest caption
 └──────┬─────────────────┘     · metadata (page, slide, sheet)
        │
        ▼  (images only)
 ┌────────────────────────┐     scripts/image_utils/filtering.is_diagram_image
 │  FILTER decorative     │     · drop by size / aspect ratio / page position
 │  images                │     · keep diagrams, flowcharts, tables, screenshots
 └──────┬─────────────────┘
        │
        ▼
 ┌────────────────────────┐     scripts/vision/describer.VisionDescriber
 │  DESCRIBE              │     · provider ∈ {openai, anthropic, gemini}
 │  (vision LLM)          │     · tile oversized images, merge per-tile outputs
 │                        │     · structured JSON: image_type, all_visible_text,
 │                        │       description, structural_elements, …
 │                        │     · retry on invalid JSON
 └──────┬─────────────────┘
        │
        ▼
 ┌────────────────────────┐     scripts/vision/output_normalizer.build_image_text_content
 │  FLATTEN to text       │     · turn structured JSON into retrievable text chunks
 └──────┬─────────────────┘
        │
        ▼
 ┌────────────────────────┐     scripts/core/chunking.chunk_text  (+ sha1 ids)
 │  CHUNK                 │     · character-based, word-boundary snapped
 │  text + flattened      │     · metadata preserved per chunk
 │  image descriptions    │
 └──────┬─────────────────┘
        │
        ▼
 ┌────────────────────────┐     scripts/storage/chroma_store.try_store_chroma
 │  INDEX                 │     · embed (local default / OpenAI / Gemini / Cohere)
 │  (run-local Chroma     │     · persist under outputs/<run_id>/chroma_db
 │  or Azure Vector)      │
 └──────┬─────────────────┘
        │
        ▼
 ┌────────────────────────┐     scripts/retrieval/chroma_rag.ChromaRAG
 │  RETRIEVE top-k        │     · metadata filter (e.g. source_type=lecture)
 │  lecture chunks        │     · top-k per question / per criterion
 └──────┬─────────────────┘
        │
        ▼
 ┌────────────────────────┐     scripts/grading/grade_submission.py
 │  GRADE                 │     · rubric + assignment + retrieved context
 │                        │     · criterion-level evidence + score
 │                        │     · TokenTracker → input/output/cache tokens + USD
 └──────┬─────────────────┘
        │
        ▼
 ┌────────────────────────┐
 │  Grade artifact        │     · written to outputs/<run_id>/grade.json
 │  (returned to UI /     │     · persisted to Azure Blob in product mode
 │   API / Blob storage)  │
 └────────────────────────┘
```

### Research-harness flow (simpler, text-only)

```
Excel (student answers)  ──┐
                           ├──▶  load_eval_data       ┐
Rubric JSON             ───┘                          │
                                                      ▼
Lectures (HTML / PPTX) ─▶ chunking_strategies ─▶ embed_chunks ─▶ top-k retrieval
                                                                     │
FEW_SHOT_EXAMPLES ─▶ leakage guard (fingerprint filter) ─▶  build_few_shot_block
                                                                     │
                                                                     ▼
                           grade_with_llm(provider)  ─▶  MAE vs. professor
                                                                     │
                                                                     ▼
                             chunking_eval_results*.json / fewshot_comparison_results.json
```

---

## 3. Subsystems

### 3.1 Extraction layer

- **Dispatch** (`scripts/core/pipeline.list_target_files` + per-type
  extractors).
- **Per-type extractors** in `scripts/extractors/`:
  `pdf_extractor.py`, `pptx_extractor.py`, `html_extractor.py`,
  `excel_extractor.py`.
- **Normalized output**: `extracted_{pdf,pptx,html,excel}_to_jsonable`
  converts the in-memory dataclasses to JSON-serializable dicts with a
  consistent schema (text blocks, tables, images with captions,
  metadata).
- **Table handling**:
  - PDF: Camelot (lattice / stream) routed through
    `app/utils/extract_content.df_to_text`.
  - Excel: openpyxl sheets, embedded images exported via image-filter
    path.

### 3.2 Vision layer (diagram → retrievable text)

- **Pre-filter**: `image_utils.filtering.is_diagram_image` rejects
  decorative images before any LLM call (area, side length, aspect
  ratio, page-position heuristic).
- **Caption hinting**: `image_utils.caption.find_best_caption_for_image`
  pairs each surviving image with the closest text block as a hint.
- **Resolution classification**: `vision.prompts.classify_image_quality`
  → `{clear, low_res, unreadable}` — changes the prompt preamble but
  still attempts extraction.
- **Provider adapter**: `vision.describer.VisionDescriber` implements
  the same `describe(...)` interface for OpenAI Responses API,
  Anthropic Messages, and Gemini `generateContent`. Returns tuple of
  `(structured_json, usage_dict)`.
- **Tiling**: when `image_pixels >= image_large_pixels_threshold`,
  `vision.tiling.split_image_into_tiles` yields per-tile bytes; each
  tile is described separately and merged by
  `output_normalizer.merge_vision_tile_outputs`.
- **Robustness**:
  - `extract_json_object` tolerates trailing prose around the JSON.
  - If `json_parse_fallback_used=True` and `vision_retry_max_tokens`
    is higher than the first pass, a second call is made with a
    `retry_note` forcing JSON-only output.
- **Flattening for RAG**: `build_image_text_content` turns the
  structured JSON into a single text blob with `image_type`, visible
  text, description, and structural elements — so the chunk remains
  semantically rich even after embedding.

### 3.3 Chunking

- Pure-function strategies in `chunking_strategies.py` (research-harness)
  and `scripts/core/chunking.py` (product).
- Product chunking: character-based sliding window with word-boundary
  snapping; deterministic `sha1_id` per chunk so re-ingesting produces
  stable IDs.
- Research chunking exposes three strategies (`semantic`, `fixed`,
  `hybrid`) so the harness can compare them on the same answer set.

### 3.4 Embedding & vector store

- **Local**: run-local Chroma collection under
  `outputs/<run_id>/chroma_db`. `chroma_store.try_store_chroma` handles
  creation + insertion; `CHROMA_EMBEDDING_PROVIDER=default` avoids
  OpenAI quota issues on reviewer machines.
- **Production**: Azure-hosted vector via `AzureVectorService` +
  embeddings via `AzureEmbeddingService` (`azure.ai.inference`) or
  `CohereEmbeddingService`. Three input types:
  `SEARCH_QUERY`, `IMAGE`, `DOCUMENT` — Cohere is called with
  `input_type` matching the use case.
- **Retrieval interface**: `ChromaRAG` (local) and
  `VectorDBService.search` (abstract) both return `(doc_id, score,
  metadata, text)` tuples so downstream grading code is
  provider-agnostic.

### 3.5 Grading

- **Prompt assembly** (`grade_submission.py`):
  1. System: persona + grading rules + originality policy.
  2. Context: rubric (verbatim), assignment (verbatim), retrieved
     lecture chunks (top-k, scored).
  3. Optional: few-shot calibration block (in the research harness) or
     task-specific prompt module (e.g. `quiz_1_brp_prompt`).
  4. Target: the student answer.
- **Output contract**: per-criterion `{evidence, score}` plus
  `overall_score`. Enforced via structured-output parsing
  (Pydantic / JSON schema) in the product.
- **Cost tracking**: every LLM call flows through `TokenTracker`, which
  looks up `MODEL_PRICING[model]` and emits
  `grading_call_cost_usd` alongside token counts.
- **Provider adapters**: OpenAI, Anthropic, Gemini — cache tokens are
  tracked where the SDK reports them (Anthropic
  cache-creation/cache-read; GPT-4o has no cache column).

### 3.6 Rubric refinement

Two-step LLM flow, implemented as a pure pipeline so each step is
separately auditable:

```
┌──────────────────────────┐     ┌────────────────────────────┐
│   Original rubric        │     │   Optional: instructor     │
│   + assignment           │     │   notes (instructions=...) │
└──────────────┬───────────┘     └──────────────┬─────────────┘
               │                                │
               ▼                                ▼
     ┌─────────────────────────────────────────────────┐
     │  critique_rubric(...)  → RubricCritique         │
     │  (specificity, point distribution, coverage,    │
     │   clarity, duplication/ambiguity, flags)        │
     │  CONSTRAINT: must NOT propose a new rubric.     │
     └─────────────────────────────────────────────────┘
                        │
                        ▼
     ┌─────────────────────────────────────────────────┐
     │  refine_rubric(original, critique, notes?)      │
     │      → Rubric                                   │
     │  CONSTRAINTS:                                   │
     │   · per-question grading_criteria points SUM    │
     │     EXACTLY to max_points                        │
     │   · specific, measurable, objective criteria    │
     │   · preserve original intent                    │
     │   · only adjust max_points if strictly needed   │
     └─────────────────────────────────────────────────┘
                        │
                        ▼ (optional persistence)
              Azure Blob  →  assignment.json + critique.json
```

Surfaced through `POST /api/v1/ai_rubric_refine` in
`app/routes/rubric_review.py`. Offline generation (no prior rubric) is
handled by `scripts/rubric_gen/generate_rubric.py`.

### 3.7 Background processing

`app/services/bg_material_processor.BackgroundMaterialProcessor`:

- Scans `TEMP_FILES_DIR` on a loop for queued work items (JSON files
  describing a grading or RAG job).
- Uses `portalocker` so multiple FastAPI workers can't pick up the same
  job.
- Runs the RAG ingest and grading pipelines off-thread via
  `ErrorHandlingThreadPool`, which surfaces task exceptions rather
  than swallowing them.
- Rationale: LLM calls are slow and unpredictable, FastAPI workers can
  be recycled, and a file-based queue survives worker restarts.

### 3.8 Auth

- JWT-based session auth in `app/utils/jwt_service.py` —
  `JWTService.get_instance().from_authorization_header` is the FastAPI
  dependency used across protected routes.
- Personal Access Tokens persisted per user under
  `user/<email>/tokens/<token_name>.json` in Blob.
- Google OAuth entry point in `app/routes/auth.py`, gated by
  `GOOGLE_OAUTH_CLIENT_FILE`.
- JWT encryption secret is generated by the standalone
  `generate_jwt_secret.py` — never committed, referenced by
  `JWT_ENCRYPTION_SECRET_FILE`.

### 3.9 Data-leakage guard (research harness)

- `FEW_SHOT_EXAMPLES` registers anchor answers per assignment, with
  source semester documented in-file.
- `run_eval()` computes an 80-char fingerprint per registered anchor
  and strips any matching eval rows before grading.
- Assignment ID is auto-inferred from path (`_infer_assignment_id`),
  so the guard is active in both baseline and few-shot runs → both
  conditions evaluate the same filtered row set.

---

## 4. Interfaces

### 4.1 REST API (FastAPI)

Base URL: `http://localhost:8000/api/v1` (dev) — Swagger at `/docs`,
ReDoc at `/redoc`.

| Prefix | Router | Notes |
| --- | --- | --- |
| `/api/v1/auth` | `auth.py` | Google OAuth + session. |
| `/api/v1/...` | `course.py` | Course CRUD. |
| `/api/v1/...` | `assignment.py` | Assignment CRUD. |
| `/api/v1/response` | `grading.py` | Trigger grading on a student response. |
| `/api/v1/...` | `rubric.py` | Rubric CRUD. |
| `/api/v1/...` | `rubric_review.py` | `POST /ai_rubric_refine`. |
| `/api/v1/...` | `student_response.py` | Submission CRUD. |
| `/api/v1/...` | `course_material.py` | Material upload / list / delete. |
| `/api/v1/...` | `user.py` | User + PAT management. |

All routers are mounted in `app/main.py` with CORS for
`http://localhost:3000` and `DEPLOYMENT_URL`.

### 4.2 Pipeline CLI

`python app/scripts/cli/run_pipeline.py --mode <stage>` where stage is
one of `extract | describe | index | retrieve | grade | full | compare`.
Each mode has its own flag set; see `ml-bu-autograder/README.md` for
full syntax.

### 4.3 Streamlit MVP

`streamlit run app/scripts/cli/mvp_web.py` — self-contained review app
that runs the full pipeline per session in a run-local output directory.

### 4.4 Next.js frontend

`frontend/src/pages/`:

- `login.js`, `settings.js`, `courses.js`, `manual_submission.js`
- `course/[id]/{index, assignments, rubrics, grading, materials,
  instructors}.js`

Talks to the FastAPI backend via `src/api.js`; theme in
`ThemeContext.js` + `styles/theme.js`.

### 4.5 Research harness CLI

`python eval_chunking_grading.py --excel ... --rubric ...
--strategies semantic fixed hybrid --models openai claude gemini`
and `python run_fewshot_comparison.py` as the higher-level driver.

---

## 5. Storage Layout

### 5.1 Azure Blob container layout (product)

```
/
├── course/
│   └── {semester_key}/                      e.g. Fall2025
│       └── {course_id}/                     e.g. CS581
│           ├── course.json
│           ├── assignment/
│           │   └── {assignment_id}/
│           │       ├── assignment.json
│           │       ├── {question_index}/
│           │       │   ├── question.json
│           │       │   └── student_response/
│           │       │       └── {student_id}/
│           │       │           ├── response.{ext}
│           │       │           └── grade.json
│           │       └── rubrics/
│           │           ├── assignment.json   (overall rubric)
│           │           └── {question_index}.json (sub-rubric)
│           └── course_material/
│               └── {material_id}.{ext}
└── user/
    └── {user_email}/
        ├── user.json
        └── tokens/
            └── {token_name}.json
```

### 5.2 Local run artifacts

```
outputs/final_phase1/<run_id>/
├── extract/                                 per-file extraction JSON
├── describe_<provider>_<model>/
│   └── chunks.jsonl                         flattened RAG-ready chunks
├── chroma_db/                               run-local Chroma
├── retrieval.jsonl                          top-k results per question
└── grade.json                               final graded output
```

### 5.3 Research-harness artifacts

```
BU MET/
├── cs581_pptx_index.jsonl                   slide-level RAG index
├── cs581_lecture_html_index.jsonl           HTML-lecture RAG index
├── chunking_eval_results*.json              per-run MAE dumps
└── fewshot_comparison_results.json          baseline-vs-few-shot table
```

---

## 6. Configuration

Layered configuration, in order of precedence (later wins):

1. Defaults in `scripts/core/config.py`.
2. `.env` / environment variables (loaded via `python-dotenv`).
3. CLI flags on `run_pipeline.py` / `mvp_web.py`.
4. API request parameters (product mode only).

### Key environment variables

| Variable | Scope | Purpose |
| --- | --- | --- |
| `OPENAI_API_KEY` | both | OpenAI grading + embeddings. |
| `ANTHROPIC_API_KEY` | both | Claude grading + vision. |
| `GEMINI_API_KEY` / `GOOGLE_API_KEY` | both | Gemini grading + embeddings. |
| `AUTO_GRADER_RUBRIC_DIR` | product | Default rubric library path. |
| `AUTO_GRADER_LECTURE_CHUNKS` | product | Path to pre-built `chunks.jsonl`. |
| `CHROMA_EMBEDDING_PROVIDER` | product | `default` keeps Chroma local. |
| `OPENAI_EMBEDDING_MODEL` | product | e.g. `text-embedding-3-small`. |
| `GOOGLE_EMBEDDING_MODEL` | product | e.g. `gemini-embedding-001`. |
| `AZURE_STORAGE_ACCOUNT_NAME`, `AZURE_CONTAINER_NAME` | product | Blob storage target. |
| `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_CLIENT_SECRET` | product | Service principal for `DefaultAzureCredential`. |
| `AZURE_LLM_DEPLOYMENT_URL`, `AZURE_LLM_DEPLOYMENT_KEY` | product | Azure OpenAI deployment for the `LLMService`. |
| `AZURE_EMBEDDING_DEPLOYMENT_*`, `AZURE_EMBEDDING_MODEL` | product | Azure embeddings. |
| `AZURE_SEARCH_ENDPOINT`, `AZURE_SEARCH_API_KEY`, `AZURE_SEARCH_INDEX_NAME`, `AZURE_SEARCH_EMBEDDING_DIMS` | product | Azure AI Search target. |
| `COHERE_EMBEDDING_KEY` | product | Cohere v2 embeddings. |
| `JWT_ENCRYPTION_SECRET_FILE` | product | Output of `generate_jwt_secret.py`. |
| `TEMP_FILES_DIR` | product | Inbox for the background processor. |
| `DEPLOYMENT_URL` | product | CORS allowlist entry + external base URL. |
| `PRODUCTION` | product | Toggles log format + strict error paths. |

---

## 7. Runtime Topology

### 7.1 Local reviewer mode

```
┌───────────────┐        ┌───────────────┐
│  Streamlit    │──────▶ │  subprocess:  │
│  mvp_web.py   │        │  run_pipeline │
└───────┬───────┘        │  (extract →   │
        │                │   describe →  │
        │                │   index →     │
        │                │   retrieve →  │
        │                │   grade)      │
        │                └──────┬────────┘
        ▼                       │
   UI tiles                     ▼
                       ┌─────────────────┐
                       │ Local Chroma    │
                       │ (per run)       │
                       └─────────────────┘
```

No Azure, no auth. Reviewer adds one or more LLM provider keys to
`app/.env` and points at an existing `chunks.jsonl` or lets `mvp_web`
build one on the fly.

### 7.2 Full product stack

```
Browser (Next.js)
       │
       ▼
FastAPI (uvicorn)  ─── JWT verify ── AzureBlobService (course data)
       │                         ──  LLMService (Azure OpenAI)
       │                         ──  CohereEmbeddingService
       │                         ──  ChromaDBService (or Azure Vector)
       │
       ├── writes job to TEMP_FILES_DIR  ─── picked up by ───▶
       │                                                      BackgroundMaterialProcessor
       │                                                         ├─ RAG ingest
       │                                                         └─ grading pipeline
       │                                                               │
       ▼                                                               ▼
  Response to user                                             grade.json → Blob
```

`BackgroundMaterialProcessor.start_task_scan_loop()` is launched in
`main.py`. Jobs survive worker restarts because they live on disk.

### 7.3 Research-harness mode

```
shell ─▶ python eval_chunking_grading.py
         ├── reads Excel + rubric
         ├── builds in-memory RAG index from cs581_pptx_index.jsonl
         ├── calls OpenAI / Claude / Gemini directly (no Azure)
         └── writes chunking_eval_results*.json
```

---

## 8. Cross-Cutting Concerns

### 8.1 Observability

- **Structured logs** via `app/utils/logging_util.setup_loggers`;
  `PRODUCTION=true` flips to JSON-friendly output.
- **Token + cost log**: `TokenTracker` appends per-call records to a
  persistent JSONL log.
- **Index HTML** (`scripts/web/templates/index.html` +
  `app/scripts/web/templates/index.html`) renders the per-call token /
  cost table for the Flask demo.
- **Run directories** under `outputs/final_phase1/<run_id>/` are
  self-contained and easy to zip for postmortems.

### 8.2 Error handling

- FastAPI `ValidationError` and `ValueError` handlers in `main.py`
  return `400` with the stringified exception.
- Vision and grading calls fail-soft: invalid JSON → one retry with
  escalated tokens; persistent failure propagates a structured error
  rather than crashing the pipeline.
- `ErrorHandlingThreadPool` ensures background task exceptions are
  logged instead of silently lost.

### 8.3 Performance & cost

- **Decorative-image filter** (`is_diagram_image`) keeps the vision
  bill bounded.
- **Tile merging** avoids over-paying for huge images that would blow
  past the provider's per-image token caps.
- **Cache-token pricing** in `MODEL_PRICING` means Anthropic
  cache-hit reads are priced ~10× cheaper than writes — the grading
  prompt is designed to exploit this.
- **Run-local embeddings** (`CHROMA_EMBEDDING_PROVIDER=default`) avoid
  OpenAI embedding quota issues and keep reviewer demos cheap.

### 8.4 Security

- Secrets (`.env`, JWT secret file, Azure keys) are never committed;
  `.env-example` documents the required keys.
- JWT verification on every protected route via the
  `from_authorization_header` dependency.
- Azure credentials go through `DefaultAzureCredential` (service
  principal or managed identity in prod, env-var creds locally).
- CORS is explicitly allow-listed (`http://localhost:3000` and
  `DEPLOYMENT_URL`).
- Academic integrity: originality is a **bounded, separate criterion**
  in every refined rubric — it cannot silently reduce conceptual
  scores, and suspected misconduct is flagged rather than
  auto-penalized.

### 8.5 Testing

- Python unit tests live under `app/tests/` (currently lightweight:
  `test_bytes_to_doc_util.py`).
- Rubric E2E regression via `rubric_test/rubric_test.py`.
- Research-harness runs (MAE dumps) act as integration tests: a
  regression in chunking, retrieval, or prompt design is visible as a
  MAE bump in `chunking_eval_results*.json`.

---

## 9. Extension Points

- **Add a grading / vision model.** Append an entry to
  `scripts/core/token_budget.MODEL_PRICING`; if it's a new provider,
  extend `VisionDescriber` / `grade_submission` with a branch that
  matches the existing provider adapters. No other code should need to
  change.
- **Add a file type.** Implement an `extract_<type>` + matching
  `extracted_<type>_to_jsonable` in `scripts/extractors/`, register in
  the extractors package, and append the extension to
  `SUPPORTED_EXTENSIONS`.
- **Add a chunking strategy.** Add a pure function to
  `chunking_strategies.py` (or `scripts/core/chunking.py`) and wire it
  into the research-harness `--strategies` choice list.
- **Add a rubric for a new quiz.** Drop `rubric_refined.txt` +
  `quiz_{N}.json` into `New Refined Rubrics/quiz_{N}/`, then add a
  `FEW_SHOT_EXAMPLES["quiz_{N}"]` entry (with documented source
  semester) in `eval_chunking_grading.py`.
- **Swap vector backends.** `VectorDBService` is the abstract
  interface; implement it for a new store and wire it into
  `bg_material_processor` in place of `ChromaDBService`.

---

## 10. Design Decisions Worth Flagging

1. **Two copies of `scripts/`** (root and `app/scripts/`) are kept
   intentionally so the CLI can run without the FastAPI stack
   installed. The `app/scripts/` version is canonical.
2. **File-based job queue** (not Celery / RQ) to keep the local
   review path trivial — nothing extra to install.
3. **Structured vision output over plain captioning** so each diagram
   produces both verbatim text (for exact retrieval matches) and a
   natural-language description (for semantic retrieval).
4. **Rubric refinement is strictly two-step** so point-sum drift can
   only happen in the revise step, which is explicitly constrained to
   preserve `max_points`.
5. **Originality as a separate, bounded criterion** rather than a
   multiplier — prevents the LLM from compounding a wording penalty
   with a conceptual penalty.
6. **Data-leakage guard defaults to on** based on path inference. There
   is no way to accidentally run a few-shot eval without the filter.
7. **Research harness writes JSON, not markdown.** All "experiment
   results" are diffable and re-processable.

---

## 11. Known Limitations

- `text-embedding-ada-002` access issues on some OpenAI projects; swap
  to `text-embedding-3-small` in `embed_chunks` or use the local
  Chroma default embedder.
- The background processor relies on a polling loop; latency is
  bounded by its scan interval, not sub-second.
- Refined rubrics currently cover Quiz 1–4; the Final Exam is not yet
  refined.
- OCR is Tesseract-based and only kicks in when vision mode is off —
  no hybrid OCR-then-vision path today.

---

## 12. Related Documentation

- [`README.md`](README.md) — setup and quickstart.
- [`FEATURES_AND_FILES.md`](FEATURES_AND_FILES.md) — features &
  per-file catalog.
- `ml-bu-autograder/README.md` — product-side quickstart.
- `ml-bu-autograder/MANIFEST.md` — full product-repo inventory.
- `ml-bu-autograder/PLAN.md` — roadmap.
- `ml-bu-autograder/CALIBRATION_*.md` — calibration writeups.
- `ml-bu-autograder/Josh Yip - Azure Documentation.md` — Azure setup
  detail.
