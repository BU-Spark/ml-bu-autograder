"""
This module implements AzureVectorService to interact with Azure Search for vector operations.
It includes functionality to create or verify search indexes, add documents with vector data,
delete documents, and perform vector-based searches using Azure Cognitive Search.
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

# Global instance for the singleton pattern.
azure_instance: Optional["AzureVectorService"] = None

class AzureVectorService:
    """
    A service for interacting with Azure Cognitive Search to store and retrieve vector data.
    
    This class provides methods to create/search/delete documents with vector representations
    and is designed to be used as a singleton.
    """
    
    def __init__(self, endpoint: str, api_key: str, index_name: str, embedding_dims: int = 1536):
        """
        Initialize a new instance of AzureVectorService.
        
        Args:
            endpoint (str): The Azure Search service endpoint URL.
            api_key (str): The API key for Azure Search.
            index_name (str): The name of the index to use for vector operations.
            embedding_dims (int, optional): Dimensionality of the embedding vectors. Defaults to 1536.
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
        Verify the existence of the search index. If it does not exist, create a new one.
        
        This method attempts to retrieve the specified index from the Azure Search service.
        If unsuccessful, it falls back to creating a new index.
        """
        try:
            index = self.index_client.get_index(self.index_name)
            logging.info(f"✅ Retrieved existing index: {self.index_name}")
        except Exception as e:
            logging.warning(f"Index '{self.index_name}' not found. Creating a new one.")
            self._create_index()

    def _create_index(self):
        """
        Create the search index with the required fields and vector search configuration.
        
        The created index includes:
         - A unique 'id' field.
         - A 'file_path' field for filtering.
         - A 'content_vector' field to store the vector representation and support vector search.
         
        It also sets up vector search using a defined HNSW algorithm configuration.
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
        Search for documents in the index using vector similarity.
        
        Args:
            query_vectors (List[List[float]]): A list of query vectors to search with.
            top_k (int, optional): Number of top results to retrieve for each vector search. Defaults to 5.
        
        Returns:
            List[List[dict]]: A list where each element is a list of dictionaries containing
            document details such as 'id', 'score', 'file_path', and the complete raw result.
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
                    "search": "",  # Required for POST body format; empty since we are doing a vector search.
                    "top": top_k,
                    "vector": {
                        "value": vector,
                        "fields": "content_vector",
                        "k": top_k
                    }
                }

                # Clean None values from payload
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
        Delete documents from the index based on their IDs.
        
        Args:
            ids (List[str]): The list of document IDs to delete.
        """
        try:
            documents = [{"id": doc_id} for doc_id in ids]
            self.client.delete_documents(documents)
            logging.info(f"Deleted {len(ids)} documents from Azure Search.")
        except Exception as e:
            logging.error("Failed to delete documents by ID", exc_info=True)
        
    def add_vectors(self, ids: List[str], vectors: List[List[float]], metadatas: List[Mapping] = None):
        """
        Add documents with their corresponding vector representations to the index.
        
        Args:
            ids (List[str]): A list of document IDs.
            vectors (List[List[float]]): A list of vector representations (list of floats).
            metadatas (List[Mapping], optional): A list of metadata dictionaries, where each dictionary
                contains additional document fields. Defaults to None.
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
    def init_singleton(endpoint: str, api_key: str, index_name: str, embedding_dims: int = 1536):
        """
        Initialize the AzureVectorService as a singleton.
        
        If the singleton is not yet created, this method creates an instance. Otherwise,
        a warning is logged that the singleton is already initialized.
        
        Args:
            endpoint (str): The Azure Search service endpoint.
            api_key (str): The API key for Azure Search.
            index_name (str): The name of the index to use.
            embedding_dims (int, optional): The dimensionality of the embedding vectors. Defaults to 1536.
        """
        global azure_instance
        if azure_instance is None:
            azure_instance = AzureVectorService(endpoint, api_key, index_name, embedding_dims)
        else:
            logging.warning("AzureVectorService singleton already initialized.")

    @staticmethod
    def get_instance() -> Optional["AzureVectorService"]:
        """
        Retrieve the instance of the AzureVectorService singleton.
        
        Returns:
            Optional[AzureVectorService]: The initialized service instance if available, otherwise None.
        """
        global azure_instance
        if azure_instance is None:
            logging.error("AzureVectorService instance not initialized. Call init_singleton first.")
        return azure_instance
"""
    def retrieve_closest_vectors_and_blob_paths(self, query_vector: List[float], top_k) -> List[dict]:
        
        Retrieve the closest matching documents based on the given vector.
        
        Each result contains the document's id, similarity score, stored vector, and its associated blob path.
        
        Args:
            query_vector (List[float]): The vector to search with.
            top_k (int, optional): The number of closest results to return. Defaults to 1.
        
        Returns:
            List[dict]: A list of dictionaries, each containing keys 'id', 'score', 'content_vector',
            'file_path', and 'raw' for the complete response data.
        
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
            
            # Parse the response and extract matching document details.
            data = response.json().get("value", [])
            results = []
            for result in data:
                file_path = result.get("file_path")
                results.append({
                    "id": result.get("id"),
                    "score": result.get("@search.score"),
                    "content_vector": result.get("content_vector"),
                    "file_path": file_path,
                    "raw": result  # Full raw result for additional context.
                })
                logging.info(f"Retrieved Document - ID: {result.get('id')}, Score: {result.get('@search.score')}, File Path: {file_path}")
            
            return results
        except Exception as e:
            logging.error("❌ Error retrieving closest vectors: " + str(e), exc_info=True)
            return []


# TESTING PURPOSE WILL REMOVE LATER 
if __name__ == "__main__":
    # Setup logging configuration
    logging.basicConfig(level=logging.INFO)

    # Replace these with your actual Azure Search service details.
    endpoint = "https://<searchname>.search.windows.net"
    api_key = "<your_api_key>"
    index_name = "<your_index_name>"

    # Initialize the AzureVectorService singleton.
    AzureVectorService.init_singleton(endpoint, api_key, index_name)
    service = AzureVectorService.get_instance()

    # Prepare a test document with a dummy vector (ensure the vector length matches the embedding dimensions)
    test_vector = [0.1] * 1536  # Example vector for testing.
    test_doc_id = "test-doc-1"
    test_blob_path = "blob/test/doc1"

    # Add the test document to the index.
    # Note: The original test code referenced a method 'add_vector_and_blob_document'
    # which has been replaced with 'add_vectors' in this implementation.
    logging.info("Adding the test document...")
    service.add_vectors([test_doc_id], [test_vector], metadatas=[{"file_path": test_blob_path}])

    # Wait a short moment to allow the indexing process to complete.
    logging.info("Waiting for the document to be indexed...")
    time.sleep(5)

    # Retrieve the closest matching vectors and their associated blob paths based on the same test vector.
    logging.info("Retrieving the closest matching vectors and blob paths...")
    results = service.retrieve_closest_vectors_and_blob_paths(test_vector, top_k=2)

    # Display the results.
    print("\nSearch Results:")
    for result in results:
        print(result)
"""