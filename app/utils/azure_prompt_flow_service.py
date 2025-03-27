import requests
from typing import Optional, Dict, Any

azure_prompt_flow_service: Optional["AzurePromptFlowService"] = None


class AzurePromptFlowService:
    """
    A utility class to interact with the PromptFlow API.
    """

    def __init__(self, base_url: str, api_key: str):
        """
        Initializes the API client with the base URL and authentication key.

        :param base_url: The base URL of the PromptFlow API.
        :param api_key: The API key for authentication.
        """
        self.base_url = base_url.rstrip("/")  # Ensure no trailing slash
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

    def query_model(self, question: str) -> Optional[Dict[str, Any]]:
        """
        Queries the PromptFlow model via the `/score` endpoint.

        :param question: The question to send to the model.
        :return: The response JSON if successful, None otherwise.
        """
        url = f"{self.base_url}/score"
        payload = {"question": question}

        response = requests.post(url, json=payload, headers=self.headers)
        return self._handle_response(response)

    def send_feedback(self, feedback_data: Dict[str, Any], flatten: bool = False) -> Optional[Dict[str, Any]]:
        """
        Sends feedback to the `/feedback` endpoint.

        :param feedback_data: The feedback data to send.
        :param flatten: Whether to flatten the feedback data.
        :return: The response JSON if successful, None otherwise.
        """
        url = f"{self.base_url}/feedback"
        params = {"flatten": str(flatten).lower()}  # Convert boolean to lowercase string

        response = requests.post(url, json=feedback_data, headers=self.headers, params=params)
        return self._handle_response(response)

    @staticmethod
    def _handle_response(response: requests.Response) -> Optional[Dict[str, Any]]:
        """
        Handles API responses, ensuring proper error handling.

        :param response: The response object from the request.
        :return: Parsed JSON response if successful, None otherwise.
        """
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error {response.status_code}: {response.text}")
            return None

    @staticmethod
    def init_singleton(base_url: str, api_key: str):
        """Initializes global singleton instance."""
        global azure_prompt_flow_service
        azure_prompt_flow_service = AzurePromptFlowService(base_url, api_key)

    @staticmethod
    def get_instance() -> Optional["AzurePromptFlowService"]:
        """Retrieves global singleton instance."""
        global azure_prompt_flow_service
        return azure_prompt_flow_service
