from enum import Enum
from typing import List, Optional, Literal

import cohere
from azure.ai.inference import EmbeddingsClient, ImageEmbeddingsClient
from azure.ai.inference.models import ImageEmbeddingInput
from azure.core.credentials import AzureKeyCredential
from pydantic import HttpUrl

embedding_service: Optional["AzureEmbeddingService"] = None


class EmbeddingInputType(Enum):
    SEARCH_QUERY = "search_query"
    IMAGE = "image"
    DOCUMENT = "search_document"


class CohereEmbeddingService:

    def __init__(self, api_key: str):
        self.co = cohere.ClientV2(api_key)

    def embed_texts(self, texts: List[str], purpose: EmbeddingInputType) -> List[List[float]]:
        all_embeddings: List[List[float]] = []
        MAX_BATCH_SIZE = 96
        for i in range(0, len(texts), MAX_BATCH_SIZE):
            batch = texts[i:i + MAX_BATCH_SIZE]
            response = self.co.embed(
                texts=batch,
                model="embed-v4.0",
                input_type=purpose.value,
                embedding_types=["float"]
            )
            all_embeddings.extend(response.embeddings.float_)

        return all_embeddings

    def embed_text(self, text: str, purpose: EmbeddingInputType) -> List[float]:
        return self.embed_texts([text], purpose)[0]

    def embed_image(self, mime_type: Literal['image/png', 'image/jpeg'], base_64_image: str) -> List[float]:
        input_image = f"data:{mime_type};base64,{base_64_image}"
        response = self.co.embed(
            images=[input_image],
            model="embed-v4.0",
            input_type=EmbeddingInputType.IMAGE,
            embedding_types=["float"]
        )
        return response.embeddings.float_[0]

    @classmethod
    def init_singleton(cls, cohere_api_key: str):
        global embedding_service
        if embedding_service is None or type(embedding_service) is not CohereEmbeddingService:
            embedding_service = cls(cohere_api_key)

    @classmethod
    def get_instance(cls):
        global embedding_service
        return embedding_service

class AzureEmbeddingService:
    """
    A service for generating embeddings using Azure AI services. 
    Supports both text and image embeddings via Azure's EmbeddingClient and ImageEmbeddingClient.
    """

    def __init__(self, azure_embedding_endpoint: HttpUrl, azure_embedding_key: str, azure_embedding_model: str):
        """
        Initializes the AzureEmbeddingService with the necessary Azure endpoint, key, and model.

        Args:
            azure_embedding_endpoint (HttpUrl): The endpoint of the Azure embedding service.
            azure_embedding_key (str): The authentication key for the Azure embedding service.
            azure_embedding_model (str): The name of the model to be used for generating embeddings.
        """
        self.text_client = EmbeddingsClient(
            endpoint=str(azure_embedding_endpoint),
            credential=AzureKeyCredential(azure_embedding_key),
            model=azure_embedding_model
        )
        self.image_client = ImageEmbeddingsClient(
            endpoint=str(azure_embedding_endpoint),
            credential=AzureKeyCredential(azure_embedding_key),
            model=azure_embedding_model
        )
        self.model = azure_embedding_model

    def embed_texts(self, texts: List[str], purpose: EmbeddingInputType) -> List[List[float]]:
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

    def embed_text(self, text: str, purpose: EmbeddingInputType) -> List[float]:
        return self.embed_texts([text], purpose)[0]

    def embed_image(self, mime_type: Literal['image/png', 'image/jpeg'], base_64_image: str,
                    text: Optional[str] = None) -> List[float]:
        """
        Generates an embedding for a single image, optionally including associated text.

        Args:
            image_format (str): The format of the image (e.g., 'png', 'jpeg').
            base_64_image (str): The base64-encoded string representation of the image.
            text (Optional[str]): An optional textual description to include with the image.

        Returns:
            List[float]: The embedding for the given image as a list of float values.
        """
        input_image = ImageEmbeddingInput(image=f"data:{mime_type};base64,{base_64_image}", text=text)
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
            azure_embedding_endpoint (HttpUrl): The endpoint of the Azure embedding service.
            azure_embedding_key (str): The authentication key for the Azure embedding service.
            azure_embedding_model (str): The name of the model to be used for generating embeddings.
        """
        global embedding_service
        if embedding_service is None or type(embedding_service) is not AzureEmbeddingService:
            embedding_service = cls(azure_embedding_endpoint, azure_embedding_key, azure_embedding_model)

    @classmethod
    def get_instance(cls):
        """
        Returns the singleton instance of the AzureEmbeddingService.
        :return: AzureEmbeddingService instance
        """
        global embedding_service
        return embedding_service
