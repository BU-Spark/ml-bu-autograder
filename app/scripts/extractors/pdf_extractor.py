from __future__ import annotations

import io
import json
import logging
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from PIL import Image

from core.chunking import clean_text, make_sort_key
from image_utils.caption import find_best_caption_for_image
from image_utils.filtering import is_diagram_image
from image_utils.ocr import OCRResult, compute_ocr
from vision.tiling import split_image_into_tiles

try:
    import fitz  # PyMuPDF
except Exception:  # pragma: no cover
    fitz = None

try:
    import camelot
except Exception:  # pragma: no cover
    camelot = None

try:
    from docling.document_converter import DocumentConverter
    from docling_core.types.doc.document import (
        TextItem, TableItem as DoclingTableItem,
        SectionHeaderItem, TitleItem, FormulaItem, ListItem,
        CodeItem, KeyValueItem,
    )
    from docling_core.types.doc.labels import DocItemLabel
    from docling_core.types.io import DocumentStream
    _DOCLING_AVAILABLE = True
except ImportError:
    _DOCLING_AVAILABLE = False

# Labels whose content is noise for RAG — skip entirely.
# caption      → redundant: PyMuPDF already attaches captions to image chunks
# footnote     → footnote text rarely contains gradeable content
# document_index → table of contents, not content
# reference    → bibliography entries, not gradeable content
# page_header/footer → already excluded by default
# checkbox_*/form/empty_value → form UI elements, no text value
_DOCLING_SKIP_LABELS: set = {
    DocItemLabel.PAGE_HEADER, DocItemLabel.PAGE_FOOTER, DocItemLabel.CAPTION,
    DocItemLabel.FOOTNOTE, DocItemLabel.DOCUMENT_INDEX, DocItemLabel.REFERENCE,
    DocItemLabel.CHECKBOX_SELECTED, DocItemLabel.CHECKBOX_UNSELECTED,
    DocItemLabel.FORM, DocItemLabel.EMPTY_VALUE,
} if _DOCLING_AVAILABLE else set()

# Cached converter so model weights are loaded once per process, not once per PDF.
_docling_converter: "DocumentConverter | None" = None


def _get_docling_converter() -> "DocumentConverter":
    global _docling_converter
    if _docling_converter is None:
        _docling_converter = DocumentConverter()
    return _docling_converter


def _check_path_traversal(extract_root: Path, rel_path: str) -> None:
    if not str((extract_root / rel_path).resolve()).startswith(str(extract_root.resolve())):
        raise ValueError(f"rel_path escapes extract_root: {rel_path!r}")


def _merge_img_stats(stats: dict, img_stats: dict) -> None:
    for key in ("images_seen", "images_kept", "images_filtered"):
        stats[key] = img_stats[key]
    if img_stats.get("issues"):
        stats["issues"].extend(img_stats["issues"])


def _append_text_block(text_blocks: list, page_num: int, text: str, doc_order: int) -> None:
    block_index = len(text_blocks)
    text_blocks.append(TextBlock(
        block_id=f"T{block_index + 1}",
        page_number=page_num,
        block_index=block_index,
        bbox={"x0": 0.0, "y0": 0.0, "x1": 0.0, "y1": 0.0},
        text=text,
        sort_key=make_sort_key(page_num, block_index),
        document_order=doc_order,
    ))

# Suppress noisy parser warnings from third-party PDF stack.
for _logger_name in ("pdfminer", "camelot", "pypdf"):
    logging.getLogger(_logger_name).setLevel(logging.ERROR)


@dataclass
class TextBlock:
    block_id: str
    page_number: int
    block_index: int
    bbox: dict[str, float]
    text: str
    sort_key: str
    document_order: int


@dataclass
class ImageItem:
    image_index: int
    page_number: int
    block_index: int
    bbox: dict[str, float | None]
    xref: int
    image_path: str
    ext: str
    caption_text: str
    caption_block_id: str | None
    caption_distance: float | None
    filter_reason: str
    ocr_text: str
    ocr_word_count: int
    ocr_avg_conf: float
    sort_key: str
    document_order: int


@dataclass
class TableItem:
    table_index: int
    page_number: int | str
    table_path: str
    table_text: str
    rows: list[list[str]] = field(default_factory=list)


@dataclass
class ExtractedPDF:
    source_path: str
    file_type: str
    page_count: int
    text_blocks: list[TextBlock]
    images: list[ImageItem]
    tables: list[TableItem]
    stats: dict[str, Any]


def _save_image(image_bytes: bytes, image_path: Path) -> None:
    image_path.parent.mkdir(parents=True, exist_ok=True)
    image_path.write_bytes(image_bytes)


