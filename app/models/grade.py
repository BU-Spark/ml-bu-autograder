from typing import Optional

from pydantic import BaseModel, Field, validator


class Grade(BaseModel):
    """
    Grade object for a student's response.
    """
    student_id: str = Field(..., description="Student's unique identifier.")
    semester: str = Field(..., description="The semester associated with the course.")
    course_id: str = Field(..., description="Associated course identifier.")
    assignment_id: str = Field(..., description="Identifier of the assignment.")
    question_index: int = Field(..., description="The index of the question in the assignment.")
    points: float = Field(..., description="Awarded points for the student's response.")
    max_points: float = Field(..., description="Maximum points possible for the question when it was graded.")
    explanation: Optional[str] = Field(
        None, description="Optional explanation for the grade, based on the rubric."
    )

    @validator("student_id", "semester", "course_id", "assignment_id", pre=True, always=True)
    def normalize_lowercase(cls, value: str) -> str:
        """Converts course_id and semester to lowercase and trims spaces."""
        return value.strip().lower()
