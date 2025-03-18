from typing import List, Optional
from pydantic import BaseModel, Field
from enum import Enum


class GradingFlag(str, Enum):
    """
    Enumeration of possible grading flags.

    These flags modify the grading behavior of the rubric.
    """
    IGNORE_SPELLINGS = "IGNORE_SPELLINGS"

    IGNORE_GRAMMAR = "IGNORE_GRAMMAR"

    ORIGINALITY = "ORIGINALITY"

    IGNORE_FORMATTING = "IGNORE_FORMATTING"


class SubRubric(BaseModel):
    """
    Sub-rubric for an individual question.
    """
    question_index: int = Field(..., description="Index of the question.")
    maximum_points: float = Field(..., description="Maximum points for this question.")
    leniency: Optional[int] = Field(
        None, ge=1, le=5,
        description="Leniency (1=very strict, 5=very lenient). If omitted, no specific question-level leniency is set."
    )
    instructor_guideline: Optional[str] = Field(
        None, description="Detailed grading criteria for the question."
    )


class Rubric(BaseModel):
    """
    Rubric object containing grading instructions.
    """
    assignment_id: str = Field(..., description="Associated assignment's ID.")
    grading_flags: Optional[List[GradingFlag]] = Field(
        None, description=(
            "List of grading flags that modify grading behavior. Options:\n"
            "- `IGNORE_SPELLINGS`: Ignore minor spelling mistakes.\n"
            "- `IGNORE_GRAMMAR`: Ignore minor grammar issues.\n"
            "- `ORIGINALITY`: Reward originality and deduct for unoriginal ideas.\n"
            "- `IGNORE_FORMATTING`: Ignore formatting issues."
        )
    )
    leniency: int = Field(
        3, ge=1, le=5, description="Overall leniency (1=very strict, 5=very lenient)."
    )
    overall_instructor_guidelines: Optional[str] = Field(
        None, description="General grading criteria applicable to all questions."
    )
    sub_rubrics: List[SubRubric] = Field(
        ..., description="List of sub-rubrics specifying grading for individual questions."
    )
