from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def _build_openai_embedding_function():
    """
    Construct an OpenAI embedding function for Chroma using the OPENAI_API_KEY.
    Falls back to None if chromadb's embedding utilities are unavailable.
    Disabled by default; enable with CHROMA_USE_OPENAI_EMBEDDINGS=1.
    """
    use_openai = str(os.getenv("CHROMA_USE_OPENAI_EMBEDDINGS", "0")).strip().lower() in {"1", "true", "yes"}
    if not use_openai:
        return None

    try:
        from chromadb.utils import embedding_functions
    except Exception:
        return None

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    model_name = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
    return embedding_functions.OpenAIEmbeddingFunction(
        model_name=model_name,
        api_key=api_key,
    )


def try_store_chroma(
    chunks: list[dict[str, Any]],
    chroma_path: str,
    chroma_collection: str,
    chroma_batch_size: int,
) -> dict[str, Any]:
    try:
        import chromadb
    except Exception as exc:
        return {"enabled": True, "ok": False, "error": f"chromadb import failed: {exc}"}

    Path(chroma_path).mkdir(parents=True, exist_ok=True)
    try:
        embed_fn = _build_openai_embedding_function()
        client = chromadb.PersistentClient(path=chroma_path)
        if embed_fn is not None:
            collection = client.get_or_create_collection(name=chroma_collection, embedding_function=embed_fn)
        else:
            collection = client.get_or_create_collection(name=chroma_collection)

        ids = [c["id"] for c in chunks]
        docs = [c["content"] for c in chunks]
        metas = []
        for c in chunks:
            m = dict(c.get("metadata", {}))
            flat = {}
            for k, v in m.items():
                if v is None:
                    continue
                if isinstance(v, (str, int, float, bool)):
                    flat[k] = v
                else:
                    flat[k] = json.dumps(v, ensure_ascii=True)
            metas.append(flat)

        # Prefer upsert to make re-indexing idempotent.
        upsert = getattr(collection, "upsert", None)
        write_fn = upsert if callable(upsert) else collection.add

        for start in range(0, len(chunks), max(1, chroma_batch_size)):
            end = min(len(chunks), start + max(1, chroma_batch_size))
            write_fn(ids=ids[start:end], documents=docs[start:end], metadatas=metas[start:end])

        return {
            "enabled": True,
            "ok": True,
            "collection": chroma_collection,
            "path": chroma_path,
            "records_added": len(chunks),
        }
    except Exception as exc:
        return {"enabled": True, "ok": False, "error": str(exc)}
