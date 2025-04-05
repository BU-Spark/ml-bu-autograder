import re
from typing import List

from pydantic import BaseModel, EmailStr, Field, field_validator


class Course(BaseModel):
    """
    Course object representing a course.
    """
    semester: str = Field(..., description="Semester when the course is offered.")
    course_id: str = Field(..., description="Unique course identifier, usually its name.")
    instructors: List[EmailStr] = Field(
        ..., description="List of instructor emails associated with the course."
    )

    @classmethod
    @field_validator("course_id", mode='before')
    def normalize_lowercase(cls, value: str) -> str:
        """Converts course_id and semester to lowercase and trims spaces."""
        if not re.fullmatch(r'[a-z0-9_]+', value):
            raise ValueError("Must contain only lowercase letters, digits, and underscores (a-z0-9_)")
        return value.strip().lower()

    @classmethod
    @field_validator("semester", mode='before')
    def normalize_lowercase(cls, value: str) -> str:
        """Converts to lowercase and trims spaces."""
        if re.fullmatch("[a-zA-Z]{1,12}[0-9]{4}", value) is not None:
            raise ValueError("Semester is in an invalid format. "
                             "Correct format looks like: seasonYYYY. (e.g. spring2025)")
        return value.strip().lower()

    @classmethod
    @field_validator("instructors", mode="before")
    def normalize_instructor_emails(cls, value: List[str]) -> List[str]:
        """Ensure all instructor emails are lowercased."""
        return [email.strip().lower() for email in value]
