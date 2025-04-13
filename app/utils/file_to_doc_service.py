import fitz  # PyMuPDF
import base64
from typing import Dict, List, Set, Tuple, Any, Optional
from pathlib import Path

# Assuming 'construct' is just for the Enum definition example
# and we can use standard Python enums or just constants.
# Using standard library Enum for DocumentContentType.
from enum import Enum as PyEnum

from pydantic import FilePath, BaseModel, Field # Use pydantic BaseModel for DocumentChunk

# Define DocumentContentType using standard Enum
class DocumentContentType(PyEnum):
    TEXT = 1
    IMAGE = 2
    AUDIO = 3
    VIDEO = 4

# Define DocumentChunk using Pydantic for potential validation/structure
class DocumentChunk(BaseModel):
    # The modality of the data
    content_type: DocumentContentType
    # The raw bytes of this data
    content: bytes
    # metadata associated with the data
    # (for example which document or page number it comes from)
    metadata: dict = Field(default_factory=dict)

    # Make Pydantic allow arbitrary types like the Enum
    class Config:
        arbitrary_types_allowed = True

    def get_as_string(self) -> str:
        if self.content_type == DocumentContentType.TEXT:
            try:
                return self.content.decode("utf-8")
            except UnicodeDecodeError:
                # Fallback or raise error? Let's return a representation
                return f"[Non-UTF8 Text: {len(self.content)} bytes]"
        else:
            # Provide a representation for non-text types
            return f"[{self.content_type.name}: {len(self.content)} bytes]"

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

    # Add a simple constructor for type hinting and clarity
    def __init__(self, original_file: str, contents: Dict[int, DocumentChunk]):
        self.original_file = original_file
        self.contents = contents

    # This method was AI generated: https://aistudio.google.com/app/prompts?state=%7B%22ids%22:%5B%2210BYwhnSJqSXol4OhtKIwAbFk6qUN3oZ7%22%5D,%22action%22:%22open%22,%22userId%22:%22112153521177605316268%22,%22resourceKeys%22:%7B%7D%7D&usp=sharing
    @classmethod
    def from_pdf(cls, file_path: FilePath, split_len_words: int = 500, overlap_words: int = 50) -> Optional["Document"]:
        """
        Extracts text and images from a PDF file in reading order, chunking text content.

        Args:
            file_path: Path to the PDF file.
            split_len_words: Maximum character length for text chunks. Chunks are created when
                       this length is reached, an image is encountered, or the document ends.
            overlap_words: Currently unused for PDF processing. A warning will be printed if non-zero.

        Returns:
            A Document object containing extracted and chunked content.

        Raises:
            FileNotFoundError: If the file_path does not exist.
            Exception: For errors during PDF processing.
        """
        if not Path(file_path).exists():
            raise FileNotFoundError(f"No such file: {file_path}")

        if overlap_words >= split_len_words:
            raise ValueError(f"Overlap ({overlap_words}) must be less than split_len ({split_len_words})")

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
                    # Basic check to ignore blocks with no real text content
                    clean_text = text_content.strip()
                    if clean_text:
                        page_items.append({
                            'type': 'text',
                            'bbox': (x0, y0, x1, y1),  # Store bbox for sorting
                            'content': clean_text,  # Use cleaned text
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
                        # Handle invalid or unavailable bbox more gracefully - maybe skip sorting?
                        # For now, require a valid bbox for inclusion in sorted items.
                        if not img_bbox_rect or not img_bbox_rect.is_valid or img_bbox_rect.is_empty:
                            print(
                                f"Warning: Skipping image xref {xref} on page {page_num_one_based} due to invalid/missing bbox.")
                            continue

                        img_bbox = tuple(img_bbox_rect)

                        base_image = doc.extract_image(xref)
                        if base_image and base_image.get("image"):
                            img_bytes = base_image["image"]
                            page_items.append({
                                'type': 'image',
                                'bbox': img_bbox,
                                'content': img_bytes,
                                'page': page_num_one_based,
                                'xref': xref
                            })
                            processed_xrefs.add(xref)
                        else:
                            print(
                                f"Warning: Could not extract image bytes for xref {xref} on page {page_num_one_based}.")

                    except Exception as e:
                        print(f"Warning: Error processing image xref {xref} on page {page_num_one_based}: {e}")

                # --- Sort items based on reading order heuristic (top-to-bottom, left-to-right) ---
                page_items.sort(key=lambda item: (item['bbox'][1], item['bbox'][0]))  # Sort by y0 then x0

                # --- Process sorted items to create chunks ---
                for item in page_items:
                    item_page = item['page']

                    if item['type'] == 'text':
                        # Simple word splitting by whitespace. Consider more robust tokenization if needed.
                        words = item['content'].split()  # Splits by whitespace
                        words = [w for w in words if w]  # Remove empty strings resulting from multiple spaces

                        if not words:  # Skip if block contained only whitespace
                            continue

                        # Add words with their page number to the buffer
                        buffered_word_data.extend([(word, item_page) for word in words])

                        # Check if buffer exceeds split_len and create chunks with overlap
                        while len(buffered_word_data) >= split_len_words:
                            words_for_chunk = buffered_word_data[:split_len_words]
                            chunk_text = " ".join([w for w, p in words_for_chunk])
                            chunk_bytes = chunk_text.encode("utf-8")
                            # Collect unique page numbers associated with the words in this chunk
                            chunk_pages = sorted(list(set([p for w, p in words_for_chunk])))
                            metadata = {'page_num': chunk_pages}

                            contents[chunk_id_counter] = DocumentChunk(
                                content_type=DocumentContentType.TEXT,
                                content=chunk_bytes,
                                metadata=metadata
                            )
                            chunk_id_counter += 1

                            # Update buffer: keep the last 'overlap' words for the next chunk
                            if overlap_words > 0:
                                buffered_word_data = buffered_word_data[split_len_words - overlap_words:]
                            else:
                                buffered_word_data = buffered_word_data[split_len_words:]
                            # Check if the remaining buffer is still >= split_len (unlikely with overlap but possible)
                            if len(buffered_word_data) < split_len_words:
                                break


                    elif item['type'] == 'image':
                        # 1. Finalize any pending text chunk before the image
                        # Check if there are words in the buffer to form a final text chunk
                        if buffered_word_data:
                            # Create a chunk from ALL remaining words in the buffer before the image
                            words_for_chunk = buffered_word_data
                            chunk_text = " ".join([w for w, p in words_for_chunk])
                            chunk_bytes = chunk_text.encode("utf-8")
                            chunk_pages = sorted(list(set([p for w, p in words_for_chunk])))
                            metadata = {'page_num': chunk_pages}

                            contents[chunk_id_counter] = DocumentChunk(
                                content_type=DocumentContentType.TEXT,
                                content=chunk_bytes,
                                metadata=metadata
                            )
                            chunk_id_counter += 1

                        # Reset text buffer *after* creating the final text chunk
                        buffered_word_data = []

                        # 2. Create the image chunk
                        img_bytes = item['content']
                        metadata = {'page_num': [item_page]}  # Image is associated only with its page
                        contents[chunk_id_counter] = DocumentChunk(
                            content_type=DocumentContentType.IMAGE,
                            content=img_bytes,
                            metadata=metadata
                        )
                        chunk_id_counter += 1

            # --- After processing all pages, check for any remaining text ---
            if buffered_word_data:
                # Create a final chunk from any remaining words in the buffer
                words_for_chunk = buffered_word_data
                chunk_text = " ".join([w for w, p in words_for_chunk])
                chunk_bytes = chunk_text.encode("utf-8")
                chunk_pages = sorted(list(set([p for w, p in words_for_chunk])))
                metadata = {'page_num': chunk_pages}

                contents[chunk_id_counter] = DocumentChunk(
                    content_type=DocumentContentType.TEXT,
                    content=chunk_bytes,
                    metadata=metadata
                )
                # chunk_id_counter += 1 # Not needed after last chunk

        except fitz.FileNotFoundError:
            raise FileNotFoundError(f"PyMuPDF could not find or open file: {file_path}")
        except Exception as e:
            print(f"An error occurred during PDF processing: {e}")
            raise RuntimeError(f"Failed to process PDF {file_path}: {e}") from e
        finally:
            if doc:
                doc.close()  # Ensure the PDF document is closed

        return cls(original_file=str(file_path), contents=contents)

    # --- Stubs for other methods as provided in the prompt ---

    @classmethod
    def from_txt(cls, file_path: FilePath, split_len: int = 5000, overlap: int = 0):
        raise NotImplementedError("from_mp3 is not implemented")

    @classmethod
    def from_png(self, file_path: FilePath):
        raise NotImplementedError("from_png is not implemented")

    @classmethod
    def from_jpg(self, file_path: FilePath):
        raise NotImplementedError("from_jpg is not implemented")

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

# Example Usage (requires a PDF file named 'example.pdf' in the same directory)
if __name__ == '__main__':
    # Create a dummy PDF for testing if one doesn't exist
    dummy_pdf_path = Path("Lecture Material\\Mod 2 HIS & EHR Clinical Functionality-Lecture Slides.pdf")

    if not dummy_pdf_path.exists():
        try:
            doc = fitz.open()  # New empty doc
            page = doc.new_page()
            page.insert_text((50, 72), "This is the first short text block on page 1.")
            # Add more text to test splitting and overlap
            long_text_part1 = " ".join([f"word{i:03}" for i in range(1, 71)])  # 70 words
            page.insert_text((50, 90), long_text_part1)
            page.insert_text((50, 144), "An intermediate block between long texts.")  # ~6 words

            page2 = doc.new_page()
            long_text_part2 = " ".join([f"word{i:03}" for i in range(71, 151)])  # 80 words
            page2.insert_text((50, 72), long_text_part2)
            page2.insert_text((50, 200), "Final text block on page 2, quite short.")  # ~8 words

            doc.save(str(dummy_pdf_path))
            doc.close()
            print(f"Created dummy PDF: {dummy_pdf_path}")
        except Exception as e:
            print(f"Could not create dummy PDF: {e}")
            if not dummy_pdf_path.exists():
                exit(1)

    try:
        # Example: Process the PDF with word count splitting and overlap
        split_words = 50
        overlap_words = 10
        print(f"\nProcessing with split_len={split_words} words, overlap={overlap_words} words...")
        document = Document.from_pdf(dummy_pdf_path, split_len_words=split_words, overlap_words=overlap_words)

        print(f"\n--- Processed Document: {document.original_file} ---")
        print(f"Total chunks: {len(document.contents)}")

        for chunk_id, chunk in sorted(document.contents.items()):  # Sort by ID for predictable output
            print(f"\n--- Chunk ID: {chunk_id} ---")
            print(f"  Type: {chunk.content_type.name}")
            print(f"  Metadata: {chunk.metadata}")
            # print(f"  Content Length (bytes): {len(chunk.content)}")

            if chunk.content_type == DocumentContentType.TEXT:
                text_content = chunk.get_as_string()
                word_count = len(text_content.split())
                print(f"  Word Count: {word_count}")
                # Print first/last few words for overlap check
                words = text_content.split()
                preview_start = " ".join(words[:15])
                preview_end = " ".join(words[-15:])
                if len(words) > 30:
                    print(f"  Content Preview: '{preview_start} ... {preview_end}'")
                else:
                    print(f"  Content: '{text_content}'")

            elif chunk.content_type == DocumentContentType.IMAGE:
                print(f"  Image Content Size: {len(chunk.content)} bytes")

        # Test overlap specifically between first few text chunks if possible
        if len(document.contents) > 1:
            chunk0 = document.contents.get(0)
            chunk1 = document.contents.get(1)
            if chunk0 and chunk1 and chunk0.content_type == DocumentContentType.TEXT and chunk1.content_type == DocumentContentType.TEXT:
                words0 = chunk0.get_as_string().split()
                words1 = chunk1.get_as_string().split()
                print("\n--- Overlap Check (Chunk 0 vs Chunk 1) ---")
                print(f"  Last {overlap_words} words of Chunk 0: {' '.join(words0[-overlap_words:])}")
                print(f"  First {overlap_words} words of Chunk 1: {' '.join(words1[:overlap_words])}")
                if words0[-overlap_words:] == words1[:overlap_words]:
                    print("  Overlap seems correct!")
                else:
                    print("  Overlap MISMATCH detected!")


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