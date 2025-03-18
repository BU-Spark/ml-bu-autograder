from pydantic import BaseModel, Field
from typing import Optional, Dict


class UploadedFileData(BaseModel):
    """
    Represents an uploaded file including the complete full binary data of that file.

    Attributes:
    - **data_type**: A string indicating the file type or extension (e.g., ".png", ".pdf", ".doc", or a URL).
    - **metadata**: A dictionary containing optional metadata such as file size, dimensions, or other descriptive information.
    - **content**: A string representing the binary content of the file encoded in Base64.
    """
    data_type: str = Field(..., description="The file type or extension (e.g., '.png', '.pdf', '.doc', URL).")
    metadata: Optional[Dict[str, str]] = Field(None,
                                               description="Optional metadata as key-value pairs (e.g., {'size': '2MB', 'dimensions': '1024x768'}).")
    content: str = Field(..., description="Binary content of the file encoded in Base64.")


class UploadedFileReference(BaseModel):
    """
    Represents an uploaded file.

    Attributes:
    - **data_type**: A string indicating the file type or extension (e.g., ".png", ".pdf", ".doc", or a URL).
    - **metadata**: A dictionary containing optional metadata such as file size, dimensions, or other descriptive information.
    - **url**: The URL for where this file can be accessed.
    """
    data_type: str = Field(..., description="The file type or extension (e.g., '.png', '.pdf', '.doc', URL).")
    metadata: Optional[Dict[str, str]] = Field(None,
                                               description="Optional metadata as key-value pairs (e.g., {'size': '2MB', 'dimensions': '1024x768'}).")
    url: str = Field(..., description="The URL for where this file can be accessed.")
