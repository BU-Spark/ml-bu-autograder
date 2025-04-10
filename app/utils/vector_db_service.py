import fnmatch
from typing import Optional, List, Dict, Mapping
import chromadb
import logging

from chromadb import QueryResult
from chromadb.errors import InvalidCollectionException

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient

chroma_instance: Optional["ChromaDBService"] = None

# azure_instance: Optional["AzureVectorService"] = None


# class AzureVectorService:
#     def __init__(self, service_endpoint: str, index_name: str, api_key: str):
#         """
#         Initializes Azure Cognitive Search client.

#         Args:
#             service_endpoint: Azure Search endpoint.
#             index_name: Name of the Azure Search index.
#             api_key: Admin API key.
#         """
#         self.service_endpoint = service_endpoint
#         self.index_name = index_name
#         self.api_key = api_key

#         try:
#             self.client = SearchClient(
#                 endpoint=service_endpoint,
#                 index_name=index_name,
#                 credential=AzureKeyCredential(api_key)
#             )
#             logging.debug(f"Initialized AzureVectorService with index '{index_name}'")
#         except Exception as e:
#             logging.error("Failed to initialize AzureVectorService", exc_info=True)
#             raise

#     def add_vectors(self, documents: List[Dict]):
#         """
#         Uploads documents (with vectors) to Azure Cognitive Search.

#         Args:
#             documents: List of documents with 'id', 'vector', and other metadata.
#         """
#         try:
#             result = self.client.upload_documents(documents=documents)
#             logging.info(f"Uploaded {len(result)} documents to Azure Search.")
#         except Exception as e:
#             logging.error("Failed to upload vectors", exc_info=True)
#             raise

#     def search(self, query_vector: List[float], top_k: int = 3, vector_field_name: str = "vector") -> List[Dict]:
#         """
#         Runs a vector similarity search on the index.

#         Args:
#             query_vector: The input query vector.
#             top_k: Number of top results to return.
#             vector_field_name: The name of the vector field in the index.

#         Returns:
#             List of documents matching the query vector.
#         """
#         try:
#             results = self.client.search(
#             search_text="",
#             vectors=[
#                 {
#                     "value": query_vector,
#                     "k": top_k,
#                     "fields": vector_field_name
#                 }
#             ]
#         )
#             return [doc for doc in results]
#         except Exception as e:
#             logging.error("Vector search failed", exc_info=True)
#             return []

#     def delete_documents_by_ids(self, ids: List[str]):
#         """
#         Deletes documents from the index by their IDs.

#         Args:
#             ids: List of document IDs to delete.
#         """
#         try:
#             documents = [{"id": doc_id} for doc_id in ids]
#             self.client.delete_documents(documents)
#             logging.info(f"Deleted {len(ids)} documents from Azure Search.")
#         except Exception as e:
#             logging.error("Failed to delete documents by ID", exc_info=True)

#     @staticmethod
#     def init_singleton(service_endpoint: str, index_name: str, api_key: str):
#         """Initializes global singleton instance."""
#         global azure_instance
#         if azure_instance is None:
#             azure_instance = AzureVectorService(service_endpoint, index_name, api_key)
#         else:
#             logging.warning("AzureVectorService singleton is already initialized.")

#     @staticmethod
#     def get_instance() -> Optional["AzureVectorService"]:
#         """Retrieves global singleton instance."""
#         global azure_instance
#         if azure_instance is None:
#             logging.error("AzureVectorService instance is not initialized. Call init_singleton first.")
#         return azure_instance


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
