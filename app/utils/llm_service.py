import base64
import json
import logging
import mimetypes
from enum import Enum
from typing import Optional, List, Type, TypeVar, Literal

from openai import AzureOpenAI
from openai.types.chat import ChatCompletionContentPartParam, ChatCompletionMessageParam, \
    ChatCompletionContentPartTextParam, ChatCompletionContentPartImageParam, ChatCompletionContentPartInputAudioParam
from openai.types.chat.chat_completion_content_part_image_param import ImageURL
from openai.types.chat.chat_completion_content_part_input_audio_param import InputAudio
from openai.types.chat.chat_completion_content_part_param import File, FileFile
from pydantic import HttpUrl, BaseModel
from typing_extensions import Buffer

# Assuming DataType and get_str_var are correctly defined elsewhere
# If not, provide their definitions or stubs
try:
    from app.utils.bytes_to_doc_util import DataType
    from app.utils.env_var_util import get_str_var
except ImportError:
    print("Warning: Could not import app utils. Defining dummy versions.")
    class DataType(Enum):
        TEXT = "text/plain"
        JSON = "application/json"
        PDF = "application/pdf"
        PNG = "image/png"
        JPEG = "image/jpeg"
        GIF = "image/gif"
        WEBP = "image/webp"
        WAV = "audio/wav"
        MP3 = "audio/mpeg" # Correct MIME type for MP3
        URL = "text/uri-list" # Example, might not be standard

        @property
        def mime_type(self):
            return self.value

        @classmethod
        def from_mime_type(cls, mime: str) -> "DataType":
            for item in cls:
                if item.value == mime:
                    return item
            raise ValueError(f"Unknown mime type: {mime}")

    def get_str_var(var_name: str, default: Optional[str] = None) -> str:
        import os
        val = os.environ.get(var_name, default)
        if val is None:
            raise ValueError(f"Environment variable '{var_name}' not set.")
        return val


# Setup basic logging if not already configured
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PromptType(Enum):
    TEXT_INPUT = 1, "text"
    IMAGE_BYTES_INPUT = 2, "image_url"
    IMAGE_WEB_URL = 3, "image_url"
    AUDIO_INPUT = 4, "input_audio"
    INPUT_FILE = 5, "file"


class PromptRole(Enum):
    SYSTEM = "system"
    USER = "user"


class PromptData:
    prompt_type: PromptType
    file_type: DataType
    filename: Optional[str]
    file_data: Buffer | bytes | str

    def __init__(self, prompt_type: PromptType, file_data: Buffer | bytes | str,
                 filename: Optional[str] = None, file_type: DataType = DataType.TEXT):
        self.prompt_type = prompt_type
        self.file_data = file_data
        self.filename = filename
        self.file_type = file_type

    def to_content(self) -> ChatCompletionContentPartParam:
        if self.prompt_type == PromptType.TEXT_INPUT:
            return ChatCompletionContentPartTextParam(
                type="text",
                text=str(self.file_data) # Ensure it's a string
            )
        elif self.prompt_type == PromptType.IMAGE_BYTES_INPUT:
            # Ensure file_data is bytes before encoding
            if not isinstance(self.file_data, bytes):
                 raise TypeError(f"Expected bytes for IMAGE_BYTES_INPUT, got {type(self.file_data)}")
            base64_data = base64.b64encode(self.file_data).decode('utf-8')
            return ChatCompletionContentPartImageParam(
                type="image_url",
                image_url=ImageURL(
                    url=f"data:{self.file_type.mime_type};base64,{base64_data}"
                )
            )
        elif self.prompt_type == PromptType.IMAGE_WEB_URL:
            return ChatCompletionContentPartImageParam(
                type="image_url",
                image_url=ImageURL(
                    url=str(self.file_data) # Ensure URL is a string
                )
            )
        elif self.prompt_type == PromptType.AUDIO_INPUT:
            if not isinstance(self.file_data, bytes):
                 raise TypeError(f"Expected bytes for AUDIO_INPUT, got {type(self.file_data)}")
            base64_data = base64.b64encode(self.file_data).decode('utf-8')
            audio_format = "wav" if self.file_type == DataType.WAV else "mp3"
            return ChatCompletionContentPartInputAudioParam(
                type="input_audio",
                input_audio=InputAudio(
                    data=base64_data,
                    format=audio_format,
                ),
            )
        elif self.prompt_type == PromptType.INPUT_FILE:
             logger.warning("Attempting to use 'file' type with Azure OpenAI, compatibility may vary.")
             if not isinstance(self.file_data, bytes):
                 raise TypeError(f"Expected bytes for INPUT_FILE, got {type(self.file_data)}")
             base64_data = base64.b64encode(self.file_data).decode('utf-8')
             # This format might need adjustment based on specific Azure capabilities
             # Often requires a prior file upload step to get a file ID.
             return File(
                type="file",
                file=FileFile(
                    file_data=f"data:{self.file_type.mime_type};base64,{base64_data}", # Placeholder format
                    file_id=self.filename, # Placeholder, might need actual Azure file ID
                    filename=self.filename,
                )
            )
        else:
            raise ValueError(f"Invalid PromptType: {self.prompt_type}")


