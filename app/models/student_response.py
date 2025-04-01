from typing import Union, Optional

from pydantic import BaseModel, Field, validator

from app.models import Grade
from app.models.uploaded_file import UploadedFileData, UploadedFileReference


class StudentResponse(BaseModel):
    """
    Represents a student’s answer to a question.
    """
    student_id: str = Field(
        ..., description="Unique identifier for the student submitting the response."
    )
    semester: str = Field(
        ..., description="The semester associated with the course."
    )
    course_id: str = Field(
        ..., description="The course identifier."
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

    @validator("student_id", "semester", "course_id", "assignment_id", pre=True, always=True)
    def normalize_lowercase(cls, value: str) -> str:
        """Converts course_id and semester to lowercase and trims spaces."""
        return value.strip().lower()


class GradedStudentResponse(StudentResponse):
    grade: Optional[Grade] = Field(..., description="The grade the LLM gave this student response. If this assignment "
                                                    "is not yet graded, the grade object may not be present.")