def _pdf_text_blocks(page: Any, page_number: int) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    blocks = page.get_text("blocks")
    for i, block in enumerate(blocks):
        if len(block) < 6:
            continue
        x0, y0, x1, y1, text = block[:5]
        btype = block[6] if len(block) >= 7 else 0
        if btype != 0:
            continue
        text = clean_text(str(text))
        if not text:
            continue
        out.append({"id": f"T{i+1}", "page": page_number,
                    "bbox": {"x0": float(x0), "y0": float(y0), "x1": float(x1), "y1": float(y1)},
                    "text": text})
    out.sort(key=lambda t: (t["bbox"]["y0"], t["bbox"]["x0"]))
    return out


def normalize_cell(v: Any) -> str:
    return clean_text(str(v)).replace("nan", "").strip()


def _df_to_text(df: Any, title: str) -> str:
    """Convert a Camelot DataFrame to rich structured text for LLM grading.
    Produces both a markdown-style grid and a key:value row format so the
    grader can read tabular data clearly.
    """
    if df is None or len(df) == 0:
        return f"TABLE: {title}\n\n(Empty table)\n"

    all_rows = [[normalize_cell(c) for c in row] for row in df.values.tolist()]

    # Detect header row: first row if it has more non-empty cells than subsequent average
    headers = all_rows[0] if all_rows else []
    data_rows = all_rows[1:] if len(all_rows) > 1 else all_rows

    out: list[str] = [f"TABLE: {title}"]

    # Markdown grid (easy for LLM to parse structure)
    if headers:
        header_line = " | ".join(h if h else "(col)" for h in headers)
        sep_line = " | ".join("---" for _ in headers)
        out.append(header_line)
        out.append(sep_line)
        for row in data_rows:
            # Pad row to header length
            padded = row + [""] * max(0, len(headers) - len(row))
            out.append(" | ".join(c if c else "" for c in padded[:len(headers)]))

    out.append("")  # blank line

    # Key-value format for each row (easier for evidence matching)
    for i, row in enumerate(data_rows, 1):
        if all(not c for c in row):
            continue
        row_parts: list[str] = []
        for h, c in zip(headers, row):
            if c:
                row_parts.append(f"{h}: {c}" if h else c)
        # Include any extra cells beyond header count
        for extra_c in row[len(headers):]:
            if extra_c:
                row_parts.append(extra_c)
        if row_parts:
            out.append(f"Row {i}: " + " | ".join(row_parts))

    return "\n".join(out)


def _is_meaningful_table(df: Any) -> bool:
    if df is None or len(df) == 0:
        return False
    body = df.iloc[1:] if len(df) > 1 else df
    return sum(1 for v in body.values.flatten() if normalize_cell(v)) >= 3


def _extract_tables(pdf_path: Path, table_dir: Path) -> tuple[list[TableItem], list[str]]:
    issues: list[str] = []
    out: list[TableItem] = []
    if camelot is None:
        issues.append("camelot_not_installed")
        return out, issues

    try:
        try:
            tables = camelot.read_pdf(str(pdf_path), pages="all", flavor="lattice")
        except Exception:
            tables = camelot.read_pdf(str(pdf_path), pages="all", flavor="stream")

        if tables.n == 0:
            tables = camelot.read_pdf(str(pdf_path), pages="all", flavor="stream")

        for i, table in enumerate(tables):
            if not _is_meaningful_table(table.df):
                continue
            table_text = _df_to_text(table.df, title=f"Table {i+1} (Page {table.page})")
            rows = [[normalize_cell(c) for c in row] for row in table.df.values.tolist()]
            page = int(table.page) if str(table.page).isdigit() else str(table.page)
            table_path = table_dir / f"table_{i+1:03d}_page_{page}.json"
            table_path.parent.mkdir(parents=True, exist_ok=True)
            payload = {"index": i + 1, "page": page, "text": table_text, "rows": rows}
            table_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")
            out.append(
                TableItem(
                    table_index=i + 1,
                    page_number=page,
                    table_path=str(table_path),
                    table_text=table_text,
                    rows=rows,
                )
            )
    except Exception as exc:
        issues.append(f"camelot_extract_failed: {exc}")

    return out, issues


