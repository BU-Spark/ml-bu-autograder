from .ocr import OCRResult, compute_ocr, detect_scanned_text
from .filtering import is_diagram_image
from .caption import find_best_caption_for_image

__all__ = [
    "OCRResult",
    "compute_ocr",
    "detect_scanned_text",
    "is_diagram_image",
    "find_best_caption_for_image",
]
