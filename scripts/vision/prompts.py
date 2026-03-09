from __future__ import annotations


def classify_image_quality(width: int, height: int, total_pixels: int) -> str:
    if width >= 200 and height >= 200 and total_pixels >= 40_000:
        return "clear"
    if width >= 50 and height >= 50 and total_pixels >= 2_500:
        return "low_res"
    return "unreadable"


def quality_warning_from_band(image_quality: str) -> str | None:
    if image_quality == "low_res":
        return "low_resolution_possible_information_loss"
    if image_quality == "unreadable":
        return "below_usable_resolution"
    return None


def image_aspect_ratio(width: int, height: int) -> float:
    return round(float(width) / max(1.0, float(height)), 4)


def build_prompt(
    image_quality: str,
    image_width: int,
    image_height: int,
    max_visible_text_items: int,
    source_file: str,
    locator: str,
    caption_hint: str,
    retry_note: str | None = None,
) -> str:
    if image_quality == "clear":
        preamble = (
            "You are a precise document analyst. This is a clear, high-resolution image "
            f"(width: {image_width}px, height: {image_height}px). "
            "Extract EVERYTHING visible. Do not summarize. Do not infer."
        )
    elif image_quality == "low_res":
        preamble = (
            "You are a precise document analyst. This image is LOW RESOLUTION "
            f"(width: {image_width}px, height: {image_height}px). "
            "Attempt full extraction and explicitly flag uncertainty. Do not guess."
        )
    else:
        preamble = (
            "You are a precise document analyst. This image is VERY LOW RESOLUTION or VERY SMALL "
            f"(width: {image_width}px, height: {image_height}px). "
            "Attempt extraction anyway and be explicit about what is indeterminate."
        )

    prompt = (
        f"{preamble}\n"
        "Rules:\n"
        "- Only report what is literally visible in the image.\n"
        "- Do not infer or add external context.\n"
        "- Preserve text verbatim where readable.\n"
        f"- Include at most {int(max_visible_text_items)} entries in all_visible_text.\n"
        "Return ONLY valid JSON with these exact keys:\n"
        "{\n"
        '  "image_type": "workflow_diagram|swimlane|table|chart|screenshot|photo|text_block|other|indeterminate",\n'
        '  "all_visible_text": ["string"],\n'
        '  "structural_elements": {\n'
        '    "boxes": "string",\n'
        '    "diamonds": "string",\n'
        '    "arrows": "string",\n'
        '    "swim_lanes": "string",\n'
        '    "other_shapes": "string"\n'
        "  },\n"
        '  "spatial_layout": "string",\n'
        '  "completeness": "string",\n'
        '  "unclear_parts": "string",\n'
        '  "quality_warning": "string"\n'
        "}\n"
        f"Source: {source_file} ({locator}).\n"
        f"Caption hint (may be empty): {caption_hint or '[none]'}"
    )
    if retry_note:
        prompt += f"\nRetry instruction: {retry_note}"
    return prompt
