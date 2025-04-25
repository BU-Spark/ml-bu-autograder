import re
from typing import Optional, Union

from pydantic import BaseModel, Field, field_validator, FilePath

from app.models.uploaded_file import UploadedFileData, UploadedFileReference


class CourseMaterial(BaseModel):
    """
    Course material object.
    """
    semester: str = Field(..., description="The semester associated with the course.")
    course_id: str = Field(..., description="Associated course identifier.")
    material_id: str = Field(..., description="The unique title or name of the material.")
    # TODO: would be nice to support some additional notes for LLM for course material adding more
    #  context but not worth the time supporting ATM.
    # additional_notes: Optional[str] = Field(
    #     None, description="Optional instructor notes."
    # )

    @field_validator("semester", mode='before')
    def validate_semester(cls, value: str) -> str:
        """Converts to lowercase and trims spaces."""
        if re.fullmatch("[a-z]{1,12}[0-9]{4}", value) is None:
            raise ValueError("Semester is in an invalid format. "
                             "Correct format (case-sensitive) looks like: seasonYYYY. (e.g. spring2025)")
        return value.strip().lower()


class CourseMaterialReference(CourseMaterial):
    data: UploadedFileReference = Field(
        ..., description="The uri reference to a previously stored course material."
    )


class CourseMaterialData(CourseMaterial):
    data: UploadedFileData = Field(
        ..., description="The binary content of the course material (must be uploaded as a base64 string)."
    )
