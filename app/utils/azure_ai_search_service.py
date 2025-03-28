import os
import sys
import logging
from typing import List, Dict, Optional, Literal
from dotenv import load_dotenv
from azure.core.credentials import AzureKeyCredential
from azure.identity import ClientSecretCredential, DefaultAzureCredential, CredentialUnavailableError
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from azure.core.exceptions import HttpResponseError
from openai import AzureOpenAI, OpenAIError

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class AzureAISearchRetriever:
    """
    A utility class to retrieve documents from Azure AI Search for RAG applications.

    Handles connection, embedding generation (optional), and various search types.
    Configuration is primarily driven by environment variables.
    """

    DEFAULT_SEARCH_DNS_SUFFIX = "search.windows.net"
    DEFAULT_SELECT_FIELDS = ["id", "content", "filepath", "title", "url"] # Fields needed for RAG
    EMBEDDING_DIMENSION = 1536 # For text-embedding-ada-002

    def __init__(self):
        """
        Initializes the retriever by loading configuration and setting up clients.
        """
        load_dotenv()
        self._load_config()
        self._validate_config()
        self._initialize_credentials()
        self._initialize_clients()
        self._test_connection() # Optional: Test connection on init

    def _load_config(self):
        """Loads configuration from environment variables."""
        logging.info("Loading configuration from environment variables...")
        # Search Config
        self.search_service_name = os.getenv("AZURE_SEARCH_SERVICE_NAME")
        self.index_name = os.getenv("AZURE_SEARCH_INDEX_NAME")
        self.search_api_key = os.getenv("AZURE_SEARCH_API_KEY") # Preferred for current setup
        self.search_dns_suffix = os.getenv("AZURE_SEARCH_DNS_SUFFIX", self.DEFAULT_SEARCH_DNS_SUFFIX)
        self.search_service_endpoint = f"https://{self.search_service_name}.{self.search_dns_suffix}"

        # Optional Service Principal Config (Alternative Auth for Search)
        self.tenant_id = os.getenv("AZURE_TENANT_ID")
        self.client_id = os.getenv("AZURE_CLIENT_ID")
        self.client_secret = os.getenv("AZURE_CLIENT_SECRET")

        # OpenAI Config (for embeddings)
        self.openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT") # Expecting BASE URL
        self.openai_key = os.getenv("AZURE_OPENAI_API_KEY")
        self.openai_deployment = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT")
        self.openai_api_version = os.getenv("AZURE_OPENAI_API_VERSION")
        self.openai_configured = all([self.openai_endpoint, self.openai_key, self.openai_deployment, self.openai_api_version])

    def _validate_config(self):
        """Validates that essential configuration is present."""
        logging.info("Validating configuration...")
        if not self.search_service_name:
            raise ValueError("Missing required environment variable: AZURE_SEARCH_SERVICE_NAME")
        if not self.index_name:
            raise ValueError("Missing required environment variable: AZURE_SEARCH_INDEX_NAME")

        # Check for at least one Search auth method
        self.use_sp_auth = all([self.tenant_id, self.client_id, self.client_secret])
        if not self.search_api_key and not self.use_sp_auth:
             # Could also check for DefaultAzureCredential scenarios if needed
            raise ValueError("Missing Search credentials: Set either AZURE_SEARCH_API_KEY or AZURE_TENANT_ID/CLIENT_ID/CLIENT_SECRET")
        if self.search_api_key and self.use_sp_auth:
            logging.warning("Both API Key and Service Principal credentials found for Search. Using API Key by default.")
            # Prioritize API Key if both are set, matching user's current setup
            self.use_sp_auth = False

        if not self.openai_configured:
            logging.warning("Azure OpenAI credentials not fully configured. Vector and Hybrid search requiring embedding generation will fail.")

    def _initialize_credentials(self):
        """Initializes the credential object for Azure Search."""
        self.search_credential = None
        if self.use_sp_auth:
            logging.info("Initializing Search client with Service Principal.")
            try:
                self.search_credential = ClientSecretCredential(
                    tenant_id=self.tenant_id,
                    client_id=self.client_id,
                    client_secret=self.client_secret
                )
                # Validate credential early
                self.search_credential.get_token("https://search.azure.com/.default")
            except (CredentialUnavailableError, Exception) as e:
                logging.error(f"Failed to initialize Service Principal credential: {e}", exc_info=True)
                raise ValueError(f"Service Principal credential failed: {e}")
        elif self.search_api_key:
             logging.info("Initializing Search client with API Key.")
             try:
                 self.search_credential = AzureKeyCredential(self.search_api_key)
             except Exception as e:
                 logging.error(f"Failed to initialize API Key credential: {e}", exc_info=True)
                 raise ValueError(f"Azure Key Credential initialization failed: {e}")
        else:
             # Fallback or for Managed Identity scenarios
             logging.info("Attempting DefaultAzureCredential for Search (ensure environment is configured).")
             try:
                 self.search_credential = DefaultAzureCredential()
                 self.search_credential.get_token("https://search.azure.com/.default")
             except (CredentialUnavailableError, Exception) as e:
                 logging.error(f"DefaultAzureCredential failed for Search: {e}", exc_info=True)
                 raise ValueError(f"DefaultAzureCredential failed for Search: {e}")


    def _initialize_clients(self):
        """Initializes the Azure Search and OpenAI clients."""
        # Initialize Search Client
        try:
            self.search_client = SearchClient(
                endpoint=self.search_service_endpoint,
                index_name=self.index_name,
                credential=self.search_credential
            )
            logging.info(f"Search client initialized for endpoint: {self.search_service_endpoint}, index: {self.index_name}")
        except Exception as e:
            logging.error(f"Failed to initialize Search client: {e}", exc_info=True)
            raise RuntimeError(f"Search client initialization failed: {e}")

        # Initialize OpenAI Client
        self.openai_client = None
        if self.openai_configured:
            try:
                self.openai_client = AzureOpenAI(
                    azure_endpoint=self.openai_endpoint, # Requires BASE URL
                    api_key=self.openai_key,
                    api_version=self.openai_api_version,
                )
                logging.info("Azure OpenAI client initialized.")
            except ValueError as e:
                 logging.error(f"Failed to initialize Azure OpenAI client. Check AZURE_OPENAI_ENDPOINT format (should be base URL). Error: {e}", exc_info=True)
                 # Don't raise, allow running without embeddings
            except Exception as e:
                logging.warning(f"Failed to initialize Azure OpenAI client: {e}", exc_info=True)
                # Don't raise, allow running without embeddings
        else:
             logging.info("Skipping Azure OpenAI client initialization (not configured).")

    def _test_connection(self):
        """Performs a basic query to test the connection and credentials."""
        logging.info("Performing initial connection test query...")
        try:
            # Use search_text="*" with top=0 for a low-impact test
            test_results = self.search_client.search(search_text="*", top=0, include_total_count=True)
            count = test_results.get_count()
            logging.info(f"Connection test successful! Found ~{count} documents. Credentials are valid for index '{self.index_name}'.")
        except HttpResponseError as e:
            logging.error(f"Connection test query failed with HTTP {e.status_code}: {e.message}", exc_info=True)
            # Provide specific advice based on common errors
            if e.status_code == 403:
                 raise PermissionError(f"Connection test failed (403 Forbidden). Verify API Key/Service Principal permissions ('Search Index Data Reader' role needed for SP) for index '{self.index_name}'. RBAC roles may take time to propagate.")
            elif e.status_code == 404:
                 raise FileNotFoundError(f"Connection test failed (404 Not Found). Verify index name '{self.index_name}' exists at '{self.search_service_endpoint}'.")
            else:
                 raise ConnectionError(f"Connection test failed (HTTP {e.status_code}). Check endpoint, network access, and credentials. Details: {e.message}")
        except Exception as e:
            logging.error(f"Unexpected error during connection test query: {e}", exc_info=True)
            raise ConnectionError(f"Unexpected error during connection test: {e}")

    def _generate_embeddings(self, text: str) -> Optional[List[float]]:
        """Generates embeddings for the given text using Azure OpenAI."""
        if not self.openai_client:
            logging.error("Cannot generate embeddings: Azure OpenAI client is not initialized.")
            return None

        logging.info(f"Generating embedding for query: '{text[:50]}...'")
        try:
            response = self.openai_client.embeddings.create(
                model=self.openai_deployment,
                input=text
            )
            embedding = response.data[0].embedding
            if len(embedding) != self.EMBEDDING_DIMENSION:
                logging.warning(f"Generated embedding dimension ({len(embedding)}) does not match expected ({self.EMBEDDING_DIMENSION}).")
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
                    "id": result.get("id"),
                    "score": result.get("@search.score"),
                    "reranker_score": result.get("@search.reranker_score"), # For semantic hybrid
                    "filepath": result.get("filepath"),
                    "title": result.get("title"),
                    "url": result.get("url"),
                    # Add any other metadata fields from DEFAULT_SELECT_FIELDS here
                }
                # Filter out None scores
                metadata = {k: v for k, v in metadata.items() if v is not None}

                doc = {
                    "rank": rank + 1,
                    "content": result.get("content", ""), # Ensure content is always a string
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
               use_semantic_ranking: bool = False # Note: Requires supported tier
               ) -> List[Dict]:
        """
        Performs a search operation based on the specified type.

        Args:
            query_text: The text query.
            top_k: The number of top results to retrieve.
            search_type: Type of search ('hybrid', 'vector', 'text'). Defaults to 'hybrid'.
            vector_query: Optional pre-computed vector for 'vector' or 'hybrid' search.
                          If None, embeddings will be generated for 'vector'/'hybrid'.
            use_semantic_ranking: If True, attempts semantic ranking (for 'text' or 'hybrid').
                                  Requires a supported service tier and configuration.

        Returns:
            A list of dictionaries, each representing a retrieved document.
            Returns an empty list if an error occurs during the search itself.
        """
        logging.info(f"Performing '{search_type}' search for query: '{query_text[:50]}...' (top_k={top_k})")

        query_vector_internal = vector_query

        # Generate embeddings if needed and not provided
        if search_type in ["hybrid", "vector"] and query_vector_internal is None:
            if not self.openai_client:
                logging.error(f"Cannot perform '{search_type}' search: OpenAI client not available for embedding generation.")
                return []
            query_vector_internal = self._generate_embeddings(query_text)
            if query_vector_internal is None:
                logging.error(f"Failed to generate embedding for '{search_type}' search.")
                return [] # Stop if embedding fails

        try:
            search_args = {
                "select": self.DEFAULT_SELECT_FIELDS,
                "top": top_k,
            }

            if search_type == "hybrid":
                if query_vector_internal is None:
                     logging.error("Hybrid search requires a query vector.")
                     return []
                search_args["search_text"] = query_text
                search_args["vector_queries"] = [
                    VectorizedQuery(vector=query_vector_internal, k_nearest_neighbors=top_k, fields="contentVector")
                ]
                # Optional Semantic Hybrid (Requires supported tier & config)
                if use_semantic_ranking:
                    search_args["query_type"] = "semantic"
                    search_args["semantic_configuration_name"] = "azureml-default" # Assumes this config exists
                    logging.info("Attempting Semantic Hybrid search.")


            elif search_type == "vector":
                if query_vector_internal is None:
                     logging.error("Vector search requires a query vector.")
                     return []
                search_args["vector_queries"] = [
                    VectorizedQuery(vector=query_vector_internal, k_nearest_neighbors=top_k, fields="contentVector")
                ]
                search_args["search_text"] = None # Pure vector

            elif search_type == "text":
                search_args["search_text"] = query_text
                # Optional Semantic Text (Requires supported tier & config)
                if use_semantic_ranking:
                    search_args["query_type"] = "semantic"
                    search_args["semantic_configuration_name"] = "azureml-default" # Assumes this config exists
                    logging.info("Attempting Semantic Text search.")

            else:
                logging.error(f"Invalid search_type: {search_type}")
                return []

            results = self.search_client.search(**search_args)
            formatted_results = self._format_results(results)
            logging.info(f"Search successful. Retrieved {len(formatted_results)} documents.")
            return formatted_results

        except HttpResponseError as e:
             # Handle specific errors like semantic feature not supported
            if use_semantic_ranking and ("semantic" in str(e).lower() or e.status_code == 400):
                 logging.warning(f"Semantic ranking failed (likely not supported/configured on service tier): {e.message}")
                 # Optionally fallback to non-semantic search here if desired
                 return [] # Return empty for now on semantic failure
            else:
                 logging.error(f"Search operation failed with HTTP {e.status_code}: {e.message}", exc_info=True)
                 return [] # Return empty list on search failure
        except Exception as e:
            logging.error(f"An unexpected error occurred during search: {e}", exc_info=True)
            return [] # Return empty list on unexpected failure

# --- Example Usage ---
if __name__ == "__main__":
    ...