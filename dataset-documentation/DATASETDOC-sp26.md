# Dataset Documentation — GradeAI Pro
**Semester:** Spring 2026  
**Project:** GradeAI Pro — AI-Powered Automated Grading System  
**GitHub Repository:** https://github.com/BU-Spark/ml-bu-autograder  
**BU Spark! Project Folder:** *(link to Google Drive folder here)*  

---

## 1. Project Information

| Field | Value |
|---|---|
| **Project Name** | GradeAI Pro — AI-Powered Auto Grader |
| **Semester** | Spring 2026 |
| **Course / Program** | Boston University MET CS / CDS |
| **Team Members** | Sai Chava *(add all team members)* |
| **Client / Stakeholder** | BU MET Faculty — *(Professor name)* |
| **Project Manager / TPM** | *(Add PM/TPM name)* |
| **GitHub Repo** | https://github.com/BU-Spark/ml-bu-autograder |
| **Google Drive** | *(Add link)* |

### Project Description

GradeAI Pro is an end-to-end automated grading system that reads student PDF/PowerPoint/Excel submissions, retrieves relevant lecture context from a vector database (RAG), and uses large language models (GPT-4o-mini, Gemini 2.5 Flash, or Claude Sonnet 4.6) to grade each submission against a professor-defined rubric. The system produces per-student PDF grade reports and CSV exports.

### Problem Statement

Manual grading of project submissions in large university courses is time-consuming, inconsistent across graders, and provides limited feedback to students. GradeAI Pro addresses this by automating rubric-based evaluation with AI, ensuring reproducible scoring with policy safeguards against grade inflation.

---

## 2. Dataset Information

GradeAI Pro uses **three categories of datasets**: (A) Lecture Knowledge Base, (B) Student Submissions, and (C) Rubric Library. Each is described below.

---

### 2A. Lecture Knowledge Base

**Purpose:** Provides factual grounding for the LLM grader via Retrieval-Augmented Generation (RAG).

#### Source

| Field | Details |
|---|---|
| **Origin** | BU MET course lecture materials (Spring 2026) |
| **Format** | HTML files (lecture slides exported as HTML) + PDF files (module decks) |
| **Collection method** | Provided directly by the course instructor |
| **Access level** | Private — course materials, not publicly redistributable |
| **Publicly available?** | No |

#### Composition

| Metric | Value |
|---|---|
| HTML lecture files | 142 files across 6 course modules |
| PDF lecture decks | 6 module PDFs |
| Total raw chunks after extraction | ~5,800 |
| After deduplication | 4,185 chunks |
| Duplicates removed | ~1,324 |
| Noise chunks removed | ~290 |
| Chunk types | HTML text (2,195), PDF text (1,888), image descriptions (91), tables (29) |
| Embedding model | `gemini-embedding-001` (768-dimensional vectors) |
| Vector database | ChromaDB (`lecture_v1` collection) |
| Retrieval distance threshold | L2 ≤ 1.5 |

#### Data Dictionary — Lecture Chunk Fields

| Field | Type | Description |
|---|---|---|
| `chunk_id` | string | Unique identifier: `{source_file}_{block_idx}` |
| `text` | string | Chunk content (max ~1,000 characters) |
| `source_path` | string | Relative path of the originating file |
| `source_format` | string | `html`, `pdf`, `image_desc`, `table` |
| `page_number` | int | Page or slide number (if applicable) |
| `block_index` | int | Ordered block position within the document |
| `document_order` | float | Global sort key for reading order |
| `content_type` | string | `text`, `table`, `image`, `heading` |
| `module` | string | Course module (M1–M6) if inferrable from path |

#### Processing Steps

1. HTML files: parsed with BeautifulSoup, 14 semantic tag types extracted (headings, paragraphs, lists, tables, code blocks, etc.)
2. PDF files: parsed with PyMuPDF; text blocks, structured tables (Camelot), and embedded images extracted per page
3. Images: described using Vision AI (OpenAI gpt-4o / Gemini / Claude) with automatic tiling for large images; OCR via Tesseract as fallback
4. Deduplication: exact-hash and near-duplicate removal (~1,324 duplicates removed)
5. Noise removal: chunks with fewer than 15 meaningful characters discarded (~290 removed)
6. Embedding: all chunks embedded via `gemini-embedding-001` (768-dim) in batches of 100
7. Storage: persisted in ChromaDB at `outputs/final_phase1/chroma_db/`

---

### 2B. Student Submissions

**Purpose:** The primary input to the grading pipeline. Each submission is graded against the rubric using lecture context retrieved from the vector database.

#### Source

| Field | Details |
|---|---|
| **Origin** | Student project submissions for BU MET course (Spring 2026) |
| **Format** | PDF (`.pdf`), PowerPoint (`.pptx`), Excel (`.xlsx`) |
| **Collection method** | Provided by the course instructor via file upload to the web UI |
| **Access level** | Strictly private — student work, FERPA-protected |
| **Publicly available?** | No — must not be committed to GitHub or shared publicly |

