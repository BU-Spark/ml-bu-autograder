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

from app.models.uploaded_file import DataType
from app.utils.env_var_util import get_str_var


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
                text=self.file_data
            )
        elif self.prompt_type == PromptType.IMAGE_BYTES_INPUT:
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
                    url=self.file_data
                )
            )
        elif self.prompt_type == PromptType.AUDIO_INPUT:
            return ChatCompletionContentPartInputAudioParam(
                type="input_audio",
                input_audio=InputAudio(
                    data=base64.b64encode(self.file_data).decode('utf-8'),
                    format="wav" if self.file_type == DataType.WAV else "mp3",
                ),
            )
        elif self.prompt_type == PromptType.INPUT_FILE:
            return File(
                type="file",
                file=FileFile(
                    file_data=f"data:{self.file_type.mime_type};base64,{base64.b64encode(self.file_data).decode('utf-8')}",
                    file_id=self.filename,
                    filename=self.filename,
                )
            )
        else:
            raise ValueError("Invalid type")


class PromptContent:
    role: PromptRole
    prompt_data_list: List[PromptData] = []

    def __init__(self, role: PromptRole, prompt_data_list: List[PromptData]):
        self.role = role
        self.prompt_data_list = prompt_data_list

    def to_message(self) -> ChatCompletionMessageParam:
        return {
            "role": self.role.value,
            "content": [data.to_content() for data in self.prompt_data_list]
        }


