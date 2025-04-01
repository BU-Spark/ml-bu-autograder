import base64
import json
import logging
from enum import Enum
from typing import List, Optional, Dict

from azure.ai.inference import EmbeddingsClient, ImageEmbeddingsClient
from azure.ai.inference.models import ImageEmbeddingInput, EmbeddingInputType
from azure.core.credentials import AzureKeyCredential
from langchain.text_splitter import RecursiveCharacterTextSplitter

import fitz
from app.utils import VectorDBService


class DataType(Enum):
    """
    Enum for different data types supported by the embedding model.
    """

    # Means that the data is from raw, stand-alone text
    RAW_TEXT = "raw/text"
    # Means that data is from raw, stand-alone image
    RAW_IMAGE = "raw/image"
    # Means that data is text from a PDF file
    PDF_TEXT = "pdf/text"
    # Means that data is an image from a PDF file
    PDF_IMAGE = "pdf/image"


class AzureEmbeddingModel:
    def __init__(self, azure_endpoint: str, azure_key: str, model: str):
        self.text_client = EmbeddingsClient(
            endpoint=azure_endpoint,
            credential=AzureKeyCredential(azure_key),
            model=model
        )
        self.image_client = ImageEmbeddingsClient(
            endpoint=azure_endpoint,
            credential=AzureKeyCredential(azure_key),
            model=model
        )
        self.model = model

    def embed_text(self, texts: List[str], purpose: EmbeddingInputType) -> List[List[float]]:
        response = self.text_client.embed(
            input=texts,
            model=self.model,
            input_type=purpose
        )
        return [item.embedding for item in response.data]

    def embed_image(self, image_format: str, base_64_image: str, text: Optional[str]) -> List[float]:
        input_image = ImageEmbeddingInput(image=f"data:image/{image_format};base64,{base_64_image}", text=text)
        response = self.image_client.embed(
            input=[input_image],
            model=self.model,
        )
        return [item.embedding for item in response.data][0]


