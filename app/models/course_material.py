from pydantic import BaseModel
from typing import Optional

from app.models import UploadedFile


class CourseMaterial(BaseModel):
    """
    Course material object.
    - **course_id**: Associated course identifier.
    - **material_id**: Unique material identifier.
    - **material_name**: Title or name of the material.
    - **additional_notes**: Optional instructor notes.
    - **data**: DataContent for the file.
    """
    course_id: str
    material_id: str
    material_name: str
    additional_notes: Optional[str] = None
    data: UploadedFile
