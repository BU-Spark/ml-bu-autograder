#!/usr/bin/env python3
"""Local test script for rubric review functionality."""

import logging
import sys
from pathlib import Path

# Path setup
_script_file = Path(__file__).resolve()
_project_root = _script_file.parents[2]
sys.path.insert(0, str(_project_root))
sys.path.insert(0, str(_script_file.parent))

# Import from local modules
try:
    from .cli import handle_errors, parse_arguments
    from .config import get_rubric_file_path
    from .core.runner import RubricTestRunner
    from .utils.storage import RubricStorage
except (ImportError, ValueError):
    from cli import handle_errors, parse_arguments
    from config import get_rubric_file_path
    from core.runner import RubricTestRunner
    from utils.storage import RubricStorage

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@handle_errors
def main():
    """Main test function."""
    args = parse_arguments()
    
    # Get rubric file path from quiz_id if not provided
    rubric_file = args.rubric_file
    if rubric_file is None:
        rubric_file = get_rubric_file_path(args.quiz_id)
    
    print("="*80)
    print("RUBRIC REVIEW LOCAL TEST SCRIPT")
    print(f"Quiz ID: {args.quiz_id}")
    print("="*80)
    
    runner = RubricTestRunner(rubric_file)
    
    if not runner.initialize_service():
        print("\nFailed to initialize LLM service. Exiting.")
        sys.exit(1)
    
    print("\nLLM service initialized successfully")
    
    assignment, rubric = runner.load_rubric()
    
    if not args.no_iterative:
        response = runner.iterative_refinement(
            assignment, rubric,
            target_score=args.target_score,
            max_iterations=args.max_iterations
        )
        if response:
            RubricStorage.save_results(response.critique, response.improved_rubric, rubric=rubric)
    else:
        critique = runner.test_critique(assignment, rubric)
        improved_rubric = runner.test_refine(assignment, rubric, critique) if critique else None
        runner.test_full_workflow(assignment, rubric)
        
        if critique or improved_rubric:
            RubricStorage.save_results(critique, improved_rubric, rubric=rubric)
        
        print("\n" + "="*80)
        print("ALL TESTS COMPLETED")
        print("="*80)


if __name__ == "__main__":
    main()
