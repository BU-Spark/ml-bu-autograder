"""
Evaluate chunking strategies for RAG grading: compare AI grades to professor grades.
Uses HTML lectures as context, Quiz 1 Excel for student answers + human scores.

API keys (env vars): OPENAI_API_KEY, ANTHROPIC_API_KEY, GOOGLE_API_KEY
"""

from pathlib import Path
import argparse
import json
import os
import re

# Column names in Excel - exact or partial match (script also tries contains "answer"/"score")
EXCEL_ANSWER_COLS = [
    "Student Answer",
    "Answer",
    "Response",
    "student_answer",
    "answer",
    "Why do we need to do Business Process Re-engineering as a part of implementing an EHR?",  # Quiz 1 long header
]
EXCEL_PROF_COLS = [
    "Human Score",
    "Professor Score",
    "Instructor Score",
    "Human Grade",
    "Prof Score",
    "human_score",
    "Score",
    "Grade",
]

BASE_DIR = Path(__file__).parent.resolve()
DATA_DIR = BASE_DIR / "fall 2025 cs 581 quiz and assignment data"
LECTURES_DIR = BASE_DIR / "Spring 2026" / "Lectures [html versions]"
RUBRIC_PATH = DATA_DIR / "New Refined Rubrics" / "quiz_1" / "quiz_1.json"
EXCEL_PATH = DATA_DIR / "Quiz 1" / "CS 581 Quiz 1 AI vs Human Anonymized.xlsx"


def _first_match(df, candidates, default=None):
    """Return first column name that exists in df (exact or startswith), or default."""
    for c in candidates:
        if c in df.columns:
            return c
        for col in df.columns:
            if col.strip().startswith(c.strip()) or (c.strip() and c.strip() in col):
                return col
    return default


def _first_match_contains(df, *keywords):
    """Return first column whose name contains any of the keywords (case-insensitive)."""
    for col in df.columns:
        lower = str(col).lower()
        if any(kw.lower() in lower for kw in keywords):
            return col
    return None


def load_eval_data(excel_path: Path, answer_col=None, prof_col=None):
    """Load student answers and professor grades from Excel."""
    import pandas as pd

    xl = pd.ExcelFile(excel_path)
    df = None
    for sheet in xl.sheet_names:
        _df = pd.read_excel(excel_path, sheet_name=sheet)
        _answer = answer_col or _first_match(_df, EXCEL_ANSWER_COLS) or _first_match_contains(_df, "answer", "response", "why do we need")
        _prof = prof_col or _first_match(_df, EXCEL_PROF_COLS) or _first_match_contains(_df, "human", "score", "grade", "prof", "instructor")
        if _answer and _prof:
            df = _df
            answer_col = _answer
            prof_col = _prof
            break
    if df is None:
        df = pd.read_excel(excel_path, sheet_name=0)
        answer_col = answer_col or _first_match(df, EXCEL_ANSWER_COLS) or _first_match_contains(df, "answer", "response", "why do we need")
        prof_col = prof_col or _first_match(df, EXCEL_PROF_COLS) or _first_match_contains(df, "human", "score", "grade", "prof", "instructor")

    if not answer_col:
        raise ValueError(
            f"Could not find answer column. Columns: {df.columns.tolist()}. "
            "Set answer_col explicitly."
        )
    if not prof_col:
        raise ValueError(
            f"Could not find professor score column. Sheets: {xl.sheet_names}. Columns on first sheet: {df.columns.tolist()}. "
            "Use a sheet that has both student answers and human scores, or set prof_col explicitly."
        )

    rows = []
    for _, r in df.iterrows():
        ans = r.get(answer_col)
        prof = r.get(prof_col)
        if pd.isna(ans) or str(ans).strip() == "":
            continue
        try:
            prof_score = float(prof) if not pd.isna(prof) else None
        except (TypeError, ValueError):
            prof_score = None
        if prof_score is None:
            continue
        rows.append({"answer": str(ans).strip(), "prof_score": prof_score})
    return rows


