from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.chunking import chunk_text, make_sort_key, sha1_id
from core.config import SUPPORTED_EXTENSIONS, get_api_key
from extractors import (
    extract_excel,
    extract_html,
    extract_pdf,
    extracted_excel_to_jsonable,
    extracted_html_to_jsonable,
    extracted_pdf_to_jsonable,
)
from storage import try_store_chroma, write_json, write_jsonl, write_per_file_json
from vision.describer import VisionDescriber, describe_image_with_strategy
from vision.output_normalizer import build_image_text_content, to_string_list


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def list_target_files(data_dir: Path) -> list[Path]:
    files: list[Path] = []
    for p in sorted(data_dir.rglob("*")):
        if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS:
            files.append(p)
    return files


def infer_source_type(rel_path: str) -> str:
    return "lecture" if "lecture" in rel_path.lower() else "student"


def guess_mime(ext: str) -> str:
    e = ext.lower().lstrip(".")
    if e in {"jpg", "jpeg"}:
        return "image/jpeg"
    if e == "png":
        return "image/png"
    if e == "gif":
        return "image/gif"
    if e in {"tif", "tiff"}:
        return "image/tiff"
    if e == "bmp":
        return "image/bmp"
    return "application/octet-stream"


def run_extract(data_dir: Path, run_root: Path, cfg: dict[str, Any]) -> dict[str, Any]:
    extract_dir = run_root / "extract"
    tables_dir = extract_dir / "tables"
    per_file_dir = extract_dir / "per_file_json"
    text_blocks_dir = extract_dir / "text_blocks"
    ocr_results_dir = extract_dir / "ocr_results"
    extract_dir.mkdir(parents=True, exist_ok=True)
    tables_dir.mkdir(parents=True, exist_ok=True)
    per_file_dir.mkdir(parents=True, exist_ok=True)
    text_blocks_dir.mkdir(parents=True, exist_ok=True)
    ocr_results_dir.mkdir(parents=True, exist_ok=True)

    files = list_target_files(data_dir)
    manifest_files: list[dict[str, Any]] = []
    failed_files: list[dict[str, str]] = []

    for file_path in files:
        rel_path = str(file_path.relative_to(data_dir))
        ext = file_path.suffix.lower()
        try:
            if ext == ".pdf":
                extracted = extract_pdf(file_path, rel_path, extract_dir, cfg)
                payload = extracted_pdf_to_jsonable(extracted)
            elif ext == ".xlsx":
                extracted = extract_excel(file_path, rel_path, extract_dir, cfg)
                payload = extracted_excel_to_jsonable(extracted)
            elif ext in {".html", ".htm"}:
                extracted = extract_html(file_path, rel_path, cfg)
                payload = extracted_html_to_jsonable(extracted)
            else:
                continue

            per_file_json_path = write_per_file_json(per_file_dir, rel_path, payload)
            images = payload.get("images", [])
            tables = payload.get("tables", payload.get("table_blocks", []))
            text_blocks = payload.get("text_blocks", [])

            text_blocks_path = text_blocks_dir / f"{rel_path}.json"
            text_blocks_path.parent.mkdir(parents=True, exist_ok=True)
            text_blocks_path.write_text(
                json.dumps({"source_path": rel_path, "text_blocks": text_blocks}, indent=2, ensure_ascii=True),
                encoding="utf-8",
            )

            ocr_payload = {
                "source_path": rel_path,
                "images": [
                    {
                        "page_number": i.get("page_number", i.get("sheet_index")),
                        "block_index": i.get("block_index"),
                        "image_path": i.get("image_path"),
                        "ocr_text": i.get("ocr_text", ""),
                        "ocr_word_count": i.get("ocr_word_count"),
                        "ocr_avg_conf": i.get("ocr_avg_conf"),
                    }
                    for i in images
                ],
            }
            ocr_results_path = ocr_results_dir / f"{rel_path}.json"
            ocr_results_path.parent.mkdir(parents=True, exist_ok=True)
            ocr_results_path.write_text(json.dumps(ocr_payload, indent=2, ensure_ascii=True), encoding="utf-8")

            manifest_files.append(
                {
                    "source_path": rel_path,
                    "file_type": payload.get("file_type"),
                    "per_file_json": str(per_file_json_path),
                    "text_blocks_json": str(text_blocks_path),
                    "ocr_results_json": str(ocr_results_path),
                    "image_count": len(images),
                    "table_count": len(tables),
                    "text_block_count": len(text_blocks),
                    "images": [
                        {
                            "page_number": i.get("page_number", i.get("sheet_index")),
                            "block_index": i.get("block_index"),
                            "image_path": i.get("image_path"),
                            "caption_text": i.get("caption_text", ""),
                            "ocr_text": i.get("ocr_text", ""),
                        }
                        for i in images
                    ],
                    "tables": [
                        {
                            "page_number": t.get("page_number", t.get("sheet_index")),
                            "table_path": t.get("table_path"),
                            "preview": str(t.get("table_text", t.get("text", "")))[:300],
                        }
                        for t in tables
                    ],
                }
            )
        except Exception as exc:
            failed_files.append({"source_path": rel_path, "error": str(exc)})

    manifest = {
        "schema_version": "1.0",
        "generated_at_utc": now_utc_iso(),
        "data_dir": str(data_dir),
        "extract_dir": str(extract_dir),
        "file_count": len(files),
        "processed_file_count": len(manifest_files),
        "failed_file_count": len(failed_files),
        "failed_files": failed_files,
        "files": manifest_files,
    }
    write_json(extract_dir / "manifest.json", manifest)
    return manifest


