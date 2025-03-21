from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

class AccessToken(BaseModel):
    """
    Token used for programmatic API access.
    """
    user_id: str = Field(
        ..., description="Unique identifier of the user who owns the token."
    )
    token_name: str = Field(
        ..., description="A friendly, user-defined name for the token."
    )
    token_id: str = Field(
        ..., description="The secret token string, displayed only once during creation."
    )
    token_expiry: Optional[datetime] = Field(
        None, description="Optional expiration time of the token. If omitted, the token never expires."
    )
