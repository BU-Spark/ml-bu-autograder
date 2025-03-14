from pydantic import BaseModel, EmailStr
from typing import List

class Course(BaseModel):
    """
    Course object representing a course.
    - **course_id**: Unique course identifier.
    - **course_name**: Name of the course.
    - **semester**: Semester when the course is offered.
    - **instructors**: List of instructor emails.
    """
    course_id: str
    course_name: str
    semester: str
    instructors: List[EmailStr]
