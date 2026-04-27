# GradeAI Pro — Complete System Architecture

---

## Overview

GradeAI Pro is an end-to-end AI-powered automated grading system. It ingests student submissions (PDF, PPTX, XLSX), understands images and diagrams via vision AI, retrieves relevant lecture context from a vector database, and grades each submission against a structured rubric using a large language model — all in one pipeline.

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                          WEB INTERFACE (Flask)                       │
│   Tab 1: Grade Submissions  │  Tab 2: Manage Lectures  │  Tab 3: Setup│
└────────────┬────────────────┴──────────┬──────────────┴──────────────┘
             │                           │
             ▼                           ▼
┌────────────────────┐       ┌───────────────────────┐
│   GRADING PIPELINE │       │   LECTURE RAG PIPELINE │
│                    │       │                        │
│  1. Extract        │       │  1. Extract Lecture    │
│  2. Vision Describe│       │  2. Vision Describe    │
│  3. Retrieve       │◄──────│  3. Embed + Index      │
│  4. LLM Grade      │       │     (ChromaDB)         │
│  5. Policy Caps    │       └───────────────────────┘
│  6. Report/PDF     │
└────────────────────┘
```

---

## Component 1 — Web Interface

**Framework:** Flask (Python 3.x)  
**Entry Point:** `scripts/web/app.py`  
**Architecture:** Blueprint-based (5 blueprints)

### Blueprints & Routes

| Blueprint | File | Key Routes |
|-----------|------|------------|
| Grading | `blueprints/grading.py` | `POST /api/grade`, `POST /api/grade-batch`, `POST /api/describe`, `POST /api/grade-existing`, `POST /api/grade-quiz-batch` |
| Lectures | `blueprints/lecture.py` | `GET/POST/DELETE /api/library/lectures`, `POST /api/index-lectures`, `POST /api/describe-lecture`, `POST /api/push-lecture-to-rag`, `POST /api/add-web-links` |
| Rubric | `blueprints/rubric.py` | `POST /api/generate-rubric` |
| Library | `blueprints/library.py` | CRUD for assignments, quizzes, rubrics |
| Reports | `blueprints/reports.py` | `GET /api/history`, `GET /api/export-csv`, `GET /api/status` |

### Configuration
- Max upload: 200 MB
- Environment: `FLASK_HOST`, `FLASK_PORT`, `FLASK_DEBUG`

---

## Component 2 — Document Extraction

**Entry:** `scripts/cli/run_pipeline.py --mode extract`  
**Core Module:** `scripts/extractors/`

### Supported Formats

| Format | Extractor | Extracts |
|--------|-----------|---------|
| PDF | `pdf_extractor.py` | Text blocks with layout, embedded images, OCR text, tables |
| PPTX | `pptx_extractor.py` | Slide text, slide images, speaker notes |
| XLSX | `excel_extractor.py` | Sheet data as structured tables (up to 600 rows) |
| HTML | `html_extractor.py` | Web page text, stripped markup |

### Output Structure
```
extract/
├── manifest.json              ← per-file metadata
├── per_file_json/             ← structured JSON per document
├── text_blocks/               ← raw text with block positions
├── ocr_results/               ← OCR text + confidence scores
└── tables/                    ← structured table data
```

### Parameters
- PDF page limit: 120 pages
- OCR confidence threshold: 70%
- Image filtering: min 80px side, min 30k area, aspect ratio 1:15 to 15:1

---

## Component 3 — Vision Description (Multimodal AI)

**Entry:** `scripts/cli/run_pipeline.py --mode describe`  
**Core Module:** `scripts/vision/describer.py`

### Vision Providers

| Provider | Model | Cost/Image | Notes |
|----------|-------|-----------|-------|
| OpenAI | gpt-4o-2024-11-20 | ~$0.00275 | Default, most accurate |
| Anthropic | claude-3-5-sonnet-20241022 | Enterprise | High quality |
| Google | gemini-2.5-flash | Low cost | Fast, good for batch |

### Tiling Strategy
- Images >1 million pixels are split into 3×3 grid tiles
- Each tile described separately, results merged
- Prevents token overflow on dense diagrams

### Output per Image Chunk
```json
{
  "content_type": "image_description",
  "content": "This diagram shows a 3-tier architecture with...",
  "page_number": 4,
  "block_index": 2,
  "image_quality": "clear|blurry|low_res",
  "detected_elements": ["flowchart", "arrows", "labels"],
  "ocr_text": "Step 1 → Step 2 → ..."
}
```

### Prompt Version
- Default: `verbose_v2` — extracts visible text, classifies diagram type, detects spatial relationships

---

## Component 4 — RAG (Retrieval-Augmented Generation)

**Index Entry:** `scripts/cli/run_pipeline.py --mode index`  
**Retrieve Entry:** `scripts/cli/run_pipeline.py --mode retrieve`  
**Core Modules:** `scripts/retrieval/chroma_rag.py`, `scripts/storage/chroma_store.py`

### Embedding Providers

| Provider | Model | Dimensions | Notes |
|----------|-------|-----------|-------|
| Local (default) | all-MiniLM-L6-v2 | 384 | On-device, no API key |
| OpenAI | text-embedding-3-small | 1536 | Good quality, low cost |
| Google | gemini-embedding-001 | 3072 | Highest quality |

### Chunk Structure
```json
{
  "id": "<SHA1 hash>",
  "content": "text content of the chunk...",
  "metadata": {
    "source_path": "lectures/Module_1.pdf",
    "source_type": "lecture",
    "format": "pdf",
    "content_type": "text|image_description|table",
    "page_number": 5,
    "block_index": 3,
    "document_order": 12,
    "filename": "Module_1.pdf"
  }
}
```

### Indexing
- Filters chunks to `source_type == "lecture"` only
- Persisted ChromaDB at `~/.cache/ai_autograder/chroma_db/`
- Shared across all grading runs (index once, reuse many times)
- Chunking: 1800 chars per chunk, 140 char overlap
- Total chunks in production: ~4,414 (9 lecture modules)

### Retrieval
- Query: student text chunk → top-K lecture matches
- Distance threshold: L2 ≤ 1.5 (0=identical, 0.8=good match, 1.5=threshold)
- Output: `retrieval.jsonl` — one row per student chunk with matched lecture excerpts

---

## Component 5 — LLM Grading Engine

**Entry:** `scripts/cli/run_pipeline.py --mode grade`  
**Core Module:** `scripts/grading/grade_submission.py`

### Grading LLM Providers

| Provider | Default Model | Notes |
|----------|--------------|-------|
| OpenAI | gpt-4o-mini | Default, fast + cheap |
| Google | gemini-2.5-flash | Fallback chain to 2.0-flash, 1.5-flash |
| Anthropic | claude-sonnet-4-6 | Highest reasoning quality |

### Rubric Parsing (3 methods in order)
1. **DOCX Table Parser** — extracts from structured rubric tables
2. **Regex Parser** — finds `(N points)` patterns in text
3. **AI Fallback** — Claude Haiku (`claude-haiku-4-5-20251001`) for prose rubrics

### Scoring Algorithm

```
1. Parse rubric → criteria with max_points + checklist_items
2. For each criterion:
   a. Evaluate each checklist item: YES / PARTIAL / NO
   b. checklist_pct = (yes + 0.67×partial) / total × 100
   c. Snap to grade band → multiplier
   d. awarded = max_points × multiplier
