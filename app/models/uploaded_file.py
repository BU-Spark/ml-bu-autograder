import base64
from enum import Enum
from typing import Optional, Dict

from pydantic import BaseModel, Field, field_validator, HttpUrl


class DataType(Enum):
    """
    Represents a list of accepted data types, along with their corresponding MIME types.
    """
    PNG = ("png", "image/png")
    JPEG = ("jpeg", "image/jpeg")
    PDF = ("pdf", "application/pdf")
    WORD_DOC = ("doc", "application/msword")
    POWERPOINT = ("ppt", "application/vnd.ms-powerpoint")
    HTML = ("html", "text/html")
    EXCEL = ("xls", "application/vnd.ms-excel")
    TEXT = ("txt", "text/plain")
    CSV = ("csv", "text/csv")
    JSON = ("json", "application/json")
    MP4 = ("mp4", "video/mp4")

    def __init__(self, extension, mime_type):
        self.extension = extension
        self.mime_type = mime_type  # _mime_type is stored privately

    def __str__(self):
        return f"{self.extension} ({self.mime_type})"

    @classmethod
    def from_mime_type(cls, mime_type):
        """
        Given a MIME type, return the corresponding enum member.
        """
        for data_type in cls:
            if data_type.mime_type == mime_type.lower():
                return data_type
        return None

    @classmethod
    def from_extension(cls, extension: str) -> Optional["DataType"]:
        """
        Converts a string value to the corresponding enum member.
        """
        for member in cls:
            if member.extension == extension.lower():
                return member
        # special case, jpg and jpeg are the same
        if extension.lower() == "jpg":
            return cls.JPEG
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