def _compute_ocr_with_optional_tiling(image_bytes: bytes, cfg: dict[str, Any]) -> OCRResult:
    try:
        with Image.open(io.BytesIO(image_bytes)) as img:
            width, height = img.size
    except Exception:
        return compute_ocr(image_bytes)

    pixels = int(width * height)
    if pixels < int(cfg.get("image_large_pixels_threshold", 1_000_000)):
        return compute_ocr(image_bytes)

    tiles, _, _, _, _, _ = split_image_into_tiles(
        image_bytes=image_bytes,
        target_max_pixels=int(cfg.get("image_tile_target_max_pixels", 1_000_000)),
        max_tiles=int(cfg.get("image_max_tiles", 9)),
    )

    results = [compute_ocr(tile["bytes"]) for tile in tiles]
    texts = [r.text for r in results if r.text]
    words = sum(int(r.word_count) for r in results)
    confs = [float(r.avg_conf) for r in results if r.avg_conf > 0]
    combined = clean_text(" ".join(texts))
    avg_conf = round(sum(confs) / len(confs), 2) if confs else 0.0
    if not combined:
        return compute_ocr(image_bytes)
    return OCRResult(text=combined, word_count=words, avg_conf=avg_conf)


def extract_images_pdf(
    file_path: Path,
    rel_path: str,
    extract_root: Path,
    cfg: dict[str, Any],
    caption_blocks_by_page: dict[int, list[dict]] | None = None,
    doc_order_start: int = 0,
    block_index_start: int = 0,
) -> tuple[list[ImageItem], dict[str, Any]]:
    """Extract images from a PDF using PyMuPDF.

    Standalone function so other extractors (e.g. Docling) can reuse PyMuPDF's
    reliable image detection — including filtering, OCR, and caption scoring —
    while using their own text extraction.

    Args:
        caption_blocks_by_page: optional dict of page_number → list of text
            block dicts (with 'bbox' and 'text') used for caption proximity
            matching. If omitted, PyMuPDF's own text is used for captions.
            Note: pass None (not zero-bbox blocks) when caller text blocks
            lack spatial coordinates, so captions fall back to PyMuPDF text.
        block_index_start: offset added to per-page image index when computing
            block_index, so callers can avoid collisions with text block indices.
    """
    if fitz is None:
        raise RuntimeError("PyMuPDF is not installed")

    _check_path_traversal(extract_root, rel_path)

    images: list[ImageItem] = []
    stats: dict[str, Any] = {
        "images_seen": 0,
        "images_kept": 0,
        "images_filtered": 0,
        "issues": [],
    }
    doc_order = doc_order_start

    doc = fitz.open(str(file_path))
    try:
        page_limit = min(len(doc), int(cfg.get("max_pdf_pages", 120)))
        for pidx in range(page_limit):
            page = doc[pidx]
            page_num = pidx + 1
            page_rect = page.rect

            if caption_blocks_by_page is not None:
                blocks_for_caption = caption_blocks_by_page.get(page_num, [])
            else:
                blocks_for_caption = _pdf_text_blocks(page, page_num)

            page_images = page.get_images(full=True)
            for img_i, img_info in enumerate(page_images, 1):
                stats["images_seen"] += 1
                xref = img_info[0]
                img_data = doc.extract_image(xref)
                if not img_data or "image" not in img_data:
                    continue

                image_bytes = img_data["image"]
                ext = str(img_data.get("ext", "png")).lower()
                rects = page.get_image_rects(xref)
                rect = rects[0] if rects else None

                with Image.open(io.BytesIO(image_bytes)) as pil_img:
                    keep, reason = is_diagram_image(pil_img.convert("RGB"), rect, float(page_rect.height), cfg)
                if not keep:
                    stats["images_filtered"] += 1
                    continue

                bbox = {
                    "x0": float(rect.x0) if rect else None,
                    "y0": float(rect.y0) if rect else None,
                    "x1": float(rect.x1) if rect else None,
                    "y1": float(rect.y1) if rect else None,
                }
                caption_text = "No caption found"
                caption_block_id: str | None = None
                caption_distance: float | None = None
                if rect is not None:
                    caption_result = find_best_caption_for_image(
                        blocks_for_caption, rect, float(page_rect.width), cfg
                    )
                    if isinstance(caption_result, tuple):
                        caption_text, caption_block_id, caption_distance = caption_result
                    else:
                        caption_text = caption_result

                ocr: OCRResult = _compute_ocr_with_optional_tiling(image_bytes, cfg)
                image_path = extract_root / "images" / rel_path / f"page_{page_num:03d}_img_{img_i:03d}.{ext}"
                _save_image(image_bytes, image_path)

                doc_order += 1
                block_index = block_index_start + img_i - 1
                images.append(
                    ImageItem(
                        image_index=img_i,
                        page_number=page_num,
                        block_index=block_index,
                        bbox=bbox,
                        xref=int(xref),
                        image_path=str(image_path),
                        ext=ext,
                        caption_text=caption_text,
                        caption_block_id=caption_block_id,
                        caption_distance=caption_distance,
                        filter_reason=reason,
                        ocr_text=ocr.text,
                        ocr_word_count=ocr.word_count,
                        ocr_avg_conf=ocr.avg_conf,
                        sort_key=make_sort_key(page_num, block_index),
                        document_order=doc_order,
                    )
                )
                stats["images_kept"] += 1
    finally:
        doc.close()

    return images, stats