3. Apply policy caps (see below)
4. Sum → overall_score (0–100)
```

### Grade Bands

| Checklist % | Multiplier |
|------------|-----------|
| 90–100% | 1.000 × max |
| 83–89% | 0.967 × max |
| 76–82% | 0.900 × max |
| 68–75% | 0.750 × max |
| 60–67% | 0.700 × max |
| 52–59% | 0.633 × max |
| 44–51% | 0.567 × max |
| < 44% | 0.500 × max |

### Policy Caps

| Policy | Trigger | Cap |
|--------|---------|-----|
| Missing workflow diagram | Assignment requires diagram but no image/table chunks found | Cap at 78% |
| Missing sections | >1 section missing or >3 sections partial | `max(0.65×total, total − 0.10×missing − 0.03×partial)` |
| No evidence | Criterion has no matched evidence in student text | Cap criterion at 60% |

### Output — grades.json
```json
{
  "student_file": "Student_3.pdf",
  "overall_score": 73.5,
  "total_max_points": 100,
  "pre_cap_score": 78.0,
  "assignment_file": "assignment_1.pdf",
  "grading_model": "claude-sonnet-4-6",
  "criterion_details": [
    {
      "criterion_id": "C1",
      "criterion_name": "Business Process Redesign",
      "max_points": 25,
      "awarded_points": 18.5,
      "checklist_pct": 74.0,
      "grade_band_snapped": true,
      "evidence_match_count": 3,
      "no_evidence_cap_applied": false
    }
  ],
  "section_coverage": [
    {"section_id": "Q1", "status": "addressed"}
  ],
  "policy_caps_applied": [],
  "confidence": 0.87
}
```

---

## Component 6 — Rubric Generation

**Entry:** `POST /api/generate-rubric`  
**Core Module:** `scripts/rubric_gen/generate_rubric.py`  
**Model:** Anthropic Claude Haiku (`claude-haiku-4-5-20251001`)

- Accepts: free-form text, PDF, DOCX, or library assignment reference
- Outputs: JSON with `criteria[]`, each having `criterion_id`, `criterion_name`, `max_points`, `checklist_items[]`
- Used when no manual rubric is uploaded

---

## Component 7 — Report Generation

**Core Module:** `scripts/web/utils/pdf_generator.py`

- Generates per-student PDF report
- Includes: overall score, criterion breakdown, checklist results, evidence snippets, policy cap notes
- Also: CSV export of all runs (`GET /api/export-csv`)

---

## End-to-End Data Flow

```
Student PDF/PPTX/XLSX
        │
        ▼
┌───────────────┐
│  1. EXTRACT   │  ← pdf_extractor / pptx_extractor / excel_extractor
│               │    Output: text blocks, images, OCR, tables
└───────┬───────┘
        │
        ▼