def _append_text_chunks(
    chunks: list[dict[str, Any]],
    *,
    rel_path: str,
    file_name: str,
    source_type: str,
    fmt: str,
    page_number: int,
    block_index: int,
    document_order: int,
    text: str,
    max_chars: int,
    overlap: int,
    min_text_chars: int,
    extra_meta: dict[str, Any] | None = None,
) -> int:
    added = 0
    for ci, piece in enumerate(chunk_text(text, max_chars, overlap), 1):
        if len(piece) < min_text_chars:
            continue
        meta = {
            "filename": file_name,
            "source_path": rel_path,
            "source_type": source_type,
            "format": fmt,
            "page_number": page_number,
            "block_index": block_index,
            "sort_key": make_sort_key(page_number, block_index),
            "document_order": document_order,
            "content_type": "text",
            "chunk_index_in_block": ci,
            "image_quality": None,
            "image_width_px": None,
            "image_height_px": None,
            "image_total_pixels": None,
            "image_aspect_ratio": None,
            "is_tiled": None,
            "tile_count": None,
            "gpt4o_called": False,
            "quality_warning": None,
        }
        if extra_meta:
            meta.update(extra_meta)
        cid = sha1_id(
            f"{rel_path}|{fmt}|page={page_number}|block={block_index}|text|doc_order={document_order}|chunk={ci}"
        )
        chunks.append({"id": cid, "content": piece, "metadata": meta})
        added += 1
    return added


