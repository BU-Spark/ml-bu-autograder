"""Rubric file parser using LLM extraction."""

import logging
import os
from dataclasses import dataclass
from typing import Optional, Tuple

from app.models.assignment import Assignment, Question
from app.models.rubric import Rubric, SubRubric, GradingCriteria
from app.utils.llm_service import LLMService, PromptBuilder, PromptRole

# Handle both relative and absolute imports
try:
    from ..config import DEFAULT_SEMESTER
    from .models import ExtractedRubricData
except ImportError:
    # Fallback for when run as script directly
    import sys
    # Add parent directory to path for imports
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)
    from config import DEFAULT_SEMESTER
    from core.models import ExtractedRubricData

logger = logging.getLogger(__name__)


def _extract_quiz_id_from_path(file_path: str) -> Optional[str]:
    """Extract quiz_id from file path (e.g., 'data/quiz_1/rubric.txt' -> 'quiz_1')."""
    parts = file_path.replace('\\', '/').split('/')
    if 'data' in parts:
        idx = parts.index('data')
        if idx + 1 < len(parts):
            return parts[idx + 1]
    return None


@dataclass
class RubricParserConfig:
    """Configuration for rubric parsing."""
    semester: str = DEFAULT_SEMESTER
    course_id: Optional[str] = None
    assignment_id: Optional[str] = None


class RubricFileParser:
    """Parser for rubric text files using LLM extraction."""
    
    def __init__(self, config: Optional[RubricParserConfig] = None):
        self.config = config or RubricParserConfig()
        self.llm = LLMService.get_instance()
        if self.llm is None:
            raise RuntimeError("LLMService must be initialized before using RubricFileParser")
    
    def parse(self, file_path: str) -> Tuple[Assignment, Rubric]:
        """Parse a rubric file using LLM and return Assignment and Rubric models.
        
        Args:
            file_path: Path to the rubric text file (can be relative or absolute)
            
        Returns:
            Tuple of (Assignment, Rubric) objects
            
        Raises:
            FileNotFoundError: If the file doesn't exist
            ValueError: If the file format is invalid or LLM extraction fails
        """
        # Resolve relative paths relative to project root
        try:
            from ..utils.path_utils import resolve_path
        except ImportError:
            from utils.path_utils import resolve_path
        resolved_path = resolve_path(file_path)
        
        if not os.path.exists(resolved_path):
            raise FileNotFoundError(f"Rubric file not found: {resolved_path}")
        
        # Extract quiz_id from path if course_id/assignment_id not set
        if self.config.course_id is None or self.config.assignment_id is None:
            quiz_id = _extract_quiz_id_from_path(file_path)
            if quiz_id:
                if self.config.course_id is None:
                    self.config.course_id = quiz_id
                if self.config.assignment_id is None:
                    self.config.assignment_id = quiz_id
        
        with open(resolved_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Use LLM to extract structured data
        logger.info("Extracting rubric information using LLM...")
        extracted_data = self._extract_with_llm(content)
        
        # Convert extracted data to Assignment and Rubric models
        assignment = self._create_assignment(extracted_data)
        rubric = self._create_rubric(extracted_data)
        
        return assignment, rubric
    
    def _extract_with_llm(self, rubric_text: str) -> ExtractedRubricData:
        """Use LLM to extract structured data from rubric text."""
        prompt = (
            PromptBuilder.builder()
            .add_message(
                PromptRole.SYSTEM,
                "You are an expert at parsing educational rubrics. Extract all relevant information "
                "from the rubric text and structure it according to the ExtractedRubricData schema. "
                "Identify questions, grading criteria, point allocations, and any guidelines. "
                "For each question, extract all grading criteria with their point values. "
                "Ensure that the sum of grading criteria points equals the max_points for each question."
            )
            .add_message(PromptRole.USER, "Extract the rubric information from the following text:")
            .add_message(PromptRole.USER, rubric_text)
            .add_message(
                PromptRole.USER,
                "Extract and structure the following information:\n"
                "- The question text(s)\n"
                "- Assignment guidelines or notes (if any)\n"
                "- Overall instructor guidelines (if any)\n"
                "- For each question:\n"
                "  * Question index (0-based)\n"
                "  * Maximum points\n"
                "  * Instructor guidelines specific to that question (if any)\n"
                "  * All grading criteria with their point allocations\n"
                "\n"
                "Make sure to:\n"
                "- Extract all grading criteria mentioned in the rubric\n"
                "- Assign appropriate criteria_id names (short, descriptive)\n"
                "- Ensure criteria descriptions are clear and specific\n"
                "- Verify that grading criteria points sum to max_points for each question"
            )
        )
        
        try:
            extracted = self.llm.generate_structured_response(prompt.build(), ExtractedRubricData)
            logger.info("Successfully extracted rubric data using LLM")
            return extracted
        except Exception as e:
            logger.error(f"LLM extraction failed: {e}", exc_info=True)
            raise ValueError(f"Failed to extract rubric data using LLM: {e}") from e
    
    def _create_assignment(self, extracted_data: ExtractedRubricData) -> Assignment:
        """Create an Assignment model from extracted data."""
        questions = [Question(question_text=extracted_data.question_text)]
        
        return Assignment(
            semester=self.config.semester,
            course_id=self.config.course_id,
            assignment_id=self.config.assignment_id,
            assignment_guidelines=extracted_data.assignment_guidelines,
            questions=questions
        )
    
    def _create_rubric(self, extracted_data: ExtractedRubricData) -> Rubric:
        """Create a Rubric model from extracted data."""
        sub_rubrics = []
        for extracted_sub in extracted_data.sub_rubrics:
            grading_criteria = [
                GradingCriteria(
                    criteria_id=crit.criteria_id,
                    criteria=crit.criteria,
                    points=crit.points
                )
                for crit in extracted_sub.grading_criteria
            ]
            
            sub_rubrics.append(
                SubRubric(
                    question_index=extracted_sub.question_index,
                    max_points=extracted_sub.max_points,
                    instructor_guideline=extracted_sub.instructor_guideline,
                    grading_criteria=grading_criteria if grading_criteria else None
                )
            )
        
        return Rubric(
            semester=self.config.semester,
            course_id=self.config.course_id,
            assignment_id=self.config.assignment_id,
            grading_flags=None,
            overall_instructor_guidelines=extracted_data.overall_instructor_guidelines,
            sub_rubrics=sub_rubrics
        )

