"""
Chunking strategies for HTML lecture text. Used by html_lecture_ingest and eval scripts.
"""

import re


def chunk_by_semantic(text: str, max_chars: int = 4000) -> list[str]:
    """Split by paragraph boundaries; sub-split long sections."""
    sections = [s.strip() for s in text.split("\n\n") if s.strip()]
    chunks, current, current_len = [], [], 0
    for sec in sections:
        sec_len = len(sec) + 2
        if current_len + sec_len > max_chars and current:
            chunks.append("\n\n".join(current))
            current, current_len = [], 0
        current.append(sec)
        current_len += sec_len
    if current:
        chunks.append("\n\n".join(current))
    return chunks


def chunk_by_fixed_tokens(text: str, chunk_chars: int = 800, overlap_chars: int = 150) -> list[str]:
    """Fixed-size sliding window with overlap. Char-based (approx tokens)."""
    text = re.sub(r"\n{3,}", "\n\n", text.strip())
    if not text:
        return []
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_chars
        chunk = text[start:end]
        if chunk.strip():
            chunks.append(chunk.strip())
        start = end - overlap_chars
        if start >= len(text):
            break
    return chunks


def chunk_hybrid(text: str, max_chars: int = 4000, sub_chunk: int = 800) -> list[str]:
    """Semantic first; if a section exceeds sub_chunk, split with fixed overlap."""
    sections = [s.strip() for s in text.split("\n\n") if s.strip()]
    chunks = []
    for sec in sections:
        if len(sec) <= max_chars:
            if len(sec) <= sub_chunk:
                chunks.append(sec)
            else:
                chunks.extend(chunk_by_fixed_tokens(sec, chunk_chars=sub_chunk, overlap_chars=100))
        else:
            chunks.extend(chunk_by_fixed_tokens(sec, chunk_chars=sub_chunk, overlap_chars=100))
    return [c for c in chunks if c.strip()]