def _describe_image_item(
    item: dict[str, Any],
    *,
    rel_path: str,
    file_name: str,
    source_type: str,
    fmt: str,
    page_number: int,
    block_index: int,
    document_order: int,
    vision: VisionDescriber | None,
    vision_provider: str,
    vision_model: str,
    cfg: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    image_path = str(item.get("image_path", ""))
    image_bytes = Path(image_path).read_bytes()
    ext = str(item.get("ext", "png"))
    caption_text = str(item.get("caption_text", "") or "")
    ocr_text = str(item.get("ocr_text", "") or "")

    vision_used = False
    vision_error = None
    structured = None
    content = "[vision_not_executed]"
    stats = {
        "vision_calls_attempted": 0,
        "vision_calls_succeeded": 0,
        "vision_errors": 0,
        "vision_input_tokens": 0,
        "vision_output_tokens": 0,
        "vision_total_tokens": 0,
        "vision_retries": 0,
        "vision_json_fallbacks": 0,
        "tiled_images": 0,
    }

    tiled = False
    tile_count = 1
    tile_rows = 1
    tile_cols = 1
    image_width = None
    image_height = None
    image_pixels = None
    image_quality = None
    image_ratio = None
    quality_warning = None
    vision_retry_used = False
    vision_json_invalid_after_retry = False
    gpt4o_called = False

    if vision is None:
        from PIL import Image
        import io
        from vision.prompts import classify_image_quality, image_aspect_ratio, quality_warning_from_band

        vision_error = "vision_client_not_ready"
        fallback = [f"[vision_error] {vision_error}"]
        if caption_text:
            fallback.append(f"Caption hint: {caption_text}")
        if ocr_text:
            fallback.append(f"OCR fallback: {ocr_text}")
        content = " ".join(fallback)
        with Image.open(io.BytesIO(image_bytes)) as img_ref:
            iw, ih = img_ref.size
        ip = int(iw * ih)
        image_width = iw
        image_height = ih
        image_pixels = ip
        image_quality = classify_image_quality(iw, ih, ip)
        image_ratio = image_aspect_ratio(iw, ih)
        quality_warning = quality_warning_from_band(image_quality)
    else:
        caption_hint = caption_text
        if ocr_text:
            caption_hint = (caption_hint + " | OCR hint: " + ocr_text[:2000]).strip(" |")

        result = describe_image_with_strategy(
            vision=vision,
            image_bytes=image_bytes,
            mime_type=guess_mime(ext),
            caption_hint=caption_hint,
            source_file=rel_path,
            locator=f"page/sheet {page_number}, image {item.get('image_index', 0)}",
            cfg=cfg,
        )

        stats["vision_calls_attempted"] += int(result.calls_attempted)
        stats["vision_calls_succeeded"] += int(result.calls_succeeded)
        stats["vision_errors"] += int(result.call_errors)
        stats["vision_input_tokens"] += int(result.input_tokens)
        stats["vision_output_tokens"] += int(result.output_tokens)
        stats["vision_total_tokens"] += int(result.total_tokens)

        tiled = bool(result.tiled)
        tile_count = int(result.tile_count)
        tile_rows = int(result.tile_rows)
        tile_cols = int(result.tile_cols)
        image_width = int(result.image_width)
        image_height = int(result.image_height)
        image_pixels = int(result.image_pixels)
        image_quality = str(result.image_quality)
        image_ratio = float(result.image_aspect_ratio)
        quality_warning = result.quality_warning
        gpt4o_called = bool(result.gpt4o_called)
        vision_retry_used = bool(result.retry_used)
        vision_json_invalid_after_retry = bool(result.json_invalid_after_retry)

        if tiled:
            stats["tiled_images"] += 1
        if vision_retry_used:
            stats["vision_retries"] += 1

        if result.structured is not None:
            structured = result.structured
            content = build_image_text_content(structured)
            vision_used = True
            if bool(structured.get("json_parse_fallback_used", False)):
                stats["vision_json_fallbacks"] += 1
            if result.error:
                vision_error = result.error
        else:
            vision_error = result.error or "vision_strategy_failed_without_output"
            fallback = [f"[vision_error] {vision_error}"]
            if caption_text:
                fallback.append(f"Caption hint: {caption_text}")
            if ocr_text:
                fallback.append(f"OCR fallback: {ocr_text}")
            content = " ".join(fallback)

    meta = {
        "filename": file_name,
        "source_path": rel_path,
        "source_type": source_type,
        "format": fmt,
        "page_number": page_number,
        "block_index": block_index,
        "sort_key": make_sort_key(page_number, block_index),
        "document_order": document_order,
        "content_type": "image_description",
        "image_path": image_path,
        "image_ext": ext,
        "caption_text": caption_text,
        "ocr_text": ocr_text,
        "ocr_word_count": item.get("ocr_word_count"),
        "ocr_avg_conf": item.get("ocr_avg_conf"),
        "vision_used": vision_used,
        "vision_provider": vision_provider,
        "vision_model": vision_model,
        "vision_error": vision_error,
        "is_tiled": tiled,
        "tile_count": tile_count,
        "tile_rows": tile_rows,
        "tile_cols": tile_cols,
        "image_width_px": image_width,
        "image_height_px": image_height,
        "image_total_pixels": image_pixels,
        "image_aspect_ratio": image_ratio,
        "image_quality": image_quality,
        "vision_retry_used": vision_retry_used,
        "vision_json_invalid_after_retry": vision_json_invalid_after_retry,
        "gpt4o_called": gpt4o_called,
        "quality_warning": quality_warning,
    }
    if structured is not None:
        extracted_text_lines = to_string_list(structured.get("all_visible_text", structured.get("visible_text", [])))
        meta.update(
            {
                "image_type": structured.get("image_type"),
                "all_visible_text": extracted_text_lines,
                "extracted_text": "\n".join(extracted_text_lines),
                "visible_text_lines": extracted_text_lines,
                "structural_elements": structured.get("structural_elements"),
                "spatial_layout": structured.get("spatial_layout"),
                "completeness": structured.get("completeness"),
                "unclear_parts": structured.get("unclear_parts"),
                "description": structured.get("description"),
                "elements": to_string_list(structured.get("elements", [])),
                "layout": structured.get("layout"),
                "vision_json_parse_fallback_used": bool(structured.get("json_parse_fallback_used", False)),
            }
        )

    cid = sha1_id(f"{rel_path}|{fmt}|page={page_number}|block={block_index}|image|doc_order={document_order}")
    return {"id": cid, "content": content, "metadata": meta}, stats


def run_describe(
    extract_dir: Path,
    describe_dir: Path,
    cfg: dict[str, Any],
    *,
    vision_provider: str,
    vision_model: str,
    prompt_version: str,
    vector_db: str,
    chroma_path: str,
    chroma_collection: str,
    chroma_batch_size: int,
    vision_input_cost_per_1m: float,
    vision_output_cost_per_1m: float,
) -> dict[str, Any]:
    manifest_path = extract_dir / "manifest.json"
    if not manifest_path.exists():
        raise RuntimeError(f"manifest.json not found in extract dir: {extract_dir}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    files = manifest.get("files", [])

    describe_dir.mkdir(parents=True, exist_ok=True)
    per_file_dir = describe_dir / "per_file_json"
    per_file_dir.mkdir(parents=True, exist_ok=True)

    api_keys = {
        "openai": get_api_key("openai"),
        "anthropic": get_api_key("anthropic"),
        "gemini": get_api_key("gemini"),
    }

    vision = None
    vision_init_error = None
    if vision_provider != "none":
        try:
            vision = VisionDescriber(
                provider=vision_provider,
                model=vision_model,
                max_tokens=int(cfg["vision_max_tokens"]),
                api_keys=api_keys,
            )
        except Exception as exc:
            vision_init_error = str(exc)

    if vision_provider != "none" and vision is None:
        raise RuntimeError(f"Vision client not ready: {vision_init_error}")

    all_chunks: list[dict[str, Any]] = []
    per_file_stats: list[dict[str, Any]] = []
    failed_files: list[dict[str, str]] = []

    totals = {
        "vision_calls_attempted": 0,
        "vision_calls_succeeded": 0,
        "vision_errors": 0,
        "vision_input_tokens": 0,
        "vision_output_tokens": 0,
        "vision_total_tokens": 0,
        "vision_retries": 0,
        "vision_json_fallbacks": 0,
        "tiled_images": 0,
    }

    for f in files:
        rel_path = str(f["source_path"])
        file_type = str(f.get("file_type", ""))
        per_file_json_path = Path(str(f["per_file_json"]))
        try:
            payload = json.loads(per_file_json_path.read_text(encoding="utf-8"))
            file_name = Path(rel_path).name
            source_type = infer_source_type(rel_path)

            chunks: list[dict[str, Any]] = []
            fstats: dict[str, Any] = {
                "source_path": rel_path,
                "file_type": file_type,
                "text_chunks": 0,
                "table_chunks": 0,
                "image_chunks": 0,
                "vision_chunks": 0,
                "ocr_chunks": 0,
                "vision_calls_attempted": 0,
                "vision_calls_succeeded": 0,
                "vision_errors": 0,
                "vision_input_tokens": 0,
                "vision_output_tokens": 0,
                "vision_total_tokens": 0,
                "vision_retries": 0,
                "vision_json_fallbacks": 0,
                "tiled_images": 0,
            }

            if file_type == "pdf":
                text_blocks = payload.get("text_blocks", [])
                images = payload.get("images", [])
                units: list[dict[str, Any]] = []
                for t in text_blocks:
                    units.append({"kind": "text", "order": int(t.get("document_order", 0)), "item": t})
                for im in images:
                    units.append({"kind": "image", "order": int(im.get("document_order", 0)), "item": im})
                units.sort(key=lambda u: u["order"])

                max_doc_order = 0
                for unit in units:
                    max_doc_order = max(max_doc_order, int(unit["order"]))
                    if unit["kind"] == "text":
                        t = unit["item"]
                        fstats["text_chunks"] += _append_text_chunks(
                            chunks,
                            rel_path=rel_path,
                            file_name=file_name,
                            source_type=source_type,
                            fmt="pdf",
                            page_number=int(t["page_number"]),
                            block_index=int(t["block_index"]),
                            document_order=int(t["document_order"]),
                            text=str(t["text"]),
                            max_chars=int(cfg["text_chunk_chars"]),
                            overlap=int(cfg["text_chunk_overlap"]),
                            min_text_chars=int(cfg["min_text_chars"]),
                            extra_meta={"block_id": t.get("block_id"), "bbox": t.get("bbox")},
                        )
                    else:
                        im = unit["item"]
                        image_chunk, s = _describe_image_item(
                            im,
                            rel_path=rel_path,
                            file_name=file_name,
                            source_type=source_type,
                            fmt="pdf",
                            page_number=int(im["page_number"]),
                            block_index=int(im["block_index"]),
                            document_order=int(im["document_order"]),
                            vision=vision,
                            vision_provider=vision_provider,
                            vision_model=vision_model,
                            cfg=cfg,
                        )
                        chunks.append(image_chunk)
                        fstats["image_chunks"] += 1
                        fstats["vision_chunks"] += 1
                        for k, v in s.items():
                            fstats[k] += int(v)

                # PDF table chunks appended after text/images with stable order.
                for ti, table in enumerate(payload.get("tables", []), 1):
                    max_doc_order += 1
                    page_number = int(table.get("page_number", 1)) if str(table.get("page_number", "")).isdigit() else 1
                    block_index = 9000 + ti
                    meta = {
                        "filename": file_name,
                        "source_path": rel_path,
                        "source_type": source_type,
                        "format": "pdf",
                        "page_number": page_number,
                        "block_index": block_index,
                        "sort_key": make_sort_key(page_number, block_index),
                        "document_order": max_doc_order,
                        "content_type": "table",
                        "table_index": table.get("table_index"),
                        "table_path": table.get("table_path"),
                    }
                    text = str(table.get("table_text", ""))
                    cid = sha1_id(f"{rel_path}|pdf|table|{ti}|doc_order={max_doc_order}")
                    chunks.append({"id": cid, "content": text, "metadata": meta})
                    fstats["table_chunks"] += 1

            elif file_type == "xlsx":
                table_blocks = payload.get("table_blocks", [])
                images = payload.get("images", [])
                units: list[dict[str, Any]] = []
                for t in table_blocks:
                    units.append({"kind": "table", "order": int(t.get("document_order", 0)), "item": t})
                for im in images:
                    units.append({"kind": "image", "order": int(im.get("document_order", 0)), "item": im})
                units.sort(key=lambda u: u["order"])

                for unit in units:
                    if unit["kind"] == "table":
                        t = unit["item"]
                        meta = {
                            "filename": file_name,
                            "source_path": rel_path,
                            "source_type": source_type,
                            "format": "xlsx",
                            "page_number": int(t["sheet_index"]),
                            "block_index": int(t["block_index"]),
                            "sort_key": str(t["sort_key"]),
                            "document_order": int(t["document_order"]),
                            "content_type": "table",
                            "sheet_name": t.get("sheet_name"),
                            "row_start": t.get("row_start"),
                            "row_end": t.get("row_end"),
                        }
                        cid = sha1_id(f"{rel_path}|xlsx|table|sheet={t.get('sheet_name')}|block={t.get('block_index')}")
                        chunks.append({"id": cid, "content": str(t.get("text", "")), "metadata": meta})
                        fstats["table_chunks"] += 1
                    else:
                        im = unit["item"]
                        image_chunk, s = _describe_image_item(
                            im,
                            rel_path=rel_path,
                            file_name=file_name,
                            source_type=source_type,
                            fmt="xlsx",
                            page_number=int(im["sheet_index"]),
                            block_index=int(im["block_index"]),
                            document_order=int(im["document_order"]),
                            vision=vision,
                            vision_provider=vision_provider,
                            vision_model=vision_model,
                            cfg=cfg,
                        )
                        chunks.append(image_chunk)
                        fstats["image_chunks"] += 1
                        fstats["vision_chunks"] += 1
                        for k, v in s.items():
                            fstats[k] += int(v)

            elif file_type == "html":
                for t in payload.get("text_blocks", []):
                    fstats["text_chunks"] += _append_text_chunks(
                        chunks,
                        rel_path=rel_path,
                        file_name=file_name,
                        source_type=source_type,
                        fmt="html",
                        page_number=1,
                        block_index=int(t["block_index"]),
                        document_order=int(t["document_order"]),
                        text=str(t["text"]),
                        max_chars=int(cfg["text_chunk_chars"]),
                        overlap=int(cfg["text_chunk_overlap"]),
                        min_text_chars=int(cfg["min_text_chars"]),
                        extra_meta={"element_tag": t.get("element_tag")},
                    )

            for k in totals:
                totals[k] += int(fstats.get(k, 0))

            fstats["chunk_count"] = len(chunks)
            per_file_output = {
                "source_path": rel_path,
                "file_type": file_type,
                "stats": fstats,
                "chunk_count": len(chunks),
                "chunks": chunks,
            }
            out_path = write_per_file_json(per_file_dir, rel_path, per_file_output)
            fstats["per_file_json"] = str(out_path)
            per_file_stats.append(fstats)
            all_chunks.extend(chunks)
        except Exception as exc:
            failed_files.append({"source_path": rel_path, "error": str(exc)})

    chunks_path = describe_dir / "chunks.jsonl"
    write_jsonl(chunks_path, all_chunks)

    counts_by_type: dict[str, int] = {}
    quality_breakdown = {"clear": 0, "low_res": 0, "unreadable": 0}
    quality_warnings_count = 0
    file_orders: dict[str, list[int]] = {}

    for c in all_chunks:
        md = c.get("metadata", {})
        ct = str(md.get("content_type", "unknown"))
        counts_by_type[ct] = counts_by_type.get(ct, 0) + 1
        q = md.get("image_quality")
        if q in quality_breakdown:
            quality_breakdown[str(q)] += 1
        if md.get("quality_warning"):
            quality_warnings_count += 1
        src = str(md.get("source_path", ""))
        dord = md.get("document_order")
        if src and isinstance(dord, int):
            file_orders.setdefault(src, []).append(dord)

    ordering_complete = True
    max_document_order = 0
    for vals in file_orders.values():
        # Chunks may share document_order when one source block is split into
        # multiple overlapping chunks; validate monotonic ordering instead.
        if vals != sorted(vals):
            ordering_complete = False
        if vals:
            max_document_order = max(max_document_order, max(vals))

    estimated_api_cost_usd = round(
        (totals["vision_input_tokens"] / 1_000_000.0) * float(vision_input_cost_per_1m)
        + (totals["vision_output_tokens"] / 1_000_000.0) * float(vision_output_cost_per_1m),
        6,
    )

    chroma_result = {"enabled": False}
    if vector_db == "chroma":
        chroma_result = try_store_chroma(
            chunks=all_chunks,
            chroma_path=chroma_path,
            chroma_collection=chroma_collection,
            chroma_batch_size=chroma_batch_size,
        )

    summary = {
        "generated_at_utc": now_utc_iso(),
        "extract_dir": str(extract_dir),
        "output_dir": str(describe_dir),
        "file_count": len(files),
        "processed_file_count": len(per_file_stats),
        "failed_file_count": len(failed_files),
        "chunk_count": len(all_chunks),
        "counts_by_content_type": counts_by_type,
        "image_quality_breakdown": quality_breakdown,
        "ordering": {
            "total_chunks": len(all_chunks),
            "max_document_order": max_document_order,
            "ordering_complete": ordering_complete,
        },
        "prompt_version": prompt_version,
        "quality_warnings_count": quality_warnings_count,
        "vision_provider": vision_provider,
        "vision_model": vision_model if vision_provider != "none" else None,
        "vision_ready": vision is not None,
        "vision_init_error": vision_init_error,
        "vision_usage": {
            "total_images_sent_to_vision": sum(int(s.get("image_chunks", 0)) for s in per_file_stats),
            "total_vision_api_calls": totals["vision_calls_attempted"],
            "vision_calls_succeeded": totals["vision_calls_succeeded"],
            "vision_errors": totals["vision_errors"],
            "vision_json_fallbacks": totals["vision_json_fallbacks"],
            "vision_retries": totals["vision_retries"],
            "tiled_images": totals["tiled_images"],
            "input_tokens": totals["vision_input_tokens"],
            "output_tokens": totals["vision_output_tokens"],
            "total_tokens": totals["vision_total_tokens"],
            "input_cost_per_1m": float(vision_input_cost_per_1m),
            "output_cost_per_1m": float(vision_output_cost_per_1m),
            "estimated_api_cost_usd": estimated_api_cost_usd,
        },
        "vector_db": vector_db,
        "vector_db_result": chroma_result,
        "failed_files": failed_files,
        "per_file_stats": per_file_stats,
        "outputs": {
            "chunks_jsonl": str(chunks_path),
            "per_file_json_dir": str(per_file_dir),
            "summary_json": str(describe_dir / "summary.json"),
        },
    }

    write_json(describe_dir / "summary.json", summary)
    return summary


def run_compare(compare_inputs: list[Path], output_dir: Path) -> dict[str, Any]:
    if len(compare_inputs) < 2:
        raise RuntimeError("compare mode requires at least two summary.json inputs")

    summaries: list[dict[str, Any]] = []
    for p in compare_inputs:
        data = json.loads(p.read_text(encoding="utf-8"))
        summaries.append(data)

    rows = []
    for s in summaries:
        rows.append(
            {
                "name": f"{s.get('vision_provider')}/{s.get('vision_model')}",
                "processed": f"{s.get('processed_file_count')}/{s.get('file_count')}",
                "chunks": s.get("chunk_count"),
                "vision_calls": s.get("vision_usage", {}).get("total_vision_api_calls"),
                "vision_retries": s.get("vision_usage", {}).get("vision_retries"),
                "vision_json_fallbacks": s.get("vision_usage", {}).get("vision_json_fallbacks"),
                "total_tokens": s.get("vision_usage", {}).get("total_tokens"),
                "estimated_cost_usd": s.get("vision_usage", {}).get("estimated_api_cost_usd"),
            }
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    report = {
        "generated_at_utc": now_utc_iso(),
        "inputs": [str(p) for p in compare_inputs],
        "rows": rows,
    }
    write_json(output_dir / "comparison_report.json", report)

    md_lines = ["# Model Comparison", "", "| Model | Processed | Chunks | Calls | Retries | Fallbacks | Tokens | Cost |", "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for r in rows:
        md_lines.append(
            f"| {r['name']} | {r['processed']} | {r['chunks']} | {r['vision_calls']} | {r['vision_retries']} | {r['vision_json_fallbacks']} | {r['total_tokens']} | {r['estimated_cost_usd']} |"
        )
    (output_dir / "comparison_report.md").write_text("\n".join(md_lines), encoding="utf-8")
    return report
