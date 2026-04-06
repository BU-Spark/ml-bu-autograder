import base64
import logging
import shutil
import tempfile
from enum import Enum
from io import BytesIO
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional, Callable, Literal

import fitz  # PyMuPDF
from pydantic import BaseModel, field_validator  # Use pydantic BaseModel for DocumentChunk
from pymupdf import FileDataError

try:
    from magic_pdf.integrations.rag.api import DataReader
    from magic_pdf.integrations.rag.type import CategoryType
    _MINERU_AVAILABLE = True
except ImportError:
    _MINERU_AVAILABLE = False

# MinerU element type sets (only defined when MinerU is available, but safe to reference
# as module-level constants used in from_pdf_mineru which guards on _MINERU_AVAILABLE)
_MINERU_TEXT_CATS: set = set()
_MINERU_IMAGE_CATS: set = set()
_MINERU_LABELS: dict = {}

if _MINERU_AVAILABLE:
    _MINERU_TEXT_CATS = {
        CategoryType.text, CategoryType.title,
        CategoryType.table, CategoryType.table_body,
        CategoryType.table_caption, CategoryType.table_footnote,
        CategoryType.image_caption, CategoryType.interline_equation,
    }
    _MINERU_IMAGE_CATS = {CategoryType.image, CategoryType.image_body}
    _MINERU_LABELS = {
        CategoryType.text: "TEXT",
        CategoryType.title: "TITLE",
        CategoryType.table: "TABLE",
        CategoryType.table_body: "TABLE",
        CategoryType.table_caption: "TABLE_CAPTION",
        CategoryType.table_footnote: "TABLE_CAPTION",
        CategoryType.image_caption: "IMAGE_CAPTION",
        CategoryType.interline_equation: "EQUATION",
        CategoryType.image: "IMAGE",
        CategoryType.image_body: "IMAGE",
    }


class DataType(Enum):
    """
    Represents a list of accepted data types, along with their corresponding MIME types.
    Note: This extends the fundamental data types defined in the bytes_to_doc_util module
    and so the below list IS NOT an exhaustive list of all data types supported.
    Other types like TEXT, PNG, etc. exist and are defined in bytes_to_doc_util.
    """
    PNG = ("png", "image/png")
    JPEG = ("jpeg", "image/jpeg")
    HTML = ("html", "text/html")
    TEXT = ("txt", "text/plain")
    CSV = ("csv", "text/csv")
    PDF = ("pdf", "application/pdf")
    JSON = ("json", "application/json")
    WORD_DOC = ("doc", "application/msword")
    POWERPOINT = ("pptx", "application/vnd.ms-powerpoint")
    EXCEL = ("xlsx", "application/vnd.ms-excel")
    MP4 = ("mp4", "video/mp4")
    MP3 = ("mp3", "audio/mpeg")
    WAV = ("wav", "audio/wav")

    mime_type: str
    extension: str

    def __init__(self, extension, mime_type):
        self.extension = extension
        self.mime_type = mime_type  # _mime_type is stored privately

    def is_audio(self):
        return self.name in ["MP3", "WAV"]

    def is_video(self):
        return self.name in ["MP4"]

    def is_fundamental(self):
        """
        "Fundamental" data types are text and images that can be safely passed directly
        to an LLM.
        """
        return self.is_text() or self.is_image()

    def is_image(self):
        return self.mime_type.startswith("image/")

    def is_text(self):
        return self.mime_type.startswith("text/")

    def __str__(self):
        return f"{self.extension} ({self.mime_type})"

    @classmethod
    def _missing_(cls, value):
        """
        Allows deserialization from just the extension like 'pdf' or 'txt'.
        """
        if isinstance(value, str):
            for member in cls:
                if member.extension == value.lower() or member.mime_type == value.lower():
                    return member
        if isinstance(value, tuple) or isinstance(value, list):
            if len(value) == 2:
                for member in cls:
                    if member.extension == value[0].lower():
                        return member
        raise ValueError(f"'{value}' is not a valid DataType extension")

    def get_to_doc_func(self, use_mineru: bool = False) -> "ToDocumentFunction":
        if self == DataType.PNG:
            return ToDocumentFunction(Document.from_png)
        elif self == DataType.JPEG:
            return ToDocumentFunction(Document.from_jpeg)
        elif self == DataType.PDF:
            if use_mineru:
                return ToDocumentFunction(Document.from_pdf_mineru)
            return ToDocumentFunction(Document.from_pdf)
        elif self == DataType.WORD_DOC:
            return ToDocumentFunction(Document.from_doc)
        elif self == DataType.POWERPOINT:
            return ToDocumentFunction(Document.from_pptx)
        elif self == DataType.HTML:
            return ToDocumentFunction(Document.from_html)
        elif self == DataType.EXCEL:
            return ToDocumentFunction(Document.from_xlsx)
        elif self == DataType.TEXT:
            return ToDocumentFunction(Document.from_txt)
        elif self == DataType.CSV:
            return ToDocumentFunction(Document.from_csv)
        elif self == DataType.JSON:
            return ToDocumentFunction(Document.from_json)
        elif self == DataType.MP4:
            return ToDocumentFunction(Document.from_mp4)
        elif self == DataType.MP3:
            return ToDocumentFunction(Document.from_mp3)
        elif self == DataType.WAV:
            return ToDocumentFunction(Document.from_wav)
        else:
            raise ValueError("Invalid DataType")

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


