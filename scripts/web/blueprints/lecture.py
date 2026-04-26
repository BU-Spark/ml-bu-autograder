"""
blueprints/lecture.py — /api/index-lectures, /api/lecture-index-stats,
                         /api/lecture-search, /api/add-web-links, /api/summarize-web-link
                         /api/library/lectures  (list / upload / delete)
                         /api/describe-lecture  (describe PDF → image-quality flags)
                         /api/push-lecture-to-rag (append chunks + re-index)
"""
from __future__ import annotations

import json
import re
import shutil
import sys
import uuid
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from werkzeug.utils import secure_filename

from flask import Blueprint, jsonify, request

from web.config import (
    DEFAULT_LECTURE_CHUNKS,
    LIBRARY_LECTURES_DIR,
    OUTPUT_ROOT,
    PROVIDERS,
    SCRIPTS_DIR,
    SHARED_LECTURE_COLLECTION,
    SUPPORT_ALLOWED_EXTS,
)
from web.utils.files import _safe
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

# ── helpers ────────────────────────────────────────────────────────────────

_IMAGE_POOR_WORDS = {
    "unclear", "blurry", "blur", "cannot", "not visible", "blank", "empty",
    "nothing", "n/a", "unreadable", "illegible", "no text", "no description",
    "not described", "not available", "none", "poor quality",
}

def _flag_chunk(chunk: dict) -> str | None:
    """Return a flag string if the chunk has image quality issues, else None."""
    meta         = chunk.get("metadata", {}) or {}
    content      = str(chunk.get("content", "") or "").strip()
    element_tag  = str(meta.get("element_tag", "") or "")
    content_type = str(meta.get("content_type", "") or "")

    is_image = element_tag in ("img_alt", "image", "figure") or content_type == "image_description"
    if not is_image:
        return None

    if not content or len(content) < 10:
        return "no_description"
    cl = content.lower()
    if any(w in cl for w in _IMAGE_POOR_WORDS):
        return "poor_quality"
    if len(content) < 25:
        return "very_short"
    return None


# ── Lecture library: list / upload / delete ────────────────────────────────

@lecture_bp.route("/api/library/lectures")
def api_list_lectures():
    LIBRARY_LECTURES_DIR.mkdir(parents=True, exist_ok=True)
    files = []
    for f in sorted(LIBRARY_LECTURES_DIR.iterdir()):
        if f.suffix.lower() in SUPPORT_ALLOWED_EXTS | {".pdf"}:
            files.append({
                "name":    f.name,
                "size_kb": round(f.stat().st_size / 1024, 1),
                "path":    str(f),
            })
    return jsonify(success=True, files=files)


@lecture_bp.route("/api/library/upload-lecture", methods=["POST"])
def api_upload_lecture():
    uploaded = request.files.get("file")
    if not uploaded or not uploaded.filename:
        return jsonify(success=False, error="No file provided."), 400
    fname = secure_filename(uploaded.filename)
    ext   = Path(fname).suffix.lower()
    if ext not in SUPPORT_ALLOWED_EXTS | {".pdf"}:
        return jsonify(success=False, error=f"Unsupported file type: {ext}"), 400
    LIBRARY_LECTURES_DIR.mkdir(parents=True, exist_ok=True)
    dest = LIBRARY_LECTURES_DIR / fname
    uploaded.save(dest)
    return jsonify(success=True, filename=fname, path=str(dest),
                   size_kb=round(dest.stat().st_size / 1024, 1))


@lecture_bp.route("/api/library/delete-lecture", methods=["POST"])
def api_delete_lecture():
    data     = request.get_json(silent=True) or {}
    filename = data.get("filename", "").strip()
    if not filename:
        return jsonify(success=False, error="No filename."), 400
    target = LIBRARY_LECTURES_DIR / secure_filename(filename)
    if target.exists():
        target.unlink()
    return jsonify(success=True)


# ── Describe lecture → image-quality audit ────────────────────────────────

