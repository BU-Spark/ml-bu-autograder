from typing import Optional, List, Tuple

from pydantic import BaseModel, EmailStr, Field, field_validator


class User(BaseModel):
    """
    User object representing an instructor.
    """
    user_email: EmailStr = Field(
        ..., description="Instructor’s email address and user id."
    )
    first_name: Optional[str] = Field(
        None, description="Instructor’s first name (optional)."
    )
    last_name: Optional[str] = Field(
        None, description="Instructor’s last name (optional)."
    )
    authenticated_courses: List[Tuple[str, str]] = Field(
        [], description="List of semester and course IDs tuples of courses that the instructor has access to.",
    )
    dark_mode: bool = Field(
        False, description="User's preference for dark mode. Defaults to `False`.",
    )

    def is_authorized_to_course(self, semester, course_id: str) -> bool:
        return self.authenticated_courses.__contains__((semester, course_id))

    @classmethod
    @field_validator('user_email', mode='before')
    def normalize_email(cls, value: str) -> str:
        """
        Ensure email is lowercased before being parsed/validated.
        """
        return value.strip().lower()