import re
from typing import Optional, Union

from pydantic import BaseModel, Field, field_validator

from app.models.uploaded_file import UploadedFileData, UploadedFileReference


class CourseMaterial(BaseModel):
    """
    Course material object.
    """
    semester: str = Field(..., description="The semester associated with the course.")
    course_id: str = Field(..., description="Associated course identifier.")
    material_id: int = Field(..., description="Unique material identifier.")
    material_name: str = Field(..., description="Title or name of the material.")
    additional_notes: Optional[str] = Field(
        None, description="Optional instructor notes."
    )
    data: Union[UploadedFileData, UploadedFileReference] = Field(
        ..., description="Either the uploaded file content or a reference to a previously stored file."
    )

    
    @field_validator("course_id", mode="before")
    def normalize_lowercase(cls, value: str) -> str:
        """Converts course_id and semester to lowercase and trims spaces."""
        return value.strip().lower()

    @field_validator("semester", mode='before')
    def validate_semester(cls, value: str) -> str:
        """Converts to lowercase and trims spaces."""
        if re.fullmatch("[a-z]{1,12}[0-9]{4}", value) is None:
            raise ValueError("Semester is in an invalid format. "
                             "Correct format (case-sensetive) looks like: seasonYYYY. (e.g. spring2025)")
        return value.strip().lower()
