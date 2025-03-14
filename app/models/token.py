from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class AccessToken(BaseModel):
    """
    Token used for programmatic API access.
    - **user_id**: Owner of the token.
    - **token_name**: Friendly name for the token.
    - **token_id**: Secret token string (displayed only once during creation).
    - **token_expiry**: Optional expiration time; if omitted, the token never expires.
    """
    user_id: str
    token_name: str
    token_id: str
    token_expiry: Optional[datetime] = None
