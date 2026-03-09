from __future__ import annotations

import base64
import io
import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any

from PIL import Image

from .output_normalizer import (
    build_image_text_content,
    extract_json_object,
    merge_vision_tile_outputs,
    normalize_vision_output,
)
from .prompts import build_prompt, classify_image_quality, image_aspect_ratio, quality_warning_from_band
from .tiling import split_image_into_tiles

try:
    from anthropic import Anthropic
except Exception:
    Anthropic = None

try:
    from openai import OpenAI
except Exception:
    OpenAI = None


@dataclass
class VisionProcessResult:
    structured: dict[str, Any] | None
    error: str | None
    calls_attempted: int
    calls_succeeded: int
    call_errors: int
    input_tokens: int
    output_tokens: int
    total_tokens: int
    retry_used: bool
    tiled: bool
    tile_count: int
    tile_rows: int
    tile_cols: int
    image_width: int
    image_height: int
    image_pixels: int
    image_quality: str
    image_aspect_ratio: float
    quality_warning: str | None
    gpt4o_called: bool
    json_invalid_after_retry: bool


class VisionDescriber:
    def __init__(self, provider: str, model: str, max_tokens: int, api_keys: dict[str, str | None]) -> None:
        self.provider = provider
        self.model = model
        self.max_tokens = max_tokens
        self._client = None
        self._api_key = None

        if provider == "anthropic":
            if Anthropic is None:
                raise RuntimeError("anthropic package is not installed")
            api_key = api_keys.get("anthropic")
            if not api_key:
                raise RuntimeError("ANTHROPIC_API_KEY is not set")
            self._client = Anthropic(api_key=api_key)
        elif provider == "openai":
            if OpenAI is None:
                raise RuntimeError("openai package is not installed")
            api_key = api_keys.get("openai")
            if not api_key:
                raise RuntimeError("OPENAI_API_KEY is not set")
            self._client = OpenAI(api_key=api_key)
        elif provider == "gemini":
            api_key = api_keys.get("gemini")
            if not api_key:
                raise RuntimeError("GEMINI_API_KEY is not set")
            self._api_key = api_key

    def describe(
        self,
        image_bytes: bytes,
        mime_type: str,
        caption_hint: str,
        source_file: str,
        locator: str,
        image_quality: str,
        image_width: int,
        image_height: int,
        max_tokens: int | None = None,
        retry_note: str | None = None,
        max_visible_text_items: int = 120,
    ) -> tuple[dict[str, Any], dict[str, int]]:
        effective_max_tokens = int(max_tokens or self.max_tokens)
        prompt = build_prompt(
            image_quality=image_quality,
            image_width=image_width,
            image_height=image_height,
            max_visible_text_items=max_visible_text_items,
            source_file=source_file,
            locator=locator,
            caption_hint=caption_hint,
            retry_note=retry_note,
        )

        if self.provider == "anthropic":
            assert self._client is not None
            b64 = base64.b64encode(image_bytes).decode("ascii")
            message = self._client.messages.create(
                model=self.model,
                max_tokens=effective_max_tokens,
                temperature=0,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": mime_type,
                                    "data": b64,
                                },
                            },
                        ],
                    }
                ],
            )
            parts = []
            for part in message.content:
                if getattr(part, "type", None) == "text":
                    parts.append(getattr(part, "text", ""))
            raw_text = " ".join(parts).strip()
            parsed_obj = extract_json_object(raw_text)
            normalized = normalize_vision_output(parsed_obj, raw_text)
            usage_obj = getattr(message, "usage", None)
            input_tokens = int(getattr(usage_obj, "input_tokens", 0) or 0)
            output_tokens = int(getattr(usage_obj, "output_tokens", 0) or 0)
            return normalized, {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
            }

        if self.provider == "openai":
            assert self._client is not None
            b64 = base64.b64encode(image_bytes).decode("ascii")
            data_url = f"data:{mime_type};base64,{b64}"
            payload = {
                "model": self.model,
                "input": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "input_text", "text": prompt},
                            {"type": "input_image", "image_url": data_url},
                        ],
                    }
                ],
                "max_output_tokens": effective_max_tokens,
                "temperature": 0,
            }
            try:
                response = self._client.responses.create(**payload)
            except TypeError:
                payload.pop("temperature", None)
                response = self._client.responses.create(**payload)
            raw_text = (getattr(response, "output_text", "") or "").strip()
            parsed_obj = extract_json_object(raw_text)
            normalized = normalize_vision_output(parsed_obj, raw_text)
            usage_obj = getattr(response, "usage", None)
            input_tokens = int(getattr(usage_obj, "input_tokens", 0) or 0)
            output_tokens = int(getattr(usage_obj, "output_tokens", 0) or 0)
            total_tokens = int(getattr(usage_obj, "total_tokens", 0) or (input_tokens + output_tokens))
            return normalized, {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": total_tokens,
            }

        if self.provider == "gemini":
            assert self._api_key is not None
            b64 = base64.b64encode(image_bytes).decode("ascii")
            endpoint = (
                "https://generativelanguage.googleapis.com/v1beta/models/"
                f"{urllib.parse.quote(self.model, safe='')}:generateContent"
                f"?key={urllib.parse.quote(self._api_key, safe='')}"
            )
            body = {
                "contents": [
                    {
                        "parts": [
                            {"text": prompt},
                            {
                                "inline_data": {
                                    "mime_type": mime_type,
                                    "data": b64,
                                }
                            },
                        ]
                    }
                ],
                "generationConfig": {
                    "temperature": 0,
                    "maxOutputTokens": effective_max_tokens,
                },
            }
            req = urllib.request.Request(
                endpoint,
                data=json.dumps(body).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            try:
                with urllib.request.urlopen(req, timeout=120) as resp:
                    raw = resp.read().decode("utf-8", errors="ignore")
            except urllib.error.HTTPError as exc:
                err_body = ""
                try:
                    err_body = exc.read().decode("utf-8", errors="ignore")
                except Exception:
                    pass
                raise RuntimeError(f"gemini_http_{exc.code}: {err_body or str(exc)}") from exc

            parsed_response = json.loads(raw) if raw else {}
            candidates = parsed_response.get("candidates", [])
            text_parts: list[str] = []
            for cand in candidates:
                content = cand.get("content", {})
                for part in content.get("parts", []):
                    t = part.get("text")
                    if t:
                        text_parts.append(str(t))
            raw_text = " ".join(text_parts).strip()
            parsed_obj = extract_json_object(raw_text)
            normalized = normalize_vision_output(parsed_obj, raw_text)
            usage_obj = parsed_response.get("usageMetadata", {}) or {}
            input_tokens = int(usage_obj.get("promptTokenCount", 0) or 0)
            output_tokens = int(usage_obj.get("candidatesTokenCount", 0) or 0)
            total_tokens = int(usage_obj.get("totalTokenCount", 0) or (input_tokens + output_tokens))
            return normalized, {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": total_tokens,
            }

        raise RuntimeError(f"Unsupported vision provider: {self.provider}")


def describe_image_with_strategy(
    vision: VisionDescriber,
    image_bytes: bytes,
    mime_type: str,
    caption_hint: str,
    source_file: str,
    locator: str,
    cfg: dict[str, Any],
) -> VisionProcessResult:
    with Image.open(io.BytesIO(image_bytes)) as img:
        width, height = img.size
    image_pixels = int(width * height)
    quality_band = classify_image_quality(width, height, image_pixels)
    aspect_ratio = image_aspect_ratio(width, height)
    quality_warning = quality_warning_from_band(quality_band)
    gpt4o_called = False

    large_image = image_pixels >= int(cfg["image_large_pixels_threshold"])
    if large_image:
        tiles, width, height, image_pixels, tile_rows, tile_cols = split_image_into_tiles(
            image_bytes=image_bytes,
            target_max_pixels=int(cfg["image_tile_target_max_pixels"]),
            max_tiles=int(cfg["image_max_tiles"]),
        )
    else:
        tile_rows, tile_cols = 1, 1
        tiles = [
            {
                "index": 1,
                "row": 1,
                "col": 1,
                "bbox": {"x0": 0, "y0": 0, "x1": width, "y1": height},
                "width": width,
                "height": height,
                "pixels": image_pixels,
                "bytes": image_bytes,
                "mime_type": mime_type,
            }
        ]

    calls_attempted = 0
    calls_succeeded = 0
    call_errors = 0
    input_tokens = 0
    output_tokens = 0
    total_tokens = 0
    retry_used = False
    json_invalid_after_retry = False
    tile_outputs: list[dict[str, Any]] = []

    for tile in tiles:
        tile_locator = locator
        if large_image:
            tile_locator = (
                f"{locator}, tile {tile['index']}/{len(tiles)} "
                f"(row {tile['row']}, col {tile['col']})"
            )

        calls_attempted += 1
        try:
            first_structured, first_usage = vision.describe(
                image_bytes=tile["bytes"],
                mime_type=tile["mime_type"],
                caption_hint=caption_hint,
                source_file=source_file,
                locator=tile_locator,
                image_quality=quality_band,
                image_width=width,
                image_height=height,
                max_tokens=int(cfg["vision_max_tokens"]),
                max_visible_text_items=int(cfg["vision_max_visible_text_items"]),
            )
            if vision.provider == "openai":
                gpt4o_called = True
            calls_succeeded += 1
            input_tokens += int(first_usage.get("input_tokens", 0))
            output_tokens += int(first_usage.get("output_tokens", 0))
            total_tokens += int(first_usage.get("total_tokens", 0))
        except Exception as exc:
            call_errors += 1
            return VisionProcessResult(
                structured=None,
                error=f"vision_call_failed ({tile_locator}): {exc}",
                calls_attempted=calls_attempted,
                calls_succeeded=calls_succeeded,
                call_errors=call_errors,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
                retry_used=retry_used,
                tiled=large_image,
                tile_count=len(tiles),
                tile_rows=tile_rows,
                tile_cols=tile_cols,
                image_width=width,
                image_height=height,
                image_pixels=image_pixels,
                image_quality=quality_band,
                image_aspect_ratio=aspect_ratio,
                quality_warning=quality_warning,
                gpt4o_called=gpt4o_called,
                json_invalid_after_retry=json_invalid_after_retry,
            )

        if not bool(first_structured.get("json_parse_fallback_used", False)):
            tile_outputs.append(first_structured)
            continue

        retry_tokens = int(cfg["vision_retry_max_tokens"])
        if retry_tokens <= int(cfg["vision_max_tokens"]):
            json_invalid_after_retry = True
            tile_outputs.append(first_structured)
            continue

        retry_used = True
        calls_attempted += 1
        try:
            second_structured, second_usage = vision.describe(
                image_bytes=tile["bytes"],
                mime_type=tile["mime_type"],
                caption_hint=caption_hint,
                source_file=source_file,
                locator=tile_locator,
                image_quality=quality_band,
                image_width=width,
                image_height=height,
                max_tokens=retry_tokens,
                retry_note=(
                    "Previous response was not valid JSON. Return only valid JSON matching the required schema and keys."
                ),
                max_visible_text_items=int(cfg["vision_max_visible_text_items"]),
            )
            if vision.provider == "openai":
                gpt4o_called = True
            calls_succeeded += 1
            input_tokens += int(second_usage.get("input_tokens", 0))
            output_tokens += int(second_usage.get("output_tokens", 0))
            total_tokens += int(second_usage.get("total_tokens", 0))
            tile_outputs.append(second_structured)
            if bool(second_structured.get("json_parse_fallback_used", False)):
                json_invalid_after_retry = True
        except Exception:
            call_errors += 1
            json_invalid_after_retry = True
            tile_outputs.append(first_structured)

    if not tile_outputs:
        return VisionProcessResult(
            structured=None,
            error="vision_strategy_failed_without_output",
            calls_attempted=calls_attempted,
            calls_succeeded=calls_succeeded,
            call_errors=call_errors,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            retry_used=retry_used,
            tiled=large_image,
            tile_count=len(tiles),
            tile_rows=tile_rows,
            tile_cols=tile_cols,
            image_width=width,
            image_height=height,
            image_pixels=image_pixels,
            image_quality=quality_band,
            image_aspect_ratio=aspect_ratio,
            quality_warning=quality_warning,
            gpt4o_called=gpt4o_called,
            json_invalid_after_retry=json_invalid_after_retry,
        )

    merged = merge_vision_tile_outputs(tile_outputs, tiled=large_image)
    if json_invalid_after_retry:
        merged["json_parse_fallback_used"] = True

    return VisionProcessResult(
        structured=merged,
        error=None,
        calls_attempted=calls_attempted,
        calls_succeeded=calls_succeeded,
        call_errors=call_errors,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
        retry_used=retry_used,
        tiled=large_image,
        tile_count=len(tiles),
        tile_rows=tile_rows,
        tile_cols=tile_cols,
        image_width=width,
        image_height=height,
        image_pixels=image_pixels,
        image_quality=quality_band,
        image_aspect_ratio=aspect_ratio,
        quality_warning=quality_warning,
        gpt4o_called=gpt4o_called,
        json_invalid_after_retry=json_invalid_after_retry,
    )


__all__ = [
    "VisionDescriber",
    "VisionProcessResult",
    "describe_image_with_strategy",
    "build_image_text_content",
]
