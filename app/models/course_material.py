from typing import Optional, Union
from pydantic import BaseModel, Field, validator
from app.models.uploaded_file import UploadedFileData, UploadedFileReference

class CourseMaterial(BaseModel):
    """
    Course material object.
    """
    semester: str = Field(..., description="The semester associated with the course.")
    course_id: str = Field(..., description="Associated course identifier.")
    material_id: str = Field(..., description="Unique material identifier.")
    material_name: str = Field(..., description="Title or name of the material.")
    additional_notes: Optional[str] = Field(
        None, description="Optional instructor notes."
    )
    data: Union[UploadedFileData, UploadedFileReference] = Field(
        ..., description="Either the uploaded file content or a reference to a previously stored file."
    )

    @validator("semester", "course_id", "material_id", pre=True, always=True)
    def normalize_lowercase(cls, value: str) -> str:
        """Converts course_id and semester to lowercase and trims spaces."""
        return value.strip().lower()
