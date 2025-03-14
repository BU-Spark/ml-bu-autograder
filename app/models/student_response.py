from pydantic import BaseModel
from typing import Optional

from app.models import UploadedFile


class ResponseData(BaseModel):
    """
    Data structure for student response content.
    - **data_type**: Type of the data (e.g., .png, .pdf, .doc, URL).
    - **metadata**: Optional metadata for the file.
    - **content**: Binary content encoded in Base64.
    """
    data_type: str
    metadata: Optional[str] = None
    content: str


class StudentResponse(BaseModel):
    """
    Represents a student’s answer to a question.
    - **student_identifier**: Student's unique identifier.
    - **assignment_id**: The assignment’s identifier.
    - **question_index**: The index of the question answered.
    - **data**: ResponseData containing the answer content.
    """
    student_identifier: str
    assignment_id: str
    question_index: int
    data: UploadedFile
