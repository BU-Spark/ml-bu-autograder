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
    if api_key:
        embed_fn = embedding_functions.OpenAIEmbeddingFunction(
            model_name="text-embedding-3-large",
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


__all__ = [
    "index_lecture_chunks_to_chroma",
    "retrieve_lecture_context_for_student_chunks",
    "IndexResult",
    "RetrievalItem",
]

