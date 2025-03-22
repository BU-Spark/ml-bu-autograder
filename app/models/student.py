from typing import Optional
from pydantic import BaseModel, Field

class Student(BaseModel):
    """
    Student object containing basic information.
    """
    student_id: str = Field(
        ..., description="Unique identifier for the student (e.g., BU email)."
    )
    first_name: Optional[str] = Field(
        None, description="Optional first name of the student."
    )
    last_name: Optional[str] = Field(
        None, description="Optional last name of the student."
    )
