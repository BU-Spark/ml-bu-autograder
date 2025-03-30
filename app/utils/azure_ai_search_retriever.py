import logging
from typing import List, Dict, Optional, Literal, Union
from azure.core.credentials import AzureKeyCredential
from azure.identity import ClientSecretCredential, DefaultAzureCredential  # Keep for type hinting
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from azure.core.exceptions import HttpResponseError
from openai import AzureOpenAI, OpenAIError, OpenAI

# Define credential types for type hinting
SearchCredential = Union[AzureKeyCredential, ClientSecretCredential, DefaultAzureCredential]


class AzureAISearchRetriever:
    """
    A utility class to retrieve documents from Azure AI Search for RAG applications.

    Accepts configuration and clients via its constructor.
    """

    DEFAULT_SELECT_FIELDS = ["id", "content", "filepath", "title", "url"]  # Fields needed for RAG
    EMBEDDING_DIMENSION = 1536  # For text-embedding-ada-002

    def __init__(self,
                 search_service_endpoint: str,
                 index_name: str,
                 search_credential: SearchCredential,
                 openai_client: Optional[AzureOpenAI | OpenAI] = None,
                 openai_embedding_deployment: Optional[str] = None,
                 select_fields: Optional[List[str]] = None,
                 embedding_dimension: int = EMBEDDING_DIMENSION):
        """
        Initializes the retriever with necessary configuration and clients.

        Args:
            search_service_endpoint: The full endpoint URL of the Azure AI Search service
                                     (e.g., "https://your-service.search.windows.net").
            index_name: The name of the search index.
            search_credential: An Azure credential object (AzureKeyCredential,
                               ClientSecretCredential, DefaultAzureCredential) for
                               authenticating with the search service.
            openai_client: An initialized AzureOpenAI client instance, required for
                           vector and hybrid searches if generating embeddings internally.
            openai_embedding_deployment: The name of the embedding model deployment in
                                         Azure OpenAI, required if openai_client is provided.
            select_fields: Optional list of fields to retrieve from the search index.
                           Defaults to DEFAULT_SELECT_FIELDS.
            embedding_dimension: The expected dimension of the embeddings.
                                Defaults to EMBEDDING_DIMENSION.
        """
        logging.info(
            f"Initializing AzureAISearchRetriever for endpoint: {search_service_endpoint}, index: {index_name}")

        if not search_service_endpoint:
            raise ValueError("search_service_endpoint cannot be empty.")
        if not index_name:
            raise ValueError("index_name cannot be empty.")
        if not search_credential:
            raise ValueError("search_credential must be provided.")

        self.search_service_endpoint = search_service_endpoint
        self.index_name = index_name
        self.search_credential = search_credential
        self.select_fields = select_fields or self.DEFAULT_SELECT_FIELDS
        self.embedding_dimension = embedding_dimension

        # OpenAI related setup
        self.openai_client = openai_client
        self.openai_embedding_deployment = openai_embedding_deployment

        if self.openai_client and not self.openai_embedding_deployment:
            logging.warning(
                "openai_client provided but openai_embedding_deployment is missing. Embedding generation will fail.")
            # Or raise ValueError("openai_embedding_deployment is required when openai_client is provided.")

        if not self.openai_client:
            logging.warning(
                "Azure OpenAI client not provided. Vector and Hybrid search requiring "
                "embedding generation within this class will fail.")

        self._initialize_search_client()
        self._test_connection()  # Optional: Test connection on init

    def _initialize_search_client(self):
        """Initializes the Azure Search client."""
        try:
            self.search_client = SearchClient(
                endpoint=self.search_service_endpoint,
                index_name=self.index_name,
                credential=self.search_credential
            )
            logging.info(
                f"Search client initialized successfully for index: {self.index_name}")
        except Exception as e:
            logging.error(f"Failed to initialize Search client: {e}", exc_info=True)
            # Reraise as a more specific error or wrap it
            raise RuntimeError(f"Search client initialization failed: {e}") from e

    def _test_connection(self):
        """Performs a basic query to test the connection and credentials."""
        logging.info("Performing initial connection test query...")
        try:
            # Use search_text="*" with top=0 for a low-impact test
            test_results = self.search_client.search(search_text="*", top=0, include_total_count=True)
            count = test_results.get_count()
            logging.info(
                f"Connection test successful! Found ~{count} documents. Credentials are valid for index '{self.index_name}'.")
        except HttpResponseError as e:
            logging.error(f"Connection test query failed with HTTP {e.status_code}: {e.message}", exc_info=True)
            # Provide specific advice based on common errors
            if e.status_code == 403:
                raise PermissionError(
                    f"Connection test failed (403 Forbidden). Verify the provided credential has permissions ('Search Index Data Reader' role needed for RBAC) for index '{self.index_name}' at '{self.search_service_endpoint}'. RBAC roles may take time to propagate.")
            elif e.status_code == 404:
                raise FileNotFoundError(
                    f"Connection test failed (404 Not Found). Verify index name '{self.index_name}' exists at '{self.search_service_endpoint}'.")
            else:
                raise ConnectionError(
                    f"Connection test failed (HTTP {e.status_code}). Check endpoint, network access, and credentials. Details: {e.message}")
        except Exception as e:
            logging.error(f"Unexpected error during connection test query: {e}", exc_info=True)
            raise ConnectionError(f"Unexpected error during connection test: {e}")

    def _generate_embeddings(self, text: str) -> Optional[List[float]]:
        """Generates embeddings for the given text using the configured Azure OpenAI client."""
        if not self.openai_client:
            logging.error("Cannot generate embeddings: Azure OpenAI client was not provided during initialization.")
            return None
        if not self.openai_embedding_deployment:
            logging.error("Cannot generate embeddings: Azure OpenAI embedding deployment name was not provided.")
            return None

        logging.info(
            f"Generating embedding for query: '{text[:50]}...' using deployment '{self.openai_embedding_deployment}'")
        try:
            response = self.openai_client.embeddings.create(
                model=self.openai_embedding_deployment,
                input=text
            )
            embedding = response.data[0].embedding
            if len(embedding) != self.embedding_dimension:
                logging.warning(
                    f"Generated embedding dimension ({len(embedding)}) does not match expected ({self.embedding_dimension}).")
            logging.info("Embedding generated successfully.")
            return embedding
        except OpenAIError as e:
            logging.error(f"Azure OpenAI API error during embedding generation: {e.code} - {e.message}", exc_info=True)
            return None
        except Exception as e:
            logging.error(f"Unexpected error during embedding generation: {e}", exc_info=True)
            return None

    def _format_results(self, results) -> List[Dict]:
        """Formats search results into a list of dictionaries suitable for RAG."""
        output_documents = []
        try:
            for rank, result in enumerate(results):
                metadata = {
                    key: result.get(key) for key in self.select_fields if
                    key != 'content' and result.get(key) is not None
                }
                # Add scores if available
                score = result.get("@search.score")
                reranker_score = result.get("@search.reranker_score")
                if score is not None:
                    metadata["score"] = score
                if reranker_score is not None:
                    metadata["reranker_score"] = reranker_score

                doc = {
                    "rank": rank + 1,
                    "content": result.get("content", ""),  # Ensure content is always a string
                    "metadata": metadata
                }
                output_documents.append(doc)
        except Exception as e:
            logging.error(f"Error formatting search results: {e}", exc_info=True)
            # Return potentially partial results or raise depending on desired robustness
        return output_documents

    def search(self,
               query_text: str,
               top_k: int = 5,
               search_type: Literal["hybrid", "vector", "text"] = "hybrid",
               vector_query: Optional[List[float]] = None,
               use_semantic_ranking: bool = False,  # Note: Requires supported tier
               semantic_configuration_name: str = "azureml-default"  # Make configurable
               ) -> List[Dict]:
        """
        Performs a search operation based on the specified type.

        Args:
            query_text: The text query.
            top_k: The number of top results to retrieve.
            search_type: Type of search ('hybrid', 'vector', 'text'). Defaults to 'hybrid'.
            vector_query: Optional pre-computed vector for 'vector' or 'hybrid' search.
                          If None and search type is 'vector' or 'hybrid', embeddings
                          will be generated using the provided openai_client.
            use_semantic_ranking: If True, attempts semantic ranking (for 'text' or 'hybrid').
                                  Requires a supported service tier and configuration.
            semantic_configuration_name: The name of the semantic configuration to use
                                         if use_semantic_ranking is True.

        Returns:
            A list of dictionaries, each representing a retrieved document.
            Returns an empty list if an error occurs during the search itself.
        """
        logging.info(
            f"Performing '{search_type}' search for query: '{query_text[:50]}...' (top_k={top_k}, semantic={use_semantic_ranking})")

        query_vector_internal = vector_query

        # Generate embeddings if needed and not provided
        if search_type in ["hybrid", "vector"] and query_vector_internal is None:
            if not self.openai_client:
                logging.error(
                    f"Cannot perform '{search_type}' search without a pre-computed vector: "
                    "Azure OpenAI client not available for embedding generation.")
                return []
            query_vector_internal = self._generate_embeddings(query_text)
            if query_vector_internal is None:
                logging.error(f"Failed to generate embedding for '{search_type}' search.")
                return []  # Stop if embedding fails

        try:
            search_args = {
                "select": self.select_fields,
                "top": top_k,
            }

            if search_type == "hybrid":
                if query_vector_internal is None:
                    # This case should ideally be caught by the check above, but double-check
                    logging.error("Hybrid search requires a query vector, but it could not be generated or provided.")
                    return []
                search_args["search_text"] = query_text
                search_args["vector_queries"] = [
                    VectorizedQuery(vector=query_vector_internal, k_nearest_neighbors=top_k, fields="contentVector")
                    # Assuming 'contentVector' field
                ]
                if use_semantic_ranking:
                    search_args["query_type"] = "semantic"
                    search_args["semantic_configuration_name"] = semantic_configuration_name
                    logging.info(
                        f"Attempting Semantic Hybrid search with configuration '{semantic_configuration_name}'.")


            elif search_type == "vector":
                if query_vector_internal is None:
                    # This case should ideally be caught by the check above, but double-check
                    logging.error("Vector search requires a query vector, but it could not be generated or provided.")
                    return []
                search_args["vector_queries"] = [
                    VectorizedQuery(vector=query_vector_internal, k_nearest_neighbors=top_k, fields="contentVector")
                    # Assuming 'contentVector' field
                ]
                search_args["search_text"] = None  # Pure vector search

            elif search_type == "text":
                search_args["search_text"] = query_text
                if use_semantic_ranking:
                    search_args["query_type"] = "semantic"
                    search_args["semantic_configuration_name"] = semantic_configuration_name
                    logging.info(f"Attempting Semantic Text search with configuration '{semantic_configuration_name}'.")

            else:
                logging.error(f"Invalid search_type: {search_type}")
                return []

            results = self.search_client.search(**search_args)
            formatted_results = self._format_results(results)
            logging.info(f"Search successful. Retrieved {len(formatted_results)} documents.")
            return formatted_results

        except HttpResponseError as e:
            if use_semantic_ranking and ("semantic" in str(e).lower() or e.status_code == 400):
                logging.warning(
                    f"Semantic ranking failed (likely not supported/configured on service tier or invalid configuration name '{semantic_configuration_name}'): {e.message}")
                # Optionally fallback to non-semantic search here if desired
                return []  # Return empty for now on semantic failure
            else:
                logging.error(f"Search operation failed with HTTP {e.status_code}: {e.message}", exc_info=True)
                return []  # Return empty list on search failure
        except Exception as e:
            logging.error(f"An unexpected error occurred during search: {e}", exc_info=True)
            return []  # Return empty list on unexpected failure
