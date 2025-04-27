import re
from typing import List, Optional

from azure.core.exceptions import HttpResponseError
from pydantic import BaseModel, Field, field_validator


class Question(BaseModel):
    question_index: int = Field(..., description="The 0-based index of the question within the assignment.")
    question_text: str = Field(..., description="The text of the question.")
<<<<<<< HEAD
    question_graphics_figures: Optional[str] = Field(
        None,
        description="Base64-encoded PNG image representing optional graphics/figures for the question."
=======
    # TODO: it would be really nice if questions supported figures/images. But not worth ATM.
    # question_graphics_figures: Optional[str] = Field(
    #     None, description="Base64-encoded PNG image representing optional graphics/figures for the question."
    # )
    independent_from_previous: bool = Field(
        True, description="Whether the question is independent from previous questions. What we mean by this is that"
                          "the LLM does not need to know any information about the previous question to answer this "
                          "one."
>>>>>>> 1e49de1db1886ead0ccd3ca3b8f1f43b7dedf5fb
    )

    # TODO: add support for questions that may depend on context from the previous question.
    @field_validator("independent_from_previous", mode='before')
    def validate_identifier(cls, value: bool) -> bool:
        """Ensures format is valid."""
        if value is False:
            raise HttpResponseError("Sorry! Currently, only independent questions are supported.")
        return value


class Assignment(BaseModel):
    semester: str = Field(..., description="The semester associated with the course.")
    course_id: str = Field(..., description="Associated course identifier.")
    assignment_id: str = Field(
        None, description="The unique title of the assignment."
    )
    assignment_guidelines: Optional[str] = Field(
        None, description="General instructions or formatting requirements."
    )
<<<<<<< HEAD
    # Default to an empty list if no questions are provided.
    questions: List[Question] = Field(
        default_factory=list, description="List of questions in order."
=======
    questions: Optional[List[Question]] = Field(
        ..., description="List of questions in order."
>>>>>>> 1e49de1db1886ead0ccd3ca3b8f1f43b7dedf5fb
    )

    @field_validator("assignment_id", mode='before')
    def validate_identifier(cls, value: str) -> str:
<<<<<<< HEAD
        # Allow both strings and numbers, converting non-strings to strings.
        if not isinstance(value, str):
            value = str(value)
        if not re.fullmatch(r'[ a-zA-Z0-9_-]+', value):
            raise ValueError("Invalid identifier: does not match the expected pattern.")
=======
        """Ensures format is valid."""
        if not re.fullmatch(r'[ a-zA-Z0-9_-]+', value):
            raise ValueError("Must contain only spaces, letters, digits, underscores and dashes")
>>>>>>> 1e49de1db1886ead0ccd3ca3b8f1f43b7dedf5fb
        return value

    @field_validator("course_id", mode='before')
    def normalize_lowercase(cls, value: str) -> str:
        """Converts to lowercase and trims spaces."""
        return value.strip().lower()

    @field_validator("semester", mode='before')
    def validate_semester(cls, value: str) -> str:
        """Converts to lowercase and trims spaces."""
        if re.fullmatch("[a-z]{1,12}[0-9]{4}", value) is None:
<<<<<<< HEAD
            raise ValueError(
                "Semester is in an invalid format. "
                "Correct format (case-sensitive) looks like: seasonYYYY. (e.g. spring2025)"
            )
=======
            raise ValueError("Semester is in an invalid format. "
                             "Correct format (case-sensitive) looks like: seasonYYYY. (e.g. spring2025)")
>>>>>>> 1e49de1db1886ead0ccd3ca3b8f1f43b7dedf5fb
        return value.strip().lower()
