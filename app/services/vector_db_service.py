import fnmatch
import json
from typing import Optional, List, Dict, Mapping

import chromadb
import logging

import requests
from chromadb import QueryResult
from chromadb.errors import InvalidCollectionException

from pydantic import FilePath

chroma_instance: Optional["ChromaDBService"] = None


class VectorDBService:

    def add_vectors(self, course_semester: str, course_id: str,
                    document_ids: List[str], vectors: List[List[float]],
                    metadatas: List[Mapping] = None):
        ...

    def add_vector(self, course_semester: str, course_id: str, id: str, vector: List[float]):
        self.add_vectors(course_semester, course_id, [id], [vector])

    def search(self, course_semester: str, course_id: str,
               query_vectors: List[List[float]], top_k: int = 5) -> QueryResult:
        ...

    def delete_course(self, course_semester: str, course_id: str):
        ...

    def delete_collection(self):
        ...

    def delete_items_by_wildcard(self, pattern: str):
        ...


class ChromaDBService(VectorDBService):
    def __init__(self, persist_directory: FilePath = FilePath("./chroma.db")):
        """
        Initializes ChromaDB service.

        Args:
            persist_directory: Directory where ChromaDB will store data.
        """
        self.client = chromadb.PersistentClient(path=str(persist_directory))
        try:
            self.collection = self.client.get_collection("ml-bu-autograder")
        except InvalidCollectionException as e:
            self.collection = self.client.create_collection("ml-bu-autograder")
        self.persist_directory = persist_directory
        logging.debug(f"Initialized ChromaDBService with persistence directory {persist_directory}")

    def add_vectors(self, course_semester: str, course_id: str,
                    document_ids: List[str], vectors: List[List[float]],
                    metadatas: List[Mapping] = None):
        """Adds vectors to a specified collection in batch for higher performance."""
        self.collection.add(
            embeddings=vectors,
            ids=document_ids,
            metadatas={
                "semester": course_semester,
                "course_id": course_id,
            }
        )
        logging.debug(f"Added {len(vectors)} vectors to collection with ids {document_ids}")

    def search(self, course_semester: str, course_id: str,
               query_vectors: List[List[float]], top_k: int = 5) -> QueryResult:
        """Queries the closest vectors from the collection."""
        results = self.collection.query(
            query_embeddings=query_vectors,
            n_results=top_k,
            where={
                "semester": course_semester,
                "course_id": course_id,
            },
        )
        logging.debug(f"Queried {len(results)} vectors from collection")
        # Convert results into
        return results

    def delete_course(self, course_semester: str, course_id: str):
        self.collection.delete(
            where={
                "course_id": course_semester,
                "course_semester": course_id
            }
        )

    def delete_collection(self):
        """
        Deletes the entire collection.
        """
        try:
            # Assuming the client provides a method to delete a collection by name.
            self.client.delete_collection("ml-bu-autograder")
            logging.info("Deleted entire collection 'ml-bu-autograder'.")
        except Exception as e:
            logging.error("Failed to delete collection", exc_info=True)

    def delete_items_by_wildcard(self, pattern: str):
        """
        Deletes items from the collection whose IDs match a given wildcard pattern.

        Args:
            pattern: A wildcard pattern (e.g. "doc1:*:text") to match item IDs.
        """
        try:
            # Retrieve all items from the collection.
            results = self.collection.get()
            all_ids = []
            # The returned IDs might be a list of lists.
            if "ids" in results:
                for sublist in results["ids"]:
                    all_ids.extend(sublist)
            # Use fnmatch to filter the IDs by the provided wildcard pattern.
            matching_ids = [id for id in all_ids if fnmatch.fnmatch(id, pattern)]
            if matching_ids:
                self.collection.delete(ids=matching_ids)
                logging.info(f"Deleted items matching pattern '{pattern}': {matching_ids}")
            else:
                logging.info(f"No items matching pattern '{pattern}' were found.")
        except Exception as e:
            logging.error("Failed to delete items by wildcard", exc_info=True)

    @staticmethod
    def init_singleton(persist_directory: FilePath = FilePath("./chroma.db")):
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
