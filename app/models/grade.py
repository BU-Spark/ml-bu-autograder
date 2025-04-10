import re
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class Grade(BaseModel):
    """
    Grade object for a student's response.
    """
    student_id: str = Field(..., description="Student's unique identifier.")
    semester: str = Field(..., description="The semester associated with the course.")
    course_id: str = Field(..., description="Associated course identifier.")
    assignment_id: int = Field(..., description="Identifier of the assignment.")
    question_index: int = Field(..., description="The index of the question in the assignment.")
    points: float = Field(..., description="Awarded points for the student's response.")
    max_points: float = Field(..., description="Maximum points possible for the question when it was graded.")
    explanation: Optional[str] = Field(
        None, description="Optional explanation for the grade, based on the rubric."
    )

    
    @field_validator("student_id", "course_id", mode="before")
    def normalize_lowercase(cls, value: str) -> str:
        """Converts course_id and semester to lowercase and trims spaces."""
        return value.strip().lower()

    
    @field_validator("semester", mode='before')
    def validate_semester(cls, value: str) -> str:
        """Converts to lowercase and trims spaces."""
        if re.fullmatch("[a-z]{1,12}[0-9]{4}", value) is None:
            raise ValueError("Semester is in an invalid format. "
                             "Correct format (case-sensetive) looks like: seasonYYYY. (e.g. spring2025)")
        return value.strip().lower()
