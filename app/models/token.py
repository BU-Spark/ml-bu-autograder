from datetime import datetime
from enum import Enum
from typing import Optional
import re

from pydantic import BaseModel, Field, field_validator, EmailStr

class TokenType(Enum):
    WEBSITE_ACCESS_TOKEN = "user_access_token"
    PERSONAL_ACCESS_TOKEN = "personal_access_token"

class UserToken(BaseModel):
    user_email: EmailStr = Field(
        None, description="The email of the user who owns this token."
    )
    token_expiry: Optional[datetime] = Field(
        None, description="Optional expiration time of the token. If omitted, the token never expires."
    )

    @classmethod
    @field_validator('user_email', mode='before')
    def normalize_email(cls, value: str) -> str:
        """
        Ensure email is lowercased before being parsed/validated.
        """
        return value.strip().lower()


class WebsiteAccessToken(UserToken):
    """
    Token used for website authentication.
    """
    ...

class PersonalAccessToken(UserToken):
    """
    Token used for programmatic API access.
    """
    token_name: str = Field(
        ..., description="User-defined name for the token. "
                         "Only lowercase alphanumeric characters and underscores are allowed."
    )
    token_expiry: Optional[datetime] = Field(
        None, description="Optional expiration time of the token. If omitted, the token never expires."
    )

    @classmethod
    @field_validator('token_name', mode='before')
    def validate_identifier(cls, value: str) -> str:
        if not re.fullmatch(r'[a-z0-9_]+', value):
            raise ValueError("Must contain only lowercase letters, digits, and underscores (a-z0-9_)")
        return value
