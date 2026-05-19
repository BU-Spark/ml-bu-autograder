#!/usr/bin/env python3
"""Script to read quiz results CSV and print all student answers."""

import csv
import sys
from pathlib import Path

try:
    from .path_utils import get_project_root
except ImportError:
    # When run as a script, define get_project_root directly
    # to avoid importing through package __init__ which has dependencies on 'app'
    def get_project_root():
        """Get the project root directory (ai-baseline)."""
        # Go up: utils -> unified_pipeline -> ai-baseline (project root)
        return Path(__file__).resolve().parents[2]


def print_student_answers(quiz_id: str):
    """Read CSV file and print all student answers.
    
    Args:
        quiz_id: The quiz identifier (e.g., "quiz_1", "quiz_2")
    """
    csv_path = Path(get_project_root()) / "data" / quiz_id / f"{quiz_id}_results.csv"
    
    if not csv_path.exists():
        print(f"Error: CSV file not found at {csv_path}")
        return
    
    # Windows console encoding fix
    if sys.platform == 'win32':
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        print("=" * 80)
        print("STUDENT ANSWERS")
        print("=" * 80)
        print()
        
        for i, row in enumerate(reader, 1):
            student_answer = row.get('student answer', '').strip()
            if not student_answer:
                continue
            
            print(f"Student Number: {row.get('Student Number', 'N/A')}")
            print(f"Answer {i}:")
            print("-" * 80)
            print(student_answer)
            print("\n" + "=" * 80 + "\n")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Print student answers from CSV")
    parser.add_argument("--quiz-id", type=str, required=True, help="Quiz identifier (e.g., 'quiz_1')")
    args = parser.parse_args()
    print_student_answers(args.quiz_id)

