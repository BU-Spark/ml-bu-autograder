# Chunking & grading evaluation

Scripts for evaluating HTML lecture chunking strategies and LLM graders against professor scores (CS 581 pilot).

- **html_lecture_ingest.py** – Ingest HTML/HTM lectures under `Lectures [html versions]` into RAG-ready JSONL.
- **chunking_strategies.py** – Semantic, fixed-window, and hybrid chunking.
- **eval_chunking_grading.py** – Load Quiz Excel + rubric, build chunk indexes, retrieve top-k, grade with OpenAI/Claude/Gemini, report MAE. Uses local `sentence-transformers` embeddings for retrieval.

Install: `pip install -r requirements-eval.txt`. Set API keys via env (e.g. `OPENAI_API_KEY`) only for the grading models you use. Output: `chunking_eval_results.json` (or `--out`).
