from __future__ import annotations

import hashlib
import re


def clean_text(text: str) -> str:
    text = str(text).replace("\x00", " ").replace("\u2014", "-")
    return re.sub(r"\s+", " ", text).strip()


def chunk_text(text: str, max_chars: int, overlap: int) -> list[str]:
    text = clean_text(text)
    if not text:
        return []
    if len(text) <= max_chars:
        return [text]

    chunks: list[str] = []
    start = 0
    n = len(text)
    while start < n:
        end = min(n, start + max_chars)
        if end < n:
            cut = text.rfind(" ", start + int(max_chars * 0.6), end)
            if cut > start:
                end = cut
        piece = text[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= n:
            break
        start = max(0, end - overlap)
    return chunks


def sha1_id(raw: str) -> str:
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def make_sort_key(page_number: int, block_index: int) -> str:
    return f"{int(page_number):04d}-{int(block_index):04d}"
