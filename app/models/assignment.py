import re
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class Question(BaseModel):
    question_text: str = Field(..., description="The text of the question.")
    question_graphics_figures: Optional[str] = Field(
        None, description="Base64-encoded PNG image representing optional graphics/figures for the question."
    )


class Assignment(BaseModel):
    """
    Assignment object containing questions and guidelines.
    """
    assignment_id: int = Field(..., description="Unique assignment identifier.")
    course_id: str = Field(..., description="Associated course identifier.")
    semester: str = Field(..., description="The semester associated with the course.")
    assignment_title: Optional[str] = Field(
        None, description="Title of the assignment."
    )
    assignment_guidelines: Optional[str] = Field(
        None, description="General instructions or formatting requirements."
    )
    questions: List[Question] = Field(
        ..., description="List of questions in order.", exclude=True  # exclude from serialization, stored separately
    )

    @classmethod
    @field_validator("assignment_id", "course_id", mode='before')
    def normalize_lowercase(cls, value: str) -> str:
        """Converts to lowercase and trims spaces."""
        return value.strip().lower()

    @classmethod
    @field_validator("semester", mode='before')
    def validate_semester(cls, value: str) -> str:
        """Converts to lowercase and trims spaces."""
        if re.fullmatch("[a-zA-Z]{1,12}[0-9]{4}", value) is not None:
            raise ValueError("Semester is in an invalid format. "
                             "Correct format looks like: seasonYYYY. (e.g. spring2025)")
        return value.strip().lower()