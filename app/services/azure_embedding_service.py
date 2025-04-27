from typing import List, Optional, Literal

# Use standard Azure AI Inference clients
# Ensure you have 'azure-ai-inference' installed: pip install azure-ai-inference
from azure.ai.inference import EmbeddingsClient, ImageEmbeddingsClient
from azure.ai.inference.models import EmbeddingInputType, ImageEmbeddingInput

# Use standard Azure Core credential type
from azure.core.credentials import AzureKeyCredential
from pydantic import HttpUrl
import logging # Import logging

# Initialize logger
logger = logging.getLogger(__name__)

# Define the singleton instance variable at the module level
embedding_service: Optional["AzureEmbeddingService"] = None


class AzureEmbeddingService:
    """
    A service for generating embeddings using Azure AI Inference SDK.
    Supports both text and image embeddings via Azure's EmbeddingClient and ImageEmbeddingClient.
    """
    text_client: EmbeddingsClient
    image_client: ImageEmbeddingsClient
    model: str

    def __init__(self, azure_embedding_endpoint: HttpUrl, azure_embedding_key: str, azure_embedding_model: str):
        """
        Initializes the AzureEmbeddingService with the necessary Azure endpoint, key, and model.

        Args:
            azure_embedding_endpoint (HttpUrl): The endpoint URL of the Azure embedding service
                                                (e.g., from your Azure AI resource).
            azure_embedding_key (str): The authentication key for the Azure embedding service.
            azure_embedding_model (str): The DEPLOYMENT NAME of the embedding model to use.
                                         (Note: Often this is the model name like 'text-embedding-ada-002',
                                         but check your Azure AI deployment details).
        """
        if not isinstance(azure_embedding_endpoint, HttpUrl):
             raise TypeError("azure_embedding_endpoint must be a Pydantic HttpUrl")
        if not isinstance(azure_embedding_key, str) or not azure_embedding_key:
             raise TypeError("azure_embedding_key must be a non-empty string")
        if not isinstance(azure_embedding_model, str) or not azure_embedding_model:
             raise TypeError("azure_embedding_model must be a non-empty string (deployment name)")

        # --- CORRECTED: Convert HttpUrl to string ---
        endpoint_str = str(azure_embedding_endpoint)
        logger.info(f"Initializing AzureEmbeddingService with endpoint: {endpoint_str}, model: {azure_embedding_model}")
        # --- END CORRECTION ---

        try:
            # Create the credential object
            credential = AzureKeyCredential(azure_embedding_key)

            # Initialize the text embeddings client
            self.text_client = EmbeddingsClient(
                endpoint=endpoint_str, # Use the string endpoint
                credential=credential,
                # Removed 'model' parameter - it's typically passed during the 'embed' call
                # model=azure_embedding_model
            )
            logger.info("Text EmbeddingsClient initialized.")

            # Initialize the image embeddings client (assuming the same endpoint and key)
            # Note: Image embedding models might be different deployments/models
            self.image_client = ImageEmbeddingsClient(
                endpoint=endpoint_str, # Use the string endpoint
                credential=credential,
                # Removed 'model' parameter - it's typically passed during the 'embed' call
                # model=azure_embedding_model
            )
            logger.info("Image EmbeddingsClient initialized.")

            # Store the model/deployment name for use in embed calls
            self.model = azure_embedding_model
            logger.info(f"Using embedding model/deployment name: {self.model}")

        except Exception as e:
            logger.error(f"Failed to initialize Azure AI Inference clients: {e}", exc_info=True)
            # Re-raise as a more specific error or handle appropriately
            raise RuntimeError("Failed to initialize Azure Embedding Service clients") from e


    def embed_texts(self, texts: List[str], purpose: Optional[EmbeddingInputType] = None) -> List[List[float]]:
        """
        Generates embeddings for a list of text inputs.

        Args:
            texts (List[str]): A list of strings to be embedded.
            purpose (Optional[EmbeddingInputType]): The input type specifying the embedding purpose
                                                    (e.g., "query", "document"). Check model compatibility.
                                                    If None, the default behavior of the model is used.

        Returns:
            List[List[float]]: A list of embeddings, where each embedding is a list of float values.

        Raises:
            RuntimeError: If the embedding generation fails.
        """
        if not texts:
             logger.warning("embed_texts called with empty list.")
             return []
        logger.info(f"Generating text embeddings for {len(texts)} items using model '{self.model}'. Purpose: {purpose}")
        try:
            # Prepare arguments for embed call
            embed_args = {
                "input": texts,
                "model": self.model # Pass model/deployment name here
            }
            if purpose:
                embed_args["input_type"] = purpose

            response = self.text_client.embed(**embed_args)

            # Check response structure
            if not response or not hasattr(response, 'data') or not response.data:
                 logger.error("Invalid or empty response received from text embedding service.")
                 raise RuntimeError("Failed to generate text embeddings: Invalid response.")

            embeddings = [item.embedding for item in response.data]
            logger.info(f"Successfully generated {len(embeddings)} text embeddings.")
            return embeddings
        except Exception as e:
             logger.error(f"Error generating text embeddings with model '{self.model}': {e}", exc_info=True)
             raise RuntimeError("Failed to generate text embeddings") from e

    def embed_text(self, text: str, purpose: Optional[EmbeddingInputType] = None) -> List[float]:
        """Generates an embedding for a single text input."""
        if not text:
             logger.warning("embed_text called with empty string.")
             # Return empty list or raise error based on desired behavior
             return []
        # Call the batch method
        results = self.embed_texts([text], purpose)
        # Handle potential empty result from batch method
        return results[0] if results else []


    def embed_image(self, mime_type: Literal['image/png', 'image/jpeg', 'image/webp'], base64_image: str, text: Optional[str] = None) -> List[float]:
        """
        Generates an embedding for a single image, optionally including associated text.
        Uses the 'multimodalembedding' feature of applicable models.

        Args:
            mime_type (Literal['image/png', 'image/jpeg', 'image/webp']): The MIME type of the image.
            base64_image (str): The base64-encoded string representation of the image (without the 'data:...' prefix).
            text (Optional[str]): An optional textual description to include with the image.

        Returns:
            List[float]: The embedding for the given image as a list of float values.

        Raises:
            RuntimeError: If the embedding generation fails.
        """
        if not base64_image:
             raise ValueError("base64_image cannot be empty.")
        logger.info(f"Generating image embedding using model '{self.model}'. Includes text: {'Yes' if text else 'No'}")

        try:
            # Construct the data URI prefix correctly
            data_uri = f"data:{mime_type};base64,{base64_image}"

            # Create the input object
            # Note: ImageEmbeddingInput might vary slightly depending on azure-ai-inference version
            input_image = ImageEmbeddingInput(image=data_uri, text=text)

            response = self.image_client.embed(
                input=[input_image],
                model=self.model, # Pass model/deployment name here
            )

             # Check response structure
            if not response or not hasattr(response, 'data') or not response.data:
                 logger.error("Invalid or empty response received from image embedding service.")
                 raise RuntimeError("Failed to generate image embeddings: Invalid response.")

            embeddings = [item.embedding for item in response.data]
            logger.info("Successfully generated image embedding.")
            # Since we send one input, we expect one output
            return embeddings[0] if embeddings else []

        except Exception as e:
            logger.error(f"Error generating image embedding with model '{self.model}': {e}", exc_info=True)
            raise RuntimeError("Failed to generate image embedding") from e

    @classmethod
    def init_singleton(cls, azure_embedding_endpoint: HttpUrl, azure_embedding_key: str, azure_embedding_model: str):
        """
        Initializes the singleton instance of the AzureEmbeddingService.

        Args:
            azure_embedding_endpoint (HttpUrl): The endpoint URL of the Azure embedding service.
            azure_embedding_key (str): The authentication key for the Azure embedding service.
            azure_embedding_model (str): The DEPLOYMENT NAME of the embedding model to use.
        """
        global embedding_service
        if embedding_service is None:
            logger.info("Initializing AzureEmbeddingService singleton...")
            try:
                embedding_service = cls(azure_embedding_endpoint, azure_embedding_key, azure_embedding_model)
                logger.info("AzureEmbeddingService singleton initialized successfully.")
            except Exception as e:
                # Log the error during initialization and prevent setting the singleton
                logger.error(f"Failed to initialize AzureEmbeddingService singleton: {e}", exc_info=True)
                # Optionally re-raise or handle termination depending on app requirements
                raise RuntimeError("AzureEmbeddingService singleton initialization failed") from e
        else:
             logger.warning("AzureEmbeddingService singleton already initialized.")

    @classmethod
    def get_instance(cls) -> "AzureEmbeddingService": # Add quotes for forward reference
        """
        Returns the singleton instance of the AzureEmbeddingService.

        Returns:
            AzureEmbeddingService: The initialized singleton instance.

        Raises:
            RuntimeError: If the service has not been initialized via init_singleton.
        """
        global embedding_service
        if embedding_service is None:
            logger.error("AzureEmbeddingService singleton accessed before initialization.")
            raise RuntimeError("AzureEmbeddingService has not been initialized. Call init_singleton first.")
        return embedding_service