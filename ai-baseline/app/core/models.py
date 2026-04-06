"""Pydantic models for extracted rubric data."""

from typing import Optional
from pydantic import BaseModel, Field


class ExtractedGradingCriteria(BaseModel):
    """Extracted grading criteria from rubric text."""
    criteria_id: str = Field(..., description="Short identifier for this criteria")
    criteria: str = Field(..., description="Detailed description of what this criteria evaluates")
    points: float = Field(..., description="Points allocated to this criteria")


class ExtractedSubRubric(BaseModel):
    """Extracted sub-rubric information."""
    question_index: int = Field(..., description="Index of the question (0-based)")
    max_points: float = Field(..., description="Maximum points for this question")
    instructor_guideline: Optional[str] = Field(None, description="Guidelines for grading this question")
    grading_criteria: list[ExtractedGradingCriteria] = Field(default_factory=list, description="List of grading criteria")


class ExtractedRubricData(BaseModel):
    """Structured data extracted from rubric text file."""
    question_text: str = Field(..., description="The question text")
    assignment_guidelines: Optional[str] = Field(None, description="General assignment guidelines or notes")
    overall_instructor_guidelines: Optional[str] = Field(None, description="Overall grading guidelines applicable to all questions")
    sub_rubrics: list[ExtractedSubRubric] = Field(..., description="List of sub-rubrics, one per question")