def extract_pdf(
    file_path: Path,
    rel_path: str,
    extract_root: Path,
    cfg: dict[str, Any],
) -> ExtractedPDF:
    use_docling = cfg.get("use_docling", False) or (
        str(os.getenv("USE_DOCLING", "false")).lower() == "true"
    )
    if use_docling:
        return extract_pdf_docling(file_path, rel_path, extract_root, cfg)

    if fitz is None:
        raise RuntimeError("PyMuPDF is not installed")

    _check_path_traversal(extract_root, rel_path)

    doc = fitz.open(str(file_path))
    text_blocks: list[TextBlock] = []
    stats: dict[str, Any] = {
        "text_blocks": 0,
        "images_seen": 0,
        "images_kept": 0,
        "images_filtered": 0,
        "tables": 0,
        "issues": [],
    }

    doc_order = 0
    page_limit = 0
    try:
        page_limit = min(len(doc), int(cfg.get("max_pdf_pages", 120)))
        for pidx in range(page_limit):
            page = doc[pidx]
            page_num = pidx + 1

            tblocks = _pdf_text_blocks(page, page_num)
            for bidx, block in enumerate(tblocks):
                doc_order += 1
                text_blocks.append(
                    TextBlock(
                        block_id=block["id"],
                        page_number=page_num,
                        block_index=bidx,
                        bbox=block["bbox"],
                        text=block["text"],
                        sort_key=make_sort_key(page_num, bidx),
                        document_order=doc_order,
                    )
                )
    finally:
        doc.close()

    # Build per-page caption blocks from extracted text for image scoring.
    caption_blocks_by_page: dict[int, list[dict]] = {}
    for tb in text_blocks:
        caption_blocks_by_page.setdefault(tb.page_number, []).append(
            {"id": tb.block_id, "page": tb.page_number, "bbox": tb.bbox, "text": tb.text}
        )

    # Delegate image extraction to the standalone extractor to avoid duplication.
    # block_index_start=len(text_blocks) offsets image block indices past text block indices.
    images, img_stats = extract_images_pdf(
        file_path, rel_path, extract_root, cfg,
        caption_blocks_by_page=caption_blocks_by_page,
        doc_order_start=doc_order,
        block_index_start=len(text_blocks),
    )
    _merge_img_stats(stats, img_stats)

    table_dir = extract_root / "tables" / rel_path
    tables, table_issues = _extract_tables(file_path, table_dir)
    stats["tables"] = len(tables)
    if table_issues:
        stats["issues"].extend(table_issues)

    stats["text_blocks"] = len(text_blocks)

    return ExtractedPDF(
        source_path=rel_path,
        file_type="pdf",
        page_count=page_limit,
        text_blocks=text_blocks,
        images=images,
        tables=tables,
        stats=stats,
    )


