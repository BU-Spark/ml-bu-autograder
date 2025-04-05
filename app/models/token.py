from datetime import datetime
from typing import Optional
import re

from pydantic import BaseModel, Field, field_validator


class AccessToken(BaseModel):
    """
    Token used for programmatic API access.
    """
    token_name: str = Field(
        ..., description="User-defined name for the token. "
                         "Only alphanumeric characters and underscores are allowed."
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
