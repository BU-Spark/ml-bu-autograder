# BU Spark AI Auto Grader

Multimodal grading pipeline for student submissions using extraction + RAG + rubric-aware scoring.

## MVP Web App (Recommended Test Path)

This is the main path reviewers should use.

### 1) Install dependencies
```bash
cd app
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2) Configure API keys (`app/.env`)
Create `app/.env` and add at least one provider key:
```env
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
GEMINI_API_KEY=
# or GOOGLE_API_KEY=

# Optional overrides
AUTO_GRADER_RUBRIC_DIR=./data/library/rubrics
AUTO_GRADER_LECTURE_CHUNKS=./outputs/final_phase1/lecture_chunks_hybrid.jsonl

# Optional embedding config
CHROMA_EMBEDDING_PROVIDER=default
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
GOOGLE_EMBEDDING_MODEL=gemini-embedding-001
```

### 3) Prepare lecture chunks for RAG (one-time)
`mvp_web` needs a lecture `chunks.jsonl` file.

If you already have one, point `AUTO_GRADER_LECTURE_CHUNKS` to it.

If not, generate lecture chunks once:
```bash
cd app
source .venv/bin/activate
python scripts/cli/run_pipeline.py \
  --mode full \
  --data-dir "<LECTURE_DATA_DIR>" \
  --source-type lecture \
  --output-root "outputs/final_phase1" \
  --run-id "lecture_bootstrap" \
  --vision-provider openai \
  --vision-model "gpt-4o-mini"
```
Then set:
```env
AUTO_GRADER_LECTURE_CHUNKS=./outputs/final_phase1/lecture_bootstrap/describe_openai_gpt-4o-mini/chunks.jsonl
```

### 4) Run `mvp_web`
```bash
cd app
source .venv/bin/activate
streamlit run scripts/cli/mvp_web.py
```

### 5) Use the UI in this order
1. Upload student submission (`pdf`, `pptx`, or `xlsx`)
2. Upload rubric and assignment (or choose preloaded files)
3. Choose provider/model
4. Click **Run Full Grading**

Pipeline executed by the app:
`extract -> describe -> index -> retrieve -> grade`

Notes:
- `mvp_web` builds a run-local Chroma DB per run.
- Index/retrieve in `mvp_web` use local embedding mode by default to avoid OpenAI embedding permission failures.

---

## Flask Web App (Alternative)
```bash
cd app
source .venv/bin/activate
python scripts/web/app.py
```
Open: [http://localhost:5000](http://localhost:5000)

---

## Project Overview

### What the system does
1. Extracts text/tables/images from student files (`pdf`, `pptx`, `xlsx`, `html`)
2. Uses selected vision model for image descriptions
3. Retrieves lecture context via Chroma RAG
4. Grades against rubric + assignment requirements
5. Returns criterion-level evidence and overall score

### Core paths (from `app/`)
- Pipeline CLI: `scripts/cli/run_pipeline.py`
- Streamlit MVP: `scripts/cli/mvp_web.py`
- Flask app: `scripts/web/app.py`
- Outputs root: `outputs/final_phase1`
- Libraries:
  - `data/library/assignments`
  - `data/library/rubrics`
  - `data/library/quizzes`

No machine-specific hardcoded paths are required.

---

## CLI Reference

### Extract
```bash
python scripts/cli/run_pipeline.py \
  --mode extract \
  --data-dir "<DATA_DIR>" \
  --output-root "outputs/final_phase1" \
  --run-id "run_01"
```

### Describe
```bash
python scripts/cli/run_pipeline.py \
  --mode describe \
  --extract-dir "outputs/final_phase1/run_01/extract" \
  --describe-dir "outputs/final_phase1/run_01/describe_openai_gpt-4o-mini" \
  --vision-provider openai \
  --vision-model "gpt-4o-mini" \
  --prompt-version "verbose_v2"
```

### Index
```bash
python scripts/cli/run_pipeline.py \
  --mode index \
  --chunks-jsonl "outputs/final_phase1/run_01/describe_openai_gpt-4o-mini/chunks.jsonl" \
  --chroma-path "outputs/final_phase1/run_01/chroma_db" \
  --chroma-collection "lecture_context_v1"
```

### Retrieve
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

---

## Supported Providers
- OpenAI: `gpt-4o-mini`, `gpt-4o-2024-11-20`
- Anthropic: `claude-sonnet-4-6`, `claude-haiku-4-5`
- Gemini: `gemini-2.5-flash`, `gemini-2.5-pro`

---

## Troubleshooting
- `*_API_KEY not set`: add key to `app/.env`, then restart.
- Missing lecture chunks: set `AUTO_GRADER_LECTURE_CHUNKS` to an existing `chunks.jsonl`.
- Chroma embedding permission issue: keep `CHROMA_EMBEDDING_PROVIDER=default`.
- OCR weak on scanned PDFs: install Tesseract and ensure it is in PATH.

---

## Security
- Never commit `.env`.
- Never commit API keys.
- Keep all paths environment-driven and project-relative.
