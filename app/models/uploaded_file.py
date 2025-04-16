import base64
from enum import Enum
from typing import Optional, Dict, Callable

from pydantic import BaseModel, Field, field_validator, HttpUrl, FilePath

from app.utils.file_to_doc_util import Document


class DataType(Enum):
    """
    Represents a list of accepted data types, along with their corresponding MIME types.
    """
    PNG = ("png", "image/png", Document.from_png)
    JPEG = ("jpeg", "image/jpeg", Document.from_jpeg)
    PDF = ("pdf", "application/pdf", Document.from_pdf)
    WORD_DOC = ("doc", "application/msword", Document.from_doc)
    POWERPOINT = ("pptx", "application/vnd.ms-powerpoint", Document.from_pptx)
    HTML = ("html", "text/html", Document.from_html)
    EXCEL = ("xlsx", "application/vnd.ms-excel", Document.from_xlsx)
    TEXT = ("txt", "text/plain", Document.from_txt)
    CSV = ("csv", "text/csv", Document.from_csv)
    JSON = ("json", "application/json", Document.from_json)
    MP4 = ("mp4", "video/mp4", Document.from_mp4)
    MP3 = ("mp3", "audio/mpeg", Document.from_mp3)
    WAV = ("wav", "audio/wav", Document.from_wav)

    to_doc_func: Callable[[FilePath], Document]
    mime_type: str
    extension: str

    def __init__(self, extension, mime_type, to_doc_func: Callable[[FilePath], Document]):
        self.extension = extension
        self.mime_type = mime_type  # _mime_type is stored privately
        self._to_doc_func = to_doc_func

    def __str__(self):
        return f"{self.extension} ({self.mime_type})"

    def is_image(self):
        return self == DataType.PNG or self == DataType.JPEG

    def to_doc(self, file_path: FilePath) -> Document:
        return self._to_doc_func(file_path)

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
