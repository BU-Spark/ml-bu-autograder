import fnmatch
from typing import Optional, List, Dict, Mapping
import chromadb
import logging

from chromadb import QueryResult
from chromadb.errors import InvalidCollectionException

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import SearchIndex

chroma_instance: Optional["ChromaDBService"] = None

# azure_instance: Optional["AzureVectorService"] = None




class VectorDBService:
    def __init__(self, endpoint: str, api_key: str, index_name: str, vector_field: str):
        self.endpoint = endpoint
        self.index_name = index_name
        self.vector_field = vector_field
        self.api_key = api_key

        credential = AzureKeyCredential(api_key)

        # Client to interact with documents (vectors)
        self.client = SearchClient(endpoint, index_name, credential=credential)
        
        # Client to manage indexes (checking or retrieving vector store)
        self.index_client = SearchIndexClient(endpoint, credential=credential)

        # Verify vector store (index) exists upon initialization
        self._verify_or_retrieve_index()
    
    def _verify_or_retrieve_index(self):
        """Verifies that the vector store index exists and retrieves it."""
        try:
            index: SearchIndex = self.index_client.get_index(self.index_name)
            logging.info(f"✅ Retrieved existing vector store index: '{self.index_name}'")
            # Optional: You could store 'index' object if schema info is needed
        except Exception as e:
            logging.error(f"Vector store index '{self.index_name}' not found: {str(e)}")
            raise

    def add_vectors(self, ids: List[str], vectors: List[List[float]],
                    metadatas: List[Mapping] = None):
        """Adds vectors to a specified collection in batch for higher performance."""
        documents = []
        for i, vector in enumerate(vectors):
            doc = {
                "id": ids[i], 
                self.vector_field: vector
            }
            if metadatas and metadatas[i]:
                doc.update(metadatas[i])
            documents.append(doc)
        try:
            upload_results = self.client.upload_documents(documents=documents)
            succeeded = [doc.key for doc in upload_results if doc.succeeded]
            failed = [doc.key for doc in upload_results if not doc.succeeded]

            if succeeded:
                logging.info(f"Uploaded vectors successfully: {succeeded}")
            if failed:
                logging.error(f"Upload failed for documents: {failed}")

        except Exception as e:
            logging.error(f"Error uploading vectors: {str(e)}")
            raise

    def search(self, query_vectors: List[List[float]], top_k: int = 5) -> QueryResult:
        """Queries the closest vectors from the collection."""
        results_batch = []

        for vector in query_vectors:
            try:
                search_results = self.client.search(
                    search_text="",  # empty required for vector-only search (we can just assume its vector only for now...)
                    vectors=[{
                        "value": vector,
                        "fields": self.vector_field,
                        "k": top_k
                    }]
                )
                results = [dict(result) for result in search_results]
                results_batch.append(results)
                logging.info(f"Retrieved top-{top_k} results for query vector.")
            except Exception as e:
                logging.error(f"Error performing vector search: {str(e)}")
                results_batch.append([])

        return results_batch


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
