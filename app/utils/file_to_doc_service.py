import logging

import fitz  # PyMuPDF
import base64
from typing import Dict, List, Tuple, Any, Optional
from pathlib import Path

# Assuming 'construct' is just for the Enum definition example
# and we can use standard Python enums or just constants.
# Using standard library Enum for DocumentContentType.
from enum import Enum as PyEnum

from pydantic import FilePath, BaseModel, Field  # Use pydantic BaseModel for DocumentChunk


# Define DocumentContentType using standard Enum
class ContentModality(PyEnum):
    TEXT = 1
    IMAGE = 2
    AUDIO = 3


# Define DocumentChunk using Pydantic for potential validation/structure
class DocumentChunk(BaseModel):
    # The modality of the data
    content_modality: ContentModality
    # The raw bytes of this data
    content: bytes
    # metadata associated with the data
    # (for example which document or page number it comes from)
    metadata: Optional[Dict[str, Any]] = None

    # Make Pydantic allow arbitrary types like the Enum
    class Config:
        arbitrary_types_allowed = True

    def get_as_string(self) -> str:
        if self.content_modality == ContentModality.TEXT:
            try:
                return self.content.decode("utf-8")
            except UnicodeDecodeError:
                # Fallback or raise error? Let's return a representation
                return f"[Non-UTF8 Text: {len(self.content)} bytes]"
        else:
            # Provide a representation for non-text types
            return f"[{self.content_modality.name}: {len(self.content)} bytes]"

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

    @classmethod
    def _validate_path(cls, file_path: FilePath) -> Path:
        """Helper to validate file path existence."""
        if not file_path.exists():
            raise FileNotFoundError(f"No such file: {file_path}")
        if not file_path.is_file():
             raise ValueError(f"Path is not a file: {file_path}")
        return file_path

    # This method was AI generated: https://aistudio.google.com/app/prompts?state=%7B%22ids%22:%5B%2210BYwhnSJqSXol4OhtKIwAbFk6qUN3oZ7%22%5D,%22action%22:%22open%22,%22userId%22:%22112153521177605316268%22,%22resourceKeys%22:%7B%7D%7D&usp=sharing
    @classmethod
    def from_pdf(cls,
                 file_path: FilePath,
                 split_len: Optional[int] = 500,
                 overlap: int = 50,
                 min_image_bytes: int = 0) -> Optional["Document"]:
        """
        Extracts text and images from a PDF file in reading order, chunking text content.

        Args:
            file_path: Path to the PDF file.
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
        file_path = Document._validate_path(file_path)

        if split_len is not None and overlap >= split_len:
            raise ValueError(
                f"Overlap ({overlap}) must be less than split_len ({split_len}) when split_len is enabled.")
        if split_len is None and overlap > 0:
            print(f"Warning: Overlap ({overlap}) is specified, but split_len is None. Overlap will be ignored.")
            overlap = 0  # Overlap is meaningless without length-based splitting

        contents: Dict[int, DocumentChunk] = {}
        chunk_id_counter = 0
        # Store tuples of (word, page_number)
        buffered_word_data: List[Tuple[str, int]] = []

        doc = None
        try:
            doc = fitz.open(str(file_path))  # PyMuPDF needs a string path

            for page_num_zero_based, page in enumerate(doc):
                page_num_one_based = page_num_zero_based + 1

                # --- Get page items (text blocks and images) ---
                page_items: List[Dict[str, Any]] = []

                # 1. Get text blocks
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
                                metadata = {'page_num': chunk_pages}

                                contents[chunk_id_counter] = DocumentChunk(
                                    content_modality=ContentModality.TEXT,
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
                            metadata = {'page_num': chunk_pages}

                            contents[chunk_id_counter] = DocumentChunk(
                                content_modality=ContentModality.TEXT,
                                content=chunk_bytes,
                                metadata=metadata
                            )
                            chunk_id_counter += 1
                            buffered_word_data = []  # Reset buffer

                        # 2. Create the image chunk (it was already checked for size earlier)
                        img_bytes = item['content']
                        metadata = {'page_num': [item_page]}
                        contents[chunk_id_counter] = DocumentChunk(
                            content_modality=ContentModality.IMAGE,
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
                    content_modality=ContentModality.TEXT,
                    content=chunk_bytes,
                    metadata=metadata
                )

        except fitz.FileNotFoundError as e:
            logging.error(f"PyMuPDF could not find or open file {file_path}: {e}")
            return None
        except Exception as e:
            logging.error(f"An error occurred during PDF processing: {e}")
            return None
        finally:
            if doc:
                doc.close()

        return cls(file_name=file_path.name, contents=contents)

    # --- Stubs for other methods as provided in the prompt ---

    @classmethod
    def from_txt(cls,
                 file_path: FilePath,
                 split_len: int = 500,  # Default split length for text
                 overlap: int = 50,  # Default overlap for text
                 encoding: str = 'utf-8') -> Optional["Document"]:
        """
        Extracts text from a plain text file, chunking the content by words.

        Args:
            file_path: Path to the TXT file.
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
        file_path = Document._validate_path(file_path)

        if overlap >= split_len:
            raise ValueError(f"Overlap ({overlap}) must be less than split_len ({split_len}).")

        contents: Dict[int, DocumentChunk] = {}
        chunk_id_counter = 0

        try:
            full_text = file_path.read_text(encoding=encoding)
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
                    content_modality=ContentModality.TEXT,
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


        except FileNotFoundError:  # Already handled by _validate_path, but good practice
            return None
        except UnicodeDecodeError as e:
            logging.error(f"Encoding error reading {file_path} with {encoding}: {e}")
            return None
        except IOError as e:
            logging.error(f"IO error reading {file_path}: {e}")
            return None
        except Exception as e:
            logging.error(f"An unexpected error occurred during TXT processing '{file_path}': {e}", exc_info=True)
            return None

        return cls(file_name=file_path.name, contents=contents)

    @classmethod
    def _from_binary_file(cls,
                          file_path: FilePath,
                          content_modality: ContentModality,
                          content_format: str) -> Optional["Document"]:
        """Reads a binary file entirely into a single chunk."""
        validated_path = cls._validate_path(file_path)
        contents: Dict[int, DocumentChunk] = {}

        try:
            file_bytes = validated_path.read_bytes()

            if not file_bytes:
                logging.warning(f"Binary file is empty: {validated_path}")
                return None

            metadata = {'content_format': content_format}

            chunk = DocumentChunk(
                content_modality=content_modality,
                content=file_bytes,
                metadata=metadata
            )
            contents[0] = chunk  # Single chunk with ID 0

        except FileNotFoundError:  # Should be caught by _validate_path
            return None
        except IOError as e:
            logging.error(f"IO error reading binary file {validated_path}: {e}")
            return None
        except Exception as e:
            logging.error(f"An unexpected error occurred during binary file processing '{validated_path}': {e}",
                          exc_info=True)
            return None

        return cls(file_name=validated_path.name, contents=contents)

    # --- NEW: from_png Implementation ---
    @classmethod
    def from_png(cls, file_path: FilePath) -> "Document":
        """
        Loads a PNG image file into a single DocumentChunk.

        Args:
            file_path: Path to the PNG file.

        Returns:
            A Document object containing one image chunk.

        Raises:
            FileNotFoundError: If the file_path does not exist or is not a file.
        """
        logging.info(f"Processing PNG file: {file_path}")
        # Delegate to the helper method
        return cls._from_binary_file(file_path, ContentModality.IMAGE, "png")

    # --- NEW: from_jpg Implementation ---
    @classmethod
    def from_jpeg(cls, file_path: FilePath) -> "Document":
        """
        Loads a JPG/JPEG image file into a single DocumentChunk.

        Args:
            file_path: Path to the JPG/JPEG file.

        Returns:
            A Document object containing one image chunk.

        Raises:
            FileNotFoundError: If the file_path does not exist or is not a file.
        """
        logging.info(f"Processing JPG/JPEG file: {file_path}")
        # Delegate to the helper method
        return cls._from_binary_file(file_path, ContentModality.IMAGE, "jpeg")

    @classmethod
    def from_mp3(cls, file_path: FilePath, split_min: float = 2.0, overlap: float = 0.33):
        raise NotImplementedError("from_mp3 is not implemented")

    @classmethod
    def from_mp4(cls, file_path: FilePath, split_min: float = 2.0, overlap: float = 0.33):
        raise NotImplementedError("from_mp4 is not implemented")

    @classmethod
    def from_xlsx(cls, file_path: FilePath, split_len: int = 5000, overlap: int = 0):
        raise NotImplementedError("from_xlsx is not implemented")

    @classmethod
    def from_csv(cls, file_path: FilePath, split_len: int = 5000, overlap: int = 0):
        raise NotImplementedError("from_csv is not implemented")

    @classmethod
    def from_json(cls, file_path: FilePath, split_len: int = 5000, overlap: int = 0):
        raise NotImplementedError("from_json is not implemented")

    @classmethod
    def from_doc(cls, file_path: FilePath, split_len: int = 5000, overlap: int = 0):
        raise NotImplementedError("from_doc is not implemented")

    @classmethod
    def from_pptx(self, file_path: FilePath, split_len: int = 5000, overlap: int = 0):
        raise NotImplementedError("from_pptx is not implemented")

    @classmethod
    def from_html(self, file_path: FilePath, split_len: int = 5000, overlap: int = 0):
        raise NotImplementedError("from_html is not implemented")