#### Composition

| Field | Details |
|---|---|
| Supported formats | `.pdf`, `.pptx`, `.xlsx` |
| Average file size | 2–15 MB per student submission |
| Typical content | Project write-ups, architecture diagrams, data visualizations, tables |
| Images per submission | 5–30 embedded images/diagrams |
| Storage location | `data/library/assignments/` (gitignored) |

#### Data Dictionary — Extracted Student Chunk Fields

| Field | Type | Description |
|---|---|---|
| `chunk_id` | string | `{student_file}_{block_idx}` |
| `text` | string | Extracted text block (max ~1,000 chars) |
| `source_type` | string | Always `"student"` |
| `source_path` | string | Original submission file path |
| `page_number` | int | Page or slide number |
| `content_type` | string | `text`, `table`, `image_desc` |
| `vision_description` | string | Vision AI description of any embedded image |
| `ocr_text` | string | OCR fallback text for images |

#### Privacy & Ethics

- Student submissions are **FERPA-protected** educational records
- All files are stored only in the local `data/` directory which is **gitignored**
- The system implements **blind grading**: filenames are anonymized before grading (e.g., "good_student.pdf" → "student.pdf") to prevent LLM bias
- No student PII is stored in ChromaDB or in any output files
- Grade reports contain scores and feedback only — no student identifiers beyond filename
- **Do not upload student files to any public service or commit them to GitHub**

---

### 2C. Rubric Library

**Purpose:** Defines the grading criteria, point values, and checklist items used by the LLM grader.

#### Source

| Field | Details |
|---|---|
| **Origin** | Professor-authored rubrics + AI-generated rubrics (claude-sonnet-4-6) |
| **Format** | DOCX (table format), PDF, plain text `.txt`, JSON |
| **Collection method** | Uploaded via web UI or generated by the AI rubric generator |
| **Access level** | Private — course materials |
| **Storage location** | `data/library/rubrics/` (gitignored) |

#### Rubric JSON Schema

AI-generated rubrics follow this JSON schema:

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
        "Specific observable item 1",
        "Specific observable item 2"
      ]
    }
  ]
}
```

**Constraints enforced:**
- Criteria points must sum to 100
- Each criterion must have 4–8 checklist items
- All point values must be > 0

#### DOCX Rubric Parsing

DOCX rubrics are parsed in priority order:
1. **Table format** — first table with columns: Criterion | Points | Checklist items
2. **Plain text regex** — patterns like `"Criterion Name (25 points)"`
3. **AI fallback** — `claude-haiku` extracts criteria when regex fails

---

### 2D. Grading Output Data

| Field | Details |
|---|---|
| **Format** | JSON (intermediate), PDF (reports), CSV (export) |
| **Storage** | `data/reports/` (PDF), served via `/api/export-csv` |
| **Privacy** | Contains grades and feedback — do not publish publicly |

#### Grade JSON Schema (per student)

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
      "missing_items": ["Item text that was not addressed"]
    }
  ],
  "section_coverage": {
    "Q1": "addressed",
    "Q2": "partial",
    "Q3": "missing"
  },
  "strengths": ["..."],
  "gaps": ["..."],
  "action_items": ["..."],
  "policy_caps_applied": ["diagram_cap_78", "section_cap_Q3"],
  "confidence": 0.85
}
```

---

## 3. Motivation

### Why was this dataset / system created?

Manual grading in large graduate courses is inconsistent, slow, and provides limited actionable feedback to students. BU MET faculty needed a scalable system that could:
- Grade multimodal submissions (text + diagrams + tables) consistently
- Tie grading back to actual lecture content (not just LLM "knowledge")
- Apply course-specific policy caps (e.g., missing workflow diagram → max 78%)
- Generate detailed, evidence-based feedback at scale

### What gap does it address?

Existing auto-grading tools (Gradescope, etc.) work well for code and multiple-choice but cannot evaluate free-form project submissions that include architecture diagrams, data analysis outputs, and written explanations. GradeAI Pro fills this gap using Vision AI + RAG grounding.

---

## 4. Collection Process

### Lecture Data
- Provided by course instructor as HTML exports of lecture slides and PDF module decks
- No web scraping or third-party APIs used for lecture content
- Collected once at semester start; re-indexed if lectures are updated

### Student Submissions
- Collected via the GradeAI Pro web UI (local upload only)
- Files are stored locally and never transmitted to third-party storage
- LLM API calls transmit extracted text (not raw files) to OpenAI/Google/Anthropic

### External API Usage

| API | Purpose | Data sent |
|---|---|---|
| OpenAI API | Vision description of images; grading LLM; embeddings | Image bytes (base64), extracted text chunks |
| Google Gemini API | Vision description; grading LLM; embeddings | Image bytes (base64), extracted text chunks |
| Anthropic API | Rubric generation; grading LLM | Extracted text chunks, rubric text |

**No raw student files are sent to external APIs.** Only extracted text and image data are transmitted.

### Temporal Scope

