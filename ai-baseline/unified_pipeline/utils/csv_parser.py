#!/usr/bin/env python3
"""Script to read quiz_1_results.csv and print all student answers."""

import csv
import sys
from pathlib import Path

try:
    from .path_utils import get_project_root
except ImportError:
    from pathlib import Path as _Path
    parent_dir = _Path(__file__).resolve().parents[1]
    if str(parent_dir) not in sys.path:
        sys.path.insert(0, str(parent_dir))
    from utils.path_utils import get_project_root


def print_student_answers(quiz_id: str = "quiz_1"):
    """Read CSV file and print all student answers."""
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
    print_student_answers()

