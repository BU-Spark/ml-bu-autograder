from typing import Optional, Tuple, Set
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
    authenticated_courses: Set[Tuple[str, str]] = Field(
        default_factory=set,
        description="Set of (semester, course ID) tuples representing courses the instructor has access to.",
    )
    dark_mode: bool = Field(
        False, description="User's preference for dark mode. Defaults to `False`.",
    )

    def is_authorized_to_course(self, semester: str, course_id: str) -> bool:
        """
        Check if the user has access to the specified course.
        """
        return (semester, course_id) in self.authenticated_courses

    @field_validator('user_email', mode='before')
    def normalize_email(cls, value: str) -> str:
        """
        Ensure email is lowercased and stripped before being parsed/validated.
        """
        return value.strip().lower()

    class Config:
        """
        Custom Pydantic config to ensure set is converted to a list for JSON serialization.
        """
        json_encoders = {
            set: list
        }