# Define DocumentChunk using Pydantic for potential validation/structure
class DocumentChunk(BaseModel):
    # The modality of the data
    data_type: DataType
    # The raw bytes of this data
    content: bytes
    # metadata associated with the data
    # (for example which document or page number it comes from)
    metadata: Optional[Dict[Literal['page_num', 'xref', 'element_type', 'caption'], Any]] = None

    @field_validator("data_type", mode="before")
    def validate_data_type(cls, dt: DataType) -> DataType:
        assert dt.is_fundamental(), "Only fundamental data types are allowed in a document chunk."
        return dt

    def get_as_string(self) -> str:
        if self.data_type == DataType.TEXT:
            try:
                return self.content.decode("utf-8")
            except UnicodeDecodeError:
                return f"[Non-UTF8 Text: {len(self.content)} bytes]"
        else:
            # Provide a representation for non-text types
            return f"[{self.data_type.name}: {len(self.content)} bytes]"

    def get_as_bytes(self) -> bytes:
        return self.content

    def get_as_base64(self) -> str:
        return base64.b64encode(self.content).decode("utf-8")


class Document:
    # document contents in the order one would naturally read them
    # int: the chunk id
    # DocumentContent: the content associated with the chunk
    file_name: str
    contents: Dict[int, DocumentChunk]

    # Add a simple constructor for type hinting and clarity
    def __init__(self, file_name: str, contents: Dict[int, DocumentChunk]):
        self.file_name = file_name
        self.contents = contents

    def get_chunk(self, chunk_id) -> DocumentChunk:
        return self.contents[chunk_id]

    # This method was AI generated: https://aistudio.google.com/app/prompts?state=%7B%22ids%22:%5B%2210BYwhnSJqSXol4OhtKIwAbFk6qUN3oZ7%22%5D,%22action%22:%22open%22,%22userId%22:%22112153521177605316268%22,%22resourceKeys%22:%7B%7D%7D&usp=sharing
    @classmethod
    def from_pdf(cls,
                 file_name: str,
                 file_bytes: bytes,
                 do_splits=True,
                 split_len: Optional[int] = 500,
                 overlap: int = 50,
                 min_image_bytes: int = 0) -> Optional["Document"]:
        """
        Extracts text and images from a PDF file in reading order, chunking text content.

        Args:
            file_name: Path to the PDF file.
            file_bytes: Bytes of the PDF file.
            split_len: Maximum number of words for text chunks. Chunks are created when
                       this limit is reached, an image is encountered, or the document ends.
                       If set to None, text splitting based on length is disabled, and text
                       chunks are only split by images or the end of the document.
            overlap: Number of words from the end of the previous text chunk to include
                     at the beginning of the next chunk. Only applicable if split_len is not None.
                     Must be less than split_len if split_len is set.
            min_image_bytes: Minimum size in bytes for an image to be included as a chunk.
                             Images smaller than this will be skipped. Defaults to 0 (include all images).

        Returns:
            A Document object containing extracted and chunked content.

        Raises:
            FileNotFoundError: If the file_path does not exist.
            ValueError: If overlap is greater than or equal to split_len when split_len is not None.
            Exception: For errors during PDF processing.
        """
        if do_splits is False:
            split_len = None
            overlap = None

        if split_len is not None and overlap >= split_len:
            raise ValueError(
                f"Overlap ({overlap}) must be less than split_len ({split_len}) when split_len is enabled.")
        if split_len is None and overlap is not None and overlap > 0:
            print(f"Warning: Overlap ({overlap}) is specified, but split_len is None. Overlap will be ignored.")
            overlap = 0  # Overlap is meaningless without length-based splitting

        contents: Dict[int, DocumentChunk] = {}
        chunk_id_counter = 0
        # Store tuples of (word, page_number)
        buffered_word_data: List[Tuple[str, int]] = []

        doc = None
        try:
            binary_stream = BytesIO(file_bytes)
            try:
                doc = fitz.open(stream=binary_stream, filetype="pdf")
            except FileDataError:
                logging.error("Failed to open pdf file. Is this even a PDF?")
                return None

            for page_num_zero_based, page in enumerate(doc):
                page_num_one_based = page_num_zero_based + 1

                # --- Get page items (text blocks and images) ---
                page_items: List[Dict[str, Any]] = []

                # 1. Get text blocks
                # todo: worth considering extracting html instead
                text_blocks = page.get_text("blocks")
                for tb in text_blocks:
                    x0, y0, x1, y1, text_content, block_no, block_type = tb
                    clean_text = text_content.strip()
                    if clean_text:
                        page_items.append({
                            'type': 'text',
                            'bbox': (x0, y0, x1, y1),
                            'content': clean_text,
                            'page': page_num_one_based
                        })

                # 2. Get image info
                image_info_list = page.get_images(full=True)
                processed_xrefs = set()
                for img_info in image_info_list:
                    xref = img_info[0]
                    if xref in processed_xrefs:
                        continue

                    try:
                        img_bbox_rect = page.get_image_bbox(img_info)
                        if not img_bbox_rect or not img_bbox_rect.is_valid or img_bbox_rect.is_empty:
                            # Still skip images without reliable bbox for sorting
                            logging.info(
                                f"Skipping image xref {xref} on page {page_num_one_based} due to invalid/missing bbox.")
                            continue

                        img_bbox = tuple(img_bbox_rect)

                        base_image = doc.extract_image(xref)
                        if base_image and base_image.get("image"):
                            img_bytes = base_image["image"]
                            image_size = len(img_bytes)

                            # Check if image meets minimum size requirement
                            if image_size < min_image_bytes:
                                logging.info(
                                    f"Skipping image xref {xref} on page {page_num_one_based} (size {image_size} bytes < min {min_image_bytes} bytes).")
                                processed_xrefs.add(xref)  # Mark as processed even if skipped
                                continue  # Skip adding this image item

                            # If image is large enough, add it to page items
                            page_items.append({
                                'type': 'image',
                                'bbox': img_bbox,
                                'content': img_bytes,
                                'ext': base_image['ext'],
                                'page': page_num_one_based,
                                'xref': xref
                            })
                            processed_xrefs.add(xref)
                        else:
                            logging.warning(
                                f"Could not extract image bytes for xref {xref} on page {page_num_one_based}.")

                    except Exception as e:
                        logging.warning(f"Error processing image xref {xref} on page {page_num_one_based}: {e}")

                # --- Sort items based on reading order heuristic (top-to-bottom, left-to-right) ---
                page_items.sort(key=lambda item: (item['bbox'][1], item['bbox'][0]))  # Sort by y0 then x0

                # --- Process sorted items to create chunks ---
                for item in page_items:
                    item_page = item['page']

                    if item['type'] == 'text':
                        words = item['content'].split()
                        words = [w for w in words if w]
                        if not words: continue

                        buffered_word_data.extend([(word, item_page) for word in words])

                        # Perform length-based chunking ONLY if split_len is enabled
                        if split_len is not None:
                            while len(buffered_word_data) >= split_len:
                                words_for_chunk = buffered_word_data[:split_len]
                                chunk_text = " ".join([w for w, p in words_for_chunk])
                                chunk_bytes = chunk_text.encode("utf-8")
                                chunk_pages = sorted(list(set([p for w, p in words_for_chunk])))
                                metadata: dict[Literal['page_num'], Any] = {'page_num': chunk_pages}

                                contents[chunk_id_counter] = DocumentChunk(
                                    data_type=DataType.TEXT,
                                    content=chunk_bytes,
                                    metadata=metadata
                                )
                                chunk_id_counter += 1

                                # Apply overlap if enabled
                                if overlap > 0:
                                    buffered_word_data = buffered_word_data[split_len - overlap:]
                                else:
                                    buffered_word_data = buffered_word_data[split_len:]
                                # Safety break in case overlap logic somehow leads to infinite loop (unlikely here)
                                if len(buffered_word_data) < split_len:
                                    break

                    elif item['type'] == 'image':
                        # Encountering an image always forces the current text buffer (if any)
                        # to be finalized into a chunk, regardless of split_len.

                        # 1. Finalize any pending text chunk before the image
                        if buffered_word_data:
                            words_for_chunk = buffered_word_data
                            chunk_text = " ".join([w for w, p in words_for_chunk])
                            chunk_bytes = chunk_text.encode("utf-8")
                            chunk_pages = sorted(list(set([p for w, p in words_for_chunk])))
                            metadata: dict[Literal['page_num'], Any] = {'page_num': chunk_pages}

                            contents[chunk_id_counter] = DocumentChunk(
                                data_type=DataType.TEXT,
                                content=chunk_bytes,
                                metadata=metadata
                            )
                            chunk_id_counter += 1
                            buffered_word_data = []  # Reset buffer

                        # 2. Create the image chunk (it was already checked for size earlier)
                        img_bytes = item['content']
                        metadata: dict[Literal['page_num', 'xref'], Any] = {'page_num': [item_page], 'xref': item['xref']}
                        data_type = DataType.from_extension(item['ext'])
                        if data_type is None:
                            logging.warning(f"Skipping image chunk due to unknown extension: {item['ext']}")
                            continue
                        contents[chunk_id_counter] = DocumentChunk(
                            data_type=data_type,
                            content=img_bytes,
                            metadata=metadata
                        )
                        chunk_id_counter += 1

            # --- After processing all pages, check for any remaining text ---
            if buffered_word_data:
                # Create a final chunk from ALL remaining words in the buffer
                words_for_chunk = buffered_word_data
                chunk_text = " ".join([w for w, p in words_for_chunk])
                chunk_bytes = chunk_text.encode("utf-8")
                chunk_pages = sorted(list(set([p for w, p in words_for_chunk])))
                metadata = {'page_num': chunk_pages}

                contents[chunk_id_counter] = DocumentChunk(
                    data_type=DataType.TEXT,
                    content=chunk_bytes,
                    metadata=metadata
                )

        except fitz.FileNotFoundError as e:
            logging.error(f"PyMuPDF could not find or open file {file_name}: {e}")
            return None
        except Exception as e:
            logging.error(f"An error occurred during PDF processing: {e}")
            return None
        finally:
            if doc:
                doc.close()

        return cls(file_name=file_name, contents=contents)

    @classmethod
    def from_pdf_mineru(
        cls,
        file_name: str,
        file_bytes: bytes,
        do_splits: bool = True,
        method: str = "auto",
        min_image_bytes: int = 0,
    ) -> Optional["Document"]:
        """
        Extracts structured content from a PDF using MinerU (magic-pdf), producing
        typed chunks (TITLE, TEXT, TABLE, IMAGE, etc.) with linked captions.

        Args:
            file_name: Name of the PDF file (used as Document identifier).
            file_bytes: Raw bytes of the PDF.
            do_splits: If True, TEXT/TABLE chunks exceeding 500 words are split.
            method: MinerU extraction method — "auto", "txt", or "ocr".
            min_image_bytes: Skip image chunks smaller than this size in bytes.

        Returns:
            A Document with structured chunks, or None on error.

        Raises:
            ImportError: If magic_pdf is not installed.
        """
        if not _MINERU_AVAILABLE:
            raise ImportError(
                "magic_pdf is not installed. Install it with: pip install magic-pdf[full]"
            )

        tmp_path = None
        work_dir = None
        try:
            # Write PDF bytes to a temp file MinerU can read
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                tmp.write(file_bytes)
                tmp_path = Path(tmp.name)

            work_dir = Path(tempfile.mkdtemp())

            rdr = DataReader(str(tmp_path), method=method, output_dir=str(work_dir))
            doc_reader = rdr.get_document_result(0)
            if doc_reader is None:
                logging.error(f"MinerU returned no result for {file_name}")
                return None

            contents: Dict[int, DocumentChunk] = {}
            chunk_id_counter = 0
            split_len = 500
            overlap = 50

            for page_num_zero_based, page in enumerate(doc_reader):
                page_num = page_num_zero_based + 1

                # Build anno_id → node lookup
                anno_id_to_node = {node.anno_id: node for node in page}

                # Build image_anno_id → caption_text from relation map
                caption_for_image: Dict[int, str] = {}
                for rel in page.get_rel_map():
                    src = anno_id_to_node.get(rel.source_anno_id)
                    tgt = anno_id_to_node.get(rel.target_anno_id)
                    if src is None or tgt is None:
                        continue
                    # Determine which node is the caption and which is the image
                    if src.category_type == CategoryType.image_caption and tgt.category_type in _MINERU_IMAGE_CATS:
                        caption_for_image[rel.target_anno_id] = src.text or ""
                    elif tgt.category_type == CategoryType.image_caption and src.category_type in _MINERU_IMAGE_CATS:
                        caption_for_image[rel.source_anno_id] = tgt.text or ""

                for node in page:
                    # Skip standalone caption nodes — attached to their image chunk
                    if node.category_type == CategoryType.image_caption:
                        continue

                    if node.category_type in _MINERU_TEXT_CATS:
                        # For TABLE nodes prefer HTML, then text
                        if node.category_type in {CategoryType.table, CategoryType.table_body}:
                            raw_text = node.html or node.text or ""
                        else:
                            raw_text = node.text or ""

                        if not raw_text.strip():
                            continue

                        element_type = _MINERU_LABELS.get(node.category_type, "TEXT")

                        if do_splits and node.category_type in {CategoryType.text, CategoryType.table,
                                                                 CategoryType.table_body}:
                            # Word-count chunking (same logic as from_pdf)
                            words = raw_text.split()
                            start = 0
                            while start < len(words):
                                end = min(start + split_len, len(words))
                                chunk_text = " ".join(words[start:end])
                                contents[chunk_id_counter] = DocumentChunk(
                                    data_type=DataType.TEXT,
                                    content=chunk_text.encode("utf-8"),
                                    metadata={"page_num": [page_num], "element_type": element_type},
                                )
                                chunk_id_counter += 1
                                next_start = start + split_len - overlap
                                start = next_start if next_start > start else start + 1
                        else:
                            contents[chunk_id_counter] = DocumentChunk(
                                data_type=DataType.TEXT,
                                content=raw_text.encode("utf-8"),
                                metadata={"page_num": [page_num], "element_type": element_type},
                            )
                            chunk_id_counter += 1

                    elif node.category_type in _MINERU_IMAGE_CATS:
                        if not node.image_path:
                            continue

                        img_file = Path(node.image_path)
                        if not img_file.is_absolute():
                            img_file = work_dir / img_file

                        resolved_img = img_file.resolve()
                        work_dir_resolved = work_dir.resolve()
                        if not resolved_img.is_relative_to(work_dir_resolved):
                            logging.warning(
                                f"MinerU image path outside work_dir, skipping: {resolved_img}"
                            )
                            continue

                        if not resolved_img.exists():
                            logging.warning(f"MinerU image path not found: {resolved_img}")
                            continue

                        img_bytes = resolved_img.read_bytes()
                        if len(img_bytes) < min_image_bytes:
                            continue

                        data_type = DataType.from_extension(resolved_img.suffix.lstrip(".").lower())
                        if data_type is None:
                            logging.warning(f"Skipping MinerU image with unknown extension: {resolved_img.suffix}")
                            continue

                        meta: Dict[str, Any] = {"page_num": [page_num], "element_type": "IMAGE"}
                        if node.anno_id in caption_for_image:
                            meta["caption"] = caption_for_image[node.anno_id]

                        contents[chunk_id_counter] = DocumentChunk(
                            data_type=data_type,
                            content=img_bytes,
                            metadata=meta,
                        )
                        chunk_id_counter += 1

        except Exception as e:
            logging.error(f"MinerU processing failed for {file_name}: {e}", exc_info=True)
            return None
        finally:
            if tmp_path is not None:
                tmp_path.unlink(missing_ok=True)
            if work_dir is not None:
                shutil.rmtree(work_dir, ignore_errors=True)

        return cls(file_name=file_name, contents=contents)

    def to_markdown(self) -> str:
        """
        Renders document contents as a Markdown string.

        MinerU-produced chunks use element_type metadata for semantic formatting.
        Legacy PyMuPDF chunks (no element_type) are rendered as plain paragraphs.
        Image chunks are represented as placeholder references.
        """
        parts: List[str] = []
        for chunk_id, chunk in sorted(self.contents.items()):
            if chunk.data_type == DataType.TEXT:
                text = chunk.get_as_string()
                element_type = (chunk.metadata or {}).get("element_type")
                if element_type == "TITLE":
                    parts.append(f"## {text}\n\n")
                elif element_type == "TABLE":
                    parts.append(f"```\n{text}\n```\n\n")
                elif element_type == "EQUATION":
                    parts.append(f"$$ {text} $$\n\n")
                elif element_type == "TABLE_CAPTION":
                    parts.append(f"*{text}*\n\n")
                elif element_type == "IMAGE_CAPTION":
                    pass  # attached to the image chunk as metadata
                else:
                    # TEXT, None (legacy PyMuPDF), or anything else → plain paragraph
                    parts.append(f"{text}\n\n")
            elif chunk.data_type.is_image():
                caption = (chunk.metadata or {}).get("caption", "")
                suffix = f" — {caption}" if caption else ""
                parts.append(f"![Image](chunk_{chunk_id}){suffix}\n\n")

        return "".join(parts)

    # This method was generated using AI: https://aistudio.google.com/app/prompts?state=%7B%22ids%22:%5B%221LjDioKGc-5H78OUXySRbPlJh0TUB0nYv%22%5D,%22action%22:%22open%22,%22userId%22:%22112153521177605316268%22,%22resourceKeys%22:%7B%7D%7D&usp=sharing
    @classmethod
    def from_txt(cls,
                 file_name: str,
                 file_bytes: bytes,
                 do_splits=True,
                 split_len: int = 500,  # Default split length for text
                 overlap: int = 50,  # Default overlap for text
                 encoding: str = 'utf-8') -> Optional["Document"]:
        """
        Extracts text from a plain text file, chunking the content by words.

        Args:
            file_name: Name of the file
            file_bytes: Bytes of the text file.
            split_len: Maximum number of words per text chunk.
            overlap: Number of words from the end of the previous text chunk to include
                     at the beginning of the next chunk. Must be less than split_len.
            encoding: The encoding to use when reading the file. Defaults to 'utf-8'.

        Returns:
            A Document object containing the text content split into chunks.

        Raises:
            FileNotFoundError: If the file_path does not exist or is not a file.
            ValueError: If overlap is greater than or equal to split_len.
        """

        if do_splits is False:
            return cls._from_binary_file(file_name, file_bytes, DataType.TEXT)

        if overlap >= split_len:
            raise ValueError(f"Overlap ({overlap}) must be less than split_len ({split_len}).")

        contents: Dict[int, DocumentChunk] = {}
        chunk_id_counter = 0

        try:
            full_text = file_bytes.decode(encoding)  # Read the entire file content to a string
            words = full_text.split()  # Split by whitespace
            words = [w for w in words if w]  # Remove empty strings resulting from multiple spaces

            current_word_index = 0
            total_words = len(words)

            while current_word_index < total_words:
                # Determine the end index for this chunk
                end_index = min(current_word_index + split_len, total_words)

                # Get the words for the current chunk
                words_for_chunk = words[current_word_index:end_index]

                if not words_for_chunk:  # Should not happen with the loop condition, but safety check
                    break

                # Join words and encode
                chunk_text = " ".join(words_for_chunk)
                chunk_bytes = chunk_text.encode(encoding)  # Use the same encoding

                # Create and store the chunk
                contents[chunk_id_counter] = DocumentChunk(
                    data_type=DataType.TEXT,
                    content=chunk_bytes,
                )
                chunk_id_counter += 1

                # Calculate the start index for the *next* chunk, considering overlap
                next_start_index = current_word_index + split_len - overlap

                # Ensure we make progress and handle edge cases
                if next_start_index <= current_word_index:
                    # This happens if overlap >= split_len, or if split_len is very small.
                    # Force progress by moving at least one word forward.
                    # The initial check `overlap >= split_len` should prevent this,
                    # but as a safeguard:
                    current_word_index += 1
                else:
                    current_word_index = next_start_index

        except UnicodeDecodeError as e:
            logging.error(f"Encoding error reading {file_name} with {encoding}: {e}")
            return None
        except Exception as e:
            logging.error(f"An unexpected error occurred during TXT processing '{file_name}': {e}", exc_info=True)
            return None

        return cls(file_name=file_name, contents=contents)

    # This method was generated using AI: https://aistudio.google.com/app/prompts?state=%7B%22ids%22:%5B%221LjDioKGc-5H78OUXySRbPlJh0TUB0nYv%22%5D,%22action%22:%22open%22,%22userId%22:%22112153521177605316268%22,%22resourceKeys%22:%7B%7D%7D&usp=sharing
    @classmethod
    def _from_binary_file(cls,
                          file_name: str,
                          file_bytes: bytes,
                          data_type: DataType) -> Optional["Document"]:
        """Reads a binary file entirely into a single chunk."""

        contents: Dict[int, DocumentChunk] = {}

        try:
            chunk = DocumentChunk(
                data_type=data_type,
                content=file_bytes,
            )
            contents[0] = chunk  # Single chunk with ID 0
        except Exception as e:
            logging.error(f"An unexpected error occurred during binary file processing '{file_name}': {e}",
                          exc_info=True)
            return None

        return cls(file_name=file_name, contents=contents)

    # This method was generated using AI: https://aistudio.google.com/app/prompts?state=%7B%22ids%22:%5B%221LjDioKGc-5H78OUXySRbPlJh0TUB0nYv%22%5D,%22action%22:%22open%22,%22userId%22:%22112153521177605316268%22,%22resourceKeys%22:%7B%7D%7D&usp=sharing
    @classmethod
    def from_png(cls, file_name: str, file_bytes: bytes, do_splits=True) -> "Document":
        """
        Loads a PNG image file into a single DocumentChunk.

        Args:
            file_name: Name of the file
            file_bytes: Bytes of the png image file.

        Returns:
            A Document object containing one image chunk.

        Raises:
            FileNotFoundError: If the file_path does not exist or is not a file.
        """
        logging.info(f"Processing PNG file: {file_name}")
        # Delegate to the helper method
        return cls._from_binary_file(file_name, file_bytes, DataType.PNG)

    # This method was generated using AI: https://aistudio.google.com/app/prompts?state=%7B%22ids%22:%5B%221LjDioKGc-5H78OUXySRbPlJh0TUB0nYv%22%5D,%22action%22:%22open%22,%22userId%22:%22112153521177605316268%22,%22resourceKeys%22:%7B%7D%7D&usp=sharing
    @classmethod
    def from_jpeg(cls, file_name: str, file_bytes: bytes, do_splits=True) -> "Document":
        """
        Loads a JPG/JPEG image file into a single DocumentChunk.

        Args:
            file_name: Name of the file
            file_bytes: Bytes of the jpeg image file.

        Returns:
            A Document object containing one image chunk.

        Raises:
            FileNotFoundError: If the file_path does not exist or is not a file.
        """
        logging.info(f"Processing JPG/JPEG file: {file_name}")
        # Delegate to the helper method
        return cls._from_binary_file(file_name, file_bytes, DataType.JPEG)

    @classmethod
    def from_mp3(cls, file_name: str, file_bytes: bytes, do_splits=True, split_min: float = 2.0,
                 overlap: float = 0.33) -> "Document":
        raise NotImplementedError("from_mp3 is not implemented")

    @classmethod
    def from_wav(cls, file_name: str, file_bytes: bytes, do_splits=True, split_min: float = 2.0,
                 overlap: float = 0.33) -> "Document":
        raise NotImplementedError("from_wav is not implemented")

    @classmethod
    def from_mp4(cls, file_name: str, file_bytes: bytes, do_splits=True, split_min: float = 2.0,
                 overlap: float = 0.33) -> "Document":
        raise NotImplementedError("from_mp4 is not implemented")

    @classmethod
    def from_xlsx(cls, file_name: str, file_bytes: bytes, do_splits=True, split_len: int = 5000,
                  overlap: int = 0) -> "Document":
        raise NotImplementedError("from_xlsx is not implemented")

    @classmethod
    def from_csv(cls, file_name: str, file_bytes: bytes, do_splits=True, split_len: int = 5000,
                 overlap: int = 0) -> "Document":
        raise NotImplementedError("from_csv is not implemented")

    @classmethod
    def from_json(cls, file_name: str, file_bytes: bytes, do_splits=True, split_len: int = 5000,
                  overlap: int = 0) -> "Document":
        raise NotImplementedError("from_json is not implemented")

    @classmethod
    def from_doc(cls, file_name: str, file_bytes: bytes, do_splits=True, split_len: int = 5000,
                 overlap: int = 0) -> "Document":
        # TODO: the approach here would be to use libre-office to convert to pdf and process that
        raise NotImplementedError("from_doc is not implemented")

    @classmethod
    def from_pptx(cls, file_name: str, file_bytes: bytes, do_splits=True, split_len: int = 5000,
                  overlap: int = 0) -> "Document":
        # TODO: the approach here would be to use libre-office to convert to pdf and process that
        raise NotImplementedError("from_pptx is not implemented")

    @classmethod
    def from_html(cls, file_name: str, file_bytes: bytes, do_splits=True, split_len: int = 5000,
                  overlap: int = 0) -> "Document":
        raise NotImplementedError("from_html is not implemented")


