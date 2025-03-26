from typing import List
from pydantic import BaseModel, EmailStr, Field, validator

class Course(BaseModel):
    """
    Course object representing a course.
    """
    semester: str = Field(..., description="Semester when the course is offered.")
    course_id: str = Field(..., description="Unique course identifier, usually its name.")
    instructors: List[EmailStr] = Field(
        ..., description="List of instructor emails associated with the course."
    )

    @validator("semester", "course_id", pre=True, always=True)
    def normalize_lowercase(cls, value: str) -> str:
        """Converts course_id and semester to lowercase and trims spaces."""
        return value.strip().lower()

    @validator("instructors", pre=True, always=True)
    def normalize_emails(cls, value: List[EmailStr]) -> List[EmailStr]:
        """Ensures all instructor emails are lowercase."""
        return [email.lower() for email in value]
