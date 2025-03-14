from pydantic import BaseModel
from typing import Optional

class Grade(BaseModel):
    """
    Grade object for a student's response.
    - **student_identifier**: Student's unique identifier.
    - **assignment_id**: Identifier of the assignment.
    - **question_index**: The index of the question.
    - **grade**: Awarded grade.
    - **explanation**: Optional explanation based on the rubric.
    """
    student_identifier: str
    assignment_id: str
    question_index: int
    grade: float
    explanation: Optional[str] = None
