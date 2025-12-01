"""Configuration constants for rubric review testing."""

# Default rubric metadata
DEFAULT_SEMESTER = "spring2025"

# Iterative refinement defaults
DEFAULT_TARGET_SCORE = 95
DEFAULT_MAX_ITERATIONS = 5


def get_rubric_file_path(quiz_id: str) -> str:
    """Get the default rubric file path for a given quiz_id.
    
    Args:
        quiz_id: The quiz identifier (e.g., "quiz_1", "quiz_2")
        
    Returns:
        Path to the rubric file relative to project root
    """
    return f"data/{quiz_id}/rubric.txt"

