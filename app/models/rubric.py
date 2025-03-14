from pydantic import BaseModel, Field
from typing import List, Optional

class SubRubric(BaseModel):
    """
    Sub-rubric for an individual question.
    - **question_index**: The question's index.
    - **maximum_points**: Maximum points available for the question.
    - **leniency**: Specific leniency (1–5; defaults to 3).
    - **instructor_guideline**: Detailed grading criteria.
    """
    question_index: int = Field(..., description="Index of the question")
    maximum_points: float = Field(..., description="Maximum points for this question")
    leniency: Optional[int] = Field(None, ge=1, le=5, description="Leniency (1=very strict, 5=very lenient). If omitted, no specific question-level leniency is set.")
    instructor_guideline: Optional[str] = Field(None, description="Detailed grading criteria for the question")

class Rubric(BaseModel):
    """
    Rubric object containing grading instructions.
    - **assignment_id**: The associated assignment's ID.
    - **grading_flags**: Optional list of grading flags (e.g., IGNORE_SPELLINGS, IGNORE_GRAMMAR).
    - **leniency**: Overall leniency (1–5).
    - **overall_instructor_guidelines**: Optional general grading criteria.
    - **sub_rubrics**: List of sub-rubric objects for each question.
    """
    assignment_id: str = Field(..., description="Associated assignment's ID")
    grading_flags: Optional[List[str]] = Field(None, description="List of grading flags")
    leniency: int = Field(..., ge=1, le=5, description="Overall leniency (1=very strict, 5=very lenient)")
    overall_instructor_guidelines: Optional[str] = Field(None, description="General grading criteria")
    sub_rubrics: List[SubRubric] = Field(..., description="List of sub-rubrics for each question")