class PromptContent:
    role: PromptRole
    # Initialize directly in __init__ to avoid class attribute sharing issues
    # prompt_data_list: List[PromptData] = []

    def __init__(self, role: PromptRole, prompt_data_list: List[PromptData]):
        self.role = role
        self.prompt_data_list = prompt_data_list if prompt_data_list is not None else []

    def to_message(self) -> ChatCompletionMessageParam:
        return {
            "role": self.role.value,
            "content": [data.to_content() for data in self.prompt_data_list]
        }


class PromptBuilder:
    # Initialize instance variables in __init__
    # _prompt: List[PromptContent] = []
    # _previous_message: Optional[PromptContent] = None

    def __init__(self):
        self._prompt: List[PromptContent] = []
        self._previous_message: Optional[PromptContent] = None


    def add_message(self, role: PromptRole, content: str) -> "PromptBuilder":
        if not isinstance(content, str):
            raise TypeError(f"Expected string content, got {type(content)}")
        prompt_data = PromptData(
            prompt_type=PromptType.TEXT_INPUT,
            file_data=content,
        )
        # Combine with previous message if role matches
        if self._previous_message is not None and self._previous_message.role == role:
            self._previous_message.prompt_data_list.append(prompt_data)
        else:
            # Create new PromptContent for this message part
            new_content = PromptContent(role, [prompt_data])
            self._prompt.append(new_content)
            self._previous_message = new_content # Update last message reference
        return self

    def add_file_bytes(self, role: PromptRole, file_type: DataType, filename: str, file_bytes: bytes | Buffer) -> "PromptBuilder":
        logger.warning("At the time of writing, Azure OpenAI might not fully support direct 'file' type uploads in chat completions.")
        if not isinstance(file_bytes, (bytes, Buffer)):
             raise TypeError(f"Expected bytes or Buffer for file_bytes, got {type(file_bytes)}")
        prompt_data = PromptData(
            prompt_type=PromptType.INPUT_FILE,
            file_data=file_bytes,
            filename=filename,
            file_type=file_type,
        )
        if self._previous_message is not None and self._previous_message.role == role:
            self._previous_message.prompt_data_list.append(prompt_data)
        else:
            new_content = PromptContent(role, [prompt_data])
            self._prompt.append(new_content)
            self._previous_message = new_content
        return self

    def add_audio_bytes(self, role: PromptRole, audio_data: bytes, mimetype: Literal['audio/wav', 'audio/mp3']) -> "PromptBuilder":
        logger.warning("At the time of writing, Azure OpenAI might not fully support direct 'input_audio' type uploads in chat completions.")
        if not isinstance(audio_data, bytes):
             raise TypeError(f"Expected bytes for audio_data, got {type(audio_data)}")
        prompt_data = PromptData(
            prompt_type=PromptType.AUDIO_INPUT,
            file_data=audio_data,
            file_type=DataType.from_mime_type(mimetype),
        )
        if self._previous_message is not None and self._previous_message.role == role:
            self._previous_message.prompt_data_list.append(prompt_data)
        else:
            new_content = PromptContent(role, [prompt_data])
            self._prompt.append(new_content)
            self._previous_message = new_content
        return self

    def add_image_bytes(self, role: PromptRole, image_data: bytes | Buffer, mimetype: Literal['image/jpeg', 'image/png', 'image/gif', 'image/webp']) -> "PromptBuilder":
        if not isinstance(image_data, (bytes, Buffer)):
             raise TypeError(f"Expected bytes or Buffer for image_data, got {type(image_data)}")
        # Ensure mimetype is valid before creating PromptData
        try:
            file_type = DataType.from_mime_type(mimetype)
        except ValueError as e:
             raise ValueError(f"Unsupported image mimetype: {mimetype}") from e

        prompt_data = PromptData(
            prompt_type=PromptType.IMAGE_BYTES_INPUT,
            file_data=image_data,
            file_type=file_type,
        )
        if self._previous_message is not None and self._previous_message.role == role:
            self._previous_message.prompt_data_list.append(prompt_data)
        else:
            new_content = PromptContent(role, [prompt_data])
            self._prompt.append(new_content)
            self._previous_message = new_content
        return self

    def add_image_url(self, role: PromptRole, image_url: HttpUrl) -> "PromptBuilder":
        if not isinstance(image_url, HttpUrl):
             raise TypeError(f"Expected pydantic.HttpUrl for image_url, got {type(image_url)}")
        prompt_data = PromptData(
            prompt_type=PromptType.IMAGE_WEB_URL,
            file_data=str(image_url), # Convert HttpUrl to string
            file_type=DataType.URL # Indicate it's a URL, not specific image type
        )
        if self._previous_message is not None and self._previous_message.role == role:
            self._previous_message.prompt_data_list.append(prompt_data)
        else:
            new_content = PromptContent(role, [prompt_data])
            self._prompt.append(new_content)
            self._previous_message = new_content
        return self

    def add_json_input(self, role: PromptRole, json_input: dict | BaseModel, excluded_fields: Optional[set] = None) -> "PromptBuilder":
        if isinstance(json_input, BaseModel):
            # Use model_dump_json for Pydantic v2
            json_string = json_input.model_dump_json(exclude=excluded_fields, indent=2) # Added indent for readability
        elif isinstance(json_input, dict):
            if excluded_fields is not None:
                # Create a copy to avoid modifying the original dict
                filtered_dict = {k: v for k, v in json_input.items() if k not in excluded_fields}
            else:
                filtered_dict = json_input
            json_string = json.dumps(filtered_dict, indent=2) # Added indent
        else:
             raise TypeError(f"Expected dict or Pydantic BaseModel for json_input, got {type(json_input)}")

        prompt_data = PromptData(
            prompt_type=PromptType.TEXT_INPUT,
            file_data=json_string,
        )
        if self._previous_message is not None and self._previous_message.role == role:
            self._previous_message.prompt_data_list.append(prompt_data)
        else:
            new_content = PromptContent(role, [prompt_data])
            self._prompt.append(new_content)
            self._previous_message = new_content
        return self

    def build(self) -> list[ChatCompletionMessageParam]:
        built_messages = [p.to_message() for p in self._prompt]
        # Clear internal state after building if desired, or keep for potential reuse/modification
        # self._prompt = []
        # self._previous_message = None
        return built_messages

    @staticmethod
    def builder() -> "PromptBuilder":
        # Returns a new instance each time
        return PromptBuilder()