┌───────────────┐
│  2. DESCRIBE  │  ← Vision AI (OpenAI / Gemini / Anthropic)
│               │    Describes every image/diagram in the submission
│               │    Output: chunks.jsonl with image_descriptions
└───────┬───────┘
        │
        ▼
┌───────────────┐
│  3. RETRIEVE  │  ← ChromaDB vector search
│               │    Matches student chunks to lecture content
│               │    Output: retrieval.jsonl (top-K lecture matches)
└───────┬───────┘
        │
        ▼
┌───────────────┐
│  4. GRADE     │  ← LLM (GPT-4o-mini / Gemini / Claude)
│               │    Rubric + Student content + Lecture context
│               │    Output: criterion scores + checklist results
└───────┬───────┘
        │
        ▼
┌───────────────┐
│  5. NORMALIZE │  ← Grade band snapping + Policy caps
│               │    Applies: evidence cap, diagram cap, section cap
│               │    Output: final overall_score
└───────┬───────┘
        │
        ▼
┌───────────────┐
│  6. REPORT    │  ← PDF report + grades.json + CSV export
└───────────────┘
```

**Lecture RAG Pipeline (runs once, shared across all grading):**
```
Lecture PDFs → Extract → Vision Describe → Chunk (1800 chars, 140 overlap) → Embed → ChromaDB
```

---

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Web Framework | Flask (Python) |
| Vector Database | ChromaDB (persistent) |
| PDF Extraction | PyMuPDF / pdfplumber |
| PPTX Extraction | python-pptx |
| OCR | pytesseract |
| Vision AI | OpenAI GPT-4V / Anthropic Claude / Google Gemini |
| Grading LLM | OpenAI GPT-4o-mini / Google Gemini / Anthropic Claude |
| Embeddings | SentenceTransformers / OpenAI / Google |
| Report Generation | ReportLab (PDF) |
| Environment | Python 3.x, .env config |

---

## Key Design Decisions

1. **Separation of Extract & Describe** — Extraction is deterministic (no AI cost). Description is AI-powered. Running extract once and describe multiple times (different providers) is efficient.

2. **Shared Lecture Index** — Lectures are indexed once into a persistent ChromaDB. All grading runs share the same index — no re-embedding on every grade.

3. **Multi-Provider Architecture** — Every AI step (vision, grading, embedding) supports OpenAI, Google, and Anthropic. Switch providers by changing one config value.

4. **Prof-style Deduction Grading** — LLM starts at full credit and deducts only for clearly missing items. Avoids overly harsh partial credit.

5. **Policy Caps as Safety Net** — Prevents AI from giving full marks when structural requirements (diagrams, sections) are missing — catches hallucinated credit.

6. **Blind Grading** — Filenames containing "example", "solution", or "answer key" are anonymized before sending to LLM to prevent bias.

---

## File System Layout

```
/FInal AI Auto Grader/
├── scripts/
│   ├── cli/
│   │   └── run_pipeline.py          ← Unified pipeline CLI (7 modes)
│   ├── core/
│   │   ├── pipeline.py              ← Orchestration logic
│   │   ├── config.py                ← Defaults + env loading
│   │   └── chunking.py              ← Text chunking
│   ├── extractors/                  ← PDF, PPTX, XLSX, HTML extractors
│   ├── vision/                      ← Vision API wrappers + tiling
│   ├── image_utils/                 ← OCR, caption scoring, filtering
│   ├── grading/
│   │   └── grade_submission.py      ← Core grading engine
│   ├── rubric_gen/                  ← AI rubric generation
│   ├── retrieval/
│   │   └── chroma_rag.py            ← Lecture indexing + retrieval
│   ├── storage/
│   │   └── chroma_store.py          ← ChromaDB persistence layer
│   └── web/
│       ├── app.py                   ← Flask app factory
│       ├── config.py                ← Web config + paths
│       ├── blueprints/              ← grading, lecture, rubric, library, reports
│       └── utils/                   ← pipeline runner, file utils, PDF gen
├── data/
│   └── library/
│       ├── assignments/             ← Saved assignment files
│       ├── quizzes/                 ← Saved quiz files
│       └── rubrics/                 ← Saved rubric files
├── outputs/
│   └── final_phase1/
│       ├── lecture_chunks_hybrid.jsonl  ← All 4,414 lecture chunks
│       └── <run_id>/                    ← Per-run outputs
│           ├── extract/
│           ├── describe_<provider>/
│           ├── retrieval.jsonl
│           └── grading/grades.json
└── .env                             ← API keys + config overrides
```

---

## Performance Characteristics

| Metric | Value |
|--------|-------|
| Lecture chunks indexed | ~4,414 (9 modules) |
| Vision cost per submission | ~$0.003–0.01 (3–5 images) |
| Grading cost per submission | ~$0.001–0.005 (gpt-4o-mini) |
| Grading accuracy | ±4 pts vs human grader |
| Time per submission (full pipeline) | ~45–90 seconds |
| Batch mode speedup | ~3–5× vs sequential |