def extract_pdf_docling(
    file_path: Path,
    rel_path: str,
    extract_root: Path,
    cfg: dict[str, Any],
) -> ExtractedPDF:
    """
    Extracts structured content from a PDF using Docling, producing typed
    TextBlock/ImageItem/TableItem records compatible with the PyMuPDF pipeline.

    Why PyMuPDF is the better default for this use case:
        Student assignment PDFs are overwhelmingly simple — single-column
        text, maybe a few inline images. For that layout, PyMuPDF is faster
        and feeds directly into this pipeline's OCR, image filtering, and
        caption scoring logic.

        This function uses Docling only for text and table extraction.
        Images are still extracted via extract_images_pdf() (PyMuPDF) so
        the full pipeline — is_diagram_image filtering, OCR fallback, and
        caption proximity scoring — is preserved even in Docling mode.

        Bottom line: for student submissions, Docling adds overhead without
        meaningfully improving text extraction quality.

    When Docling is worth enabling:
        Course materials with genuinely complex layouts — multi-column lab
        reports, papers with dense side-by-side figures and captions, or
        slides with rich tables. Docling's semantic element types (TITLE,
        TABLE, EQUATION, IMAGE with linked captions) improve RAG retrieval
        quality for those cases where PyMuPDF produces garbled or merged text.

    Coming back to Docling:
        This function is intentionally kept and wired up (--use-docling flag
        or USE_DOCLING=true env var) so it is easy to revisit without further
        plumbing. If assignments start including formatted lab reports or
        papers, flip the flag — no changes needed.

    Requires `pip install docling`.
    """
    if not _DOCLING_AVAILABLE:
        raise RuntimeError(
            "docling is not installed. Install it with: pip install docling"
        )

    _check_path_traversal(extract_root, rel_path)

    max_pages = int(cfg.get("max_pdf_pages", 120))
    min_text_chars = int(cfg.get("min_text_chars", 30))
    file_bytes = file_path.read_bytes()
    safe_name = Path(rel_path).name

    text_blocks: list[TextBlock] = []
    images: list[ImageItem] = []
    tables: list[TableItem] = []
    stats: dict[str, Any] = {
        "text_blocks": 0,
        "images_seen": 0,
        "images_kept": 0,
        "images_filtered": 0,
        "tables": 0,
        "issues": [],
    }

    doc_stream = DocumentStream(name=safe_name, stream=io.BytesIO(file_bytes))
    result = _get_docling_converter().convert(source=doc_stream)
    docling_doc = result.document

    doc_order = 0
    table_index = 0
    table_dir = extract_root / "tables" / rel_path

    for item, _level in docling_doc.iterate_items():
        prov = getattr(item, "prov", None)
        page_num = getattr(prov[0], "page_no", 1) if prov else 1

        if page_num > max_pages:
            continue

        if getattr(item, "label", None) in _DOCLING_SKIP_LABELS:
            continue

        if isinstance(item, (TitleItem, SectionHeaderItem)):
            text = (item.text or "").strip()
            if len(text) < min_text_chars // 2:  # titles can be short, use half threshold
                continue
            formatted = f"[TITLE] {text}"
        elif isinstance(item, FormulaItem):
            text = (item.text or "").strip()
            if not text:  # formulas can be short (e.g. "E=mc²"), no min_text_chars
                continue
            formatted = f"[EQUATION] {text}"
        elif isinstance(item, DoclingTableItem):
            html = item.export_to_html(doc=docling_doc, add_caption=False)
            if not html or not html.strip():
                continue
            table_index += 1
            doc_order += 1
            table_path = table_dir / f"table_{table_index:03d}_page_{page_num}.json"
            table_path.parent.mkdir(parents=True, exist_ok=True)
            payload = {"index": table_index, "page": page_num, "text": html, "rows": []}
            table_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")
            tables.append(TableItem(
                table_index=table_index,
                page_number=page_num,
                table_path=str(table_path),
                table_text=html,
                rows=[],
            ))
            continue
        elif isinstance(item, CodeItem):
            text = (item.text or "").strip()
            if not text:  # code can be short, no min_text_chars
                continue
            formatted = f"[CODE] {text}"
        elif isinstance(item, (KeyValueItem, TextItem, ListItem)):
            text = (item.text or "").strip()
            if len(text) < min_text_chars:
                continue
            formatted = text
        else:
            continue

        doc_order += 1
        _append_text_block(text_blocks, page_num, formatted, doc_order)

    # Use PyMuPDF for image extraction to preserve filtering, OCR, and caption scoring.
    # Docling text blocks have zero bboxes, so caption proximity scoring would be
    # non-functional if we passed them — pass None so extract_images_pdf falls back
    # to PyMuPDF's own text blocks for caption matching.
    images, img_stats = extract_images_pdf(
        file_path, rel_path, extract_root, cfg,
        caption_blocks_by_page=None,
        doc_order_start=doc_order,
        block_index_start=len(text_blocks),
    )
    _merge_img_stats(stats, img_stats)

    stats["text_blocks"] = len(text_blocks)
    stats["tables"] = len(tables)

    try:
        total_pages = int(docling_doc.num_pages()) if callable(getattr(docling_doc, "num_pages", None)) else int(getattr(docling_doc, "num_pages", 0) or 0)
    except Exception:
        total_pages = 0
    return ExtractedPDF(
        source_path=rel_path,
        file_type="pdf",
        page_count=min(total_pages, max_pages) if total_pages else max_pages,
        text_blocks=text_blocks,
        images=images,
        tables=tables,
        stats=stats,
    )


def extracted_pdf_to_jsonable(extracted: ExtractedPDF) -> dict[str, Any]:
    return {
        "source_path": extracted.source_path,
        "file_type": extracted.file_type,
        "page_count": extracted.page_count,
        "stats": extracted.stats,
        "text_blocks": [asdict(x) for x in extracted.text_blocks],
        "images": [asdict(x) for x in extracted.images],
        "tables": [asdict(x) for x in extracted.tables],
    }
