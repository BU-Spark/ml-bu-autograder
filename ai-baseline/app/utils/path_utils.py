"""Path resolution utilities."""

from pathlib import Path


def get_project_root() -> Path:
    """Get the project root directory (ai-baseline)."""
    # Go up: utils -> unified_pipeline -> ai-baseline (project root)
    return Path(__file__).resolve().parents[2]


def resolve_path(file_path: str) -> str:
    """Resolve a relative file path to an absolute path."""
    path = Path(file_path)
    if path.is_absolute():
        return str(path)
    return str(get_project_root() / file_path)