@lecture_bp.route("/api/describe-lecture", methods=["POST"])
def api_describe_lecture():
    lecture_path_str  = request.form.get("lecture_path", "").strip()
    describe_provider = request.form.get("describe_provider", "openai")
    describe_model    = (
        request.form.get("describe_model", "").strip()
        or PROVIDERS.get(describe_provider, {}).get("model", "gpt-4o-mini")
    )

    if not lecture_path_str:
        return jsonify(success=False, error="No lecture file path provided."), 400

    lecture_path = Path(lecture_path_str)
    if not lecture_path.exists():
        return jsonify(success=False, error=f"File not found: {lecture_path.name}"), 404

    # Build run dir
    slug   = re.sub(r"[^a-z0-9]+", "_", lecture_path.stem.lower())[:30]
    run_id = f"lec_{slug}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:4]}"
    run_root     = OUTPUT_ROOT / run_id
    upload_dir   = run_root / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    safe_model   = _safe(describe_model)
    extract_dir  = run_root / "extract"
    describe_dir = run_root / f"describe_lecture_{describe_provider}_{safe_model}"

    # Copy lecture file into the upload dir so the pipeline can find it
    shutil.copy2(str(lecture_path), str(upload_dir / lecture_path.name))

    # Step 1: Extract
    steps: list[dict] = []
    code, out = _run(_cli() + [
        "--mode",        "extract",
        "--data-dir",    str(upload_dir),
        "--source-type", "lecture",
        "--output-root", str(OUTPUT_ROOT),
        "--run-id",      run_id,
    ])
    steps.append({"step": "Extract Lecture", "ok": code == 0, "log": out[-2000:]})
    if code != 0:
        return jsonify(
            success=False,
            error="Lecture extraction failed. Check the log.",
            steps=steps,
            log=out[-3000:],
        ), 500

    # Step 2: Describe
    code, out = _run(_cli() + [
        "--mode",            "describe",
        "--extract-dir",     str(extract_dir),
        "--describe-dir",    str(describe_dir),
        "--vision-provider", describe_provider,
        "--vision-model",    describe_model,
        "--prompt-version",  "verbose_v2",
        "--source-type",     "lecture",
    ])
    steps.append({"step": "Describe Lecture", "ok": code == 0, "log": out[-2000:]})
    if code != 0:
        return jsonify(
            success=False,
            error="Describe pipeline failed. Check the log.",
            steps=steps,
            log=out[-3000:],
        ), 500

    # Read output chunks
    chunks_file = describe_dir / "chunks.jsonl"
    if not chunks_file.exists():
        return jsonify(success=False, error="Describe completed but chunks.jsonl not found."), 500

    all_chunks: list[dict] = []
    flagged:    list[dict] = []

    for i, line in enumerate(chunks_file.read_text(encoding="utf-8").splitlines()):
        if not line.strip():
            continue
        try:
            chunk = json.loads(line)
        except Exception:
            continue

        meta    = chunk.get("metadata", {}) or {}
        content = str(chunk.get("content", "") or "").strip()
        flag    = _flag_chunk(chunk)
        page    = meta.get("page_number", "?")

        all_chunks.append({
            "id":           chunk.get("id", f"c{i}"),
            "content":      content[:300],
            "content_type": meta.get("content_type", "text"),
            "element_tag":  meta.get("element_tag", ""),
            "page":         page,
            "flag":         flag,
        })
        if flag:
            flagged.append({
                "chunk_id": chunk.get("id", f"c{i}"),
                "page":     page,
                "flag":     flag,
                "preview":  content[:120] if content else "(empty)",
            })

    return jsonify(
        success=True,
        run_id=run_id,
        chunks_file=str(chunks_file),
        lecture_name=lecture_path.name,
        total_chunks=len(all_chunks),
        flagged_count=len(flagged),
        flagged=flagged,
        # Preview first 80 chunks for the UI
        chunks_preview=all_chunks[:80],
    )


# ── Push described chunks to RAG ──────────────────────────────────────────

@lecture_bp.route("/api/push-lecture-to-rag", methods=["POST"])
def api_push_lecture_to_rag():
    data         = request.get_json(silent=True) or {}
    chunks_file  = data.get("chunks_file", "").strip()
    skip_flagged = bool(data.get("skip_flagged", True))

    if not chunks_file or not Path(chunks_file).exists():
        return jsonify(success=False, error="Chunks file not found."), 400

    # Read chunks, optionally skip flagged images
    new_chunks: list[dict] = []
    for line in Path(chunks_file).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            chunk = json.loads(line)
        except Exception:
            continue
        if skip_flagged and _flag_chunk(chunk):
            continue
        new_chunks.append(chunk)

    if not new_chunks:
        return jsonify(success=False, error="No valid chunks to push (all were flagged or file is empty)."), 400

    # Append new (deduplicated) chunks to the shared JSONL
    dest = DEFAULT_LECTURE_CHUNKS
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.exists():
        dest.write_text("", encoding="utf-8")

    existing_ids: set[str] = set()
    for line in dest.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                existing_ids.add(json.loads(line)["id"])
            except Exception:
                pass

    added = 0
    with dest.open("a", encoding="utf-8") as f:
        for chunk in new_chunks:
            if chunk.get("id") not in existing_ids:
                f.write(json.dumps(chunk, ensure_ascii=False) + "\n")
                added += 1

    if added == 0:
        return jsonify(success=True, added_chunks=0, message="All chunks already in RAG (no duplicates added).")

    # Re-index Chroma
    chroma_dir = _shared_chroma_dir()
    chroma_dir.mkdir(parents=True, exist_ok=True)
    code, out = _run(_cli() + [
        "--mode",              "index",
        "--chunks-jsonl",      str(dest),
        "--chroma-path",       str(chroma_dir),
        "--chroma-collection", SHARED_LECTURE_COLLECTION,
        "--output-root",       str(OUTPUT_ROOT),
        "--run-id",            "shared_lecture_index",
    ], extra_env=_embedding_env())

    if code != 0:
        return jsonify(
            success=False,
            error="Chunks saved but Chroma re-index failed.",
            added_chunks=added,
            log=out[-1000:],
        ), 500

    return jsonify(
        success=True,
        added_chunks=added,
        message=f"✓ {added} chunk(s) added to RAG and index rebuilt.",
    )


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
