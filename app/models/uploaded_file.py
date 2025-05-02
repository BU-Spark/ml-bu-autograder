import base64

from pydantic import BaseModel, Field, HttpUrl, FilePath, validator, field_validator

from app.utils.bytes_to_doc_util import DataType


class UploadedFileData(BaseModel):
    """
    Represents an uploaded file including the complete full binary data of that file.

    Attributes:
    - **data_type**: A string indicating the file type or extension (e.g., ".png", ".pdf", ".doc", or a URL).
    - **metadata**: A dictionary containing optional metadata such as file size, dimensions, or other descriptive information.
    - **content**: A string representing the binary content of the file encoded in Base64.
    """
    data_type: DataType = Field(..., description="The data type which 'content' should be interpret as.")
    #metadata: Optional[Dict[str, str]] = Field(None, description="Optional metadata as key-value pairs.")
    content: str = Field(..., description="Binary content of the file (must be uploaded as a base64-encoded string).")

    def content_as_bytes(self) -> bytes:
        return base64.b64decode(self.content)


class UploadedFileReference(BaseModel):
    """
    Represents an uploaded file.

    Attributes:
    - **data_type**: A string indicating the file type or extension (e.g., ".png", ".pdf", ".doc", or a URL).
    - **metadata**: A dictionary containing optional metadata such as file size, dimensions, or other descriptive information.
    - **url**: The URL for where this file can be accessed.
    """
    data_type: DataType = Field(..., description="The file type or extension (e.g., '.png', '.pdf', '.doc', URL).")
    # metadata: Optional[Dict[str, str]] = Field(None,
    #                                            description="Optional metadata as key-value pairs (e.g., {'size': '2MB', 'dimensions': '1024x768'}).")
    uri: HttpUrl | FilePath = Field(..., description="The URL for where this file can be accessed.")
