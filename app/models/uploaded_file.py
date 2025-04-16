from enum import Enum
from typing import Optional, Callable

from pydantic import BaseModel, Field, HttpUrl, FilePath


class DataType(Enum):
    """
    Represents a list of accepted data types, along with their corresponding MIME types.
    """
    PNG = ("png", "image/png")
    JPEG = ("jpeg", "image/jpeg")
    PDF = ("pdf", "application/pdf")
    WORD_DOC = ("doc", "application/msword")
    POWERPOINT = ("pptx", "application/vnd.ms-powerpoint")
    HTML = ("html", "text/html")
    EXCEL = ("xlsx", "application/vnd.ms-excel")
    TEXT = ("txt", "text/plain")
    CSV = ("csv", "text/csv")
    JSON = ("json", "application/json")
    MP4 = ("mp4", "video/mp4")
    MP3 = ("mp3", "audio/mpeg")
    WAV = ("wav", "audio/wav")

    mime_type: str
    extension: str

    def __init__(self, extension, mime_type):
        self.extension = extension
        self.mime_type = mime_type  # _mime_type is stored privately

    def __str__(self):
        return f"{self.extension} ({self.mime_type})"

    def get_to_doc_func(self) -> Callable[[str, bytes], "Document"]:
        from app.utils.bytes_to_doc_util import Document
        if self == DataType.PNG:
            return Document.from_png
        elif self == DataType.JPEG:
            return Document.from_jpeg
        elif self == DataType.PDF:
            return Document.from_pdf
        elif self == DataType.WORD_DOC:
            return Document.from_doc
        elif self == DataType.POWERPOINT:
            return Document.from_pptx
        elif self == DataType.HTML:
            return Document.from_html
        elif self == DataType.EXCEL:
            return Document.from_xlsx
        elif self == DataType.TEXT:
            return Document.from_txt
        elif self == DataType.CSV:
            return Document.from_csv
        elif self == DataType.JSON:
            return Document.from_json
        elif self == DataType.MP4:
            return Document.from_mp4
        elif self == DataType.MP3:
            return Document.from_mp3
        elif self == DataType.WAV:
            return Document.from_wav
        else:
            raise ValueError("Invalid DataType")

    def is_image(self):
        return self == DataType.PNG or self == DataType.JPEG

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
