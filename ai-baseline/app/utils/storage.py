"""File I/O operations for rubrics and results."""

import json
import logging
from pathlib import Path
from typing import Optional

from app.models.assignment import Assignment
from app.models.rubric import Rubric
from app.models.rubric_review import RubricCritique

try:
    from .path_utils import get_project_root, resolve_path
except ImportError:
    import sys
    from pathlib import Path as _Path
    parent_dir = _Path(__file__).resolve().parents[1]
    if str(parent_dir) not in sys.path:
        sys.path.insert(0, str(parent_dir))
    from utils.path_utils import get_project_root, resolve_path

logger = logging.getLogger(__name__)


class RubricStorage:
    """Handles storage operations for rubrics."""
    
    @staticmethod
    def format_rubric_as_text(rubric: Rubric, assignment: Assignment) -> str:
        """Format the rubric as text similar to the original rubric.txt format."""
        lines = []
        
        # Add each question's rubric
        for sub_rubric in sorted(rubric.sub_rubrics, key=lambda x: x.question_index):
            question_idx = sub_rubric.question_index
            
            # Get question text
            question_text = ""
            if assignment.questions and question_idx < len(assignment.questions):
                question_text = assignment.questions[question_idx].question_text
            
            # Add question header
            lines.append("Question")
            if question_text:
                lines.append(question_text)
            
            # Add assignment guidelines as note if available
            if assignment.assignment_guidelines:
                lines.append(assignment.assignment_guidelines)
            
            lines.append("")  # Empty line
            
            # Add grading rubric header
            lines.append("Grading Rubric")
            
            # Add grading criteria
            if sub_rubric.grading_criteria:
                for criteria in sub_rubric.grading_criteria:
                    lines.append(f"Up to {int(criteria.points)} Points for {criteria.criteria}")
            
            lines.append(f"Maximum of {int(sub_rubric.max_points)} Points")
            lines.append("")  # Empty line
            
            # Add instructor guideline if available
            if sub_rubric.instructor_guideline:
                lines.append(sub_rubric.instructor_guideline)
                lines.append("")
            
            # Add overall guidelines if available
            if rubric.overall_instructor_guidelines:
                lines.append(rubric.overall_instructor_guidelines)
                lines.append("")
            
            # Add grading flags if available
            if rubric.grading_flags:
                flags_text = ", ".join([f.value for f in rubric.grading_flags])
                lines.append(f"Grading Flags: {flags_text}")
                lines.append("")
        
        return "\n".join(lines)
    
    @staticmethod
    def _get_quiz_folder(rubric: Rubric) -> str:
        """Extract quiz folder name from rubric assignment_id."""
        return rubric.assignment_id or "unknown"
    
    @staticmethod
    def save_refined_rubric(
        rubric: Rubric,
        assignment: Assignment,
        rubric_file_path: Optional[str] = None,
        output_dir: Optional[str] = None
    ) -> str:
        """Save the refined rubric to a text file."""
        output_dir = output_dir or "data/rubric-refined"
        quiz_folder = RubricStorage._get_quiz_folder(rubric)
        output_path = Path(resolve_path(output_dir)) / quiz_folder
        output_path.mkdir(parents=True, exist_ok=True)
        
        file_path = output_path / "rubric_refined.txt"
        file_path.write_text(RubricStorage.format_rubric_as_text(rubric, assignment), encoding='utf-8')
        
        logger.info(f"Refined rubric saved to {file_path}")
        return str(file_path)
    
    @staticmethod
    def save_results(
        critique: Optional[RubricCritique] = None,
        improved_rubric: Optional[Rubric] = None,
        rubric: Optional[Rubric] = None,
        output_dir: str = "data/rubric-feedback"
    ) -> Optional[str]:
        """Save test results to a JSON file."""
        if not critique and not improved_rubric:
            return None
        
        rubric_for_quiz = improved_rubric or rubric
        quiz_folder = RubricStorage._get_quiz_folder(rubric_for_quiz) if rubric_for_quiz else "unknown"
        
        output_path = Path(resolve_path(output_dir)) / quiz_folder
        output_path.mkdir(parents=True, exist_ok=True)
        
        file_path = output_path / f"{quiz_folder}.json"
        results = {}
        if critique:
            results["critique"] = critique.model_dump()
        if improved_rubric:
            results["improved_rubric"] = improved_rubric.model_dump()
        
        file_path.write_text(json.dumps(results, indent=2), encoding='utf-8')
        
        logger.info(f"Test results saved to {file_path}")
        print(f"\nResults saved to {file_path}")
        return str(file_path)
    
    @staticmethod
    def save_refined_rubric_json(rubric: Rubric, output_dir: str = "data/rubric-refined") -> str:
        """Save the refined rubric as JSON."""
        quiz_folder = RubricStorage._get_quiz_folder(rubric)
        output_path = Path(resolve_path(output_dir)) / quiz_folder
        output_path.mkdir(parents=True, exist_ok=True)
        
        file_path = output_path / f"{quiz_folder}.json"
        file_path.write_text(json.dumps(rubric.model_dump(), indent=2), encoding='utf-8')
        
        logger.info(f"Refined rubric JSON saved to {file_path}")
        return str(file_path)

