from __future__ import annotations

import io
import math
from typing import Any

from PIL import Image


def compute_tile_grid(width: int, height: int, target_max_pixels: int, max_tiles: int) -> tuple[int, int]:
    target = max(1, int(target_max_pixels))
    max_tiles = max(2, int(max_tiles))
    total_pixels = max(1, width * height)
    desired_tiles = max(2, math.ceil(total_pixels / target))
    desired_tiles = min(desired_tiles, max_tiles)

    best_rows = 1
    best_cols = desired_tiles
    best_score = float("inf")

    for rows in range(1, desired_tiles + 1):
        cols = math.ceil(desired_tiles / rows)
        if rows * cols > max_tiles:
            continue
        tile_w = math.ceil(width / cols)
        tile_h = math.ceil(height / rows)
        tile_pixels = tile_w * tile_h
        aspect_penalty = abs((tile_w / max(1, tile_h)) - 1.0)
        score = tile_pixels + aspect_penalty * 10000 + (rows * cols - desired_tiles) * 100
        if score < best_score:
            best_score = score
            best_rows, best_cols = rows, cols

    if best_rows * best_cols < 2:
        if width >= height:
            best_rows, best_cols = 1, 2
        else:
            best_rows, best_cols = 2, 1
    return best_rows, best_cols


def split_image_into_tiles(
    image_bytes: bytes,
    target_max_pixels: int,
    max_tiles: int,
) -> tuple[list[dict[str, Any]], int, int, int, int, int]:
    with Image.open(io.BytesIO(image_bytes)) as img:
        rgb = img.convert("RGB")
        width, height = rgb.size
        total_pixels = width * height
        rows, cols = compute_tile_grid(width, height, target_max_pixels, max_tiles)

        tile_w = math.ceil(width / cols)
        tile_h = math.ceil(height / rows)

        tiles: list[dict[str, Any]] = []
        idx = 0
        for r in range(rows):
            for c in range(cols):
                left = c * tile_w
                upper = r * tile_h
                right = min(width, left + tile_w)
                lower = min(height, upper + tile_h)
                if right <= left or lower <= upper:
                    continue
                crop = rgb.crop((left, upper, right, lower))
                buf = io.BytesIO()
                crop.save(buf, format="PNG")
                idx += 1
                tiles.append(
                    {
                        "index": idx,
                        "row": r + 1,
                        "col": c + 1,
                        "bbox": {"x0": left, "y0": upper, "x1": right, "y1": lower},
                        "width": right - left,
                        "height": lower - upper,
                        "pixels": (right - left) * (lower - upper),
                        "bytes": buf.getvalue(),
                        "mime_type": "image/png",
                    }
                )
        return tiles, width, height, total_pixels, rows, cols
