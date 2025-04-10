import re
from typing import List, Set
from pydantic import BaseModel, EmailStr, Field, field_validator


class Course(BaseModel):
    """
    Course object representing a course.
    """

    semester: str = Field(
        ..., description="Semester when the course is offered."
    )

    course_id: str = Field(
        ..., description="Unique course identifier, usually its name."
    )

    instructors: Set[EmailStr] = Field(
        default_factory=set,
        description="Set of instructor emails associated with the course."
    )

    @field_validator("course_id", mode='before')
    def normalize_lowercase(cls, value: str) -> str:
        """
        Converts course_id and semester to lowercase and trims spaces.
        Validates format: lowercase letters, digits, and underscores only.
        """
        if not re.fullmatch(r'[a-z0-9_]+', value):
            raise ValueError("Must contain only lowercase letters, digits, and underscores (a-z0-9_)")
        return value.strip().lower()

    @field_validator("semester", mode='before')
    def validate_semester(cls, value: str) -> str:
        """
        Converts to lowercase and trims spaces.
        Ensures semester follows the format: seasonYYYY (e.g. spring2025).
        """
        if re.fullmatch("[a-z]{1,12}[0-9]{4}", value) is None:
            raise ValueError("Semester is in an invalid format. "
                             "Correct format (case-sensitive) looks like: seasonYYYY. (e.g. spring2025)")
        return value.strip().lower()

    @field_validator("instructors", mode="before")
    def normalize_instructor_emails(cls, value: List[str]) -> List[str]:
        """
        Ensure all instructor emails are lowercased and stripped.
        """
        return [email.strip().lower() for email in value]

    def normalize_instructor_email(cls, value: EmailStr) -> EmailStr:
        """
        Ensure a single instructor email is lowercased and stripped.
        Not a validator, but can be called manually.
        """
        return value.strip().lower()

    class Config:
        """
        Custom Pydantic config to ensure set is converted to list for JSON serialization.
        """
        json_encoders = {
            set: list
        }
