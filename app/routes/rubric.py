from fastapi import APIRouter, HTTPException, status
from typing import Optional
from app.models.rubric import Rubric

router = APIRouter()

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
async def create_rubric(rubric: Rubric):
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
async def get_ai_rubric(assignment_id: str, instructions: Optional[str] = None):
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
async def get_rubric(assignment_id: str, question_index: Optional[int] = None):
    for rubric in dummy_rubrics:
        if rubric.assignment_id == assignment_id:
            return rubric
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rubric not found.")