class ToDocumentFunction:
    def __init__(self, func: Callable[[str, bytes, bool], Document]):
        self._call_func_ = func

    def __call__(self, filename: str, content_bytes: bytes, do_splits: bool = True) -> Document:
        return self._call_func_(filename, content_bytes, do_splits)


# --- Helper Function to Print Document Chunks ---
def print_document_summary(document: Document, title: str):
    logging.debug(f"\n--- {title} ---")
    logging.debug(f"Original File: {document.file_name}")
    logging.debug(f"Total chunks: {len(document.contents)}")

    for chunk_id, chunk in sorted(document.contents.items()):
        logging.debug(f"\n--- Chunk ID: {chunk_id} ---")
        logging.debug(f"  Type: {chunk.data_type.name}")
        logging.debug(f"  Metadata: {chunk.metadata}")

        if chunk.data_type == DataType.TEXT:
            text_content = chunk.get_as_string()
            word_count = len(text_content.split())
            logging.debug(f"  Word Count: {word_count}")
            words = text_content.split()
            preview_start = " ".join(words[:15])
            preview_end = " ".join(words[-15:])
            if len(words) > 30:
                logging.debug(f"  Content Preview: '{preview_start} ... {preview_end}'")
            else:
                logging.debug(f"  Content: '{text_content}'")

        elif chunk.data_type.is_image():
            image_size = len(chunk.content)
            logging.debug(f"  Image Content Size: {image_size} bytes")
            # Optionally print base64 preview if needed, but it's very long
            # logging.debug(f"  Image Base64 Preview: {chunk.get_as_base64()[:50]}...")


