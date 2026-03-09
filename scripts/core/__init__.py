from .config import DEFAULT_CONFIG, SUPPORTED_EXTENSIONS, get_api_key, load_environment, merged_config
from .chunking import chunk_text, clean_text, make_sort_key, sha1_id

__all__ = [
    "DEFAULT_CONFIG",
    "SUPPORTED_EXTENSIONS",
    "load_environment",
    "merged_config",
    "get_api_key",
    "clean_text",
    "chunk_text",
    "make_sort_key",
    "sha1_id",
    # pipeline entrypoints are lazily imported via __getattr__
    "run_extract",
    "run_describe",
    "run_compare",
]


def __getattr__(name: str):  # type: ignore[no-untyped-def]
    # Keep imports of `core.*` lightweight so scripts like `--help` don't require
    # optional heavy deps (OCR/vision/etc.) unless the pipeline is actually used.
    if name in {"run_extract", "run_describe", "run_compare"}:
        from .pipeline import run_compare, run_describe, run_extract

        return {"run_extract": run_extract, "run_describe": run_describe, "run_compare": run_compare}[name]
    raise AttributeError(name)
