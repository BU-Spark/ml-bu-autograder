from __future__ import annotations

from typing import Any

from PIL import Image


def is_diagram_image(
    pil_img: Image.Image,
    img_rect: Any,
    page_height: float,
    cfg: dict[str, Any],
) -> tuple[bool, str]:
    w, h = pil_img.size

    if w * h < int(cfg["min_area"]):
        return False, f"too_small_area_{w*h}"
    if min(w, h) < int(cfg["min_side"]):
        return False, f"too_small_side_{min(w,h)}"

    aspect = w / max(h, 1)
    if aspect > float(cfg["max_aspect_ratio"]):
        return False, f"ultra_wide_{aspect:.2f}"
    if aspect < float(cfg["min_aspect_ratio"]):
        return False, f"ultra_tall_{aspect:.2f}"

    if img_rect is not None and page_height > 0:
        center_y = (float(img_rect.y0) + float(img_rect.y1)) / 2.0
        margin = float(cfg["page_margin_pct"]) * float(page_height)
        if center_y < margin:
            return False, "header_region"
        if center_y > float(page_height) - margin:
            return False, "footer_region"

    return True, "ok"