if __name__ == '__main__':
    # Create a dummy PDF for testing if one doesn't exist
    dummy_pdf_path = Path(
        "I:\\.shortcut-targets-by-id\\1q2B2T_aTytCWO8SdBLnWpTNEQcPtXqE8\\BU MET\\cs581_quiz_and_assignment_data\\Lecture Material\\Mod 2 HIS & EHR Clinical Functionality-Lecture Slides.pdf")

    try:
        # Test Case 1: Standard splitting with overlap
        split_words = 50
        overlap_words = 10

        bytes = open(dummy_pdf_path, "rb").read()
        file_name = "dummy.pdf"

        document1 = Document.from_pdf(file_name, bytes,
                                      split_len=split_words,
                                      overlap=overlap_words,
                                      min_image_bytes=0)  # Include all "images" (none in this dummy)
        print_document_summary(document1,
                               f"Test 1: split_len={split_words}, overlap={overlap_words}, min_image_bytes=0")

        # Test Case 2: No length splitting (split_len=None)
        document2 = Document.from_pdf(file_name, bytes,
                                      split_len=None,
                                      overlap=overlap_words,  # Overlap will be ignored
                                      min_image_bytes=0)
        print_document_summary(document2,
                               f"Test 2: split_len=None (Overlap {overlap_words} ignored), min_image_bytes=0")
        # Expected: Fewer chunks, potentially large ones, only split by (simulated) images or page ends if structure allows.

        # Test Case 3: Splitting with high min_image_bytes (won't affect this dummy PDF)
        # If the dummy PDF had real images, this setting could cause them to be skipped.
        high_min_bytes = 1024 * 1024  # 1 MB
        document3 = Document.from_pdf(file_name, bytes,
                                      split_len=split_words,
                                      overlap=overlap_words,
                                      min_image_bytes=high_min_bytes)
        print_document_summary(document3,
                               f"Test 3: split_len={split_words}, overlap={overlap_words}, min_image_bytes={high_min_bytes}")
        # Expected: Same as Test 1 for *this* dummy PDF, as it has no real images to skip.
        # If it had images < 1MB, they would be skipped and text chunks might merge across them.


    except FileNotFoundError as e:
        print(e)
    except NotImplementedError as e:
        print(e)
    except ValueError as e:
        print(f"Configuration Error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred during example usage: {e}")
        import traceback

        traceback.print_exc()
