import re
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class Question(BaseModel):
    question_text: str = Field(..., description="The text of the question.")
    question_graphics_figures: Optional[str] = Field(
        None, description="Base64-encoded PNG image representing optional graphics/figures for the question."
    )


class Assignment(BaseModel):
    semester: str = Field(..., description="The semester associated with the course.")
    course_id: str = Field(..., description="Associated course identifier.")
    assignment_id: str = Field(
        None, description="The unique title of the assignment."
    )
    assignment_guidelines: Optional[str] = Field(
        None, description="General instructions or formatting requirements."
    )
    questions: Optional[List[Question]] = Field(
        ..., description="List of questions in order."
    )

    @field_validator("assignment_id", mode='before')
    def validate_identifier(cls, value: str) -> str:
        """Ensures format is valid."""
        if not re.fullmatch(r'[ a-zA-Z0-9_-]+', value):
            raise ValueError("Must contain only spaces, letters, digits, underscores and dashes")
        return value

    @field_validator("course_id", mode='before')
    def normalize_lowercase(cls, value: str) -> str:
        """Converts to lowercase and trims spaces."""
        return value.strip().lower()

    @field_validator("semester", mode='before')
    def validate_semester(cls, value: str) -> str:
        """Converts to lowercase and trims spaces."""
        if re.fullmatch("[a-z]{1,12}[0-9]{4}", value) is None:
            raise ValueError("Semester is in an invalid format. "
                             "Correct format (case-sensitive) looks like: seasonYYYY. (e.g. spring2025)")
        return value.strip().lower()