def load_rubric(path: Path) -> str:
    """Build grading rubric string from quiz JSON."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    parts = [data.get("overall_instructor_guidelines", "")]
    for sr in data.get("sub_rubrics", []):
        parts.append(sr.get("instructor_guideline", ""))
        for gc in sr.get("grading_criteria", []):
            parts.append(f"- {gc.get('criteria_id', '')}: {gc.get('criteria', '')}")
    return "\n\n".join(p for p in parts if p)


def build_chunks_from_lectures(root_dir: Path, strategy: str) -> list[dict]:
    """Build list of {text, metadata} chunks using given strategy."""
    from html_lecture_ingest import iter_lecture_html, extract_text_from_html
    from chunking_strategies import chunk_by_semantic, chunk_by_fixed_tokens, chunk_hybrid

    root_dir = Path(root_dir).resolve()
    # If default root has no lectures, try Spring 2026 explicitly
    candidates = [root_dir]
    if (root_dir / "Spring 2026").exists():
        candidates.append(root_dir / "Spring 2026")

    chunks = []
    for _root in candidates:
        for html_path in iter_lecture_html(str(_root)):
            try:
                text = extract_text_from_html(html_path)
            except Exception:
                continue
            if not text.strip():
                continue

            if strategy == "semantic":
                texts = chunk_by_semantic(text, max_chars=4000)
            elif strategy == "fixed":
                texts = chunk_by_fixed_tokens(text, chunk_chars=800, overlap_chars=150)
            elif strategy == "hybrid":
                texts = chunk_hybrid(text, max_chars=4000, sub_chunk=800)
            else:
                raise ValueError(f"Unknown strategy: {strategy}")

            for i, t in enumerate(texts):
                chunks.append({"text": t, "metadata": {"source": html_path.name, "strategy": strategy}})
        if chunks:
            break
    return chunks


_emb_model = None


def _get_emb_model():
    """Lazily load a local sentence-transformers model for embeddings."""
    global _emb_model
    if _emb_model is None:
        from sentence_transformers import SentenceTransformer

        # Small, fast, widely-used open-source embedding model
        _emb_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    return _emb_model


def embed_chunks(chunks: list[dict]) -> list[dict]:
    """Embed chunks locally using an open-source model. Returns chunks with 'embedding' key."""
    model = _get_emb_model()
    texts = [c["text"] for c in chunks]
    # Encode in batches for efficiency
    embeddings = model.encode(texts, batch_size=64, show_progress_bar=False)
    for c, emb in zip(chunks, embeddings):
        c["embedding"] = emb.tolist()
    return chunks


def embed_query(query: str) -> list[float]:
    """Embed a single query using the same local model."""
    model = _get_emb_model()
    emb = model.encode([query])[0]
    return emb.tolist()


def cosine_sim(a: list[float], b: list[float]) -> float:
    """Cosine similarity."""
    import math
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def retrieve(chunks: list[dict], query: str, k: int = 5) -> list[str]:
    """Retrieve top-k chunk texts by similarity to query."""
    q_emb = embed_query(query)
    scored = [(cosine_sim(c["embedding"], q_emb), c["text"]) for c in chunks]
    scored.sort(key=lambda x: -x[0])
    return [t for _, t in scored[:k]]


# LLM configs: (provider, model_id, env_var)
# Allowed OpenAI model identifiers (use exact strings)
OPENAI_MODELS = (
    "gpt-4o-2024-11-20",
    "gpt-4o-2024-08-06",
    "gpt-4o-mini-2024-07-18",
    "gpt-4o-mini",
    "gpt-4o-2024-05-13",
)

LLM_CONFIGS = {
    "openai": ("openai", OPENAI_MODELS[0], "OPENAI_API_KEY"),  # default: gpt-4o-2024-11-20
    "claude": ("anthropic", "claude-3-5-sonnet-20241022", "ANTHROPIC_API_KEY"),
    "gemini": ("google", "gemini-1.5-flash", "GOOGLE_API_KEY"),
}


def grade_with_llm(
    rubric: str,
    context: str,
    student_answer: str,
    provider: str = "openai",
    model_id: str | None = None,
) -> float | None:
    """Call LLM to grade; return numeric score or None on failure."""
    cfg = LLM_CONFIGS.get(provider)
    if not cfg:
        raise ValueError(f"Unknown provider: {provider}. Use one of: {list(LLM_CONFIGS)}")
    prov, default_model, env_var = cfg
    # For OpenAI, use provided model_id or default; must be one of OPENAI_MODELS
    if prov == "openai":
        model_id = model_id or default_model
        if model_id not in OPENAI_MODELS:
            model_id = default_model
    else:
        model_id = model_id or default_model

    if not os.environ.get(env_var):
        return None

    prompt = f"""You are grading a short-answer quiz question. Use ONLY the rubric and retrieved context below.

