from typing import Optional
from pydantic import BaseModel, Field
from app.models.uploaded_file import UploadedFile

class CourseMaterial(BaseModel):
    """
    Course material object.
    """
    course_id: str = Field(..., description="Associated course identifier.")
    material_id: str = Field(..., description="Unique material identifier.")
    material_name: str = Field(..., description="Title or name of the material.")
    additional_notes: Optional[str] = Field(
        None, description="Optional instructor notes."
    )
    data: UploadedFile = Field(..., description="DataContent for the file.")
