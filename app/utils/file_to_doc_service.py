import fitz  # PyMuPDF
import base64
from typing import Dict, List, Set, Tuple, Any
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
    def from_pdf(cls, file_path: FilePath, split_len: int = 5000, overlap: int = 350) -> "Document":
        """
        Extracts text and images from a PDF file in reading order, chunking text content.

        Args:
            file_path: Path to the PDF file.
            split_len: Maximum character length for text chunks. Chunks are created when
                       this length is reached, an image is encountered, or the document ends.
            overlap: Currently unused for PDF processing. A warning will be printed if non-zero.

        Returns:
            A Document object containing extracted and chunked content.

        Raises:
            FileNotFoundError: If the file_path does not exist.
            Exception: For errors during PDF processing.
        """
        if not Path(file_path).exists():
             raise FileNotFoundError(f"No such file: {file_path}")

        if overlap != 0:
            # Overlap isn't naturally handled by this modality-change/length-based splitting.
            # Could be implemented by taking `overlap` chars from the *previous* chunk,
            # but that complicates page number tracking significantly. Sticking to requirements.
            print(f"Warning: Non-zero overlap ({overlap}) requested, but overlap is not "
                  f"currently implemented for PDF text chunking in this method.")


        contents: Dict[int, DocumentChunk] = {}
        chunk_id_counter = 0
        current_text_buffer = ""
        # Keep track of all pages contributing to the current text buffer
        current_text_pages: Set[int] = set()

        doc = None
        try:
            doc = fitz.open(str(file_path)) # PyMuPDF needs a string path

            for page_num_zero_based, page in enumerate(doc):
                page_num_one_based = page_num_zero_based + 1

                # --- Get page items (text blocks and images) ---
                page_items: List[Dict[str, Any]] = []

                # 1. Get text blocks using get_text("blocks") which includes basic sorting
                text_blocks = page.get_text("blocks")
                for tb in text_blocks:
                    x0, y0, x1, y1, text_content, block_no, block_type = tb
                    # Basic check to ignore blocks with no real text content
                    if text_content.strip():
                         page_items.append({
                             'type': 'text',
                             'bbox': (x0, y0, x1, y1), # Store bbox for sorting
                             'content': text_content,
                             'page': page_num_one_based
                         })

                # 2. Get image info and try to find their bounding boxes on the page
                image_info_list = page.get_images(full=True)
                processed_xrefs = set() # Avoid processing same image multiple times if listed strangely
                for img_info in image_info_list:
                    xref = img_info[0]
                    if xref in processed_xrefs:
                        continue

                    try:
                        # get_image_bbox can fail for some image types/placements
                        img_bbox_rect = page.get_image_bbox(img_info)
                        if not img_bbox_rect or not img_bbox_rect.is_valid or img_bbox_rect.is_empty:
                            # If bbox invalid/unavailable, we can't reliably sort it.
                            # Option 1: Skip. Option 2: Add without bbox (will sort poorly).
                            # Let's try to extract image but maybe log warning about placement.
                            print(f"Warning: Could not get valid bbox for image xref {xref} on page {page_num_one_based}. Order may be affected.")
                            # Use a default bbox that likely sorts it after text? Or skip sorting?
                            # For now, let's proceed but be aware ordering might be off.
                            # We still need *some* bbox for sorting key. Use page bounds? Risky.
                            # Let's try using a placeholder bbox based on image index? No, stick to available.
                            # If bbox is invalid, maybe skip adding it to sortable items for now.
                            # Alternative: Use page.get_text("dict") which might embed image bbox info better.
                            # Sticking with current approach: if no valid bbox, maybe skip adding to page_items for sorting.
                            continue # Skip adding image if bbox is unreliable for sorting

                        img_bbox = tuple(img_bbox_rect) # Convert fitz.Rect to tuple

                        # Extract image bytes
                        base_image = doc.extract_image(xref)
                        if base_image and base_image.get("image"): # Check extraction success and content
                            img_bytes = base_image["image"]
                            page_items.append({
                                'type': 'image',
                                'bbox': img_bbox,
                                'content': img_bytes,
                                'page': page_num_one_based,
                                'xref': xref # Optional: keep for metadata/debugging
                            })
                            processed_xrefs.add(xref)
                        else:
                             print(f"Warning: Could not extract image bytes for xref {xref} on page {page_num_one_based}.")

                    except Exception as e:
                        # Catch potential errors during bbox finding or extraction
                        print(f"Warning: Error processing image xref {xref} on page {page_num_one_based}: {e}")


                # --- Sort items based on reading order heuristic (top-to-bottom, left-to-right) ---
                page_items.sort(key=lambda item: (item['bbox'][1], item['bbox'][0])) # Sort by y0 then x0

                # --- Process sorted items to create chunks ---
                for item in page_items:
                    item_page = item['page']

                    if item['type'] == 'text':
                        # Append text content. Add a newline separator between blocks for readability.
                        current_text_buffer += item['content'] + "\n"
                        current_text_pages.add(item_page)

                        # Check if buffer exceeds split_len and create chunks
                        while len(current_text_buffer) >= split_len:
                            chunk_text = current_text_buffer[:split_len]
                            chunk_bytes = chunk_text.encode("utf-8")
                            metadata = {'page_num': sorted(list(current_text_pages))}

                            contents[chunk_id_counter] = DocumentChunk(
                                content_type=DocumentContentType.TEXT,
                                content=chunk_bytes,
                                metadata=metadata
                            )
                            chunk_id_counter += 1

                            # Update buffer with remainder
                            current_text_buffer = current_text_buffer[split_len:]
                            # Reset pages for the *next* chunk? No, the remainder might still
                            # contain text from previous pages. Only add *new* pages as they
                            # contribute text to the *updated* buffer.
                            # However, the pages contributing *just* to the remainder start *at least*
                            # with the current page.
                            # Let's clear and add current page - simpler tracking for next chunk start.
                            # If a split happens mid-page, this is fine. If it happens across pages,
                            # the next chunk correctly starts associating with the current page.
                            current_text_pages = {item_page} # Reset pages for the remaining buffer part


                    elif item['type'] == 'image':
                        # 1. Finalize any pending text chunk before the image
                        # Strip() ensures we don't create empty chunks from whitespace buffers
                        trimmed_text_buffer = current_text_buffer.strip()
                        if trimmed_text_buffer:
                            chunk_bytes = trimmed_text_buffer.encode("utf-8")
                            # Use the pages collected *before* resetting due to split
                            metadata = {'page_num': sorted(list(current_text_pages))}
                            contents[chunk_id_counter] = DocumentChunk(
                                content_type=DocumentContentType.TEXT,
                                content=chunk_bytes,
                                metadata=metadata
                            )
                            chunk_id_counter += 1

                        # Reset text buffer and associated pages *after* creating the text chunk
                        current_text_buffer = ""
                        current_text_pages = set()

                        # 2. Create the image chunk
                        img_bytes = item['content']
                        # Image metadata typically just includes the page it was found on
                        metadata = {'page_num': [item_page]}
                        # Optional: add more metadata like bbox if needed later
                        # metadata['bbox'] = item['bbox']
                        # metadata['xref'] = item['xref']

                        contents[chunk_id_counter] = DocumentChunk(
                            content_type=DocumentContentType.IMAGE,
                            content=img_bytes,
                            metadata=metadata
                        )
                        chunk_id_counter += 1

            # --- After processing all pages, check for any remaining text ---
            trimmed_text_buffer = current_text_buffer.strip()
            if trimmed_text_buffer:
                chunk_bytes = trimmed_text_buffer.encode("utf-8")
                metadata = {'page_num': sorted(list(current_text_pages))}
                contents[chunk_id_counter] = DocumentChunk(
                    content_type=DocumentContentType.TEXT,
                    content=chunk_bytes,
                    metadata=metadata
                )
                # chunk_id_counter += 1 # Not strictly needed for last chunk id

        except fitz.FileNotFoundError:
             # This might be caught by the initial Path check, but good practice
             raise FileNotFoundError(f"PyMuPDF could not find or open file: {file_path}")
        except Exception as e:
            # Catch other PyMuPDF or processing errors
            print(f"An error occurred during PDF processing: {e}")
            # Depending on requirements, either raise, return partial, or empty.
            # Raising seems appropriate for unexpected errors.
            raise RuntimeError(f"Failed to process PDF {file_path}: {e}") from e
        finally:
            if doc:
                doc.close() # Ensure the PDF document is closed

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
    def from_doc(cls, file_path: FilePath, split_len: int = 5000, overlap: int = 0):
        raise NotImplementedError("from_doc is not implemented")