llm_service: Optional["LLMService"] = None


# https://learn.microsoft.com/en-us/azure/ai-services/openai/how-to/responses?tabs=python-secure
class LLMService:
    client: AzureOpenAI
    deployment_name: str
    T = TypeVar('T', bound=BaseModel)

    def __init__(self, endpoint_url: HttpUrl, api_key: str):
        if not isinstance(endpoint_url, HttpUrl):
            raise TypeError(f"Expected pydantic.HttpUrl for endpoint_url, got {type(endpoint_url)}")
        if not isinstance(api_key, str) or not api_key:
            raise TypeError(f"Expected non-empty string for api_key, got {type(api_key)}")

        # --- CORRECTED API VERSION EXTRACTION ---
        api_version = None
        # Use model_dump to get query params as dict if Pydantic v2+ (otherwise access ._query)
        query_params_list = endpoint_url.query_params() # returns list of tuples
        logger.debug(f"Raw query parameters list: {query_params_list}")
        for key, value in query_params_list:
            # Use case-insensitive comparison for 'api-version'
            if key.lower() == "api-version":
                api_version = value
                logger.info(f"Found api-version: {api_version}")
                break # Exit loop once found
        # --- END CORRECTION ---

        if api_version is None:
            raise ValueError("api-version is required in the endpoint URL query parameters (e.g., ?api-version=YYYY-MM-DD)")

        # Convert HttpUrl to string for the client
        azure_endpoint_str = str(endpoint_url)

        # Extract deployment name from the URL path
        try:
            # Example URL format: https://<res>.openai.azure.com/openai/deployments/<dep_name>/...
            path_parts = endpoint_url.path.strip('/').split('/') if endpoint_url.path else []
            # Find 'deployments' segment and get the next segment
            deployment_index = path_parts.index('deployments')
            if deployment_index + 1 >= len(path_parts):
                 raise IndexError("No segment found after 'deployments' in URL path.")
            self.deployment_name = path_parts[deployment_index + 1]
            if not self.deployment_name: # Check if the segment is empty
                 raise ValueError("Deployment name segment in URL path is empty.")
            logger.info(f"Extracted deployment name: {self.deployment_name}")
        except (ValueError, IndexError) as e:
            logger.error(f"Could not automatically extract deployment name from path '{endpoint_url.path}': {e}", exc_info=True)
            raise ValueError(
                "Could not extract deployment name from endpoint URL path. "
                "Expected format like '.../openai/deployments/<deployment-name>/...'"
            ) from e

        # Initialize the Azure OpenAI client
        try:
            self.client = AzureOpenAI(
                api_version=api_version,
                azure_endpoint=azure_endpoint_str, # Use the string URL
                api_key=api_key,
                # Consider adding timeout settings
                # timeout=httpx.Timeout(60.0, read=10.0, write=10.0, connect=3.0),
            )
            logger.info(f"AzureOpenAI client initialized for endpoint: {azure_endpoint_str} and deployment: {self.deployment_name}")
        except Exception as e:
            logger.error(f"Failed to initialize AzureOpenAI client: {e}", exc_info=True)
            # Raise a more specific error if possible, or a generic runtime error
            raise RuntimeError("Failed to initialize AzureOpenAI client") from e

    def generate_response(self, prompts: List[ChatCompletionMessageParam]) -> Optional[str]:
        """Generates a text response from the LLM."""
        if not prompts:
            logger.warning("generate_response called with empty prompts list.")
            return None
        try:
            logger.info(f"Sending request to deployment '{self.deployment_name}' with {len(prompts)} messages.")
            # logger.debug(f"Prompts: {prompts}") # Be cautious logging potentially large/sensitive prompts
            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=prompts,
                seed=42,  # For reproducibility, consider making this configurable
                temperature=0.0, # Low temperature for deterministic output
                # Consider adding max_tokens, top_p, etc. if needed
            )
            # Add checks for response structure
            if not response.choices:
                 logger.error("LLM response contained no choices.")
                 return None
            message = response.choices[0].message
            if message is None or message.content is None:
                 logger.error("LLM choice message or content was None.")
                 return None

            content = message.content
            logger.info("Successfully received response from LLM.")
            # logger.debug(f"LLM Response Content: {content[:500]}...") # Log snippet
            return content
        except Exception as e:
            # Log the specific error from the OpenAI library if available
            logger.error(f"Error during LLM request to deployment '{self.deployment_name}': {e}", exc_info=True)
            return None # Or raise CustomLLMError("Failed to generate response") from e

    def generate_structured_response(self, prompts: List[ChatCompletionMessageParam], response_format: Type[T]) -> Optional[T]:
        """Generates a structured response parsed into the specified Pydantic model."""
        if not prompts:
            logger.warning("generate_structured_response called with empty prompts list.")
            return None
        if not issubclass(response_format, BaseModel):
             raise TypeError("response_format must be a Pydantic BaseModel subclass.")

        try:
            logger.info(f"Sending request for structured response (type: {response_format.__name__}) to deployment '{self.deployment_name}' with {len(prompts)} messages.")
            # logger.debug(f"Prompts: {prompts}")
            # Note: '.beta.chat.completions.parse' might change in future openai library versions
            completion = self.client.beta.chat.completions.parse(
                model=self.deployment_name,
                messages=prompts,
                response_format=response_format,
                seed=42,
                temperature=0.0,
            )
            # Add checks for response structure
            if not completion.choices:
                 logger.error("Structured LLM response contained no choices.")
                 return None
            message = completion.choices[0].message
            if message is None or message.parsed is None:
                 logger.error("Structured LLM choice message or parsed content was None.")
                 return None

            parsed_response = message.parsed
            # Optional: Validate that the parsed response is actually an instance of the expected type
            if not isinstance(parsed_response, response_format):
                 logger.error(f"Parsed response type mismatch. Expected {response_format.__name__}, got {type(parsed_response).__name__}")
                 return None # Or attempt re-parsing / raise error

            logger.info(f"Successfully received and parsed structured response of type {response_format.__name__}.")
            # logger.debug(f"Parsed Response Object: {parsed_response}")
            return parsed_response
        except Exception as e:
            logger.error(f"Error during structured LLM request or parsing for deployment '{self.deployment_name}' and type '{response_format.__name__}': {e}", exc_info=True)
            return None # Or raise CustomLLMError("Failed to generate structured response") from e

    @staticmethod
    def init_singleton(endpoint_url: HttpUrl, api_key: str):
        global llm_service
        if llm_service is None:
            logger.info("Initializing LLMService singleton...")
            llm_service = LLMService(endpoint_url, api_key)
            logger.info("LLMService singleton initialized.")
        else:
             logger.warning("LLMService singleton already initialized.")


    @staticmethod
    def get_instance() -> "LLMService": # Use quotes for forward reference
        global llm_service
        if llm_service is None:
            logger.error("LLMService singleton accessed before initialization.")
            raise RuntimeError("LLMService has not been initialized. Call init_singleton first.")
        return llm_service

