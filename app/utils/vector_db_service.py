from typing import Optional, List, Dict, Mapping
import chromadb
import logging

from chromadb import QueryResult
from chromadb.errors import InvalidCollectionException

chroma_instance: Optional["ChromaDBService"] = None


class VectorDBService:

    def add_vectors(self, ids: List[str], vectors: List[List[float]],
                    metadatas: List[Mapping] = None):
        """Adds vectors to a specified collection in batch for higher performance."""
        ...

    def search(self, query_vectors: List[List[float]], top_k: int = 5) -> QueryResult:
        """Queries the closest vectors from the collection."""


class ChromaDBService(VectorDBService):
    def __init__(self, persist_directory: str = "./chroma.db"):
        """
        Initializes ChromaDB service.

        Args:
            persist_directory: Directory where ChromaDB will store data.
        """
        self.client = chromadb.PersistentClient(path=persist_directory)
        try:
            self.collection = self.client.get_collection("ml-bu-autograder")
        except InvalidCollectionException as e:
            self.collection = self.client.create_collection("ml-bu-autograder")
        self.persist_directory = persist_directory
        logging.debug(f"Initialized ChromaDBService with persistence directory {persist_directory}")

    def add_vectors(self, ids: List[str], vectors: List[List[float]],
                    metadatas: List[Mapping] = None):
        """Adds vectors to a specified collection in batch for higher performance."""
        self.collection.add(embeddings=vectors, ids=ids, metadatas=metadatas or [{} for _ in ids])
        logging.debug(f"Added {len(vectors)} vectors to collection with ids {ids}")

    def search(self, query_vectors: List[List[float]], top_k: int = 5) -> QueryResult:
        """Queries the closest vectors from the collection."""
        results = self.collection.query(query_embeddings=query_vectors, n_results=top_k)
        logging.debug(f"Queried {len(results)} vectors from collection")
        # Convert results into
        return results

    @staticmethod
    def init_singleton(persist_directory: str = "./chroma.db"):
        """Initializes global singleton instance."""
        global chroma_instance
        if chroma_instance is None:
            chroma_instance = ChromaDBService(persist_directory)
        else:
            logging.warning("ChromaDBService singleton is already initialized.")

    @staticmethod
    def get_instance() -> Optional["ChromaDBService"]:
        """Retrieves global singleton instance."""
        global chroma_instance
        if chroma_instance is None:
            logging.error("ChromaDBService instance is not initialized. Call init_singleton first.")
        return chroma_instance
