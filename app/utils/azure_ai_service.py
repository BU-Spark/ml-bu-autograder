from typing import Optional
#from azure.ai.ml import MLClient

azure_ai_service: Optional["AzureAIService"] = None


class AzureAIService:
    def __init__(self, credential):
        ...  # TODO

    @staticmethod
    def init_singleton(credential):
        # TODO
        global azure_ai_service
        azure_ai_service = AzureAIService(credential)

    @staticmethod
    def get_instance() -> Optional["AzureAIService"]:
        global azure_ai_service
        return azure_ai_service
