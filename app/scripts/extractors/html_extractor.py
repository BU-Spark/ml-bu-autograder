from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup, Tag

from core.chunking import clean_text, make_sort_key


@dataclass
class HtmlTextBlock:
    element_tag: str
    page_number: int
    block_index: int
    text: str
    sort_key: str
    document_order: int


@dataclass
class ExtractedHTML:
    source_path: str
    file_type: str
    text_blocks: list[HtmlTextBlock]
    stats: dict[str, Any]


# Tags to strip entirely — navigation chrome, scripts, ads
_STRIP_TAGS = [
    "script", "style", "noscript", "nav", "header", "footer",
    "aside", "menu", "button", "form", "input", "select", "textarea",
    "iframe", "embed", "object", "svg", "canvas",
]

# Heading tags — always keep, even if short (e.g. "Q1")
_HEADING_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6"}

# Block-level content tags extracted as individual text blocks
_CONTENT_TAGS = _HEADING_TAGS | {
    "p", "li", "blockquote", "pre", "code",
    "dt", "dd", "figcaption", "caption",
}

# CSS class / id keywords that indicate navigation chrome — decompose these
_NAV_KEYWORDS = (
    "nav", "menu", "sidebar", "breadcrumb",
    "cookie", "banner", "advertisement", "social", "share", "popup",
)


def _is_nav_element(tag: Tag) -> bool:
    cls = " ".join(tag.get("class") or []).lower()
    tid = (tag.get("id") or "").lower()
    return any(k in cls or k in tid for k in _NAV_KEYWORDS)


def _extract_table_as_text(table: Tag) -> str:
    """Convert an HTML <table> into a pipe-delimited readable text block.
    Returns empty string for layout tables (video players, single-cell wrappers, etc.)
    """
    # Skip layout/wrapper tables: only 1 cell total → not a data table
    all_cells = table.find_all(["th", "td"])
    if len(all_cells) <= 1:
        return ""
    # Skip video-player tables: their text contains "video cannot be displayed"
    full_text = table.get_text(" ", strip=True).lower()
    if "video cannot be displayed" in full_text or "videos cannot be played" in full_text:
        return ""

    rows_text: list[str] = []
    for row in table.find_all("tr"):
        cells = row.find_all(["th", "td"])
        if not cells:
            continue
        row_str = " | ".join(
            clean_text(cell.get_text(" ", strip=True))
            for cell in cells
            if clean_text(cell.get_text(" ", strip=True))
        )
        if row_str.strip():
            rows_text.append(row_str)
    if not rows_text:
        return ""
    # Insert a visual separator after the header row
    if len(rows_text) > 1:
        rows_text.insert(1, "-" * min(60, max(len(rows_text[0]), 20)))
    return "\n".join(rows_text)


def extract_html(file_path: Path, rel_path: str, cfg: dict[str, Any]) -> ExtractedHTML:
    html = file_path.read_text(encoding="utf-8", errors="ignore")
    soup = BeautifulSoup(html, "html.parser")

    # Remove chrome/navigation tags
    for tag in soup.find_all(_STRIP_TAGS):
        tag.decompose()

    # Remove nav-like elements by class/id heuristics
    for tag in soup.find_all(True):
        if isinstance(tag, Tag) and _is_nav_element(tag):
            tag.decompose()

    # Use a much lower threshold for HTML — headings like "Q1" or "Step 3" are only 2-6 chars
    min_chars = max(3, int(cfg.get("min_text_chars", 30)) // 5)

    out: list[HtmlTextBlock] = []
    stats = {
        "elements_scanned": 0,
        "elements_kept": 0,
        "tables_extracted": 0,
        "images_extracted": 0,
        "text_blocks": 0,
    }
    doc_order = 0
    el_idx = 0
    processed: set[int] = set()  # track elements already handled

    def _add_block(tag_name: str, text: str, min_len: int = min_chars) -> None:
        nonlocal doc_order, el_idx
        text = clean_text(text)
        if len(text) < min_len:
            return
        doc_order += 1
        el_idx += 1
        out.append(
            HtmlTextBlock(
                element_tag=tag_name,
                page_number=1,
                block_index=el_idx,
                text=text,
                sort_key=make_sort_key(1, el_idx),
                document_order=doc_order,
            )
        )
        stats["elements_kept"] += 1

    for element in soup.descendants:
        stats["elements_scanned"] += 1

        if not isinstance(element, Tag):
            continue

        tag_name = str(getattr(element, "name", "") or "").lower()
        if not tag_name:
            continue

        if id(element) in processed:
            continue

        # --- Tables: render as formatted rows ---
        if tag_name == "table":
            table_text = _extract_table_as_text(element)
            if table_text:
                _add_block("table", table_text, min_len=10)
                stats["tables_extracted"] += 1
            # Mark all table descendants processed so cells aren't double-counted
            for desc in element.descendants:
                if isinstance(desc, Tag):
                    processed.add(id(desc))
            processed.add(id(element))
            continue

        # --- Images: extract alt/title text ---
        if tag_name == "img":
            alt = (element.get("alt") or element.get("title") or "").strip()
            if alt:
                _add_block("img_alt", f"[Image: {clean_text(alt)}]", min_len=5)
                stats["images_extracted"] += 1
            processed.add(id(element))
            continue

        # --- Content tags: extract as individual text blocks ---
        if tag_name in _CONTENT_TAGS:
            # Skip cells already consumed by a table
            if element.find_parent("table"):
                processed.add(id(element))
                continue
            text = element.get_text(" ", strip=True)
            # Headings can be very short (e.g. "Q1", "Step 2")
            min_len = 3 if tag_name in _HEADING_TAGS else min_chars
            _add_block(tag_name, text, min_len=min_len)
            # Mark nested content tags processed to avoid double extraction
            for desc in element.descendants:
                if isinstance(desc, Tag) and str(getattr(desc, "name", "")).lower() in _CONTENT_TAGS:
                    processed.add(id(desc))
            processed.add(id(element))
            continue

    stats["text_blocks"] = len(out)
    return ExtractedHTML(source_path=rel_path, file_type="html", text_blocks=out, stats=stats)


def extracted_html_to_jsonable(extracted: ExtractedHTML) -> dict[str, Any]:
    return {
        "source_path": extracted.source_path,
        "file_type": extracted.file_type,
        "stats": extracted.stats,
        "text_blocks": [asdict(x) for x in extracted.text_blocks],
    }
