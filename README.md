# BU Spark AI Auto Grader

Unified multimodal grading pipeline for course submissions.

The project supports:
- Extraction from `PDF`, `PPTX`, `XLSX`, `HTML`
- Vision description with `OpenAI`, `Gemini`, or `Anthropic`
- RAG retrieval with `ChromaDB`
- Rubric-aware grading with evidence-backed scoring
- Web app flow (upload -> extract -> describe -> retrieve -> grade)

## 1) Quick Start

### Prerequisites
- Python 3.10+
- `pip`
- Optional for OCR/table quality:
  - Tesseract OCR installed and available in PATH
  - Ghostscript (for Camelot PDF table extraction)

### Setup
```bash
# from repo root
cd app
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create `app/.env`:
```env
# Choose whichever providers you will use
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
GEMINI_API_KEY=
# or GOOGLE_API_KEY=

# Optional embedding provider for Chroma: openai | google | default
CHROMA_EMBEDDING_PROVIDER=default

# Optional embedding model overrides
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
GOOGLE_EMBEDDING_MODEL=gemini-embedding-001

# Optional library location overrides (no hardcoded machine paths needed)
AUTO_GRADER_RUBRIC_DIR=./data/library/rubrics
AUTO_GRADER_LECTURE_CHUNKS=./outputs/final_phase1/lecture_chunks_hybrid.jsonl
```

## 2) No Hardcoded Paths

This codebase now uses environment-driven or project-relative paths only.

Defaults (when env vars are not set):
- Rubrics library: `app/data/library/rubrics`
- Lecture chunks: `app/outputs/final_phase1/lecture_chunks_hybrid.jsonl`
- Outputs root: `app/outputs/final_phase1`

## 3) Web App Usage

### Flask Web App
```bash
cd app
source .venv/bin/activate
python scripts/web/app.py
```
Open: [http://localhost:5000](http://localhost:5000)

### Streamlit MVP
```bash
cd app
source .venv/bin/activate
streamlit run scripts/cli/mvp_web.py
```

## 4) CLI Pipeline Usage

Run from `app/` for consistent paths.

### Extract
```bash
python scripts/cli/run_pipeline.py \
  --mode extract \
  --data-dir "../Spring 2026" \
  --output-root "outputs/final_phase1" \
  --run-id "run_01"
```

### Describe (vision)
```bash
python scripts/cli/run_pipeline.py \
  --mode describe \
  --extract-dir "outputs/final_phase1/run_01/extract" \
  --describe-dir "outputs/final_phase1/run_01/describe_openai_gpt-4o-mini" \
  --vision-provider openai \
  --vision-model "gpt-4o-mini" \
  --prompt-version "verbose_v2"
```

### Index lecture chunks to Chroma
```bash
python scripts/cli/run_pipeline.py \
  --mode index \
  --chunks-jsonl "outputs/final_phase1/run_01/describe_openai_gpt-4o-mini/chunks.jsonl" \
  --chroma-path "outputs/final_phase1/run_01/chroma_db" \
  --chroma-collection "lecture_context_v1"
```

### Retrieve lecture context for student chunks
```bash
python scripts/cli/run_pipeline.py \
  --mode retrieve \
  --chunks-jsonl "outputs/final_phase1/run_01/describe_openai_gpt-4o-mini/chunks.jsonl" \
  --chroma-path "outputs/final_phase1/run_01/chroma_db" \
  --chroma-collection "lecture_context_v1" \
  --retrieval-out-jsonl "outputs/final_phase1/run_01/retrieval.jsonl"
```

### Grade
```bash
python scripts/cli/run_pipeline.py \
  --mode grade \
  --chunks-jsonl "outputs/final_phase1/run_01/describe_openai_gpt-4o-mini/chunks.jsonl" \
  --retrieval-out-jsonl "outputs/final_phase1/run_01/retrieval.jsonl" \
  --student-path "Student 1.pdf" \
  --grading-provider openai \
  --grading-model "gpt-4o-mini" \
  --rubric-file "data/library/rubrics/assignment_1_rubric.docx" \
  --assignment-file "data/library/assignments/assignment_1.pdf"
```

## 5) Supported Providers and Models

- OpenAI: `gpt-4o-mini`, `gpt-4o-2024-11-20`
- Anthropic: `claude-sonnet-4-6`, `claude-haiku-4-5`
- Gemini: `gemini-2.5-flash`, `gemini-2.5-pro`

## 6) Important Folders

Inside `app/`:
- `scripts/`: extraction, vision, retrieval, grading, web
- `data/library/assignments`: assignment files
- `data/library/rubrics`: rubric files
- `data/library/quizzes`: quiz files
- `outputs/final_phase1`: run outputs (`extract`, `describe`, `retrieval`, `grading`)

## 7) Common Troubleshooting

- `*_API_KEY not set`: add key to `app/.env` and restart process.
- Chroma embedding permission issues: set `CHROMA_EMBEDDING_PROVIDER=default`.
- Missing lecture chunks file: set `AUTO_GRADER_LECTURE_CHUNKS` to a valid `chunks.jsonl`.
- OCR weak on some PDFs: ensure Tesseract is installed and accessible.

## 8) Security Notes

- Never commit `.env` or API keys.
- Keep rubric/assignment paths project-relative or env-configured.
- Review PR diffs for secrets before pushing.

