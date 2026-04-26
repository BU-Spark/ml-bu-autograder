"""
blueprints/lecture.py — /api/index-lectures, /api/lecture-index-stats,
                         /api/lecture-search, /api/add-web-links, /api/summarize-web-link
"""
from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

from flask import Blueprint, jsonify, request

from web.config import (
    DEFAULT_LECTURE_CHUNKS,
    OUTPUT_ROOT,
    SCRIPTS_DIR,
    SHARED_LECTURE_COLLECTION,
)
from web.utils.pipeline import (
    _cli,
    _embedding_env,
    _embedding_provider,
    _run,
    _shared_chroma_dir,
    _shared_chroma_ready,
)
from web.utils.web_scraper import fetch_page_text, resolve_summarizer_api_key, summarize_text

lecture_bp = Blueprint("lecture", __name__)


@lecture_bp.route("/api/index-lectures", methods=["POST"])
def api_index_lectures():
    if not DEFAULT_LECTURE_CHUNKS.exists():
        return jsonify(success=False, error=f"Lecture chunks not found at: {DEFAULT_LECTURE_CHUNKS}"), 404

    chroma_dir = _shared_chroma_dir()
    chroma_dir.mkdir(parents=True, exist_ok=True)
    code, out = _run(_cli() + [
        "--mode", "index",
        "--chunks-jsonl", str(DEFAULT_LECTURE_CHUNKS),
        "--chroma-path", str(chroma_dir),
        "--chroma-collection", SHARED_LECTURE_COLLECTION,
        "--output-root", str(OUTPUT_ROOT),
        "--run-id", "shared_lecture_index",
    ], extra_env=_embedding_env())

    if code != 0:
        return jsonify(success=False, error="Lecture indexing failed.", log=out[-3000:]), 500
    return jsonify(success=True, message="Lecture index built successfully.", log=out[-1000:])


@lecture_bp.route("/api/lecture-index-stats")
def api_lecture_index_stats():
    if not DEFAULT_LECTURE_CHUNKS.exists():
        return jsonify(success=False, error="No lecture chunks file found.")

    lines = [l for l in DEFAULT_LECTURE_CHUNKS.read_text(encoding="utf-8").splitlines() if l.strip()]
    total_chunks = len(lines)

    files: dict = defaultdict(lambda: {
        "filename": "", "format": "", "chunks": 0,
        "tag_counts": defaultdict(int), "sample": "",
        "is_web": False, "web_url": "", "web_title": "",
    })
    format_counts: dict = defaultdict(int)
    tag_counts:    dict = defaultdict(int)
    total_chars = 0

    for line in lines:
        try:
            c = json.loads(line)
        except Exception:
            continue
        meta    = c.get("metadata", {}) or {}
        fname   = meta.get("filename", "unknown")
        fmt     = meta.get("format", "unknown")
        tag     = meta.get("element_tag") or fmt
        content = str(c.get("content", ""))

        f = files[fname]
        f["filename"] = fname
        f["format"]   = fmt
        f["chunks"]  += 1
        f["tag_counts"][tag] = f["tag_counts"].get(tag, 0) + 1
        if not f["sample"]:
            f["sample"] = content[:200]
        if fmt == "web_summary":
            f["is_web"]     = True
            f["web_url"]    = meta.get("web_url", "")
            f["web_title"]  = meta.get("web_title", "")

        format_counts[fmt] += 1
        tag_counts[tag]     = tag_counts.get(tag, 0) + 1
        total_chars        += len(content)

    sorted_files = sorted(files.values(), key=lambda x: (x["is_web"], -x["chunks"]))
    for f in sorted_files:
        f["tag_counts"] = dict(f["tag_counts"])

    return jsonify(
        success=True,
        total_chunks=total_chunks,
        total_files=len(files),
        total_chars=total_chars,
        avg_chunk_chars=round(total_chars / max(1, total_chunks)),
        format_breakdown=dict(format_counts),
        tag_breakdown=dict(tag_counts),
        chroma_ready=_shared_chroma_ready(),
        embedding_provider=_embedding_provider(),
        files=sorted_files,
    )


@lecture_bp.route("/api/lecture-search")
def api_lecture_search():
    query = request.args.get("q", "").strip()
    top_k = int(request.args.get("k", "5"))
    if not query:
        return jsonify(success=False, error="No query provided.")
    if not _shared_chroma_ready():
        return jsonify(success=False, error="Lecture index not ready. Click 'Build Lecture Index' first.")

    try:
        import chromadb
        if str(SCRIPTS_DIR) not in sys.path:
            sys.path.insert(0, str(SCRIPTS_DIR))
        from storage.chroma_store import _build_embedding_function

        client   = chromadb.PersistentClient(path=str(_shared_chroma_dir()))
        embed_fn = _build_embedding_function()
        col = (
            client.get_or_create_collection("lecture_v1", embedding_function=embed_fn)
            if embed_fn else
            client.get_or_create_collection("lecture_v1")
        )
        result = col.query(
            query_texts=[query],
            n_results=min(top_k, col.count()),
            include=["documents", "metadatas", "distances"],
        )
        docs  = (result.get("documents") or [[]])[0]
        metas = (result.get("metadatas") or [[]])[0]
        dists = (result.get("distances") or [[]])[0]
        hits  = [
            {
                "content":      doc[:400],
                "filename":     (meta or {}).get("filename", ""),
                "element_tag":  (meta or {}).get("element_tag", ""),
                "distance":     round(float(dist), 4),
                "relevance_pct": round(max(0, (1 - float(dist) / 2)) * 100, 1),
            }
            for doc, meta, dist in zip(docs, metas, dists)
        ]
        return jsonify(success=True, query=query, hits=hits)
    except Exception as exc:
        return jsonify(success=False, error=str(exc))


