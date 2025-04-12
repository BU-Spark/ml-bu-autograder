import base64
import json
import mimetypes
from enum import Enum
from typing import Optional, List, Type, TypeVar

from openai import AzureOpenAI
from pydantic import HttpUrl, BaseModel
from typing_extensions import Buffer

from app.models import Rubric, SubRubric
from app.models.rubric import GradingCriteria
from app.utils import env_var_util


class PromptType(Enum):
    TEXT_INPUT = 1, "text"
    IMAGE_BYTES_INPUT = 2, "image_url"
    IMAGE_WEB_URL = 3, "image_url"
    AUDIO_INPUT = 4, "input_audio"
    INPUT_FILE = 5, "file"


class PromptRole(Enum):
    SYSTEM = "system"
    USER = "user"


class FileData:
    mimetype: str
    img_data: Buffer | bytes

    def __init__(self, mimetype: str, img_data: Buffer | bytes):
        self.mimetype = mimetype
        self.img_data = img_data


class PromptData:
    prompt_type: PromptType
    data: str | FileData

    def __init__(self, prompt_type: PromptType, data: str | FileData):
        self.prompt_type = prompt_type
        self.data = data

    def to_dict(self) -> dict:
        if self.prompt_type == PromptType.TEXT_INPUT:
            return {
                "type": self.prompt_type.value[1],
                "text": self.data
            }
        elif self.prompt_type == PromptType.IMAGE_BYTES_INPUT or self.prompt_type == PromptType.INPUT_FILE:
            base64_data = base64.b64encode(self.data.img_data).decode('utf-8')
            return {
                "type": self.prompt_type.value[1],
                "image_url": {
                    "url": f"data:image/{self.data.mimetype};base64,{base64_data}"
                }
            }
        elif self.prompt_type == PromptType.IMAGE_WEB_URL:
            return {
                "type": self.prompt_type.value[1],
                "image_url": {
                    "url": f"{self.data}"
                }
            }
        elif self.prompt_type == PromptType.AUDIO_INPUT:
            raise ValueError("Unsupported type")
        else:
            raise ValueError("Invalid type")


class PromptContent:
    role: PromptRole
    prompt_data_list: List[PromptData] = []

    def __init__(self, role: PromptRole, prompt_data_list: List[PromptData]):
        self.role = role
        self.prompt_data_list = prompt_data_list

    def to_dict(self) -> dict:
        return {
            "role": self.role.value,
            "content": [data.to_dict() for data in self.prompt_data_list]
        }


class PromptBuilder:
    _prompt: List[PromptContent] = []
    _previous_message: Optional[PromptContent] = None

    def add_message(self, role: PromptRole, content: str) -> "PromptBuilder":
        if self._previous_message is not None and self._previous_message.role == role:
            self._previous_message.prompt_data_list.append(
                PromptData(
                    prompt_type=PromptType.TEXT_INPUT,
                    data=content,
                )
            )
        else:
            self._prompt.append(PromptContent(role, [PromptData(PromptType.TEXT_INPUT, content)]))
            self._previous_message = self._prompt[-1]
        return self

    def add_file_bytes(self, role: PromptRole, file_data: FileData) -> "PromptBuilder":
        if self._previous_message is not None and self._previous_message.role == role:
            self._previous_message.prompt_data_list.append(
                PromptData(
                    prompt_type=PromptType.INPUT_FILE,
                    data=file_data,
                )
            )
        else:
            self._prompt.append(PromptContent(role, [PromptData(PromptType.INPUT_FILE, file_data)]))
            self._previous_message = self._prompt[-1]
        return self

    def add_image_bytes(self, role: PromptRole, image_data: FileData) -> "PromptBuilder":
        if self._previous_message is not None and self._previous_message.role == role:
            self._previous_message.prompt_data_list.append(
                PromptData(
                    prompt_type=PromptType.IMAGE_BYTES_INPUT,
                    data=image_data,
                )
            )
        else:
            self._prompt.append(PromptContent(role, [PromptData(PromptType.IMAGE_BYTES_INPUT, image_data)]))
            self._previous_message = self._prompt[-1]
        return self

    def add_image_url(self, role: PromptRole, image_url: HttpUrl) -> "PromptBuilder":
        if self._previous_message is not None and self._previous_message.role == role:
            self._previous_message.prompt_data_list.append(
                PromptData(
                    prompt_type=PromptType.IMAGE_WEB_URL,
                    data=image_url.encoded_string(),
                )
            )
        else:
            self._prompt.append(PromptContent(role, [PromptData(PromptType.IMAGE_WEB_URL, image_url.encoded_string())]))
            self._previous_message = self._prompt[-1]
        return self

    def add_json_input(self, role: PromptRole, json_input: dict | BaseModel) -> "PromptBuilder":
        if isinstance(json_input, BaseModel):
            json_input = json_input.model_dump_json()
        else:
            json_input = json.dumps(json_input)
        if self._previous_message is not None and self._previous_message.role == role:
            self._previous_message.prompt_data_list.append(
                PromptData(
                    prompt_type=PromptType.TEXT_INPUT,
                    data=json_input,
                )
            )
        else:
            self._prompt.append(PromptContent(role, [PromptData(PromptType.TEXT_INPUT, json_input)]))
            self._previous_message = self._prompt[-1]
        return self

    def build(self) -> list[dict]:
        return [p.to_dict() for p in self._prompt]

    @staticmethod
    def builder() -> "PromptBuilder":
        return PromptBuilder()


