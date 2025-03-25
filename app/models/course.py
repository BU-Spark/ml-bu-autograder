from typing import List
from pydantic import BaseModel, EmailStr, Field

class Course(BaseModel):
    """
    Course object representing a course.
    """
    course_id: str = Field(..., description="Unique course identifier, usually its name.")
    semester: str = Field(..., description="Semester when the course is offered.")
    instructors: List[EmailStr] = Field(
        ..., description="List of instructor emails associated with the course."
    )
