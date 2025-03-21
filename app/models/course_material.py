from typing import Optional, Union
from pydantic import BaseModel, Field
from app.models.uploaded_file import UploadedFileData, UploadedFileReference

class CourseMaterial(BaseModel):
    """
    Course material object.
    """
    course_id: str = Field(..., description="Associated course identifier.")
    semester: str = Field(..., description="The semester associated with the course.")
    material_id: str = Field(..., description="Unique material identifier.")
    material_name: str = Field(..., description="Title or name of the material.")
    additional_notes: Optional[str] = Field(
        None, description="Optional instructor notes."
    )
    data: Union[UploadedFileData, UploadedFileReference] = Field(
        ..., description="Either the uploaded file content or a reference to a previously stored file."
    )
