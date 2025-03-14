from pydantic import BaseModel
from typing import List, Optional

class Question(BaseModel):
    """
    Represents a question in an assignment.
    - **question_text**: The text of the question.
    - **question_graphics_figures**: Optional graphics/figures associated with the question.
    """
    question_text: str
    question_graphics_figures: Optional[str] = None

class Assignment(BaseModel):
    """
    Assignment object containing questions and guidelines.
    - **assignment_id**: Unique assignment identifier.
    - **course_id**: Associated course identifier.
    - **assignment_title**: Title of the assignment.
    - **assignment_guidelines**: General instructions or formatting requirements.
    - **ordered_list**: List of questions in order.
    """
    assignment_id: str
    course_id: str
    assignment_title: Optional[str] = None
    assignment_guidelines: Optional[str] = None
    ordered_list: List[Question]