RUBRIC:
{rubric}

RETRIEVED LECTURE CONTEXT (for reference):
{context[:6000]}

STUDENT ANSWER:
{student_answer}

Respond with ONLY a single number (the score, e.g. 12 or 8.5). No explanation. Maximum 16 points for this question."""

    try:
        if prov == "openai":
            from openai import OpenAI
            client = OpenAI()
            resp = client.chat.completions.create(
                model=model_id,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
            )
            content = resp.choices[0].message.content.strip()
        elif prov == "anthropic":
            from anthropic import Anthropic
            client = Anthropic()
            resp = client.messages.create(
                model=model_id,
                max_tokens=64,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
            )
            content = resp.content[0].text.strip()
        elif prov == "google":
            import google.generativeai as genai
            genai.configure(api_key=os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY"))
            model = genai.GenerativeModel(model_id)
            resp = model.generate_content(prompt, generation_config={"temperature": 0})
            content = resp.text.strip() if resp.text else ""
        else:
            return None

        m = re.search(r"[\d.]+", content)
        return float(m.group()) if m else None
    except Exception:
        return None


def run_eval(
    excel_path: Path = EXCEL_PATH,
    rubric_path: Path = RUBRIC_PATH,
    lectures_root: Path = BASE_DIR,
    strategies: list[str] | None = None,
    models: list[str] | None = None,
    openai_model: str | None = None,
    max_eval: int = 15,
    k_retrieve: int = 5,
    out_path: Path | None = None,
):
    """Run evaluation: load data, build indexes per strategy, grade with each LLM, compute MAE."""
    strategies = strategies or ["semantic", "fixed", "hybrid"]
    models = models or ["openai", "claude", "gemini"]
    openai_model = openai_model or OPENAI_MODELS[0]

    def has_key(m):
        env_var = LLM_CONFIGS.get(m, ("", "", ""))[2]
        if m == "gemini":
            return bool(os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY"))
        return bool(os.environ.get(env_var))

    available = [m for m in models if has_key(m)]
    if not available:
        print("No LLM API keys found. Set OPENAI_API_KEY, ANTHROPIC_API_KEY, and/or GOOGLE_API_KEY.")
        return
    print(f"Using LLMs: {available}")

    if not excel_path.exists():
        print(f"Excel not found: {excel_path}")
        print("  Update EXCEL_PATH or pass --excel. Expected columns for answer: " + ", ".join(EXCEL_ANSWER_COLS[:3]))
        print("  For professor score: " + ", ".join(EXCEL_PROF_COLS[:3]))
        return

    print("Loading eval data...")
    eval_rows = load_eval_data(excel_path)
    eval_rows = eval_rows[:max_eval]
    print(f"  {len(eval_rows)} rows")

    print("Loading rubric...")
    rubric = load_rubric(rubric_path)

    query = "Business Process Re-engineering BPR EHR implementation workflows interoperability"

    results = {}
    for strategy in strategies:
        print(f"\n--- Strategy: {strategy} ---")
        chunks = build_chunks_from_lectures(lectures_root, strategy)
        if not chunks:
            print(f"  No chunks for {strategy}; skipping.")
            if strategy == "semantic":
                p = Path(lectures_root).resolve()
                hint = p / "Lectures [html versions]" if (p / "Lectures [html versions]").exists() else p / "Spring 2026" / "Lectures [html versions]"
                print(f"  Hint: ensure .html or .htm lectures exist under: {hint}")
                print(f"  Or pass --lectures /path/to/parent/of/Lectures [html versions]")
            continue
        print(f"  {len(chunks)} chunks")
        chunks = embed_chunks(chunks)

        for model_name in available:
            errors = []
            print(f"  [{model_name}]")
            for i, row in enumerate(eval_rows):
                context_chunks = retrieve(chunks, query, k=k_retrieve)
                context = "\n\n---\n\n".join(context_chunks)
                model_id = openai_model if model_name == "openai" else None
                ai_score = grade_with_llm(rubric, context, row["answer"], provider=model_name, model_id=model_id)
                if ai_score is not None:
                    err = abs(ai_score - row["prof_score"])
                    errors.append(err)
                    print(f"    Row {i+1}: prof={row['prof_score']} ai={ai_score:.1f} err={err:.1f}")
            if errors:
                mae = sum(errors) / len(errors)
                key = f"{strategy}+{model_name}"
                results[key] = {"mae": mae, "n": len(errors)}
                print(f"    MAE = {mae:.2f} (n={len(errors)})")

    print("\n=== Summary ===")
    for key, r in results.items():
        print(f"  {key}: MAE = {r['mae']:.2f}")

    if results:
        best_key = min(results, key=lambda k: results[k]["mae"])
        best_mae = results[best_key]["mae"]
        print(f"\n>>> Best: {best_key} (MAE = {best_mae:.2f})")

    # Optionally write results to a JSON file
    if out_path is not None:
        payload = {
            "results": results,
            "best": {"key": best_key, "mae": best_mae} if results else None,
            "config": {
                "strategies": strategies,
                "models": models,
                "openai_model": openai_model,
                "max_eval": max_eval,
                "k_retrieve": k_retrieve,
            },
        }
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

    return results


def inspect_excel(path: Path):
    """Print Excel columns and sample rows for column mapping."""
    import pandas as pd
    df = pd.read_excel(path, sheet_name=0)
    print("Columns:", df.columns.tolist())
    print("\nFirst 2 rows (answer-like, score-like):")
    if df.empty:
        print("  (no rows in sheet)")
    else:
        for c in df.columns:
            if any(k in str(c).lower() for k in ["answer", "response", "score", "grade", "human"]):
                print(f"  {c}: {df[c].iloc[0]!r} ...")


def _parse_args():
    p = argparse.ArgumentParser(description="Evaluate chunking strategies for RAG grading.")
    p.add_argument("--inspect", action="store_true", help="Print Excel columns and exit")
    p.add_argument("--excel", default=str(EXCEL_PATH), help="Path to Quiz Excel")
    p.add_argument("--rubric", default=str(RUBRIC_PATH), help="Path to rubric JSON")
    p.add_argument("--lectures", default=str(BASE_DIR), help="Root dir containing Lectures [html versions]")
    p.add_argument("--strategies", nargs="+", default=["semantic", "fixed", "hybrid"])
    p.add_argument("--models", nargs="+", default=["openai", "claude", "gemini"],
                   help="LLMs to use: openai, claude, gemini")
    p.add_argument("--openai-model", default=OPENAI_MODELS[0], choices=OPENAI_MODELS,
                   help=f"OpenAI model (default: {OPENAI_MODELS[0]})")
    p.add_argument("--max-eval", type=int, default=15, help="Max evaluation rows")
    p.add_argument("--k", type=int, default=5, help="Retrieve top-k chunks")
    p.add_argument("--out", default="chunking_eval_results.json",
                   help="Path to write JSON results (default: chunking_eval_results.json)")
    return p.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    if args.inspect:
        inspect_excel(Path(args.excel))
    else:
        run_eval(
            excel_path=Path(args.excel),
            rubric_path=Path(args.rubric),
            lectures_root=Path(args.lectures),
            strategies=args.strategies,
            models=args.models,
            openai_model=args.openai_model,
            max_eval=args.max_eval,
            k_retrieve=args.k,
            out_path=Path(args.out) if args.out else None,
        )