| Dataset | Collection Period |
|---|---|
| Lecture corpus | January 2026 — indexed January/February 2026 |
| Student submissions (Spring 2026) | March–April 2026 |
| Rubrics | March 2026 (created/uploaded per assignment) |

---

## 5. Preprocessing

| Step | Tool | Description |
|---|---|---|
| PDF text extraction | PyMuPDF | Text blocks, tables, embedded images per page |
| HTML extraction | BeautifulSoup | 14 semantic tag types, structured tables |
| PPTX extraction | python-pptx | Slide text, shapes, embedded images |
| Excel extraction | openpyxl | Sheet tables, cell values, embedded images |
| OCR | Tesseract (pytesseract) | Fallback for scanned/image-only PDFs |
| Image description | OpenAI gpt-4o / Gemini / Claude | Multimodal vision API call per image |
| Image tiling | Custom (vision/tiling.py) | Auto-tiles images >2.5M pixels into 2×2..3×3 grids |
| Text chunking | Custom (core/chunking.py) | Max 1,000 chars, 100-char overlap |
| Deduplication | Exact hash + near-duplicate | Removes exact and near-exact duplicate chunks |
| Noise removal | Length + content filter | Removes chunks < 15 meaningful characters |
| Embedding | `gemini-embedding-001` | 768-dimensional dense vectors, batches of 100 |

All preprocessing code is in `scripts/` — see `scripts/core/pipeline.py` for the full orchestration.

---

## 6. Uses

### Current Uses
- Automated grading of BU MET CS/CDS project submissions (Spring 2026)
- AI-assisted rubric generation for course assignments
- Batch quiz grading from Excel spreadsheets
- Per-student PDF feedback reports

### Potential Future Uses
- Grading submissions for multiple courses simultaneously (multi-course support)
- Student self-assessment tool (students grade their own work before submission)
- Teaching assistant training (compare AI grades vs. human grades)
- Research on LLM grading consistency and bias

### Constraints on Use
- **Must not be used** to make final grade decisions without human review
- **Must not be used** for high-stakes assessments without instructor oversight
- **Student data must not** be shared publicly or committed to version control
- **LLM outputs** should be treated as a grading aid, not a ground truth

---

## 7. Distribution

### Access Levels

| Dataset | Access Level | Who can access |
|---|---|---|
| Lecture corpus | Private — course materials | Course instructor + project team |
| Student submissions | Private — FERPA protected | Course instructor only |
| Rubric library | Private — course materials | Course instructor + project team |
| ChromaDB vector index | Private — derived from lectures | Project team + successor teams |
| Grade reports / CSV | Private — student grades | Course instructor only |
| Source code | Public | Open source on GitHub |
| `.env` / API keys | Private — never share | Individual developer only |

### Data Sharing Policy
- All private data files are in `.gitignore` and must **never** be committed to GitHub
- If sharing this project with future teams, provide a **fresh** `.env.example` and ask them to obtain their own API keys
- Student grades must only be shared through official BU channels

---

## 8. Maintenance

### How to Update the Lecture Corpus

```bash
# 1. Upload new lecture PDFs via the web UI → Manage Lectures tab
# 2. Click "Describe Lecture" for each new file
# 3. Click "Index All Lectures into RAG" to rebuild the ChromaDB index
```

The system supports incremental indexing — existing chunks are preserved when new lectures are added.

### How to Add New Rubrics

1. Upload via the web UI → Rubric & Setup tab → Upload Rubric
2. Or generate automatically: Rubric & Setup → Generate Rubric from Assignment

### Model Version Updates

If LLM providers release new models, update `scripts/web/config.py`:

```python
PROVIDERS = {
    "anthropic": {"model": "claude-sonnet-4-7"},   # update here
    "openai":    {"model": "gpt-4o"},               # update here
    "gemini":    {"model": "gemini-2.5-pro"},        # update here
}
```

Also update vision models in `scripts/web/blueprints/grading.py` and `scripts/vision/describer.py`.

### Contact for Data Access

For access to lecture materials, student submissions, or grade data from Spring 2026:
- Course Instructor: *(add name and email)*
- Project PM/TPM: *(add name and email)*
- BU Spark!: buspark@bu.edu

---

## 9. Known Limitations

| Limitation | Impact | Suggested Fix |
|---|---|---|
| LLM non-determinism | Scores may vary ±2 pts between identical runs | Average 2–3 runs for high-stakes grading |
| No automated test suite | Grading logic bugs may go undetected | Add pytest unit tests (see `For Future Developers` in README) |
| English-only | Non-English submissions may score poorly | Add language detection + multilingual prompt |
| Image quality dependency | Low-resolution diagrams score lower | Add image quality warnings in the UI |
| No authentication | Web UI is open to anyone on localhost | Add Flask-Login before any network-accessible deployment |
| Max 40K chars per submission | Very long submissions are truncated | Add sliding-window chunked grading |
| Single ChromaDB collection | All lectures share one namespace | Add per-course collection support |

---

*Last updated: Spring 2026 · GradeAI Pro · Boston University MET CS/CDS*
