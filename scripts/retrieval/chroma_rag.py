from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def filter_chunks_by_source_type(chunks: list[dict[str, Any]], source_type: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for c in chunks:
        md = c.get("metadata", {}) or {}
        if str(md.get("source_type", "")).lower() == source_type.lower():
            out.append(c)
    return out


@dataclass
class IndexResult:
    ok: bool
    error: str | None
    records_indexed: int
    records_total: int
    chroma_result: dict[str, Any] | None


def index_lecture_chunks_to_chroma(
    *,
    chunks_jsonl: Path,
    chroma_path: str,
    chroma_collection: str,
    chroma_batch_size: int,
    lecture_source_type: str = "lecture",
) -> IndexResult:
    from storage.chroma_store import try_store_chroma

    all_chunks = read_jsonl(chunks_jsonl)
    lecture_chunks = filter_chunks_by_source_type(all_chunks, lecture_source_type)
    chroma_result = try_store_chroma(
        chunks=lecture_chunks,
        chroma_path=chroma_path,
        chroma_collection=chroma_collection,
        chroma_batch_size=chroma_batch_size,
    )
    ok = bool(chroma_result.get("ok")) if chroma_result.get("enabled") else False
    err = chroma_result.get("error") if not ok else None
    return IndexResult(
        ok=ok,
        error=err,
        records_indexed=len(lecture_chunks),
        records_total=len(all_chunks),
        chroma_result=chroma_result,
    )


@dataclass
class RetrievalItem:
    student_chunk_id: str
    student_source_path: str
    student_content_type: str
    query_text: str
    top_k: int
    results: dict[str, Any]


def retrieve_lecture_context_for_student_chunks(
    *,
    chroma_path: str,
    chroma_collection: str,
    student_chunks_jsonl: Path,
    top_k: int,
    out_jsonl: Path,
    student_source_type: str = "student",
) -> dict[str, Any]:
    try:
        import chromadb
        from chromadb.utils import embedding_functions
    except Exception as exc:
        raise RuntimeError(f"chromadb import failed: {exc}") from exc

    student_chunks = filter_chunks_by_source_type(read_jsonl(student_chunks_jsonl), student_source_type)
    client = chromadb.PersistentClient(path=chroma_path)

    embed_fn = None
    api_key = os.getenv("OPENAI_API_KEY")
    use_openai = str(os.getenv("CHROMA_USE_OPENAI_EMBEDDINGS", "0")).strip().lower() in {"1", "true", "yes"}
    if api_key and use_openai:
        model_name = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
        embed_fn = embedding_functions.OpenAIEmbeddingFunction(
            model_name=model_name,
            api_key=api_key,
        )

    if embed_fn is not None:
        collection = client.get_or_create_collection(name=chroma_collection, embedding_function=embed_fn)
    else:
        collection = client.get_or_create_collection(name=chroma_collection)

    out_jsonl.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with out_jsonl.open("w", encoding="utf-8") as f:
        for c in student_chunks:
            md = c.get("metadata", {}) or {}
            query_text = str(c.get("content", "") or "").strip()
            if not query_text:
                continue

            q = collection.query(query_texts=[query_text], n_results=int(top_k))
            item = RetrievalItem(
                student_chunk_id=str(c.get("id", "")),
                student_source_path=str(md.get("source_path", "")),
                student_content_type=str(md.get("content_type", "")),
                query_text=query_text,
                top_k=int(top_k),
                results=q,
            )
            f.write(json.dumps(item.__dict__, ensure_ascii=True) + "\n")
            written += 1

    return {
        "ok": True,
        "student_chunks_considered": len(student_chunks),
        "queries_written": written,
        "out_jsonl": str(out_jsonl),
        "chroma_path": chroma_path,
        "chroma_collection": chroma_collection,
        "top_k": int(top_k),
    }


def retrieve_lecture_context_for_assignment(
    *,
    chroma_path: str,
    chroma_collection: str,
    assignment_file: Path,
    top_k: int,
    out_jsonl: Path,
    chunk_size: int = 1000,
) -> dict[str, Any]:
    """Query the lecture ChromaDB using assignment description text as queries.

    Splits the assignment text into overlapping chunks and queries the lecture
    index with each chunk. Results are written in the same JSONL format as
    ``retrieve_lecture_context_for_student_chunks`` so grading is unchanged.
    """
    try:
        import chromadb
        from chromadb.utils import embedding_functions
    except Exception as exc:
        raise RuntimeError(f"chromadb import failed: {exc}") from exc

    # Read assignment text — reuse the same reader from grading if available,
    # otherwise fall back to plain UTF-8.
    assignment_text = ""
    suffix = assignment_file.suffix.lower()
    if suffix in {".txt", ".md"}:
        assignment_text = assignment_file.read_text(encoding="utf-8", errors="ignore").strip()
    elif suffix == ".docx":
        try:
            from docx import Document
            doc = Document(str(assignment_file))
            assignment_text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
        except Exception:
            assignment_text = assignment_file.read_text(encoding="utf-8", errors="ignore").strip()
    elif suffix == ".pdf":
        try:
            import fitz  # PyMuPDF
            pdf = fitz.open(str(assignment_file))
            assignment_text = "\n".join(page.get_text() for page in pdf)
        except Exception:
            assignment_text = ""
    else:
        assignment_text = assignment_file.read_text(encoding="utf-8", errors="ignore").strip()

    if not assignment_text:
        out_jsonl.parent.mkdir(parents=True, exist_ok=True)
        out_jsonl.write_text("")
        return {"ok": True, "queries_written": 0, "note": "assignment file was empty"}

    # Split into overlapping chunks to cover the whole assignment
    overlap = chunk_size // 4
    queries: list[str] = []
    start = 0
    while start < len(assignment_text):
        chunk = assignment_text[start: start + chunk_size].strip()
        if chunk:
            queries.append(chunk)
        start += chunk_size - overlap
        if start >= len(assignment_text):
            break

    client = chromadb.PersistentClient(path=chroma_path)
    embed_fn = None
    api_key = os.getenv("OPENAI_API_KEY")
    use_openai = str(os.getenv("CHROMA_USE_OPENAI_EMBEDDINGS", "0")).strip().lower() in {"1", "true", "yes"}
    if api_key and use_openai:
        model_name = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
        embed_fn = embedding_functions.OpenAIEmbeddingFunction(
            model_name=model_name,
            api_key=api_key,
        )

    if embed_fn is not None:
        collection = client.get_or_create_collection(name=chroma_collection, embedding_function=embed_fn)
    else:
        collection = client.get_or_create_collection(name=chroma_collection)

    out_jsonl.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with out_jsonl.open("w", encoding="utf-8") as f:
        for i, query_text in enumerate(queries):
            q = collection.query(query_texts=[query_text], n_results=int(top_k))
            item = RetrievalItem(
                student_chunk_id=f"assignment_query_{i}",
                student_source_path=str(assignment_file),
                student_content_type="assignment",
                query_text=query_text,
                top_k=int(top_k),
                results=q,
            )
            f.write(json.dumps(item.__dict__, ensure_ascii=True) + "\n")
            written += 1

    return {
        "ok": True,
        "assignment_file": str(assignment_file),
        "queries_written": written,
        "out_jsonl": str(out_jsonl),
        "chroma_path": chroma_path,
        "chroma_collection": chroma_collection,
        "top_k": int(top_k),
    }


__all__ = [
    "index_lecture_chunks_to_chroma",
    "retrieve_lecture_context_for_student_chunks",
    "retrieve_lecture_context_for_assignment",
    "IndexResult",
    "RetrievalItem",
]
