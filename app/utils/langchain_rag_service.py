import base64
import logging
from typing import List, Optional

from azure.ai.inference import EmbeddingsClient, ImageEmbeddingsClient
from azure.ai.inference.models import ImageEmbeddingInput, EmbeddingInputType
from azure.core.credentials import AzureKeyCredential
from langchain.text_splitter import RecursiveCharacterTextSplitter

import fitz
from app.utils import VectorDBService


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
                 chunk_size: int = 500,
                 chunk_overlap: int = 50):
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
        metadatas = [{"data": chunk, "overlap": self.chunk_overlap} for i, chunk in enumerate(chunks)]

        ids = []
        for chunk_num in chunk_nums:
            ids.append(f"{doc_id}:{chunk_num}:text")
        self.db.add_vectors(ids=ids, vectors=vectors, metadatas=metadatas)

    def upload_image(self):
        ...

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
        sorted_results = []
        for id, distance, metadata in zip(results['ids'][0], results['distances'][0], results['metadatas'][0]):
            sorted_results.append(
                {
                    'id': id,
                    'distances': distance,
                    'data': metadata["data"],
                    'overlap': int(metadata["overlap"]),
                }
            )
        sorted_results = sorted(sorted_results, key=lambda x: x['id'])

        rag_context_string = ""
        for i in range(len(sorted_results)):
            rag_context_string += f"Document ID: \"{sorted_results[i]['id']}\"\n"
            if i == 0:
                rag_context_string += sorted_results[i]["data"]
            elif sorted_results[i]['overlap'] == 0:
                rag_context_string += sorted_results[i]['text']
            else:
                # if two consecutive elements are from the same doc and consecutive
                # chunks then trim according to chunk overlap
                prev_doc_parts = sorted_results[i - 1]['id'].split(":")
                prev_doc_name = prev_doc_parts[0]
                prev_doc_chunk = int(prev_doc_parts[1])
                current_doc_parts = sorted_results[i]["id"].split(":")
                current_doc_name = current_doc_parts[0]
                current_doc_chunk = int(current_doc_parts[1])
                if prev_doc_name == current_doc_name and prev_doc_chunk == current_doc_chunk - 1:
                    rag_context_string += sorted_results[i]["data"][self.chunk_overlap:]
            rag_context_string += "\n----------\n"

        return rag_context_string

    def upload_pdf(self, doc_id: str, pdf_path: str):
        """
        Processes a PDF with both text and figures, extracts and embeds content,
        and uploads the embeddings to the vector DB.

        Args:
            doc_id: Unique identifier for the document.
            pdf_path: Path to the PDF file.
        """
        # Open the PDF using PyMuPDF
        doc = fitz.open(pdf_path)
        doc_ids = []

        metadatas = []
        # Iterate through pages
        for page_num, page in enumerate(doc):
            # Extract text
            page_text = page.get_text()
            doc_ids.append(f"{doc_id}:{page_num}:text:0")
            metadatas.append({
                "data": page_text,
                "overlap": 0,
            })
            # Extract images
            image_list = page.get_images(full=True)
            for img_index, img in enumerate(image_list):
                xref = img[0]
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                base64_str = base64.b64encode(image_bytes).decode("utf-8")

                doc_ids.append(f"{doc_id}:{page_num}:image:{img_index}")
                metadatas.append({
                    "data": page_text,
                    "overlap": 0,
                })
                image_items.append({
                    "image": base64_str,
                    "page": page_num,
                    "type": "image",
                })

        # Create embeddings for text
        if text_chunks:
            text_embeddings = self.embedding_model.embed_text(
                texts=[item["data"] for item in text_chunks],
                purpose=EmbeddingInputType.TEXT
            )
        else:
            text_embeddings = []

        # Create embeddings for images
        image_embeddings = []
        for item in image_items:
            emb = self.embedding_model.embed_image(
                image_format="png",  # Adjust the format as needed.
                base_64_image=item["image"],
                text=item.get("caption", "")
            )
            image_embeddings.append(emb)

        # Prepare ids and metadata for both text and images.
        ids = []
        vectors = []
        metadatas = []
        # For text chunks
        for i, item in enumerate(text_chunks):
            ids.append(f"{doc_id}:text:{i}")
            vectors.append(text_embeddings[i])
            metadatas.append({
                "text": item["text"],
                "page": item["page"],
                "type": "text",
                "overlap": self.chunk_overlap
            })
        # For images
        offset = len(text_chunks)
        for i, item in enumerate(image_items):
            ids.append(f"{doc_id}:image:{i}")
            vectors.append(image_embeddings[i])
            metadatas.append({
                "page": item["page"],
                "type": "image"
            })

        # Upload all embeddings to the vector DB.
        self.db.add_vectors(ids=ids, vectors=vectors, metadatas=metadatas)
        logging.info(f"Uploaded PDF '{doc_id}' with {len(text_chunks)} text chunks and {len(image_items)} images.")

    @classmethod
    def init_singleton(cls,
                       db: VectorDBService,
                       embedding_model: AzureEmbeddingModel,
                       chunk_size: int = 500,
                       chunk_overlap: int = 50):
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
