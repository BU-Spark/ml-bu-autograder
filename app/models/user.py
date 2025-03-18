from typing import Optional
from pydantic import BaseModel, EmailStr, Field

class User(BaseModel):
    """
    User object representing an instructor.
    """
    user_id: str = Field(
        ..., description="Internal unique identifier for the instructor."
    )
    first_name: Optional[str] = Field(
        None, description="Instructor’s first name (optional)."
    )
    last_name: Optional[str] = Field(
        None, description="Instructor’s last name (optional)."
    )
    dark_mode: bool = Field(
        False, description="User's preference for dark mode. Defaults to `False`."
    )
    user_email: EmailStr = Field(
        ..., description="Instructor’s email address."
    )


class PersonalAuthenticationToken(BaseModel):
    """
    JWT for interactive sessions on the official front end.
    """
    user_id: str = Field(
        ..., description="Unique identifier of the user."
    )
    authentication_token: str = Field(
        ..., description="The JSON Web Token (JWT) string used for authentication."
    )
