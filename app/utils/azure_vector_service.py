import logging
from typing import Optional, List, Mapping

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

azure_instance: Optional["AzureVectorService"] = None

class AzureVectorService:
    def __init__(self, endpoint: str, api_key: str, index_name: str, embedding_dims: int = 1536):
        self.endpoint = endpoint
        self.index_name = index_name
        self.embedding_dims = embedding_dims
        self.api_key = api_key

        credential = AzureKeyCredential(api_key)
        self.client = SearchClient(endpoint, index_name, credential=credential)
        self.index_client = SearchIndexClient(endpoint, credential=credential)
        self._verify_or_create_index()

    def _verify_or_create_index(self):
        try:
            index = self.index_client.get_index(self.index_name)
            logging.info(f"✅ Retrieved existing index: {self.index_name}")
        except Exception as e:
            logging.warning(f"Index '{self.index_name}' not found. Creating a new one.")
            self._create_index()

    def _create_index(self):
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

    def add_vectors(self, ids: List[str], vectors: List[List[float]], metadatas: List[Mapping] = None):
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
        global azure_instance
        if azure_instance is None:
            azure_instance = AzureVectorService(endpoint, api_key, index_name, embedding_dims)
        else:
            logging.warning("AzureVectorService singleton already initialized.")

    @staticmethod
    def get_instance() -> Optional["AzureVectorService"]:
        global azure_instance
        if azure_instance is None:
            logging.error("AzureVectorService instance not initialized. Call init_singleton first.")
        return azure_instance
