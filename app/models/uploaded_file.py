import base64
from enum import Enum
from typing import Optional, Dict

from pydantic import BaseModel, Field, field_validator, HttpUrl


class DataType(Enum):
    """
    Represents a list of accepted data types.
    """
    # TODO: determine which of these will we support
    PNG = "png"
    jpg = "jpg"
    jpeg = "jpeg"
    PDF = "pdf"
    WORD_DOC = "doc"
    POWERPOINT = "ppt"
    URL = "url"
    EXCEL = "xls"
    TEXT = "txt"
    CSV = "csv"
    JSON = "json"
    MP4 = "mp4"

    @classmethod
    def from_value(cls, val: str) -> Optional["DataType"]:
        """
        Converts a string value to the corresponding DataType enum member.
        """
        for member in cls:
            if member.value == val.lower():
                return member
        return None


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
    content: bytes = Field(..., description="Binary content of the file (must be uploaded as a base64-encoded string).")

    @field_validator("content", mode="before")
    @classmethod
    def decode_base64_data(cls, v) -> bytes:
        if isinstance(v, str):
            try:
                return base64.b64decode(v, validate=True)
            except Exception as e:
                raise ValueError("Invalid base64-encoded data") from e
        return v


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
    url: HttpUrl = Field(..., description="The URL for where this file can be accessed.")
