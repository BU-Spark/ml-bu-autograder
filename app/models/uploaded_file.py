from pydantic import BaseModel, Field
from typing import Optional

class UploadedFile(BaseModel):
    """
    Represents an uploaded file.

    Attributes:
    - **data_type**: A string indicating the file type or extension (e.g., ".png", ".pdf", ".doc", or a URL).
    - **metadata**: Optional metadata that can include details such as file size, dimensions, or other descriptive information.
    - **content**: A string representing the binary content of the file encoded in Base64.
    """
    data_type: str = Field(..., description="The file type or extension (e.g., '.png', '.pdf', '.doc', URL).")
    metadata: Optional[str] = Field(None, description="Optional metadata (e.g., file size, dimensions) for the file.")
    content: str = Field(..., description="Binary content of the file encoded in Base64.")
