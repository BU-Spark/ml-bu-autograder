# System Design — GradeAI Pro

**Project:** GradeAI Pro — AI-Powered Automated Grading System  
**Semester:** Spring 2026  
**Program:** Boston University MET CS / CDS  
**GitHub:** https://github.com/BU-Spark/ml-bu-autograder  

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [High-Level Architecture](#2-high-level-architecture)
3. [Component 1 — Web Interface (Flask)](#3-component-1--web-interface-flask)
4. [Component 2 — Document Extraction](#4-component-2--document-extraction)
5. [Component 3 — Vision Description (Multimodal AI)](#5-component-3--vision-description-multimodal-ai)
6. [Component 4 — Lecture RAG Pipeline](#6-component-4--lecture-rag-pipeline)
7. [Component 5 — LLM Grading Engine](#7-component-5--llm-grading-engine)
8. [Component 6 — Rubric Generation](#8-component-6--rubric-generation)
9. [Component 7 — Quiz Batch Grading](#9-component-7--quiz-batch-grading)
10. [Component 8 — Report Generation](#10-component-8--report-generation)
11. [End-to-End Data Flow](#11-end-to-end-data-flow)
12. [API Reference](#12-api-reference)
13. [Technology Stack](#13-technology-stack)
14. [Key Design Decisions](#14-key-design-decisions)
15. [Data Schemas](#15-data-schemas)
16. [Infrastructure & Deployment](#16-infrastructure--deployment)
17. [Security & Privacy](#17-security--privacy)
18. [Performance Characteristics](#18-performance-characteristics)

---

## 1. System Overview

GradeAI Pro is an end-to-end automated grading system that reads student submissions in PDF, PowerPoint (PPTX), and Excel (XLSX) format, retrieves relevant lecture context from a vector database using Retrieval-Augmented Generation (RAG), and uses large language models (GPT-4o, Gemini 2.5 Flash, or Claude Sonnet 4.6) to evaluate each submission against a professor-authored or AI-generated rubric.

### Core Capabilities

| Capability | Description |
|---|---|
| Multimodal extraction | Reads text, tables, and embedded images/diagrams from PDF/PPTX/XLSX |
| Vision AI description | Describes diagrams and charts using GPT-4o, Gemini, or Claude vision |
| RAG grounding | Retrieves matching lecture content before grading — reduces hallucination |
| Rubric-driven scoring | Grades each criterion with YES/PARTIAL/NO checklist evaluation |
| Policy caps | Prevents over-grading when structural requirements (diagrams, sections) are missing |
| Grade band normalization | Maps checklist percentage to instructor-calibrated point multipliers |
| AI rubric generation | Auto-generates structured JSON rubrics from assignment text |
| Few-shot calibration | Aligns LLM scores to human grader expectations using scored exemplars |
| Batch quiz grading | Grades Excel quiz submissions column-by-column |
| PDF reports | Generates per-student reports with evidence, scores, and feedback |
| CSV export | Exports all grades in a spreadsheet-ready format |

---

## 2. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          WEB INTERFACE  (Flask)                              │
│  ┌──────────────────────┐  ┌──────────────────────┐  ┌─────────────────┐   │
│  │  Grade Submissions   │  │   Manage Lectures    │  │  Rubric & Setup │   │
│  └──────────┬───────────┘  └──────────┬───────────┘  └────────┬────────┘   │
└─────────────┼──────────────────────────┼───────────────────────┼────────────┘
              │                          │                        │
              ▼                          ▼                        ▼
   ┌─────────────────────┐   ┌───────────────────────┐  ┌────────────────────┐
   │   GRADING PIPELINE  │   │  LECTURE RAG PIPELINE │  │  RUBRIC GENERATION │
   │                     │   │                       │  │                    │
   │  1. Extract         │   │  1. Extract Lectures  │  │  Assignment text   │
   │  2. Vision Describe │   │  2. Vision Describe   │  │        ↓           │
   │  3. RAG Retrieve    │◄──│  3. Embed → ChromaDB  │  │  claude-sonnet-4-6 │
   │  4. LLM Grade       │   │     (4,185 chunks)    │  │        ↓           │
   │  5. Policy Caps     │   └───────────────────────┘  │  JSON rubric       │
   │  6. PDF Report      │                              └────────────────────┘
   └─────────────────────┘
```

The system has **four independent pipelines** that share the same ChromaDB vector store:

1. **Lecture RAG Pipeline** — Run once per course to build the knowledge base
2. **Grading Pipeline** — Run per assignment to evaluate student submissions
3. **Rubric Generation** — Run on-demand to auto-create rubrics from assignment text
4. **Quiz Batch Pipeline** — Run per quiz to grade Excel submissions

---

## 3. Component 1 — Web Interface (Flask)

**Entry point:** `scripts/web/app.py`  
**Architecture:** Flask application factory pattern with Blueprint-based routing  
**Template engine:** Jinja2  
**Frontend:** Single-page HTML (`scripts/web/templates/index.html`) with vanilla JavaScript  

### Blueprint Structure

| Blueprint | File | Responsibility |
|---|---|---|
| `grading` | `blueprints/grading.py` | Student submission grading (single + batch), quiz batch grading |
| `lecture` | `blueprints/lecture.py` | Lecture upload, vision description, RAG push |
| `rubric` | `blueprints/rubric.py` | AI rubric generation from assignment text |
| `library` | `blueprints/library.py` | CRUD for assignments, rubrics, quizzes in the library |
| `reports` | `blueprints/reports.py` | Grading history, CSV export, job status polling |

### Web-to-Pipeline Bridge

The web app **never imports grading code directly**. Instead:

```
Browser → Flask Blueprint → scripts/web/utils/pipeline.py → subprocess
                                                              ↓
                                               scripts/cli/run_pipeline.py
```

`pipeline.py` calls `run_pipeline.py` as a subprocess with appropriate flags. This architecture:
- Keeps the web process lightweight (no memory leak from long grading runs)
- Allows CLI-only use independent of the web server
- Enables streaming logs back to the browser via Server-Sent Events

### Key Configuration (`scripts/web/config.py`)

| Setting | Default | Description |
|---|---|---|
| `MAX_CONTENT_LENGTH` | 200 MB | Max upload size |
| `CHROMA_PATH` | `outputs/final_phase1/chroma_db` | Vector DB location |
| `CHROMA_COLLECTION` | `lecture_v1` | ChromaDB collection name |
| `PROVIDERS` | OpenAI / Gemini / Anthropic | Available grading providers |
| `FLASK_HOST` | `0.0.0.0` | Bind address |
| `FLASK_PORT` | `5000` | HTTP port |

---

## 4. Component 2 — Document Extraction

**Entry:** `scripts/cli/run_pipeline.py --mode extract`  
**Core module:** `scripts/extractors/`  
**Orchestration:** `scripts/core/pipeline.py`  

### Supported Input Formats

| Format | Extractor | What is Extracted |
|---|---|---|
| `.pdf` | `pdf_extractor.py` | Text blocks with layout positions, embedded images (JPEG/PNG), OCR for scanned pages, table structure via Camelot |
| `.pptx` | `pptx_extractor.py` | Slide text (all text shapes), speaker notes, embedded images per slide |
| `.xlsx` | `excel_extractor.py` | Tabular cell data from all sheets (up to 600 rows), embedded images |
| `.html` | `html_extractor.py` | Web page text stripped of markup, used for lecture HTML slides |

### PDF Extraction Detail

`pdf_extractor.py` uses **PyMuPDF** (fitz) as the primary engine:

1. Opens PDF page by page (limit: 120 pages)
2. Extracts text blocks with bounding box coordinates
3. Extracts embedded images (filtered by minimum size: 80px side, 30k area)
4. For scanned PDFs or image-heavy pages, falls back to Tesseract OCR
5. OCR confidence threshold: 70% (below this, text is discarded)
6. Tables are detected with Camelot (lattice method for bordered tables)

### Extraction Output Structure

```
extract/
├── manifest.json              ← file list + per-file metadata
├── per_file_json/
│   ├── Student_1.json         ← structured block list per document
│   └── Student_2.json
├── text_blocks/               ← raw text with page + block positions
├── ocr_results/               ← OCR text, confidence score per image
└── tables/                    ← structured table JSON (Camelot output)
```

### Image Filtering Pipeline

```
Raw image from PDF/PPTX
    ↓
Minimum size check (80×80px, area≥30,000)
    ↓
Aspect ratio check (not wider than 15:1 or taller than 1:15)
    ↓
Dedup hash check (skip identical images across pages)
    ↓
Pass → saved to extract/images/ for vision description
```

---

## 5. Component 3 — Vision Description (Multimodal AI)

**Entry:** `scripts/cli/run_pipeline.py --mode describe`  
**Core module:** `scripts/vision/describer.py`  

Every extracted image (diagram, chart, screenshot, architecture figure) is described by a Vision AI model before grading. This converts visual information into text that the LLM grader can evaluate.

### Vision Providers

| Provider | Model | Notes |
|---|---|---|
| OpenAI | `gpt-4o-2024-11-20` | Highest accuracy; default recommendation |
| Anthropic | `claude-3-5-sonnet-20241022` | Good quality; more conservative on ambiguous images |
| Google Gemini | `gemini-2.5-flash` | Fast and low-cost; good for batch runs |

### Tiling Strategy (`scripts/vision/tiling.py`)

Large images (>2.5 million pixels) are **automatically tiled** before sending to the vision API:

```
Image >2.5M pixels
    ↓
Calculate grid: 2×2 (4–9M px), 3×3 (>9M px)
    ↓
Split into tiles with 10% overlap (prevents boundary artifacts)
    ↓
Describe each tile separately
    ↓
Merge tile descriptions into one coherent summary
```

This prevents:
- Token overflow on very large architecture diagrams
- Loss of detail in dense flowcharts that would be downsampled

### Vision Prompt (`scripts/vision/prompts.py`)

The default prompt (`verbose_v2`) instructs the model to:
1. Describe all visible text (OCR-level detail)
2. Classify the diagram type (flowchart, architecture diagram, ER diagram, etc.)
3. Identify spatial relationships (arrows, connections, hierarchy)
4. List all labeled components

### Output Chunk Schema

```json
{
  "content_type": "image_description",
  "content": "This architecture diagram shows a 3-tier web application with...",
  "page_number": 4,
  "block_index": 2,
  "image_quality": "clear",
  "detected_elements": ["flowchart", "database symbol", "arrows", "labels"],
  "ocr_text": "Step 1 → Step 2 → Database → Output"
}
```

---

## 6. Component 4 — Lecture RAG Pipeline

**Index entry:** `scripts/cli/run_pipeline.py --mode index`  
**Retrieve entry:** `scripts/cli/run_pipeline.py --mode retrieve`  
**Core modules:** `scripts/retrieval/chroma_rag.py`, `scripts/storage/chroma_store.py`  

### Purpose

Before grading, the system retrieves the lecture content most relevant to each student chunk. This "grounding" ensures the LLM grader evaluates submissions against actual course material — not just general AI knowledge.

### Lecture Indexing Pipeline

```
Lecture PDFs/HTMLs
    ↓
Extract (pdf_extractor / html_extractor)
    ↓
Vision describe images (same as student pipeline)
    ↓
Merge all chunks → lecture_chunks_hybrid.jsonl
    ↓
Deduplication (exact hash + near-duplicate removal)
    ↓
Noise filter (remove chunks < 15 meaningful chars)
    ↓
Embed (gemini-embedding-001, 768-dim, batches of 100)
    ↓
Persist to ChromaDB (collection: lecture_v1)
```

### Embedding Providers

| Provider | Model | Dimensions | Notes |
|---|---|---|---|
| Google (default) | `gemini-embedding-001` | 768 | Used for production index |
| OpenAI | `text-embedding-3-small` | 1536 | Higher dimensional |
| Local (fallback) | `all-MiniLM-L6-v2` | 384 | No API key needed |

### ChromaDB Index

- **Collection name:** `lecture_v1`
- **Storage path:** `outputs/final_phase1/chroma_db/`
- **Total chunks:** 4,185 (after deduplication + noise removal)
  - HTML text: 2,195 chunks
  - PDF text: 1,888 chunks
  - Image descriptions: 91 chunks
  - Tables: 29 chunks
- **Source:** 142 HTML lecture files + 6 PDF modules across 6 course modules

### Chunk Schema (Stored in ChromaDB)

```json
{
  "id": "<SHA1 hash of content>",
  "content": "In a relational database, normalization is the process of...",
  "metadata": {
    "source_path": "lectures/Module_3_Database_Design.html",
    "source_type": "lecture",
    "format": "html",
    "content_type": "text",
    "page_number": 5,
    "block_index": 3,
    "document_order": 12.0,
    "module": "M3"
  }
}
```

### Retrieval

At grading time, each student text chunk is used as a query:

```python
# chroma_rag.py
results = collection.query(
    query_texts=[student_chunk],
    n_results=8,           # top-8 matches
    include=["documents", "distances", "metadatas"]
)
# Filter: only include matches with L2 distance ≤ 1.5
relevant_lectures = [r for r in results if r["distance"] <= 1.5]
```

Output: `retrieval.jsonl` — one row per student chunk with matched lecture excerpts attached.

---

## 7. Component 5 — LLM Grading Engine

**Entry:** `scripts/cli/run_pipeline.py --mode grade`  
**Core module:** `scripts/grading/grade_submission.py`  

This is the heart of the system. The grading engine takes a student submission (as structured chunks + retrieved lecture context) and a rubric, then scores each criterion using an LLM.

### Grading LLM Providers

| Provider | Default Model | Characteristics |
|---|---|---|
| OpenAI | `gpt-4o-mini` | Fast, low cost; good for large batches |
| Google Gemini | `gemini-2.5-flash` | Fallback chain: 2.5-flash → 2.0-flash → 1.5-flash |
| Anthropic | `claude-sonnet-4-6` | Highest reasoning quality; best for rubric evaluation |

### Rubric Parsing (3 Methods in Priority Order)

1. **DOCX Table Parser** — reads the first table with columns: Criterion | Points | Checklist items
2. **Regex Parser** — finds patterns like `"Criterion Name (25 points):"` in text
3. **AI Fallback** — sends rubric text to `claude-haiku-4-5` to extract structure when the above fail

### Scoring Algorithm

```
For each rubric criterion:
  1. Build grading prompt:
     - System: role + grading instructions + few-shot examples (if calibration file present)
     - User: student content (text chunks + image descriptions + table data)
             + retrieved lecture context (top-8 matches from ChromaDB)
             + checklist items to evaluate

  2. LLM evaluates each checklist item:
     YES     → item clearly present and correct
     PARTIAL → item partially addressed or weak evidence
     NO      → item missing or incorrect

  3. Calculate checklist_pct:
     checklist_pct = (yes_count + 0.67 × partial_count) / total_items × 100

  4. Map to grade band:
     90–100% → 1.000 × max_points
     83–89%  → 0.967 × max_points
     76–82%  → 0.900 × max_points
     68–75%  → 0.750 × max_points
     60–67%  → 0.700 × max_points
     52–59%  → 0.633 × max_points
     44–51%  → 0.567 × max_points
     < 44%   → 0.500 × max_points

  5. awarded_points = max_points × multiplier

Sum all criterion points → overall_score (0–100)
Apply policy caps (see below)
```

### Policy Caps

Policy caps prevent the LLM from awarding full marks when structural requirements are missing:

| Policy | Trigger | Effect |
|---|---|---|
| Diagram cap | Assignment requires a workflow diagram but no image/table chunks found in submission | Cap overall score at 78% |
| Section cap | >1 required section missing OR >3 sections only partial | `max(0.65×total, total − 0.10×missing − 0.03×partial)` |
| Evidence cap | A criterion has no matching lecture evidence (all matches > L2 1.5) | Cap that criterion at 60% of its max points |

Caps are recorded in `policy_caps_applied[]` in the output and shown in the PDF report.

### Few-Shot Calibration

When the LLM's default scoring diverges from a human grader's expected range, **few-shot calibration** aligns the AI by including scored exemplars in the system prompt.

**Calibration files:** `scripts/grading/calibrations/*.txt`

Each file contains 3–5 example answers with human-assigned scores and justifications. The grading engine prepends the file's content to the system prompt when `--few-shot-file` is passed.

**Current calibration:** `quiz1_q13_bpr_system_prompt.txt` (Quiz 1, Question 13, Business Process Redesign)

To add calibration for a new question:
1. Create `scripts/grading/calibrations/<quiz_name>_system_prompt.txt`
2. Add 3–5 example answers with expected scores
3. Pass `--few-shot-file scripts/grading/calibrations/<quiz_name>_system_prompt.txt`

### Grading Output Schema

```json
{
  "student_file": "Student_3.pdf",
  "overall_score": 73.5,
  "total_max_points": 100,
  "pre_cap_score": 78.0,
  "assignment_file": "assignment_1.pdf",
  "grading_provider": "anthropic",
  "grading_model": "claude-sonnet-4-6",
  "criterion_details": [
    {
      "criterion_id": "C1",
      "criterion_name": "Business Process Redesign",
      "max_points": 25,
      "awarded_points": 18.5,
      "checklist_pct": 74.0,
      "yes_count": 4,
      "partial_count": 1,
      "no_count": 2,
      "grade_band_snapped": true,
      "evidence_refs": ["Page 3 — The current workflow diagram shows...", "Slide 7 — AS-IS process map"],
      "missing_items": ["No TO-BE process map found", "KPI metrics not quantified"],
      "no_evidence_cap_applied": false
    }
  ],
  "section_coverage": [
    {"section_id": "Q1", "status": "addressed"},
    {"section_id": "Q2", "status": "partial"},
    {"section_id": "Q3", "status": "missing"}
  ],
  "policy_caps_applied": ["section_cap_Q3"],
  "strengths": ["Strong AS-IS analysis", "Clear problem statement"],
  "gaps": ["Missing TO-BE workflow diagram", "No quantified improvement metrics"],
  "confidence": 0.87
}
```

---

## 8. Component 6 — Rubric Generation

**Entry:** `POST /api/generate-rubric`  
**Core module:** `scripts/rubric_gen/generate_rubric.py`  
**Model:** `claude-sonnet-4-6` (Anthropic)  

The rubric generator takes free-form assignment text (pasted or from an uploaded file) and produces a structured JSON rubric with criteria, point values, and checklist items.

### Modes

| Mode | Description |
|---|---|
| **Generate** | Creates a rubric from scratch given assignment instructions |
| **Enhance** | Takes an existing rough rubric and refines/expands checklist items |

### Constraints Enforced

- Criteria points must sum to exactly 100
- Each criterion must have 4–8 checklist items
- All point values must be > 0
- Criterion IDs follow `C1, C2, C3...` format

### Rubric JSON Schema

```json
{
  "rubric_title": "Assignment 1 Rubric",
  "total_points": 100,
  "criteria": [
    {
      "id": "C1",
      "name": "Business Process Analysis",
      "max_points": 25,
      "weight": 0.25,
      "checklist_items": [
        "Identifies at least 3 current process pain points",
        "Includes AS-IS workflow diagram",
        "Quantifies current process inefficiencies with data",
        "Applies course concepts (BPR, workflow patterns)",
        "Cites at least one lecture reference"
      ]
    }
  ]
}
```

### Parsing Uploaded Rubrics (DOCX/PDF/TXT)

When a professor uploads an existing rubric instead of generating one, it is parsed in priority order:

1. **DOCX Table** — first table where columns match `Criterion | Points | Checklist`
2. **Regex** — patterns like `"Criterion Name (N points):"` with bullet lists
3. **AI fallback** — `claude-haiku-4-5` extracts structure from unformatted text

---

## 9. Component 7 — Quiz Batch Grading

**Entry:** `POST /api/grade-quiz-batch`  
**Handler:** `scripts/web/blueprints/grading.py → grade_quiz_batch()`  

Quiz batch grading handles Excel submissions where each column is a question and each row is a student's answers.

### Column Detection

The system uses **fuzzy column matching** to identify answer columns:
- Pattern: column headers matching `Q[0-9]+`, `Question [0-9]+`, or similar
- Handles variable spacing, case differences, extra text in headers
- Student ID column auto-detected (first column with non-numeric unique values)

### Per-Cell Grading

Each cell (one student's answer to one question) is graded individually:

```
Student answer text
    ↓
Retrieve lecture context (top-8 from ChromaDB)
    ↓
LLM grades against question rubric
    ↓
Returns: score (0–max), justification, confidence
```

### Few-Shot Calibration for Quizzes

Quiz-specific calibration files align the LLM to expected scoring ranges per question. The calibration file is plain text and can be edited by the instructor without code changes.

### Output

- Scored Excel file with added columns: `Q1_score`, `Q1_feedback`, `Q2_score`, etc.
- Summary row at bottom with class averages per question

---

## 10. Component 8 — Report Generation

**Core module:** `scripts/web/utils/pdf_generator.py`  
**Library:** ReportLab  

### PDF Report Contents

Each student PDF report includes:

1. **Header** — student filename, assignment name, date, grading model
2. **Summary box** — overall score, percentage, grade band
3. **Criterion table** — per-criterion score, checklist %, points awarded
4. **Checklist detail** — YES/PARTIAL/NO for each item with evidence quotes
5. **Policy cap log** — which caps were applied and why
6. **Strengths & gaps** — bullet lists from LLM analysis
7. **Evidence references** — page/slide citations from the student submission

### CSV Export

`GET /api/export-csv` returns all grading runs in one CSV:

| Column | Description |
|---|---|
| `student_file` | Submission filename |
| `overall_score` | Final score (0–100) |
| `grading_model` | LLM model used |
| `C1_score`, `C1_pct` | Per-criterion scores |
| `policy_caps` | Comma-separated cap list |
| `timestamp` | Grading timestamp |

---

## 11. End-to-End Data Flow

### Grading Pipeline (per student submission)

```
┌──────────────────────────────────────────────────────────────┐
│ INPUT: Student PDF / PPTX / XLSX                             │
└──────────────────────────────────────────────────────────────┘
                            │
              POST /api/grade-batch (Flask)
                            │
              subprocess: run_pipeline.py --mode grade
                            │
         ┌──────────────────▼──────────────────────┐
         │  STEP 1: EXTRACT                         │
         │  pdf_extractor / pptx_extractor /        │
         │  excel_extractor                         │
         │  Output: text blocks, images, tables     │
         └──────────────────┬──────────────────────┘
                            │
         ┌──────────────────▼──────────────────────┐
         │  STEP 2: VISION DESCRIBE                 │
         │  describer.py + tiling.py                │
         │  Vision API: OpenAI / Gemini / Anthropic │
         │  Output: image_description chunks        │
         └──────────────────┬──────────────────────┘
                            │
         ┌──────────────────▼──────────────────────┐
         │  STEP 3: RAG RETRIEVE                    │
         │  chroma_rag.py                           │
         │  Query: ChromaDB lecture_v1              │
         │  Top-8 lecture matches, L2 ≤ 1.5        │
         │  Output: retrieval.jsonl                 │
         └──────────────────┬──────────────────────┘
                            │
         ┌──────────────────▼──────────────────────┐
         │  STEP 4: LLM GRADE                       │
         │  grade_submission.py                     │
         │  Input: student chunks + lecture context │
         │         + rubric + few-shot calibration  │
         │  Output: criterion scores + checklist    │
         └──────────────────┬──────────────────────┘
                            │
         ┌──────────────────▼──────────────────────┐
         │  STEP 5: POLICY CAPS + NORMALIZATION     │
         │  Apply diagram cap, section cap,         │
         │  evidence cap, grade band mapping        │
         │  Output: grades.json                     │
         └──────────────────┬──────────────────────┘
                            │
         ┌──────────────────▼──────────────────────┐
         │  STEP 6: REPORT                          │
         │  pdf_generator.py → .pdf report          │
         │  grades.json → CSV export                │
         └──────────────────────────────────────────┘
```

### Lecture Indexing Pipeline (run once per course)

```
Lecture PDFs / HTML slides
    ↓
Extract (pdf_extractor + html_extractor)
    ↓
Vision describe (describer.py) ← POST /api/describe-lecture
    ↓
Merge → lecture_chunks_hybrid.jsonl
    ↓
Dedup (exact hash + near-dup removal)
    ↓
Noise filter (< 15 meaningful chars → discard)
    ↓
Embed (gemini-embedding-001, batch=100) ← POST /api/index-lectures
    ↓
Persist → ChromaDB (lecture_v1)
```

---

## 12. API Reference

### Grading Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/grade` | Grade a single uploaded submission |
| `POST` | `/api/grade-batch` | Grade multiple submissions in batch |
| `POST` | `/api/grade-existing` | Grade a file already in the library |
| `POST` | `/api/grade-quiz-batch` | Grade an Excel quiz file |
| `POST` | `/api/describe` | Describe images in an uploaded file |

### Lecture Management Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/library/lectures` | List uploaded lectures |
| `POST` | `/api/library/lectures` | Upload a new lecture file |
| `DELETE` | `/api/library/lectures/<name>` | Remove a lecture |
| `POST` | `/api/describe-lecture` | Run vision description on a lecture |
| `POST` | `/api/push-lecture-to-rag` | Embed + index a lecture into ChromaDB |
| `POST` | `/api/index-lectures` | Rebuild the full ChromaDB index |
| `POST` | `/api/add-web-links` | Scrape and add web pages as lecture content |

### Rubric & Library Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/generate-rubric` | AI-generate a rubric from assignment text |
| `GET/POST/DELETE` | `/api/library/assignments` | Manage assignment files |
| `GET/POST/DELETE` | `/api/library/rubrics` | Manage rubric files |
| `GET/POST/DELETE` | `/api/library/quizzes` | Manage quiz files |

### Reports & Utilities

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/history` | List all grading runs |
| `GET` | `/api/export-csv` | Download all grades as CSV |
| `GET` | `/api/status` | Job status polling (SSE) |
| `GET` | `/api/report/<filename>` | Serve a PDF grade report |

---

## 13. Technology Stack

| Layer | Technology | Version | Notes |
|---|---|---|---|
| Web framework | Flask | 2.x | Blueprint architecture, subprocess-based pipeline |
| Vector database | ChromaDB | 0.4.x | Persistent local storage |
| PDF extraction | PyMuPDF (fitz) | 1.23.x | Primary text + image extractor |
| PDF table extraction | Camelot | 0.11.x | Lattice method for bordered tables |
| PPTX extraction | python-pptx | 0.6.x | Slide text, shapes, images |
| OCR | Tesseract + pytesseract | 5.x | Fallback for scanned PDFs |
| Vision AI | OpenAI API | gpt-4o-2024-11-20 | Image description |
| Vision AI | Anthropic API | claude-3-5-sonnet-20241022 | Image description |
| Vision AI | Google AI API | gemini-2.5-flash | Image description |
| Grading LLM | OpenAI API | gpt-4o-mini | Primary grader |
| Grading LLM | Anthropic API | claude-sonnet-4-6 | Highest quality grader |
| Grading LLM | Google AI API | gemini-2.5-flash | Fast/cheap grader |
| Rubric generation | Anthropic API | claude-sonnet-4-6 | Rubric JSON generation |
| Embeddings | Google AI API | gemini-embedding-001 | 768-dim vectors |
| Embeddings | OpenAI API | text-embedding-3-small | 1536-dim vectors |
| Embeddings | SentenceTransformers | all-MiniLM-L6-v2 | Local fallback, 384-dim |
| Report generation | ReportLab | 4.x | Per-student PDF reports |
| Excel I/O | openpyxl | 3.x | Quiz reading + scored output |
| Environment config | python-dotenv | 1.x | .env file loading |

---

## 14. Key Design Decisions

### 1. Subprocess-Based Pipeline (Web → CLI)

The web app spawns `run_pipeline.py` as a subprocess rather than importing grading code directly. This decision was deliberate:
- **Memory safety:** Long grading runs don't leak memory into the Flask worker process
- **Independence:** CLI can be used without the web server for automation scripts
- **Streaming logs:** stdout from the subprocess can be streamed back to the browser
- **Isolation:** A crash in grading doesn't take down the web server

### 2. Shared, Persistent Vector Index

Lectures are indexed once into a ChromaDB collection that persists across all grading runs. The index is NOT rebuilt per student or per assignment. This means:
- Index time (embed + store): ~15–30 minutes once per semester
- Retrieval time: <100ms per query at runtime
- The index must be updated when new lectures are added

### 3. Multi-Provider AI (Vision + Grading + Embeddings)

Every AI step supports OpenAI, Google, and Anthropic interchangeably. The provider is selected at runtime via a dropdown (web) or `--provider` flag (CLI). Design benefits:
- Cost management: use cheap Gemini for large batches, expensive Claude for high-stakes grading
- Resilience: if one provider is down, switch immediately
- Comparison: grade the same submission with two providers to validate consistency

### 4. Grade Bands (Not Raw Percentages)

Rather than directly converting checklist percentage to points, the system snaps to discrete grade bands. This mirrors how human graders assign letter-grade-like scores and prevents artificial precision:
- 74.3% and 75.2% snap to the same band (75% multiplier) → same grade
- Avoids "73.7 / 100" precision that is meaningless in rubric scoring

### 5. Policy Caps as Guard Rails

The LLM tends to over-credit partial work ("they mentioned it vaguely, give partial"). Policy caps prevent this by hard-capping scores when structural requirements are provably absent:
- A submission with no workflow diagram cannot score above 78% regardless of LLM assessment
- Implemented as post-processing after LLM scoring — LLM doesn't know about caps

### 6. Blind Grading

Filenames containing "example", "good", "solution", "answer", or "key" are anonymized before sending to the LLM. This prevents the LLM from being influenced by filenames that suggest answer quality.

### 7. Few-Shot Calibration as Plain Text

Calibration files are plain `.txt` files edited directly by instructors. There is no UI for calibration — this is intentional. Keeping calibration as text means:
- Instructors can update calibration without code changes
- Calibration is version-controllable alongside code
- Easy to inspect exactly what examples the LLM sees

---

## 15. Data Schemas

### Lecture Chunk (stored in ChromaDB + JSONL)

| Field | Type | Description |
|---|---|---|
| `chunk_id` | string | `{source_file}_{block_idx}` |
| `text` | string | Chunk content (max ~1,000 chars) |
| `source_path` | string | Relative path to source lecture file |
| `source_format` | string | `html`, `pdf`, `image_desc`, `table` |
| `source_type` | string | Always `"lecture"` |
| `page_number` | int | Page or slide number |
| `block_index` | int | Block position within document |
| `document_order` | float | Global sort key for reading order |
| `content_type` | string | `text`, `table`, `image`, `heading` |
| `module` | string | Course module (M1–M6) if inferrable |

### Student Chunk (intermediate, not persisted in ChromaDB)

| Field | Type | Description |
|---|---|---|
| `chunk_id` | string | `{student_file}_{block_idx}` |
| `text` | string | Extracted text block (max ~1,000 chars) |
| `source_type` | string | Always `"student"` |
| `source_path` | string | Original submission file path |
| `page_number` | int | Page or slide number |
| `content_type` | string | `text`, `table`, `image_desc` |
| `vision_description` | string | Vision AI description of embedded image |
| `ocr_text` | string | OCR fallback text |

### Rubric JSON

```json
{
  "rubric_title": "string",
  "total_points": 100,
  "criteria": [
    {
      "id": "C1",
      "name": "string — criterion name",
      "max_points": 25,
      "weight": 0.25,
      "checklist_items": [
        "Observable item 1",
        "Observable item 2"
      ]
    }
  ]
}
```

### Grade Output JSON

```json
{
  "student_file": "string",
  "overall_score": 87.5,
  "overall_percentage": 0.875,
  "grading_provider": "anthropic",
  "grading_model": "claude-sonnet-4-6",
  "criterion_details": [
    {
      "criterion_id": "C1",
      "criterion_name": "string",
      "max_points": 25,
      "awarded_points": 22.5,
      "checklist_pct": 0.90,
      "yes_count": 4,
      "partial_count": 1,
      "no_count": 0,
      "evidence_refs": ["Page 3 — ...", "Slide 7 — ..."],
      "missing_items": ["Item text not addressed"]
    }
  ],
  "section_coverage": {"Q1": "addressed", "Q2": "partial", "Q3": "missing"},
  "strengths": ["..."],
  "gaps": ["..."],
  "action_items": ["..."],
  "policy_caps_applied": ["diagram_cap_78", "section_cap_Q3"],
  "confidence": 0.85
}
```

---

## 16. Infrastructure & Deployment

### Current Deployment (Local)

| Aspect | Configuration |
|---|---|
| Runtime | Python 3.10+ virtual environment (`.venv`) |
| Web server | Flask development server (`python scripts/web/app.py`) |
| Host | `localhost:5000` by default |
| Data storage | Local filesystem (`data/`, `outputs/`) |
| Vector DB | ChromaDB local persistent storage |
| API keys | `.env` file (never committed to git) |

### Recommended Production Deployment (Future)

| Aspect | Recommended Approach |
|---|---|
| Web server | Gunicorn with 4 workers |
| Reverse proxy | Nginx (for static files + SSL termination) |
| Job queue | Celery + Redis (replace subprocess-based pipeline) |
| Authentication | Flask-Login with role-based access (instructor / TA) |
| Data storage | S3-compatible object storage for submissions and reports |
| Vector DB | ChromaDB with Docker or Pinecone for hosted option |
| Secrets | AWS Secrets Manager or Vault (not .env files) |
| Monitoring | Sentry for error tracking, CloudWatch for usage metrics |

### Environment Variables

| Variable | Required | Description |
|---|---|---|
| `OPENAI_API_KEY` | Yes (if using OpenAI) | OpenAI API key |
| `ANTHROPIC_API_KEY` | Yes (if using Anthropic) | Anthropic API key |
| `GEMINI_API_KEY` | Yes (if using Gemini) | Google Gemini API key |
| `FLASK_HOST` | No | Default: `0.0.0.0` |
| `FLASK_PORT` | No | Default: `5000` |
| `FLASK_DEBUG` | No | Default: `False` |
| `CHROMA_PATH` | No | Default: `outputs/final_phase1/chroma_db` |
| `CHROMA_COLLECTION` | No | Default: `lecture_v1` |

---

## 17. Security & Privacy

### Student Data (FERPA)

- All student submission files are stored in `data/` — **gitignored**, never committed
- The LLM receives only extracted text and image descriptions — not raw files
- No student PII is stored in ChromaDB, logs, or exported CSVs
- Grade reports contain scores and feedback only — no student names (only filenames)
- **Blind grading:** filenames are anonymized before sending to the LLM

### API Key Security

- API keys are stored only in `.env` (gitignored)
- `.env.example` shows required keys with placeholder values — safe to commit
- Keys are loaded via `python-dotenv` — never hardcoded

### Known Security Gaps (Future Work)

- **No authentication** — web UI is accessible to anyone on the local machine
- **Subprocess injection risk** — filenames passed to `run_pipeline.py` should be sanitized (currently uses `shlex.quote`)
- **No rate limiting** — a malicious request could trigger many expensive LLM calls

---

## 18. Performance Characteristics

| Metric | Value |
|---|---|
| Lecture indexing (initial) | ~20–40 min for 148 lecture files (embedding cost dominates) |
| Vision description per image | 2–8 seconds (OpenAI gpt-4o) |
| Vision cost per student submission | ~$0.003–0.01 (3–5 images average) |
| Grading cost per student (gpt-4o-mini) | ~$0.001–0.005 |
| Grading cost per student (claude-sonnet-4-6) | ~$0.01–0.05 |
| Total cost per student (describe + grade) | ~$0.005–0.06 depending on provider |
| Grading time per student | 30–120 seconds |
| ChromaDB retrieval latency | <100ms for top-8 (4,185 chunks) |
| Max submission size supported | ~40,000 characters of extracted text |
| PDF pages supported | Up to 120 pages |
| Max concurrent grading | 1 (subprocess-based; add Celery for parallelism) |

---

*GradeAI Pro — Spring 2026 · Boston University MET CS/CDS*  
*Last updated: April 2026*
