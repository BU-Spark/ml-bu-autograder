from pydantic import BaseModel

from app.models.uploaded_file import UploadedFile


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
