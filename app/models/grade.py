from typing import Optional

from pydantic import BaseModel, Field


class Grade(BaseModel):
    """
    Grade object for a student's response.
    """
    points: float = Field(..., description="Awarded points for the student's response.")
    max_points: float = Field(..., description="Maximum points possible for the question when it was graded.")
    explanation: Optional[str] = Field(
        None, description="Optional explanation for the grade, based on the rubric."
    )
