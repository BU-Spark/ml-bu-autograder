"""Command line interface for rubric review testing."""

import argparse
import logging
import sys

# Handle both relative and absolute imports
try:
    from .config import (
        DEFAULT_MAX_ITERATIONS,
        DEFAULT_TARGET_SCORE,
        get_rubric_file_path
    )
except ImportError:
    from config import (
        DEFAULT_MAX_ITERATIONS,
        DEFAULT_TARGET_SCORE,
        get_rubric_file_path
    )

logger = logging.getLogger(__name__)


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Test rubric review functionality locally"
    )
    parser.add_argument(
        "--quiz-id",
        type=str,
        required=True,
        help="Quiz identifier (e.g., 'quiz_1', 'quiz_2')"
    )
    parser.add_argument(
        "--rubric-file",
        type=str,
        default=None,
        help="Path to rubric file (default: data/{quiz_id}/rubric.txt). If not provided, will be derived from --quiz-id."
    )
    parser.add_argument(
        "--no-iterative",
        action="store_true",
        help="Disable iterative refinement (run single-pass tests instead)"
    )
    parser.add_argument(
        "--target-score",
        type=int,
        default=DEFAULT_TARGET_SCORE,
        help=f"Target critique score for iterative refinement (default: {DEFAULT_TARGET_SCORE})"
    )
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=DEFAULT_MAX_ITERATIONS,
        help=f"Maximum iterations for iterative refinement (default: {DEFAULT_MAX_ITERATIONS})"
    )
    return parser.parse_args()


def handle_errors(func):
    """Decorator to handle common errors."""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except FileNotFoundError as e:
            logger.error(f"File not found: {e}")
            sys.exit(1)
        except ValueError as e:
            logger.error(f"Invalid file format: {e}")
            sys.exit(1)
        except KeyboardInterrupt:
            print("\n\nTest interrupted by user.")
            sys.exit(1)
        except Exception as e:
            logger.error(f"Unexpected error during testing: {e}", exc_info=True)
            sys.exit(1)
    return wrapper

