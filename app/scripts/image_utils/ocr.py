from __future__ import annotations

import io
from dataclasses import dataclass

import pytesseract
from PIL import Image

from core.chunking import clean_text


@dataclass
class OCRResult:
    text: str
    word_count: int
    avg_conf: float


def _tesseract_available() -> bool:
    try:
        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False


def compute_ocr(image_bytes: bytes) -> OCRResult:
    if not _tesseract_available():
        # Tesseract binary not installed — skip OCR gracefully instead of crashing
        return OCRResult(text="", word_count=0, avg_conf=0.0)

    with Image.open(io.BytesIO(image_bytes)) as img:
        img = img.convert("RGB")
        data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
        words: list[str] = []
        confs: list[float] = []
        for i in range(len(data["text"])):
            t = clean_text(data["text"][i])
            if not t:
                continue
            words.append(t)
            try:
                c = float(data["conf"][i])
            except Exception:
                c = -1.0
            if c >= 0:
                confs.append(c)
        text = clean_text(" ".join(words))
        avg_conf = round(sum(confs) / len(confs), 2) if confs else 0.0
        return OCRResult(text=text, word_count=len(words), avg_conf=avg_conf)


def detect_scanned_text(ocr: OCRResult, cfg: dict[str, object]) -> bool:
    char_threshold = int(cfg.get("ocr_char_threshold", 280))
    word_threshold = int(cfg.get("ocr_word_threshold", 45))
    min_conf = float(cfg.get("ocr_min_confidence_for_scanned", 55.0))
    by_volume = (len(ocr.text) >= char_threshold) or (ocr.word_count >= word_threshold)
    return by_volume and (ocr.avg_conf >= min_conf)