# Example Usage (requires a PDF file named 'example.pdf' in the same directory)
if __name__ == '__main__':
    # Create a dummy PDF for testing if one doesn't exist
    dummy_pdf_path = Path("Lecture Material\\Mod 2 HIS & EHR Clinical Functionality-Lecture Slides.pdf")

    try:
        # Example: Process the PDF with a small split length to test chunking
        document = Document.from_pdf(dummy_pdf_path, split_len=500)

        print(f"\n--- Processed Document: {document.original_file} ---")
        print(f"Total chunks: {len(document.contents)}")

        for chunk_id, chunk in document.contents.items():
            print(f"\n--- Chunk ID: {chunk_id} ---")
            print(f"  Type: {chunk.content_type.name}")
            print(f"  Metadata: {chunk.metadata}")
            print(f"  Content Length (bytes): {len(chunk.content)}")

            if chunk.content_type == DocumentContentType.TEXT:
                # Print first 100 chars of text content
                print(f"  Content Preview: '{chunk.get_as_string()}'")
            elif chunk.content_type == DocumentContentType.IMAGE:
                # Print image info (base64 for brevity is too long, just size)
                 print(f"  Image Content Size: {len(chunk.content)} bytes")

    except FileNotFoundError as e:
        print(e)
    except NotImplementedError as e:
        print(e)
    except Exception as e:
        print(f"An unexpected error occurred during example usage: {e}")