class LangchainRAGService:
    _instance = None

    def __init__(self,
                 db: VectorDBService,
                 embedding_model: AzureEmbeddingModel,
                 chunk_size: int = 2500,
                 chunk_overlap: int = 250,
                 min_image_pixels: int = 240):
        """
        Initializes the Langchain RAG Service.

        Args:
            db: Instance of ChromaDBService.
            embedding_model: The embedding model to use.
            chunk_size: Maximum size of each text chunk.
            chunk_overlap: Number of overlapping characters between chunks.
        """
        self.db = db
        self.embedding_model = embedding_model
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_image_pixels = min_image_pixels
        logging.debug(f"LangchainRAGService initialized with DB: {db} and embedding model: {embedding_model}")

    def _split_document(self, text: str) -> List[str]:
        """
        Splits the input text into chunks.

        Args:
            text: The full document text.

        Returns:
            A list of text chunks.
        """
        splitter = RecursiveCharacterTextSplitter(chunk_size=self.chunk_size, chunk_overlap=self.chunk_overlap)
        return splitter.split_text(text)

    def upload_document(self, doc_id: str, text: str):
        """
        Splits the document into chunks, embeds them, and uploads to the ChromaDB.

        Args:
            doc_id: Unique identifier for the document.
            text: The full document text.
        """
        chunks = self._split_document(text)
        vectors = self.embedding_model.embed_text(texts=chunks, purpose=EmbeddingInputType.TEXT)
        chunk_nums = list(range(len(chunks)))
        # TODO: remove, the actual text should probably be stored in blob storage
        #  this is temp for the POC
        metadatas = [{"data": chunk, "overlap": self.chunk_overlap, "type": DataType.RAW_TEXT.value} for i, chunk in
                     enumerate(chunks)]

        ids = []
        for chunk_num in chunk_nums:
            ids.append(f"{doc_id}:{chunk_num}:text")
        self.db.add_vectors(ids=ids, vectors=vectors, metadatas=metadatas)

    def upload_image(self, doc_id: str, base64_image_data: str):
        """
        Uploads an image to the vector DB.
        Args:
            doc_id: Unique identifier for the document.
            base64_image_data: Base64 encoded image data.
        """
        image_embedding = self.embedding_model.embed_image(
            image_format="png",
            base_64_image=base64_image_data,
            text=""
        )
        self.db.add_vectors(
            ids=[f"{doc_id}:0:image"],
            vectors=[image_embedding],
            metadatas=[{"type": DataType.RAW_IMAGE.value}])
        logging.info(f"Uploaded image for document '{doc_id}'.")

    def retrieve(self, query: str, top_k: int = 3) -> str:
        """
        Embeds a query and retrieves the top-k most similar document chunks from the DB.

        Args:
            query: The search query string.
            top_k: Number of results to retrieve.

        Returns:
            The search results from ChromaDBService.
        """
        query_vector = self.embedding_model.embed_text(texts=[query], purpose=EmbeddingInputType.QUERY)
        results = self.db.search(query_vectors=query_vector, top_k=top_k)
        logging.info(f"Retrieved {len(results)} result(s) for query '{query}'.")
        return results

    def _create_pdf_text_chunks(self, page_texts: Dict[int, str], chunk_size: int) -> List[Dict]:
        """
        Custom logic to chunk PDF text, respecting page boundaries for metadata.

        Args:
            page_texts: Dictionary mapping page_num (int) to page text (str).
            chunk_size: The target maximum size for each chunk.

        Returns:
            A list of dictionaries, each containing 'text' and 'page_map'.
        """
        final_chunks = []
        current_chunk_text = ""
        current_page_map: Dict[int, str] = {}

        sorted_page_nums = sorted(page_texts.keys())

        for page_num in sorted_page_nums:
            page_text = page_texts[page_num].strip()  # Work with stripped text
            if not page_text:
                continue  # Skip empty pages

            remaining_page_text = page_text
            while remaining_page_text:
                space_left = chunk_size - len(current_chunk_text)

                # If the current chunk is full or can't even hold a single char, finalize it
                if space_left <= 0:
                    if current_chunk_text:  # Avoid adding empty chunks
                        final_chunks.append({
                            "text": current_chunk_text,
                            "page_map": current_page_map.copy()  # Use copy!
                        })
                    current_chunk_text = ""
                    current_page_map = {}
                    space_left = chunk_size  # Reset space for the new chunk

                # Determine the text portion to add from the current page
                # Take up to space_left characters
                can_add_len = min(len(remaining_page_text), space_left)
                portion_to_add = remaining_page_text[:can_add_len]

                # Add the portion to the current chunk
                # Add a space separator ONLY if the chunk already has content
                separator = " " if current_chunk_text else ""
                current_chunk_text += separator + portion_to_add

                # Update the page map for the current page number
                if page_num not in current_page_map:
                    current_page_map[page_num] = portion_to_add
                else:
                    # Append using the same separator logic
                    current_page_map[page_num] += separator + portion_to_add

                # Update the remaining text from the page
                remaining_page_text = remaining_page_text[can_add_len:]

                # Optional: Check if chunk is *exactly* full now, could finalize
                # if len(current_chunk_text) >= chunk_size: # Or just == chunk_size
                #    # This might create slightly more chunks but ensures max size isn't exceeded
                #    final_chunks.append({"text": current_chunk_text, "page_map": current_page_map.copy()})
                #    current_chunk_text = ""
                #    current_page_map = {}
                #    # Note: If we finalize here, the `while remaining_page_text` loop
                #    # continues and will immediately start a new chunk in the next iteration.

        # Add the last chunk if it has any content
        if current_chunk_text:
            final_chunks.append({
                "text": current_chunk_text,
                "page_map": current_page_map
            })

        logging.info(f"Custom chunking created {len(final_chunks)} text chunks.")
        return final_chunks

    # TODO: add parallelization because we spend forever waiting for api
    def upload_pdf(self, doc_id: str, pdf_path: str):
        """
        Processes PDF: Extracts text/images. Uses custom logic to chunk text,
        creating accurate page_map metadata.

        AI generated. Prompt used:
        Add an upload_pdf method using fitz. The method has the following requirements:
        You should combine the text of the PDF and and chunk it up.
        The method should also extract images in the pdf.
        The metadata for the text should include a dict containing a mapping between the page number the text from the chunk was on and the text on that page. This is because a chunk may span multiple pages.
        Similarly, each image should have a metadata indicating the page the image was on.
        Remember to account for the fact that when we chunk images there may or may not be some overlap. Might that affect your solution?
        ...
        With your current approach, even if a page contains very little text, it gets its own entire chunk. This doesn't seem right.
        ...
        how about instead of trying to use RecursiveCharacterTextSplitter we create our own splitting logic as well. this is significantly simplify all challanges


        Args:
            doc_id: Unique identifier for the PDF document.
            pdf_path: Path to the PDF file.
        """
        logging.info(f"Starting PDF processing (Custom Chunker) for doc '{doc_id}' @ '{pdf_path}'.")
        page_texts: Dict[int, str] = {}
        images_data: List[Dict] = []
        skipped_image_count = 0

        try:
            doc = fitz.open(pdf_path)
            logging.debug(f"Opened PDF '{pdf_path}' with {len(doc)} pages.")

            # 1. Extract Page Texts & Images
            for page_num, page in enumerate(doc):  # page_num is 0-based
                text = page.get_text("text", sort=True)
                if text:
                    page_texts[page_num] = text  # Keep original spacing for now, strip in chunker

                # Extract images (same logic as before)
                page_images = page.get_images(full=True)
                for img_index, img_info in enumerate(page_images):
                    xref = img_info[0]
                    try:
                        base_image = doc.extract_image(xref)
                        # *** Add size check here ***
                        img_width = base_image["width"]
                        img_height = base_image["height"]
                        if img_width*img_height < self.min_image_pixels:
                            logging.debug(
                                f"Skipping small image {img_index} on page {page_num} (xref: {xref}, size: {img_width}x{img_height})")
                            skipped_image_count += 1
                            continue  # Skip to the next image
                        images_data.append({
                            "page_num": page_num, "image_bytes": base_image["image"],
                            "ext": base_image["ext"], "xref": xref, "index_on_page": img_index
                        })
                    except Exception as img_exc:
                        logging.warning(
                            f"Could not extract image {img_index} (xref: {xref}) on page {page_num}: {img_exc}")

            if skipped_image_count > 0:
                logging.info(f"Skipping {skipped_image_count} images because of small image size.")
            doc.close()
            logging.debug(f"PDF closed. Extracted text from {len(page_texts)} pages and {len(images_data)} images.")

            # --- Text Processing using Custom Chunker ---
            if page_texts:
                # 2. Create Chunks using the custom logic
                custom_chunks_data = self._create_pdf_text_chunks(page_texts, self.chunk_size)

                # 3. Embed and Upload Final Text Chunks
                if custom_chunks_data:
                    texts_to_embed = [chunk["text"] for chunk in custom_chunks_data]
                    # Ensure we handle the case where embedding returns fewer vectors than expected
                    try:
                        text_vectors = self.embedding_model.embed_text(texts=texts_to_embed,
                                                                       purpose=EmbeddingInputType.DOCUMENT)
                    except Exception as embed_err:
                        logging.error(f"Text embedding failed for {doc_id}: {embed_err}", exc_info=True)
                        text_vectors = []  # Ensure upload doesn't proceed with mismatched data

                    if text_vectors and len(text_vectors) == len(custom_chunks_data):
                        text_metadatas = []
                        text_ids = []
                        for i, chunk_data in enumerate(custom_chunks_data):
                            metadata = {
                                "source_doc_id": doc_id,
                                "chunk_num": i,
                                "page_map_json": json.dumps(chunk_data["page_map"]),  # The accurately constructed map
                                "type": DataType.PDF_TEXT.value,
                                "chunk_length": len(chunk_data["text"])  # Store length
                            }
                            text_metadatas.append(metadata)
                            text_ids.append(f"{doc_id}:{i}:text")

                        self.db.add_vectors(ids=text_ids, vectors=text_vectors, metadatas=text_metadatas)
                        logging.info(
                            f"Uploaded {len(text_ids)} PDF text chunks for document '{doc_id}' using custom chunker.")
                    elif custom_chunks_data:  # Only log error if we expected vectors but didn't get matching count
                        logging.error(
                            f"Mismatch or failure during embedding: {len(custom_chunks_data)} chunks generated, but {len(text_vectors) if text_vectors else 0} vectors obtained for '{doc_id}'. Upload aborted.")
                else:
                    logging.info(f"No text chunks generated by custom chunker for '{doc_id}'.")
            else:
                logging.warning(f"No text content extracted from PDF '{doc_id}'.")

            # --- Image Processing (remains the same) ---
            if images_data:
                # ... (image embedding and upload logic is identical to previous versions) ...
                image_vectors = []
                image_metadatas = []
                image_ids = []
                logging.debug(f"Embedding {len(images_data)} images for '{doc_id}'.")
                for idx, img_data in enumerate(images_data):
                    try:
                        base64_image = base64.b64encode(img_data["image_bytes"]).decode('utf-8')
                        img_vector = self.embedding_model.embed_image(
                            image_format=img_data["ext"], base_64_image=base64_image, text=None
                        )
                        image_vectors.append(img_vector)
                        metadata = {
                            "source_doc_id": doc_id,
                            "page": img_data["page_num"],
                            "image_index_on_page": img_data["index_on_page"],
                            "xref": img_data["xref"],
                            "data": base64_image,
                            "type": DataType.PDF_IMAGE.value
                        }
                        image_metadatas.append(metadata)
                        image_ids.append(f"{doc_id}:{img_data['page_num']}:{img_data['index_on_page']}:image")
                    except Exception as embed_err:
                        logging.error(
                            f"Failed to process or embed image {idx} (page {img_data['page_num']}, xref {img_data['xref']}) for doc '{doc_id}': {embed_err}",
                            exc_info=True)

                if image_vectors:
                    self.db.add_vectors(ids=image_ids, vectors=image_vectors, metadatas=image_metadatas)
                    logging.info(f"Uploaded {len(image_ids)} PDF images for document '{doc_id}'.")
                else:
                    logging.warning(f"No images were successfully embedded for upload from '{doc_id}'.")
            else:
                logging.info(f"No images found or extracted from PDF '{doc_id}'.")


        except FileNotFoundError:
            logging.error(f"PDF file not found at path: {pdf_path}")
        except fitz.FileDataError as pdf_err:
            logging.error(f"Error processing PDF file '{pdf_path}' for doc '{doc_id}': {pdf_err}", exc_info=True)
        except Exception as e:
            logging.error(f"An unexpected error occurred during PDF processing for doc '{doc_id}': {e}", exc_info=True)

    @classmethod
    def init_singleton(cls,
                       db: VectorDBService,
                       embedding_model: AzureEmbeddingModel,
                       chunk_size: int = 2500,
                       chunk_overlap: int = 250):
        """
        Initializes the singleton instance of LangchainRAGService.
        If an instance already exists, a warning is logged.

        Args:
            db: Instance of ChromaDBService.
            embedding_model: Embedding model to use.
            chunk_size: Maximum size of text chunks.
            chunk_overlap: Overlap between chunks.

        Returns:
            The singleton instance of LangchainRAGService.
        """
        if cls._instance is None:
            cls._instance = cls(db, embedding_model, chunk_size, chunk_overlap)
            logging.debug("LangchainRAGService singleton created.")
        else:
            logging.warning("LangchainRAGService singleton is already initialized.")
        return cls._instance

    @classmethod
    def get_instance(cls) -> Optional["LangchainRAGService"]:
        """
        Retrieves the singleton instance of LangchainRAGService.

        Returns:
            The singleton instance if initialized, otherwise logs an error.
        """
        if cls._instance is None:
            logging.error("LangchainRAGService is not initialized. Call init_singleton first.")
        return cls._instance
