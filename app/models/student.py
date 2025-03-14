from pydantic import BaseModel
from typing import Optional

class Student(BaseModel):
    """
    Student object containing basic information.
    - **student_identifier**: Unique identifier (e.g., BU email).
    - **first_name**: Optional first name.
    - **last_name**: Optional last name.
    """
    student_identifier: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