# TODO: delete me - Example Usage Block
if __name__ == '__main__':
    from dotenv import load_dotenv
    import os # Import os for path manipulation

    # Assuming these models are defined correctly in your project structure
    try:
        # Attempt to import your actual models
        from app.models import Rubric, SubRubric
        from app.models.rubric import GradingCriteria
        logger.info("Successfully imported app.models.")
    except ImportError:
        # Define dummy models for standalone testing if needed
        logger.warning("Could not import app.models. Using dummy models for testing.")
        class GradingCriteria(BaseModel):
            criteria_id: str
            criteria: str
            points: float
        class SubRubric(BaseModel):
            question_index: int
            max_points: float
            grading_criteria: List[GradingCriteria]
            instructor_guideline: Optional[str] = None
        class Rubric(BaseModel):
            semester: str
            course_id: str
            assignment_id: str
            grading_flags: Optional[List[str]] = None # Assuming flags are strings
            overall_instructor_guidelines: Optional[str] = None
            sub_rubrics: List[SubRubric]
            leniency: Optional[int] = None # Added leniency based on frontend code


    load_dotenv() # Load environment variables from .env file

    try:
        # Get sensitive info from environment variables
        endpoint_str = get_str_var("AZURE_LLM_DEPLOYMENT_URL")
        subscription_key = get_str_var("AZURE_LLM_DEPLOYMENT_KEY")
        # Use Pydantic v2 approach for URL parsing
        try:
            endpoint = HttpUrl(endpoint_str)
        except Exception as e:
            logger.error(f"Invalid Azure endpoint URL format: {endpoint_str} - {e}", exc_info=True)
            exit(1) # Exit if URL is invalid

        # Initialize the service
        LLMService.init_singleton(endpoint, subscription_key)
        llm = LLMService.get_instance()

        # --- Test Case 1: Basic Text Generation ---
        print("\n--- Test Case 1: Basic Text ---")
        prompt1 = (PromptBuilder.builder()
                   .add_message(PromptRole.SYSTEM, "You are a helpful assistant.")
                   .add_message(PromptRole.USER, "What is the capital of France?")
                   .add_message(PromptRole.USER, "And what is the capital of Spain?")
                   .build())
        response1 = llm.generate_response(prompt1)
        print(f"Response 1:\n{response1}\n")

        # --- Test Case 2: Image Input (Bytes) ---
        print("--- Test Case 2: Image Input (Bytes) ---")
        # Use relative path or ensure the absolute path is correct for your environment
        # Example: Get path relative to the current script directory
        script_dir = os.path.dirname(__file__) # Directory of the current script
        # Construct path - adjust 'Downloads/image.png' as needed
        default_image_path = os.path.join(script_dir, "..", "test_assets", "image.png") # Example relative path
        file_path_img = os.environ.get("TEST_IMAGE_PATH", default_image_path) # Allow override via env var

        if os.path.exists(file_path_img):
            try:
                with open(file_path_img, "rb") as img_file:
                    image_bytes = img_file.read()
                mime_type, _ = mimetypes.guess_type(file_path_img)
                # Ensure it's a supported image type for the model
                supported_image_types = ['image/png', 'image/jpeg', 'image/gif', 'image/webp']
                if mime_type not in supported_image_types:
                    raise ValueError(f"Unsupported image type: {mime_type}. Supported: {supported_image_types}")

                prompt2 = (PromptBuilder.builder()
                           .add_message(PromptRole.USER, "Describe the following image accurately.")
                           .add_image_bytes(PromptRole.USER, image_bytes, mime_type) # Pass correct mimetype
                           .add_message(PromptRole.USER, "Also, very briefly, do you like turtles?") # Adding another text part
                           .build())
                response2 = llm.generate_response(prompt2)
                print(f"Response 2:\n{response2}\n")
            except ValueError as e:
                print(f"ERROR: {e}. Skipping Test Case 2.")
            except Exception as e:
                print(f"An unexpected error occurred in Test Case 2: {e}")
        else:
             print(f"ERROR: Image file not found at '{file_path_img}'. Skipping Test Case 2.")


        # --- Test Case 3: Structured Output (Rubric Improvement) ---
        print("--- Test Case 3: Structured Output (Rubric) ---")
        # Example Rubric - Adjust if your model definition differs
        example_rubric = Rubric(
            semester="fall2024",
            course_id="CS101",
            assignment_id='1',
            grading_flags=["IGNORE_SPELLINGS"],
            overall_instructor_guidelines="Be moderately strict. Focus on clarity and correctness. Deduct points for major deviations.",
            leniency=3,
            sub_rubrics=[
                SubRubric(
                    question_index=0, # Use 0-based index
                    max_points=10.0,
                    grading_criteria=[], # Empty criteria list - AI should populate
                    instructor_guideline="Assess the student's explanation of the quicksort algorithm's time complexity.",
                ),
                SubRubric(
                    question_index=1, # Use 0-based index
                    max_points=5.0,
                    grading_criteria=[
                        GradingCriteria(criteria_id="correctness", criteria="Code compiles and runs producing the correct output for standard test cases.", points=2.0),
                        GradingCriteria(criteria_id="efficiency", criteria="Code uses reasonable data structures and avoids unnecessary computations.", points=1.0)
                        # Note: Points (3.0) don't sum to max_points (5.0) - AI should add/adjust criteria
                    ],
                    instructor_guideline="Evaluate the submitted Python code for sorting a list.",
                )
            ]
        )

        prompt3_system = ("You are an AI assistant specialized in improving grading rubrics for university courses. "
                          "Analyze the provided rubric JSON. For each sub-rubric: "
                          "1. Ensure the sum of points for its 'grading_criteria' equals the sub-rubric's 'max_points'. "
                          "2. If 'grading_criteria' are missing, create detailed criteria relevant to the 'instructor_guideline'. "
                          "3. If criteria exist but are vague or points don't sum up, revise them to be specific, measurable, and cover the 'max_points'. Ensure each criterion has a unique 'criteria_id'. "
                          "4. Do NOT change the 'question_index' or 'max_points' of any sub-rubric. "
                          "Respond ONLY with the improved rubric as a valid JSON object matching the provided Pydantic model structure. Do not include any explanatory text before or after the JSON.")

        prompt3 = (PromptBuilder.builder()
                   .add_message(PromptRole.SYSTEM, prompt3_system)
                   .add_message(PromptRole.USER, "Improve the following rubric JSON:")
                   .add_json_input(PromptRole.USER, example_rubric) # Pass the rubric model directly
                   .build())

        # Expecting the response to be parsable as a Rubric object
        structured_response = llm.generate_structured_response(prompt3, Rubric)
        if structured_response:
            # Use model_dump_json for Pydantic v2
            print(f"Structured Response (Improved Rubric):\n{structured_response.model_dump_json(indent=4)}\n")
        else:
            print("Failed to get or parse structured response for Test Case 3.\n")

        # --- Test Case 4: File Input (PDF Analysis - Placeholder) ---
        # This test case is highly dependent on the specific Azure model's capabilities
        # regarding file processing via the API (which is often limited).
        print("--- Test Case 4: File Input (PDF - Expect Warning/Potential Failure) ---")
        default_pdf_path = os.path.join(script_dir, "..", "test_assets", "report.pdf") # Example relative path
        other_file_path_pdf = os.environ.get("TEST_PDF_PATH", default_pdf_path)

        if os.path.exists(other_file_path_pdf):
            try:
                with open(other_file_path_pdf, "rb") as pdf_file:
                    pdf_bytes = pdf_file.read()

                prompt4 = (PromptBuilder.builder()
                           .add_message(PromptRole.USER, "You have been provided with a file named 'report.pdf'. What is this filename?")
                           # Providing filename and bytes, using INPUT_FILE type (warning expected)
                           .add_file_bytes(PromptRole.USER, DataType.PDF, "report.pdf", pdf_bytes)
                           .add_message(PromptRole.USER, "Based on the content (if accessible), provide a one-sentence summary. If you cannot access the content, state that.")
                           .build())
                response4 = llm.generate_response(prompt4)
                print(f"Response 4:\n{response4}\n")
            except Exception as e:
                print(f"An unexpected error occurred in Test Case 4: {e}")
        else:
            print(f"ERROR: PDF file not found at '{other_file_path_pdf}'. Skipping Test Case 4.")


    except ValueError as e:
         # Catch specific errors like missing env vars or invalid URL/API key format
         logger.error(f"Configuration Error: {e}", exc_info=True)
    except RuntimeError as e:
         # Catch errors during singleton initialization/retrieval
         logger.error(f"Runtime Error: {e}", exc_info=True)
    except Exception as e:
        # Catch any other unexpected errors during setup or execution
        logger.error(f"An unexpected error occurred in the main execution block: {e}", exc_info=True)