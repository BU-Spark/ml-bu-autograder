from typing import List
from pydantic import BaseModel, EmailStr, Field

class Course(BaseModel):
    """
    Course object representing a course.
    """
    course_id: str = Field(..., description="Unique course identifier.")
    course_name: str = Field(..., description="Name of the course.")
    semester: str = Field(..., description="Semester when the course is offered.")
    instructors: List[EmailStr] = Field(
        ..., description="List of instructor emails associated with the course."
    )
