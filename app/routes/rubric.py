import re
from typing import Optional

from fastapi import APIRouter, HTTPException, status, Query, Body
from pydantic import Field, BaseModel, field_validator

from app.models import Course
from app.models.rubric import Rubric, SubRubric, GradingFlag
from app.utils import JWTService
from app.utils.azure_blob_service import AzureBlobService

router = APIRouter()
user_from_auth = JWTService.get_instance().from_authorization_header


class EditSubRubricRequest(BaseModel):
    """
    Request model for editing a sub-rubric of an assignment.
    Allows modification of grading criteria for individual questions.
    """
    semester: str = Field(..., description="Semester of the course.")
    course_id: str = Field(..., description="Identifier of the course.")
    assignment_id: int = Field(..., description="Identifier of the assignment.")
    sub_rubric: SubRubric = Field(...,
                                  description="Sub-rubric object containing grading instructions and criteria for that specific question.")

    @classmethod
    @field_validator("semester", mode='before')
    def validate_semester(cls, value: str) -> str:
        """Converts to lowercase and trims spaces."""
        if re.fullmatch("[a-zA-Z]{1,12}[0-9]{4}", value) is not None:
            raise ValueError("Semester is in an invalid format. "
                             "Correct format looks like: seasonYYYY. (e.g. spring2025)")
        return value.strip().lower()


# Dummy storage for rubrics
dummy_rubrics = []


@router.put(
    "/rubric",
    response_model=Rubric,
    summary="Create Rubric",
    description="Manually creates a new rubric for an assignment.",
    responses={
        400: {"description": "Missing or invalid parameters."},
        404: {"description": "Assignment not found."},
        401: {"description": "Requester is not authenticated."},
        403: {"description": "Authenticated but access is not allowed."}
    }
)
async def create_rubric(
        rubric: Rubric = Body(..., description="Rubric object containing grading instructions and sub-rubrics.")
):
    blob_uploader = AzureBlobService.get_instance()
    dummy_rubrics.append(rubric)
    return rubric


@router.get(
    "/ai_rubric",
    response_model=Rubric,
    summary="Enhance Rubric with AI",
    description="Enhances an existing rubric using AI-based improvements. If a rubric does not exist for the given assignment, a new one is generated. Note: This only proposes a new rubric and does not modify an existing one.",
    responses={
        502: {"description": "External LLM API call failure."},
        401: {"description": "Requester is not authenticated."},
        403: {"description": "Authenticated but access is not allowed."}
    }
)
async def get_ai_rubric(
        semester: str = Field(..., description="Semester of the course."),
        course_id: str = Field(..., description="Identifier of the course."),
        assignment_id: int = Query(..., description="Identifier of the assignment."),
        instructions: Optional[str] = Query(None, description="Optional specific improvement instructions for the AI.")
):
    # validate params
    semester = Course.validate_semester(semester)
    course_id = Course.normalize_lowercase(course_id)

    blob_uploader = AzureBlobService.get_instance()
    dummy_rubric = Rubric(
        semester="spring2024",
        course_id="cs123",
        assignment_id=assignment_id,
        grading_flags=[GradingFlag.IGNORE_SPELLINGS],
        leniency=4,
        overall_instructor_guidelines="Improved guidelines based on AI.",
        sub_rubrics=[]
    )
    return dummy_rubric


@router.get(
    "/rubric",
    response_model=Rubric,
    summary="Get Rubric",
    description="Retrieves the rubric for a specified assignment (or for a specific question).",
    responses={
        404: {"description": "Rubric or specified question not found."},
        401: {"description": "Requester is not authenticated."},
        403: {"description": "Authenticated but access is not allowed."}
    }
)
async def get_rubric(
        semester: str = Field(..., description="Semester of the course."),
        course_id: str = Field(..., description="Identifier of the course."),
        assignment_id: int = Query(..., description="Identifier of the assignment."),
        question_index: Optional[int] = Query(None,
                                              description="Optional question index to retrieve a specific sub-rubric.")
):
    # validate params
    semester = Course.validate_semester(semester)
    course_id = Course.normalize_lowercase(course_id)

    blob_uploader = AzureBlobService.get_instance()
    for rubric in dummy_rubrics:
        if rubric.assignment_id == assignment_id:
            return rubric
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rubric not found.")
