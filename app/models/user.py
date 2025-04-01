from typing import Optional, List, Tuple

from pydantic import BaseModel, EmailStr, Field


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


class PersonalAuthenticationToken(BaseModel):
    """
    JWT for interactive sessions on the official front end.
    """
    user_email: EmailStr = Field(
        ..., description="Instructor’s email address and user id."
    )
    authentication_token: str = Field(
        ..., description="The JSON Web Token (JWT) string used for authentication."
    )
