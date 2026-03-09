from __future__ import annotations

import json
import re
from typing import Any

from core.chunking import clean_text


def default_structural_elements(indeterminate: bool = False) -> dict[str, str]:
    d = "indeterminate" if indeterminate else "none"
    return {
        "boxes": d,
        "diamonds": d,
        "arrows": d,
        "swim_lanes": d,
        "other_shapes": d,
    }


def to_string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        v = clean_text(value)
        return [v] if v else []
    if isinstance(value, list):
        out: list[str] = []
        for item in value:
            s = clean_text(str(item))
            if s:
                out.append(s)
        return out
    s = clean_text(str(value))
    return [s] if s else []


def extract_json_object(text: str) -> dict[str, Any] | None:
    text = text.strip()
    if not text:
        return None

    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.IGNORECASE | re.DOTALL)
    if fenced:
        candidate = fenced.group(1).strip()
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass

    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass

    start = text.find("{")
    while start != -1:
        depth = 0
        for i in range(start, len(text)):
            ch = text[i]
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    candidate = text[start : i + 1]
                    try:
                        parsed = json.loads(candidate)
                        if isinstance(parsed, dict):
                            return parsed
                    except Exception:
                        break
        start = text.find("{", start + 1)
    return None


def dedupe_preserve_order(values: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for v in values:
        s = clean_text(v)
        if not s or s in seen:
            continue
        seen.add(s)
        out.append(s)
    return out


def choose_merged_image_type(image_types: list[str], tiled: bool) -> str:
    cleaned = [clean_text(v) for v in image_types if clean_text(v) and clean_text(v) != "unknown"]
    if not cleaned:
        return "tiled_image" if tiled else "unknown"
    counts: dict[str, int] = {}
    for t in cleaned:
        counts[t] = counts.get(t, 0) + 1
    top = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
    return top


def normalize_vision_output(obj: dict[str, Any] | None, raw_text: str) -> dict[str, Any]:
    if obj is None:
        fallback_text = clean_text(raw_text)
        structural = default_structural_elements(indeterminate=True)
        return {
            "image_type": "indeterminate",
            "all_visible_text": [],
            "structural_elements": structural,
            "spatial_layout": "indeterminate",
            "completeness": "unknown",
            "unclear_parts": fallback_text or "model returned invalid/truncated response",
            "quality_warning": "response_not_valid_json",
            "visible_text": [],
            "description": fallback_text or "[no_description_returned]",
            "elements": [],
            "layout": "indeterminate",
            "json_parse_fallback_used": True,
        }

    image_type = clean_text(str(obj.get("image_type", "indeterminate"))) or "indeterminate"
    all_visible_text = to_string_list(obj.get("all_visible_text", obj.get("visible_text", [])))
    structural_elements_raw = obj.get("structural_elements", {})
    if not isinstance(structural_elements_raw, dict):
        structural_elements_raw = {}
    base_struct = default_structural_elements(indeterminate=False)
    structural_elements = {
        "boxes": clean_text(str(structural_elements_raw.get("boxes", base_struct["boxes"]))),
        "diamonds": clean_text(str(structural_elements_raw.get("diamonds", base_struct["diamonds"]))),
        "arrows": clean_text(str(structural_elements_raw.get("arrows", base_struct["arrows"]))),
        "swim_lanes": clean_text(str(structural_elements_raw.get("swim_lanes", base_struct["swim_lanes"]))),
        "other_shapes": clean_text(str(structural_elements_raw.get("other_shapes", base_struct["other_shapes"]))),
    }
    spatial_layout = clean_text(str(obj.get("spatial_layout", obj.get("layout", ""))))
    completeness = clean_text(str(obj.get("completeness", ""))) or "unknown"
    unclear_parts = clean_text(str(obj.get("unclear_parts", "")))
    quality_warning = clean_text(str(obj.get("quality_warning", "")))
    description = clean_text(str(obj.get("description", "")))
    if not description:
        description = clean_text(
            f"Type={image_type}; layout={spatial_layout or 'n/a'}; completeness={completeness}; unclear={unclear_parts or 'none'}"
        )
    visible_text = all_visible_text
    elements = dedupe_preserve_order(
        [
            structural_elements.get("boxes", ""),
            structural_elements.get("diamonds", ""),
            structural_elements.get("arrows", ""),
            structural_elements.get("swim_lanes", ""),
            structural_elements.get("other_shapes", ""),
        ]
    )
    layout = spatial_layout
    return {
        "image_type": image_type,
        "all_visible_text": all_visible_text,
        "structural_elements": structural_elements,
        "spatial_layout": spatial_layout,
        "completeness": completeness,
        "quality_warning": quality_warning,
        "visible_text": visible_text,
        "description": description,
        "elements": elements,
        "layout": layout,
        "unclear_parts": unclear_parts,
        "json_parse_fallback_used": False,
    }


def merge_vision_tile_outputs(tile_outputs: list[dict[str, Any]], tiled: bool) -> dict[str, Any]:
    image_types = [str(t.get("image_type", "unknown")) for t in tile_outputs]
    all_visible_text: list[str] = []
    boxes: list[str] = []
    diamonds: list[str] = []
    arrows: list[str] = []
    swim_lanes: list[str] = []
    other_shapes: list[str] = []
    spatial_layout_parts: list[str] = []
    description_parts: list[str] = []
    completeness_parts: list[str] = []
    unclear_parts_list: list[str] = []
    quality_warning_parts: list[str] = []
    parse_fallback_used = False

    for i, t in enumerate(tile_outputs, 1):
        all_visible_text.extend(to_string_list(t.get("all_visible_text", t.get("visible_text", []))))

        struct = t.get("structural_elements", {})
        if not isinstance(struct, dict):
            struct = {}

        for key, target in [
            ("boxes", boxes),
            ("diamonds", diamonds),
            ("arrows", arrows),
            ("swim_lanes", swim_lanes),
            ("other_shapes", other_shapes),
        ]:
            val = clean_text(str(struct.get(key, "")))
            if val:
                target.append(f"Tile {i}: {val}" if tiled else val)

        layout = clean_text(str(t.get("spatial_layout", t.get("layout", ""))))
        if layout:
            spatial_layout_parts.append(f"Tile {i}: {layout}" if tiled else layout)

        description = clean_text(str(t.get("description", "")))
        if description:
            description_parts.append(f"Tile {i}: {description}" if tiled else description)

        completeness = clean_text(str(t.get("completeness", "")))
        if completeness:
            completeness_parts.append(f"Tile {i}: {completeness}" if tiled else completeness)

        unclear = clean_text(str(t.get("unclear_parts", "")))
        if unclear:
            unclear_parts_list.append(unclear)

        warning = clean_text(str(t.get("quality_warning", "")))
        if warning:
            quality_warning_parts.append(warning)

        if bool(t.get("json_parse_fallback_used", False)):
            parse_fallback_used = True

    merged_structural = {
        "boxes": clean_text(" | ".join(dedupe_preserve_order(boxes))) or "none",
        "diamonds": clean_text(" | ".join(dedupe_preserve_order(diamonds))) or "none",
        "arrows": clean_text(" | ".join(dedupe_preserve_order(arrows))) or "none",
        "swim_lanes": clean_text(" | ".join(dedupe_preserve_order(swim_lanes))) or "none",
        "other_shapes": clean_text(" | ".join(dedupe_preserve_order(other_shapes))) or "none",
    }

    merged_layout = clean_text(" ".join(spatial_layout_parts)) or "indeterminate"
    merged_description = clean_text(" | ".join(dedupe_preserve_order(description_parts)))
    merged_completeness = clean_text(" | ".join(dedupe_preserve_order(completeness_parts))) or "unknown"
    merged_unclear = clean_text(" | ".join(dedupe_preserve_order(unclear_parts_list)))
    merged_quality_warning = clean_text(" | ".join(dedupe_preserve_order(quality_warning_parts)))
    merged_text = dedupe_preserve_order(all_visible_text)

    return {
        "image_type": choose_merged_image_type(image_types, tiled=tiled),
        "all_visible_text": merged_text,
        "structural_elements": merged_structural,
        "spatial_layout": merged_layout,
        "completeness": merged_completeness,
        "unclear_parts": merged_unclear,
        "quality_warning": merged_quality_warning,
        "visible_text": merged_text,
        "description": (
            merged_description
            or clean_text(
                f"Type={choose_merged_image_type(image_types, tiled=tiled)}; layout={merged_layout}; completeness={merged_completeness}; unclear={merged_unclear or 'none'}"
            )
            or "[no_description_returned]"
        ),
        "elements": dedupe_preserve_order(
            [
                merged_structural["boxes"],
                merged_structural["diamonds"],
                merged_structural["arrows"],
                merged_structural["swim_lanes"],
                merged_structural["other_shapes"],
            ]
        ),
        "layout": merged_layout,
        "json_parse_fallback_used": parse_fallback_used,
    }


def build_image_text_content(vision_struct: dict[str, Any]) -> str:
    image_type = clean_text(str(vision_struct.get("image_type", "indeterminate"))) or "indeterminate"
    visible_text_list = to_string_list(vision_struct.get("all_visible_text", vision_struct.get("visible_text", [])))
    structural_elements = vision_struct.get("structural_elements", {})
    if not isinstance(structural_elements, dict):
        structural_elements = {}
    spatial_layout = clean_text(str(vision_struct.get("spatial_layout", vision_struct.get("layout", ""))))
    description = clean_text(str(vision_struct.get("description", "")))
    completeness = clean_text(str(vision_struct.get("completeness", ""))) or "unknown"
    unclear_parts = clean_text(str(vision_struct.get("unclear_parts", "")))
    quality_warning = clean_text(str(vision_struct.get("quality_warning", "")))

    sections: list[str] = []
    sections.append(f"Image type: {image_type}")
    if description:
        sections.append(f"Image description: {description}")
    sections.append(
        "Extracted visible text:\n"
        + ("\n".join(f"- {line}" for line in visible_text_list) if visible_text_list else "- [none]")
    )
    sections.append(
        "Structural elements:\n"
        + "\n".join(
            [
                f"- boxes: {clean_text(str(structural_elements.get('boxes', 'none')))}",
                f"- diamonds: {clean_text(str(structural_elements.get('diamonds', 'none')))}",
                f"- arrows: {clean_text(str(structural_elements.get('arrows', 'none')))}",
                f"- swim_lanes: {clean_text(str(structural_elements.get('swim_lanes', 'none')))}",
                f"- other_shapes: {clean_text(str(structural_elements.get('other_shapes', 'none')))}",
            ]
        )
    )
    if spatial_layout:
        sections.append(f"Spatial layout: {spatial_layout}")
    sections.append(f"Completeness: {completeness}")
    if unclear_parts:
        sections.append(f"Unclear parts: {unclear_parts}")
    if quality_warning:
        sections.append(f"Quality warning: {quality_warning}")
    return "\n\n".join(sections).strip()
