from typing import Optional
from pydantic import BaseModel, Field

class Grade(BaseModel):
    """
    Grade object for a student's response.
    """
    student_identifier: str = Field(..., description="Student's unique identifier.")
    assignment_id: str = Field(..., description="Identifier of the assignment.")
    question_index: int = Field(..., description="The index of the question in the assignment.")
    grade: float = Field(..., description="Awarded grade for the student's response.")
    explanation: Optional[str] = Field(
        None, description="Optional explanation for the grade, based on the rubric."
    )
