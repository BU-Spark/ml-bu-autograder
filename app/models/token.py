from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class AccessToken(BaseModel):
    """
    Token used for programmatic API access.
    """
    token_name: str = Field(
        ..., description="A friendly, user-defined name for the token."
    )
    token_expiry: Optional[datetime] = Field(
        None, description="Optional expiration time of the token. If omitted, the token never expires."
    )
    # Note: the token id is not stored