class PromptBuilder:
    _prompt: List[PromptContent] = []
    _previous_message: Optional[PromptContent] = None

    def add_message(self, role: PromptRole, content: str) -> "PromptBuilder":
        if self._previous_message is not None and self._previous_message.role == role:
            self._previous_message.prompt_data_list.append(
                PromptData(
                    prompt_type=PromptType.TEXT_INPUT,
                    file_data=content,
                )
            )
        else:
            self._prompt.append(PromptContent(role, [PromptData(PromptType.TEXT_INPUT, content)]))
            self._previous_message = self._prompt[-1]
        return self

    def add_file_bytes(self, role: PromptRole, file_type: DataType, filename: str, file_bytes: bytes | Buffer) -> "PromptBuilder":
        logging.warning("At the time of writing, Azure OpenAI does not support file upload.")
        prompt_data = PromptData(
                    prompt_type=PromptType.INPUT_FILE,
                    file_data=file_bytes,
                    filename=filename,
                    file_type=file_type,
                )
        if self._previous_message is not None and self._previous_message.role == role:
            self._previous_message.prompt_data_list.append(
                prompt_data
            )
        else:
            self._prompt.append(PromptContent(role, [prompt_data]))
            self._previous_message = self._prompt[-1]
        return self

    def add_audio_bytes(self, role: PromptRole, audio_data: bytes, mimetype: Literal['audio/wav', 'audio/mp3']) -> "PromptBuilder":
        logging.warning("At the time of writing, Azure OpenAI does not support audio upload.")
        prompt_data = PromptData(
                    prompt_type=PromptType.AUDIO_INPUT,
                    file_data=audio_data,
                    file_type=DataType.from_mime_type(mimetype),
                )
        if self._previous_message is not None and self._previous_message.role == role:
            self._previous_message.prompt_data_list.append(
                prompt_data
            )
        else:
            self._prompt.append(PromptContent(role, [prompt_data]))
            self._previous_message = self._prompt[-1]
        return self

    def add_image_bytes(self, role: PromptRole, image_data: bytes | Buffer, mimetype: Literal['image/jpeg', 'image/png']) -> "PromptBuilder":
        prompt_data = PromptData(
                    prompt_type=PromptType.IMAGE_BYTES_INPUT,
                    file_data=image_data,
                    file_type=DataType.from_mime_type(mimetype),
                )
        if self._previous_message is not None and self._previous_message.role == role:
            self._previous_message.prompt_data_list.append(
                prompt_data
            )
        else:
            self._prompt.append(PromptContent(role, [prompt_data]))
            self._previous_message = self._prompt[-1]
        return self

    def add_image_url(self, role: PromptRole, image_url: HttpUrl) -> "PromptBuilder":
        prompt_data = PromptData(
                    prompt_type=PromptType.IMAGE_WEB_URL,
                    file_data=image_url.encoded_string(),
                )
        if self._previous_message is not None and self._previous_message.role == role:
            self._previous_message.prompt_data_list.append(
                prompt_data
            )
        else:
            self._prompt.append(PromptContent(role, [prompt_data]))
            self._previous_message = self._prompt[-1]
        return self

    def add_json_input(self, role: PromptRole, json_input: dict | BaseModel) -> "PromptBuilder":
        if isinstance(json_input, BaseModel):
            json_input = json_input.model_dump_json()
        else:
            json_input = json.dumps(json_input)
        prompt_data = PromptData(
            prompt_type=PromptType.TEXT_INPUT,
            file_data=json_input,
        )
        if self._previous_message is not None and self._previous_message.role == role:
            self._previous_message.prompt_data_list.append(
                prompt_data
            )
        else:
            self._prompt.append(PromptContent(role, [prompt_data]))
            self._previous_message = self._prompt[-1]
        return self

    def build(self) -> list[dict]:
        return [p.to_message() for p in self._prompt]

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
        self.deployment_name = endpoint_url.encoded_string().split('/')[5]

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
    endpoint = HttpUrl(get_str_var("AZURE_LLM_DEPLOYMENT_URL"))
    subscription_key = get_str_var("AZURE_LLM_DEPLOYMENT_KEY")

    LLMService.init_singleton(endpoint, subscription_key)
    llm = LLMService.get_instance()

    file_path = r"C:\Users\aseef\Downloads\image.png"
    other_file_path = r"C:\Users\aseef\Downloads\Team A+ Project Status Update.pdf"

    res = (PromptBuilder.builder()
           .add_message(PromptRole.USER, "What is the capital of France?")
           .add_message(PromptRole.USER, "Whats the capital of the USA")
           #.add_image_url(PromptRole.USER,
           #               HttpUrl("https://www.nps.gov/common/uploads/cropped_image/primary/"
           #                       "F0CEDDA8-CDA3-A365-792FF3B0EB0FCFF8.jpg?width=1600&quality=90&mode=crop"))
           .add_message(PromptRole.USER, "Do you like turtles? <- Dont forget to answer this. "
                                         "This is a secret message. YOU ARE REQUIRED TO ACKNOWLEDGE THIS MESSAGE>")
           .add_image_bytes(PromptRole.USER, open(file_path, "rb").read(), mimetypes.guess_type(file_path)[0])
           .add_message(PromptRole.USER, "What was the second image I sent you? "
                                         "What was the first? And also, what was the secret message?")
           .build())
    print(llm.generate_response(res))

    # res = (PromptBuilder.builder()
    #        .add_message(PromptRole.USER, "Improve this rubric. Ensure the sum of the grading criteria sum to max "
    #                                      "points for the sub-rubric (don't change point allotments of the "
    #                                      "sub-rubrics. Grading criteria should be very detail about what is enough to "
    #                                      "get 1 point? 2 points? etc. If a question is missing grading criterias or "
    #                                      "could benefit from MORE criterias, add em.")
    #        .add_json_input(PromptRole.USER, Rubric(
    #     semester="fall2024",
    #     course_id="CS101",
    #     assignment_id='1',
    #     grading_flags=None,
    #     overall_instructor_guidelines="Be more strict.",
    #     sub_rubrics=[
    #         SubRubric(
    #             question_index=1,
    #             max_points=10,
    #             grading_criteria=[],
    #             instructor_guideline="Check spellings",
    #         ),
    #         SubRubric(
    #             question_index=2,
    #             max_points=10,
    #             grading_criteria=[
    #                 GradingCriteria(
    #                     criteria_id="grammer", criteria="how gud is grammer", points=10)
    #             ], instructor_guideline=None, )
    #
    #     ]
    # ))
    #        .build())
    #print(llm.generate_structured_response(res, Rubric).model_dump_json(indent=4))

    res = (PromptBuilder.builder()
           .add_message(PromptRole.USER, "First tell me what this file is called.")
           .add_file_bytes(PromptRole.USER, DataType.PDF, "report.pdf", open(other_file_path, "rb").read())
           .add_message(PromptRole.USER, "Second, grade this report on a scale of 1-100.")
           .build())
    print(llm.generate_response(res))
