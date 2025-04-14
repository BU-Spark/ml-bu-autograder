from typing import List, Optional, Literal

from azure.ai.inference import EmbeddingsClient, ImageEmbeddingsClient
from azure.ai.inference.models import EmbeddingInputType, ImageEmbeddingInput
from azure.core.credentials import AzureKeyCredential
from pydantic import HttpUrl

embedding_service: Optional["AzureEmbeddingService"] = None


class AzureEmbeddingService:
    """
    A service for generating embeddings using Azure AI services. 
    Supports both text and image embeddings via Azure's EmbeddingClient and ImageEmbeddingClient.
    """

    def __init__(self, azure_embedding_endpoint: HttpUrl, azure_embedding_key: str, azure_embedding_model: str):
        """
        Initializes the AzureEmbeddingService with the necessary Azure endpoint, key, and model.

        Args:
            azure_endpoint (str): The endpoint of the Azure embedding service.
            azure_key (str): The authentication key for the Azure embedding service.
            model (str): The name of the model to be used for generating embeddings.
        """
        self.text_client = EmbeddingsClient(
            endpoint=azure_embedding_endpoint.encoded_string(),
            credential=AzureKeyCredential(azure_embedding_key),
            model=azure_embedding_model
        )
        self.image_client = ImageEmbeddingsClient(
            endpoint=azure_embedding_endpoint.encoded_string(),
            credential=AzureKeyCredential(azure_embedding_key),
            model=azure_embedding_model
        )
        self.model = azure_embedding_model

    def embed_text(self, texts: List[str], purpose: EmbeddingInputType) -> List[List[float]]:
        """
        Generates embeddings for a list of text inputs.

        Args:
            texts (List[str]): A list of strings to be embedded.
            purpose (EmbeddingInputType): The input type specifying the embedding purpose.

        Returns:
            List[List[float]]: A list of embeddings, where each embedding is a list of float values.
        """
        response = self.text_client.embed(
            input=texts,
            model=self.model,
            input_type=purpose
        )
        return [item.embedding for item in response.data]

    def embed_image(self, image_format: Literal['png', 'jpeg'], base_64_image: str, text: Optional[str]) -> List[float]:
        """
        Generates an embedding for a single image, optionally including associated text.

        Args:
            image_format (str): The format of the image (e.g., 'png', 'jpeg').
            base_64_image (str): The base64-encoded string representation of the image.
            text (Optional[str]): An optional textual description to include with the image.

        Returns:
            List[float]: The embedding for the given image as a list of float values.
        """
        input_image = ImageEmbeddingInput(image=f"data:image/{image_format};base64,{base_64_image}", text=text)
        response = self.image_client.embed(
            input=[input_image],
            model=self.model,
        )
        return [item.embedding for item in response.data][0]

    @classmethod
    def init_singleton(cls, azure_embedding_endpoint: HttpUrl, azure_embedding_key: str, azure_embedding_model: str):
        """
        Initializes the singleton instance of the AzureEmbeddingService.

        Args:
            azure_embedding_endpoint (str): The endpoint of the Azure embedding service.
            azure_embedding_key (str): The authentication key for the Azure embedding service.
            azure_embedding_model (str): The name of the model to be used for generating embeddings.
        """
        global embedding_service
        if embedding_service is None:
            embedding_service = cls(azure_embedding_endpoint, azure_embedding_key, azure_embedding_model)

    @classmethod
    def get_instance(cls):
        """
        Returns the singleton instance of the AzureEmbeddingService.
        :return: AzureEmbeddingService instance
        """
        global embedding_service
        return embedding_service