@lecture_bp.route("/api/add-web-links", methods=["POST"])
def api_add_web_links():
    data     = request.get_json(silent=True) or {}
    urls: list[str] = [u.strip() for u in (data.get("urls") or []) if u.strip()]
    provider = str(data.get("provider") or "openai").lower()
    model    = str(data.get("model") or "").strip()

    if not urls:
        return jsonify(success=False, error="No URLs provided."), 400

    api_key, model = resolve_summarizer_api_key(provider, model)
    if provider not in {"openai", "gemini", "anthropic"}:
        return jsonify(success=False, error=f"Unknown provider: {provider}"), 400
    if not api_key:
        return jsonify(success=False, error=f"No API key found for provider '{provider}'."), 400

    if str(SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_DIR))
    from core.chunking import chunk_text, sha1_id, make_sort_key

    results: list[dict]    = []
    new_chunks: list[dict] = []

    for url in urls:
        try:
            title, page_text, _ = fetch_page_text(url)
            if len(page_text) < 50:
                results.append({"url": url, "ok": False, "error": "Page too short or empty."})
                continue
            summary = summarize_text(title, page_text, provider=provider, model=model, api_key=api_key)
            if not summary:
                results.append({"url": url, "ok": False, "error": "LLM returned empty summary."})
                continue

            slug = re.sub(r"[^a-z0-9]+", "_", url.lower())[:60]
            url_chunk_count = 0
            for ci, piece in enumerate(chunk_text(summary, 1800, 140), 1):
                if len(piece) < 20:
                    continue
                cid = sha1_id(f"web_link|{url}|chunk={ci}")
                new_chunks.append({
                    "id":      cid,
                    "content": piece,
                    "metadata": {
                        "filename": slug + ".web", "source_path": url,
                        "source_type": "lecture", "format": "web_summary",
                        "page_number": 1, "block_index": ci,
                        "sort_key": make_sort_key(1, ci), "document_order": ci,
                        "content_type": "text", "element_tag": "web_summary",
                        "web_url": url, "web_title": title,
                        "chunk_index_in_block": ci,
                        "image_quality": None, "image_width_px": None,
                        "image_height_px": None, "image_total_pixels": None,
                        "image_aspect_ratio": None, "is_tiled": None,
                        "tile_count": None, "gpt4o_called": False, "quality_warning": None,
                    },
                })
                url_chunk_count += 1
            results.append({"url": url, "ok": True, "title": title,
                             "summary_chars": len(summary), "chunks": url_chunk_count})
        except Exception as exc:
            results.append({"url": url, "ok": False, "error": str(exc)[:200]})

    if not new_chunks:
        return jsonify(success=False, error="No chunks generated from provided URLs.", results=results)

    chunks_path = DEFAULT_LECTURE_CHUNKS
    if not chunks_path.exists():
        chunks_path.parent.mkdir(parents=True, exist_ok=True)
        chunks_path.write_text("", encoding="utf-8")

    existing_ids: set[str] = set()
    for line in chunks_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                existing_ids.add(json.loads(line)["id"])
            except Exception:
                pass

    added_count = 0
    with chunks_path.open("a", encoding="utf-8") as f:
        for chunk in new_chunks:
            if chunk["id"] not in existing_ids:
                f.write(json.dumps(chunk, ensure_ascii=False) + "\n")
                added_count += 1

    if added_count == 0:
        return jsonify(success=True, message="All URLs already indexed.", results=results)

    chroma_dir = _shared_chroma_dir()
    chroma_dir.mkdir(parents=True, exist_ok=True)
    code, out = _run(_cli() + [
        "--mode", "index",
        "--chunks-jsonl", str(chunks_path),
        "--chroma-path", str(chroma_dir),
        "--chroma-collection", SHARED_LECTURE_COLLECTION,
        "--output-root", str(OUTPUT_ROOT),
        "--run-id", "shared_lecture_index",
    ], extra_env=_embedding_env())

    if code != 0:
        return jsonify(success=False, error="Chunks saved but Chroma re-index failed.",
                       added_chunks=added_count, results=results, log=out[-1000:]), 500

    return jsonify(
        success=True,
        message=f"Indexed {added_count} new chunk(s) from {sum(1 for r in results if r['ok'])} URL(s).",
        added_chunks=added_count,
        results=results,
    )


@lecture_bp.route("/api/summarize-web-link", methods=["POST"])
def api_summarize_web_link():
    data     = request.get_json(silent=True) or {}
    url      = str(data.get("url") or "").strip()
    provider = str(data.get("provider") or "openai").lower()
    model    = str(data.get("model") or "").strip()

    if not url:
        return jsonify(success=False, error="No URL provided."), 400

    api_key, model = resolve_summarizer_api_key(provider, model)
    if provider not in {"openai", "gemini", "anthropic"}:
        return jsonify(success=False, error=f"Unknown provider: {provider}"), 400
    if not api_key:
        return jsonify(success=False, error=f"No API key found for provider '{provider}'."), 400

    try:
        title, page_text, preview_lines = fetch_page_text(url)
        if len(page_text) < 50:
            return jsonify(success=False, error="Page too short or empty after extraction.")
        summary = summarize_text(title, page_text, provider=provider, model=model,
                                 api_key=api_key, max_tokens=700)
        if not summary:
            return jsonify(success=False, error="LLM returned empty summary.")
        return jsonify(
            success=True, url=url, title=title,
            extracted_chars=len(page_text), extracted_lines=len(preview_lines),
            raw_preview=preview_lines, summary=summary,
            model_used=model, provider=provider,
        )
    except Exception as exc:
        return jsonify(success=False, error=str(exc)[:300])
