from __future__ import annotations

import json
from pathlib import Path
from typing import Any


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
        client = chromadb.PersistentClient(path=chroma_path)
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
