from typing import Optional

from fastapi import APIRouter, HTTPException, status, Query, Body
from pydantic import Field, BaseModel

from app.models.rubric import Rubric, SubRubric
from app.utils import JWTService
from app.utils.azure_blob_service import AzureBlobService

router = APIRouter()
user_from_authorization_header = None


@router.on_event("startup")
async def set_user_from_auth_header():
    global user_from_authorization_header
    user_from_authorization_header = JWTService.get_instance().from_authorization_header


class EditSubRubricRequest(BaseModel):
    """
    Request model for editing a sub-rubric of an assignment.
    Allows modification of grading criteria for individual questions.
    """
    semester: str = Field(..., description="Semester of the course.")
    course_id: str = Field(..., description="Identifier of the course.")
    assignment_id: str = Field(..., description="Identifier of the assignment.")
    sub_rubric: SubRubric = Field(...,
                                  description="Sub-rubric object containing grading instructions and criteria for that specific question.")


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
        assignment_id: str = Query(..., description="Identifier of the assignment."),
        instructions: Optional[str] = Query(None, description="Optional specific improvement instructions for the AI.")
):
    blob_uploader = AzureBlobService.get_instance()
    dummy_rubric = Rubric(
        assignment_id=assignment_id,
        grading_flags=["IGNORE_SPELLINGS", "IGNORE_GRAMMAR"],
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
        assignment_id: str = Query(..., description="Identifier of the assignment."),
        question_index: Optional[int] = Query(None,
                                              description="Optional question index to retrieve a specific sub-rubric.")
):
    blob_uploader = AzureBlobService.get_instance()
    for rubric in dummy_rubrics:
        if rubric.assignment_id == assignment_id:
            return rubric
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rubric not found.")
