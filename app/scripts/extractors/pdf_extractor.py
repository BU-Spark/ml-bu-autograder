from __future__ import annotations

import io
import json
import logging
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
        out.append(
            {
                "id": f"T{i+1}",
                "page": page_number,
                "bbox": {"x0": float(x0), "y0": float(y0), "x1": float(x1), "y1": float(y1)},
                "text": text,
            }
        )
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
    non_empty_cells = 0
    for v in body.values.flatten():
        if normalize_cell(v):
            non_empty_cells += 1
    return non_empty_cells >= 3


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

    texts: list[str] = []
    confs: list[float] = []
    words = 0
    for tile in tiles:
        res = compute_ocr(tile["bytes"])
        if res.text:
            texts.append(res.text)
        words += int(res.word_count)
        if res.avg_conf > 0:
            confs.append(float(res.avg_conf))

    combined = clean_text(" ".join(texts))
    avg_conf = round(sum(confs) / len(confs), 2) if confs else 0.0
    if not combined:
        return compute_ocr(image_bytes)
    return OCRResult(text=combined, word_count=words, avg_conf=avg_conf)


def extract_pdf(
    file_path: Path,
    rel_path: str,
    extract_root: Path,
    cfg: dict[str, Any],
) -> ExtractedPDF:
    if fitz is None:
        raise RuntimeError("PyMuPDF is not installed")

    doc = fitz.open(str(file_path))
    text_blocks: list[TextBlock] = []
    images: list[ImageItem] = []
    stats: dict[str, Any] = {
        "text_blocks": 0,
        "images_seen": 0,
        "images_kept": 0,
        "images_filtered": 0,
        "tables": 0,
        "issues": [],
    }

    doc_order = 0
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

            page_images = page.get_images(full=True)
            blocks_for_caption = [
                {
                    "id": tb.block_id,
                    "page": tb.page_number,
                    "bbox": tb.bbox,
                    "text": tb.text,
                }
                for tb in text_blocks
                if tb.page_number == page_num
            ]

            page_rect = page.rect
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
                if rect is not None:
                    caption_text = find_best_caption_for_image(
                        blocks_for_caption,
                        rect,
                        float(page_rect.width),
                        cfg,
                    )

                caption_block_id = None
                caption_distance = None
                ocr: OCRResult = _compute_ocr_with_optional_tiling(image_bytes, cfg)

                image_path = extract_root / "images" / rel_path / f"page_{page_num:03d}_img_{img_i:03d}.{ext}"
                _save_image(image_bytes, image_path)

                doc_order += 1
                block_index = len(tblocks) + img_i - 1
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
