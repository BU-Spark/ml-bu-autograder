"""
This module defines AzureVectorService, a helper class for interacting with Azure Cognitive Search.
It provides functionality to create or verify search indexes, add or delete documents with vector data,
and perform vector-based searches.
"""

import logging
from typing import Optional, List, Mapping, Any
import time 
import requests
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    VectorSearch,
    VectorSearchProfile,
    HnswAlgorithmConfiguration,
    SearchField,
    SimpleField,
    SearchFieldDataType
)
from pydantic import HttpUrl

# Global variable to hold the AzureVectorService singleton instance.
azure_instance: Optional["AzureVectorService"] = None

class AzureVectorService:
    """
    Service for managing vector operations with Azure Cognitive Search.
    
    This class provides methods to verify or create an index, add documents with vector data, delete documents,
    and search for documents using vector similarity.
    """

    def __init__(self, endpoint: str, api_key: str, index_name: str, embedding_dims: int = 1536):
        """
        Initialize a new AzureVectorService instance.

        Args:
            endpoint (str): The Azure Search service endpoint.
            api_key (str): The API key to authenticate with Azure Search.
            index_name (str): The name of the index to use.
            embedding_dims (int, optional): The dimension of the embedding vectors. Defaults to 1536.
        """
        self.endpoint = endpoint
        self.index_name = index_name
        self.embedding_dims = embedding_dims
        self.api_key = api_key

        credential = AzureKeyCredential(api_key)
        self.client = SearchClient(endpoint, index_name, credential=credential)
        self.index_client = SearchIndexClient(endpoint, credential=credential)
        self._verify_or_create_index()

    def _verify_or_create_index(self):
        """
        Verify if the search index exists, and if not, create a new index.

        The method attempts to fetch the index using the provided index name. If it is not found,
        it falls back to creating the index by invoking the _create_index method.
        """
        try:
            index = self.index_client.get_index(self.index_name)
            logging.info(f"✅ Retrieved existing index: {self.index_name}")
        except Exception as e:
            logging.warning(f"Index '{self.index_name}' not found. Creating a new one.")
            self._create_index()

    def _create_index(self):
        """
        Create a new search index with vector search capabilities.

        The index includes:
          - A unique 'id' field.
          - A 'file_path' field (filterable) for storing metadata.
          - A 'content_vector' field (searchable) configured for vector search.
        """
        fields = [
            SimpleField(name="id", type=SearchFieldDataType.String, key=True),
            SimpleField(name="file_path", type=SearchFieldDataType.String, filterable=True),
            SearchField(
                name="content_vector",
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                searchable=True,
                vector_search_dimensions=self.embedding_dims,
                vector_search_profile_name="my-vector-profile"
            )
        ]
        vector_search = VectorSearch(
            profiles=[
                VectorSearchProfile(
                    name="my-vector-profile",
                    algorithm_configuration_name="my-hnsw-config"
                )
            ],
            algorithms=[
                HnswAlgorithmConfiguration(name="my-hnsw-config")
            ]
        )

        index = SearchIndex(name=self.index_name, fields=fields, vector_search=vector_search)
        self.index_client.create_or_update_index(index)
        logging.info(f"✅ Index '{self.index_name}' created successfully.")

    def search_vectors(self, query_vectors: List[List[float]], top_k: int = 5) -> List[List[dict]]:
        """
        Search for documents in the index using a list of query vectors.

        Each query vector is used to perform a vector search, and the top matching documents 
        (with respect to vector similarity) are returned.

        Args:
            query_vectors (List[List[float]]): A list of query vectors.
            top_k (int, optional): The maximum number of results to return per query. Defaults to 5.

        Returns:
            List[List[dict]]: A list where each element is a list of matching document dictionaries containing:
                - id: The document ID.
                - score: The search score.
                - file_path: The associated file path metadata.
                - raw: The full raw search result.
        """
        results_batch = []

        for i, vector in enumerate(query_vectors):
            try:
                search_url = f"{self.endpoint}/indexes/{self.index_name}/docs/search?api-version=2023-07-01-Preview"

                headers = {
                    "Content-Type": "application/json",
                    "api-key": self.api_key
                }

                payload = {
                    "search": "",  # Required for the POST body; empty for pure vector search.
                    "top": top_k,
                    "vector": {
                        "value": vector,
                        "fields": "content_vector",
                        "k": top_k
                    }
                }

                # Remove keys with None values from the payload.
                payload = {k: v for k, v in payload.items() if v is not None}

                response = requests.post(search_url, headers=headers, json=payload)
                response.raise_for_status()

                data = response.json().get("value", [])
                formatted_results = []
                for result in data:
                    formatted_results.append({
                        "id": result.get("id"),
                        "score": result.get("@search.score"),
                        "file_path": result.get("file_path"),
                        "raw": result
                    })

                results_batch.append(formatted_results)
                logging.info(f"🔍 Retrieved {len(formatted_results)} results for vector #{i}.")

            except Exception as e:
                logging.error(f"❌ Error searching vector #{i}: {str(e)}", exc_info=True)
                results_batch.append([])

        return results_batch

    def delete_documents_by_ids(self, ids: List[str]):
        """
        Delete documents from the index using their IDs.

        Args:
            ids (List[str]): A list of document IDs to be deleted from the index.
        """
        try:
            documents = [{"id": doc_id} for doc_id in ids]
            self.client.delete_documents(documents)
            logging.info(f"Deleted {len(ids)} documents from Azure Search.")
        except Exception as e:
            logging.error("Failed to delete documents by ID", exc_info=True)
    

    def add_vectors(self, ids: List[str], vectors: List[List[float]], metadatas: List[Mapping] = None):
        """
        Add documents to the index with their corresponding vector representations and additional metadata.

        Args:
            ids (List[str]): A list of document IDs.
            vectors (List[List[float]]): A list of vectors corresponding to each document.
            metadatas (List[Mapping], optional): A list of metadata dictionaries, one for each document.
                If provided, this metadata will be merged into the document. Defaults to None.
        """
        documents = []
        for i, vector in enumerate(vectors):
            doc = {
                "id": ids[i],
                "content_vector": vector
            }
            if metadatas and metadatas[i]:
                doc.update(metadatas[i])
            documents.append(doc)

        try:
            upload_results = self.client.upload_documents(documents=documents)
            succeeded = [doc.key for doc in upload_results if doc.succeeded]
            failed = [doc.key for doc in upload_results if not doc.succeeded]

            if succeeded:
                logging.info(f"Uploaded documents successfully: {succeeded}")
            if failed:
                logging.error(f"Failed to upload documents: {failed}")
        except Exception as e:
            logging.error(f"Error uploading documents: {str(e)}")
            raise

    @staticmethod
    def init_singleton(endpoint: HttpUrl, api_key: str, index_name: str, embedding_dims: int = 1536):
        """
        Initialize the AzureVectorService singleton.

        If the singleton has not been created, this method instantiates the service. If it already exists,
        a warning is logged.

        Args:
            endpoint (str): The Azure Search service endpoint.
            api_key (str): The API key for accessing Azure Search.
            index_name (str): The name of the index.
            embedding_dims (int, optional): The dimension of the embedding vectors. Defaults to 1536.
        """
        global azure_instance
        if azure_instance is None:
            azure_instance = AzureVectorService(endpoint.encoded_string(), api_key, index_name, embedding_dims)
        else:
            logging.warning("AzureVectorService singleton already initialized.")

    @staticmethod
    def get_instance() -> Optional["AzureVectorService"]:
        """
        Get the singleton instance of AzureVectorService.

        Returns:
            Optional[AzureVectorService]: The instance if initialized, otherwise None.
        """
        global azure_instance
        if azure_instance is None:
            logging.error("AzureVectorService instance not initialized. Call init_singleton first.")
        return azure_instance

    def retrieve_closest_vectors_and_blob_paths(self, query_vector: List[float], top_k: int = 1) -> List[dict]:
        """
        Retrieve the closest matching documents based on the given vector.
        Each result contains only the stored vector and associated metadata,
        which includes the document's id and the blob file path.

        Args:
            query_vector (List[float]): The vector to search with.
            top_k (int, optional): The number of closest results to return. Defaults to 1.

        Returns:
            List[dict]: A list of dictionaries, each containing:
                - content_vector: The stored vector.
                - metadata: A dictionary containing additional metadata such as 'id' and 'file_path'.
        """
        try:
            # Build the search URL for your Azure Search index.
            search_url = f"{self.endpoint}/indexes/{self.index_name}/docs/search?api-version=2023-07-01-Preview"
            headers = {
                "Content-Type": "application/json",
                "api-key": self.api_key
            }
            
            # Construct the payload for a vector search.
            payload = {
                "search": "",  # Must be provided even if not doing a keyword search.
                "top": top_k,
                "vector": {
                    "value": query_vector,
                    "fields": "content_vector",
                    "k": top_k
                }
            }
            payload = {k: v for k, v in payload.items() if v is not None}
            
            # Execute the POST request.
            response = requests.post(search_url, headers=headers, json=payload)
            response.raise_for_status()
            
            # Parse the response and extract only the vector and metadata.
            data = response.json().get("value", [])
            results = []
            for result in data:
                results.append({
                    "content_vector": result.get("content_vector"),
                    "metadata": {
                        "id": result.get("id"),
                        "file_path": result.get("file_path")
                    }
                })
                logging.info(f"Retrieved Document - ID: {result.get('id')}, File Path: {result.get('file_path')}")
                # logging.info(f"Vector score: {result.get("content_vector")}")
            return results
        except Exception as e:
            logging.error("Error retrieving closest vectors: " + str(e), exc_info=True)
            return []
