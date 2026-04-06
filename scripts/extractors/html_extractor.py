from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup

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


def extract_html(file_path: Path, rel_path: str, cfg: dict[str, Any]) -> ExtractedHTML:
    html = file_path.read_text(encoding="utf-8", errors="ignore")
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup.find_all(["script", "style", "nav", "header", "footer", "noscript"]):
        tag.decompose()

    kept_tags = {"p", "h1", "h2", "h3", "li"}
    elements = soup.find_all(list(kept_tags))

    out: list[HtmlTextBlock] = []
    stats = {"elements_scanned": 0, "elements_kept": 0, "text_blocks": 0}
    doc_order = 0

    for el_idx, el in enumerate(elements, 1):
        stats["elements_scanned"] += 1
        tag_name = str(getattr(el, "name", "") or "").lower()
        if tag_name not in kept_tags:
            continue
        text = clean_text(el.get_text(" ", strip=True))
        if len(text) < int(cfg.get("min_text_chars", 30)):
            continue

        stats["elements_kept"] += 1
        doc_order += 1
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

    stats["text_blocks"] = len(out)
    return ExtractedHTML(source_path=rel_path, file_type="html", text_blocks=out, stats=stats)


def extracted_html_to_jsonable(extracted: ExtractedHTML) -> dict[str, Any]:
    return {
        "source_path": extracted.source_path,
        "file_type": extracted.file_type,
        "stats": extracted.stats,
        "text_blocks": [asdict(x) for x in extracted.text_blocks],
    }
