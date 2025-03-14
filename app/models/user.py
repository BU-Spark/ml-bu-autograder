from pydantic import BaseModel, EmailStr
from typing import Optional

class User(BaseModel):
    """
    User object representing an instructor.
    - **user_id**: Internal unique identifier.
    - **first_name**: Instructor’s first name.
    - **last_name**: Instructor’s last name.
    - **user_email**: Instructor’s email address.
    """
    user_id: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    user_email: EmailStr

class PersonalAuthenticationToken(BaseModel):
    """
    JWT for interactive sessions on the official front end.
    - **user_id**: ID of the user.
    - **authentication_token**: The JWT string.
    """
    user_id: str
    authentication_token: str