# --- Helper Function to Print Document Chunks ---
def print_document_summary(document: Document, title: str):
    print(f"\n--- {title} ---")
    print(f"Original File: {document.original_file}")
    print(f"Total chunks: {len(document.contents)}")

    for chunk_id, chunk in sorted(document.contents.items()):
        print(f"\n--- Chunk ID: {chunk_id} ---")
        print(f"  Type: {chunk.content_modality.name}")
        print(f"  Metadata: {chunk.metadata}")

        if chunk.content_modality == ContentModality.TEXT:
            text_content = chunk.get_as_string()
            word_count = len(text_content.split())
            print(f"  Word Count: {word_count}")
            words = text_content.split()
            preview_start = " ".join(words[:15])
            preview_end = " ".join(words[-15:])
            if len(words) > 30:
                print(f"  Content Preview: '{preview_start} ... {preview_end}'")
            else:
                 print(f"  Content: '{text_content}'")

        elif chunk.content_modality == ContentModality.IMAGE:
             image_size = len(chunk.content)
             print(f"  Image Content Size: {image_size} bytes")
             # Optionally print base64 preview if needed, but it's very long
             # print(f"  Image Base64 Preview: {chunk.get_as_base64()[:50]}...")

if __name__ == '__main__':
    # Create a dummy PDF for testing if one doesn't exist
    dummy_pdf_path = Path("Lecture Material\\Mod 2 HIS & EHR Clinical Functionality-Lecture Slides.pdf")

    try:
        # Test Case 1: Standard splitting with overlap
        split_words = 50
        overlap_words = 10
        document1 = Document.from_pdf(dummy_pdf_path,
                                      split_len=split_words,
                                      overlap=overlap_words,
                                      min_image_bytes=0)  # Include all "images" (none in this dummy)
        print_document_summary(document1,
                               f"Test 1: split_len={split_words}, overlap={overlap_words}, min_image_bytes=0")

        # Test Case 2: No length splitting (split_len=None)
        document2 = Document.from_pdf(dummy_pdf_path,
                                      split_len=None,
                                      overlap=overlap_words,  # Overlap will be ignored
                                      min_image_bytes=0)
        print_document_summary(document2,
                               f"Test 2: split_len=None (Overlap {overlap_words} ignored), min_image_bytes=0")
        # Expected: Fewer chunks, potentially large ones, only split by (simulated) images or page ends if structure allows.

        # Test Case 3: Splitting with high min_image_bytes (won't affect this dummy PDF)
        # If the dummy PDF had real images, this setting could cause them to be skipped.
        high_min_bytes = 1024 * 1024  # 1 MB
        document3 = Document.from_pdf(dummy_pdf_path,
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
