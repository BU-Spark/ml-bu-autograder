from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from core.chunking import clean_text


_FIG_REGEX = re.compile(r"^fig(ure)?\s*\d+", re.IGNORECASE)
_DIAGRAM_REGEX = re.compile(r"^diagram\s*\d+", re.IGNORECASE)
CAPTION_PREFIXES = ("figure", "fig.", "fig ", "diagram", "image", "workflow", "step", "table")


@dataclass
class CaptionBlock:
    page: int
    x0: float
    y0: float
    x1: float
    y1: float
    text: str


def _block_from_any(b: Any) -> CaptionBlock:
    if isinstance(b, CaptionBlock):
        return b
    if isinstance(b, dict):
        if "bbox" in b:
            bb = b["bbox"]
            return CaptionBlock(
                page=int(b.get("page", 1)),
                x0=float(bb["x0"]),
                y0=float(bb["y0"]),
                x1=float(bb["x1"]),
                y1=float(bb["y1"]),
                text=clean_text(str(b.get("text", ""))),
            )
        return CaptionBlock(
            page=int(b.get("page", 1)),
            x0=float(b["x0"]),
            y0=float(b["y0"]),
            x1=float(b["x1"]),
            y1=float(b["y1"]),
            text=clean_text(str(b.get("text", ""))),
        )
    raise TypeError("Unsupported caption block type")


def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def assign_column_bin(x_center: float, page_width: float, n_bins: int) -> int:
    bin_width = page_width / n_bins
    return min(int(x_center / max(1.0, bin_width)), n_bins - 1)


def _collapse_group(group: list[CaptionBlock]) -> CaptionBlock:
    if len(group) == 1:
        return group[0]
    text = " ".join(clean_text(g.text) for g in group)
    return CaptionBlock(
        page=group[0].page,
        x0=min(g.x0 for g in group),
        y0=group[0].y0,
        x1=max(g.x1 for g in group),
        y1=group[-1].y1,
        text=clean_text(text),
    )


def merge_caption_lines(candidates: list[Any], max_line_gap: float) -> list[CaptionBlock]:
    blocks = sorted([_block_from_any(c) for c in candidates], key=lambda b: b.y0)
    if not blocks:
        return []
    merged: list[CaptionBlock] = []
    group = [blocks[0]]
    for block in blocks[1:]:
        prev = group[-1]
        vertical_gap = block.y0 - prev.y1
        x_close = abs(block.x0 - prev.x0) < 40
        if vertical_gap <= max_line_gap and x_close:
            group.append(block)
        else:
            merged.append(_collapse_group(group))
            group = [block]
    merged.append(_collapse_group(group))
    return merged


def score_caption_candidate(img_rect: Any, block: Any, cfg: dict[str, Any]) -> float:
    b = _block_from_any(block)
    below_dist = abs(b.y0 - float(img_rect.y1))
    above_dist = abs(float(img_rect.y0) - b.y1)
    vertical_dist = min(below_dist, above_dist)

    below_bonus = float(cfg["caption_below_bonus"]) if b.y0 >= float(img_rect.y1) else 0.0

    overlap_x0 = max(float(img_rect.x0), b.x0)
    overlap_x1 = min(float(img_rect.x1), b.x1)
    overlap = max(0.0, overlap_x1 - overlap_x0)
    img_w = max(1.0, float(img_rect.x1) - float(img_rect.x0))
    overlap_ratio = overlap / img_w
    overlap_bonus = overlap_ratio * float(cfg["caption_overlap_bonus"])

    t = b.text.lower()
    prefix_bonus = float(cfg["caption_prefix_bonus"]) if any(t.startswith(p) for p in CAPTION_PREFIXES) else 0.0

    regex_boost = 0.0
    if _FIG_REGEX.match(b.text) or _DIAGRAM_REGEX.match(b.text):
        regex_boost = float(cfg["caption_regex_boost"])

    excess = len(b.text) - int(cfg["caption_length_penalty_start"])
    length_penalty = clamp(excess / float(cfg["caption_length_penalty_scale"]), 0.0, 60.0)

    if len(b.text) > int(cfg["caption_max_length"]):
        return -9999.0

    return (100.0 - vertical_dist) + below_bonus + overlap_bonus + prefix_bonus + regex_boost - length_penalty


def find_best_caption_for_image(
    page_blocks: list[Any],
    img_rect: Any,
    page_width: float,
    cfg: dict[str, Any],
) -> str:
    img_x_center = (float(img_rect.x0) + float(img_rect.x1)) / 2.0
    img_col = assign_column_bin(img_x_center, page_width, int(cfg["column_bins"]))

    nearby: list[CaptionBlock] = []
    for raw_block in page_blocks:
        b = _block_from_any(raw_block)
        b_x_center = (b.x0 + b.x1) / 2.0
        b_col = assign_column_bin(b_x_center, page_width, int(cfg["column_bins"]))
        if b_col != img_col:
            continue

        vertical_dist = min(abs(b.y0 - float(img_rect.y1)), abs(float(img_rect.y0) - b.y1))
        if vertical_dist > float(cfg["caption_vertical_window"]):
            continue
        nearby.append(b)

    if not nearby:
        return "No caption found"

    merged = merge_caption_lines(nearby, float(cfg["caption_max_line_gap"]))
    scored = [(score_caption_candidate(img_rect, b, cfg), b) for b in merged]
    scored.sort(key=lambda x: x[0], reverse=True)

    top = [
        clean_text(b.text)
        for score, b in scored[: int(cfg["caption_max_candidates"])]
        if score > -9999.0 and clean_text(b.text)
    ]
    return " ".join(top) if top else "No caption found"
