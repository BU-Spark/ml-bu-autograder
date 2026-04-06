# BU Spark AI Auto Grader

Multimodal grading pipeline for student submissions using extraction + RAG + rubric-aware scoring.

## Run MVP (Top Commands)

### Flask web app (primary)
```bash
cd app
source .venv/bin/activate
python scripts/web/app.py
```
Open: [http://localhost:5000](http://localhost:5000)

### Streamlit app (`mvp_web`) (optional)
```bash
cd app
source .venv/bin/activate
streamlit run scripts/cli/mvp_web.py
```

---

## One-Time Setup

### 1) Install requirements
```bash
cd app
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2) Configure API keys (`app/.env`)
```env
# Use one or more providers
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
GEMINI_API_KEY=
# or GOOGLE_API_KEY=

# Chroma embeddings: openai | google | default
CHROMA_EMBEDDING_PROVIDER=default

# Optional overrides
AUTO_GRADER_RUBRIC_DIR=./data/library/rubrics
AUTO_GRADER_LECTURE_CHUNKS=./outputs/final_phase1/lecture_chunks_hybrid.jsonl
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
GOOGLE_EMBEDDING_MODEL=gemini-embedding-001
```

### 3) Prepare lecture chunks for RAG (required once)
The web apps need `AUTO_GRADER_LECTURE_CHUNKS` pointing to a lecture `chunks.jsonl`.

If you already have one, keep that path.

If not, generate it:
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

---

## What the MVP Does
1. Upload student submission (`pdf`, `pptx`, `xlsx`)
2. Upload/select rubric + assignment
3. Extract structured content into chunks
4. Describe images with selected model provider
5. Index/retrieve lecture context from ChromaDB
6. Grade against rubric and output evidence-backed score

Core flow:
`Upload -> Extract -> Describe -> Index -> Retrieve -> Grade`

---

## Core Paths
From `app/`:
- Pipeline CLI: `scripts/cli/run_pipeline.py`
- Flask app: `scripts/web/app.py`
- Streamlit app: `scripts/cli/mvp_web.py`
- Outputs root: `outputs/final_phase1`
- Library folders:
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
- `*_API_KEY not set`: add the key to `app/.env`, restart app.
- Chroma embedding permission issues: set `CHROMA_EMBEDDING_PROVIDER=default`.
- Missing lecture chunks: set `AUTO_GRADER_LECTURE_CHUNKS` to an existing `chunks.jsonl`.
- OCR weak on scanned PDFs: install Tesseract and verify it is in PATH.

---

## Security
- Never commit `.env`.
- Never commit API keys.
- Keep paths environment-driven and project-relative.
