from typing import List, Optional
from pydantic import BaseModel, Field

class Question(BaseModel):
    """
    Represents a question in an assignment.
    """
    question_text: str = Field(..., description="The text of the question.")
    question_graphics_figures: Optional[str] = Field(
        None, description="Optional graphics/figures associated with the question."
    )

class Assignment(BaseModel):
    """
    Assignment object containing questions and guidelines.
    """
    assignment_id: str = Field(..., description="Unique assignment identifier.")
    course_id: str = Field(..., description="Associated course identifier.")
    assignment_title: Optional[str] = Field(
        None, description="Title of the assignment."
    )
    assignment_guidelines: Optional[str] = Field(
        None, description="General instructions or formatting requirements."
    )
    ordered_list: List[Question] = Field(
        ..., description="List of questions in order."
    )