llm_service: Optional["LLMService"] = None


# https://learn.microsoft.com/en-us/azure/ai-services/openai/how-to/responses?tabs=python-secure
class LLMService:
    client: AzureOpenAI
    T = TypeVar('T', bound=BaseModel)

    def __init__(self, endpoint_url: HttpUrl, api_key: str):
        api_version = None
        for param in endpoint_url.query_params():
            if param[0] == "api-version":
                api_version = param[1]
                break
        if api_version is None:
            raise ValueError("api-version is required in the endpoint URL")
        self.client = AzureOpenAI(
            api_version=api_version,
            azure_endpoint=endpoint_url.encoded_string(),
            api_key=api_key,
        )
        self.deployment_name = endpoint_url.encoded_string().split('/')[3]

    def generate_response(self, prompts: List[dict]) -> str:
        response = self.client.chat.completions.create(
            model=self.deployment_name,
            messages=prompts,
            seed=42,  # 100% reproducibility
            temperature=0.0,
        )
        return response.choices[0].message.content

    def generate_structured_response(self, prompts: List[dict], response_format: Type[T]) -> T:
        completion = self.client.beta.chat.completions.parse(
            model=self.deployment_name,
            # replace with the model deployment name of your gpt-4o 2024-08-06 deployment
            messages=prompts,
            response_format=response_format,
        )
        return completion.choices[0].message.parsed

    @staticmethod
    def init_singleton(endpoint_url: HttpUrl, api_key: str):
        global llm_service
        llm_service = LLMService(endpoint_url, api_key)

    @staticmethod
    def get_instance() -> Optional["LLMService"]:
        global llm_service
        return llm_service


# TODO: delete me
if __name__ == '__main__':
    from dotenv import load_dotenv

    load_dotenv()
    endpoint = HttpUrl(env_var_util.get_str_var("AZURE_LLM_DEPLOYMENT_URL"))
    subscription_key = env_var_util.get_str_var("AZURE_LLM_DEPLOYMENT_KEY")

    LLMService.init_singleton(endpoint, subscription_key)
    llm = LLMService.get_instance()

    file_path = r"C:\Users\aseef\Downloads\image.png"
    file_data = FileData(mimetypes.guess_type(file_path)[0], open(file_path, "rb").read())

    res = (PromptBuilder.builder()
           .add_message(PromptRole.USER, "What is the capital of France?")
           .add_message(PromptRole.USER, "Whats the capital of the USA")
           .add_image_url(PromptRole.USER,
                          HttpUrl("https://www.nps.gov/common/uploads/cropped_image/primary/"
                                  "F0CEDDA8-CDA3-A365-792FF3B0EB0FCFF8.jpg?width=1600&quality=90&mode=crop"))
           .add_message(PromptRole.USER, "Do you like turtles?")
           .add_image_bytes(PromptRole.USER, file_data)
           .add_message(PromptRole.USER, "What was the second image I sent you? What was the first?")
           .build())
    # print(llm.generate_response(res))

    res = (PromptBuilder.builder()
           .add_message(PromptRole.USER, "Improve this rubric.")
           .add_json_input(PromptRole.USER, Rubric(
        semester="fall2024",
        course_id="CS101",
        assignment_id=1,
        grading_flags=None,
        leniency=3,
        overall_instructor_guidelines="Be more strict.",
        sub_rubrics=[
            SubRubric(
                question_index=1,
                max_points=10,
                grading_criteria=[],
                leniency=2,
                instructor_guideline="Check spellings",
            ),
            SubRubric(
                question_index=2,
                max_points=10,
                grading_criteria=[
                    GradingCriteria(
                        criteria_id="grammer", criteria="how gud is grammer", points=5)
                ],
                leniency=2, instructor_guideline=None, )

        ]
    ))
           .build())
    print(llm.generate_structured_response(res, Rubric).model_dump_json(indent=4))
