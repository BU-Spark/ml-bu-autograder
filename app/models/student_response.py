from typing import Union

from pydantic import BaseModel, Field
from app.models.uploaded_file import UploadedFileData, UploadedFileReference

class StudentResponse(BaseModel):
    """
    Represents a student’s answer to a question.
    """
    student_identifier: str = Field(
        ..., description="Unique identifier for the student submitting the response."
    )
    assignment_id: str = Field(
        ..., description="Identifier of the assignment the response belongs to."
    )
    question_index: int = Field(
        ..., description="Index of the question being answered within the assignment."
    )
    data: Union[UploadedFileData, UploadedFileReference] = Field(
        ..., description="Either the uploaded file content or a reference to a previously stored file."
    )
