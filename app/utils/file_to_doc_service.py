import base64
from typing import Dict

from construct import Enum
from pydantic import FilePath


class DocumentContentType(Enum):
    TEXT = 1
    IMAGE = 2
    AUDIO = 3
    VIDEO = 4

class DocumentChunk:
    # The modality of the data
    content_type: DocumentContentType
    # The raw bytes of this data
    content: bytes
    # metadata associated with the data
    # (for example which document or page number it comes from)
    metadata: dict = {}

    def get_as_string(self) -> str:
        return self.content.decode("utf-8")

    def get_as_bytes(self) -> bytes:
        return self.content

    def get_as_base64(self) -> str:
        return base64.b64encode(self.content).decode("utf-8")

class Document:
    # document contents in the order one would naturally read them
    # int: the chunk id
    # DocumentContent: the content associated with the chunk
    original_file: str
    contents: Dict[int, DocumentChunk]

    @classmethod
    def from_pdf(cls, file_path: FilePath, split_len: int = 5000, overlap: int = 0) -> "Document":
        # TODO:
        #  Uses PyMuPDF to extract text and images in the order one would naturally read them.
        #  Text contents are split (chunked) by either reaching the split_len or the end of the
        #  text component. This means that the end of a chunk can be triggered by either reaching the
        #  maximum size allowed for the chunk, or reaching the end of the PDF, or running into content
        #  in another modality (i.e. an image).
        #  For PDFs additional metadata is also tracked. Specifically, inside metadata we store
        #  page_num: List[int] which contains a list of all pages whose content this chunk contains.
        ...

    @classmethod
    def from_mp3(cls, file_path: FilePath, split_min: float = 2.0, overlap: float = 0.33):
        ...

    @classmethod
    def from_mp4(cls, file_path: FilePath, split_min: float = 2.0, overlap: float = 0.33):
        ...

    @classmethod
    def from_xlsx(cls, file_path: FilePath, split_len: int = 5000, overlap: int = 0):
        ...

    @classmethod
    def from_doc(cls, file_path: FilePath, split_len: int = 5000, overlap: int = 0):
        ...

