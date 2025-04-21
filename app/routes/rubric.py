# app/routes/rubric.py

import re
from typing import Optional, List
from fastapi import APIRouter, HTTPException, status, Query, Body, Depends
from pydantic import Field, BaseModel, field_validator

from app.models import Course
# Rubric model now expects assignment_id as str
from app.models.rubric import Rubric, SubRubric, GradingFlag
from app.utils import JWTService, UserToken
from app.utils.azure_blob_service import AzureBlobService
import logging

logger = logging.getLogger(__name__)

router = APIRouter()
user_from_auth = JWTService.get_instance().from_authorization_header

# Removed unused EditSubRubricRequest model definition


@router.put(
    "/rubric",
    response_model=Rubric,
    summary="Create or Replace Rubric",
    description="Manually creates or completely replaces a rubric for an assignment.",
    # ... responses ...
)
async def create_or_replace_rubric(
        # Body expects Rubric model (which now expects assignment_id: str)
        rubric: Rubric = Body(..., description="Rubric object..."),
        user_meta: UserToken = Depends(user_from_auth),
):
    blob_uploader = AzureBlobService.get_instance()
    semester = rubric.semester
    course_id = rubric.course_id
    assignment_id = rubric.assignment_id # This is now a str

    # Auth Checks...
    if not blob_uploader.course_exists(semester, course_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course does not exist.")
    user = blob_uploader.get_user(user_meta.user_email)
    if not user or (semester, course_id) not in user.authenticated_courses:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User not found or access not allowed.")

    # Check if assignment exists (pass the str ID)
    # Ensure assignment_exists in AzureBlobService handles str ID
    if not blob_uploader.assignment_exists(semester, course_id, assignment_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment does not exist.")

    # Upload the rubric (pass the str ID)
    # Ensure upload_rubric in AzureBlobService handles str ID
    try:
        blob_uploader.upload_rubric(semester, course_id, assignment_id, rubric)
        logger.info(f"Rubric created/replaced for assignment {assignment_id} in {semester}/{course_id}")
        return rubric
    except Exception as e:
         logger.exception(f"Failed to upload rubric for assignment {assignment_id} in {semester}/{course_id}: {e}")
         raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to save rubric.")


@router.get(
    "/ai_rubric",
    response_model=Rubric,
    summary="Get AI Rubric Suggestion",
    # ... responses ...
)
async def get_ai_rubric(
        semester: str = Query(..., description="Semester..."),
        course_id: str = Query(..., description="Course ID."),
        # --- CHANGED TYPE: Back to str ---
        assignment_id: str = Query(..., description="Assignment ID."),
        # --- END CHANGE ---
        instructions: Optional[str] = Query(None, description="Optional instructions..."),
        user_meta: UserToken = Depends(user_from_auth),
):
    # validate params first (using Course model methods as example)
    try:
        semester = Course.validate_semester(semester)
        course_id = Course.normalize_lowercase(course_id)
        # You might want a validator for assignment_id string pattern here too if needed
    except Exception as e: # Catch potential validation errors
         raise HTTPException(status_code=400, detail=f"Invalid parameter: {e}")

    blob_uploader = AzureBlobService.get_instance()

    # Auth checks...
    if not blob_uploader.course_exists(semester, course_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course does not exist.")
    user = blob_uploader.get_user(user_meta.user_email)
    if not user or (semester, course_id) not in user.authenticated_courses:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User not found or access not allowed.")
    if not blob_uploader.assignment_exists(semester, course_id, assignment_id): # Pass str ID
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment does not exist.")

    # TODO: Implement actual AI API call here using the string assignment_id

    logger.warning(f"AI Rubric generation not implemented for {semester}/{course_id}/{assignment_id}. Returning dummy data.")
    dummy_rubric = Rubric(
        semester=semester,
        course_id=course_id,
        assignment_id=assignment_id, # Use the string ID
        grading_flags=[GradingFlag.IGNORE_SPELLINGS],
        leniency=4,
        overall_instructor_guidelines="[AI Generated] Placeholder guidelines.",
        sub_rubrics=[]
    )
    return dummy_rubric


@router.get(
    "/rubric",
    response_model=Rubric,
    summary="Get Rubric",
    description="Retrieves the rubric for a specified assignment.",
    # ... responses ...
)
async def get_rubric(
        semester: str = Query(..., description="Semester..."),
        course_id: str = Query(..., description="Course ID."),
        # --- CHANGED TYPE: Back to str ---
        assignment_id: str = Query(..., description="Assignment ID."),
        # --- END CHANGE ---
        # Removing question_index as endpoint returns full Rubric
        # question_index: Optional[int] = Query(None, ...),
        user_meta: UserToken = Depends(user_from_auth),
):
    blob_uploader = AzureBlobService.get_instance()

    # validate params
    try:
        semester = Course.validate_semester(semester)
        course_id = Course.normalize_lowercase(course_id)
        # Add validation for assignment_id pattern if needed
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid parameter: {e}")

    # Auth Checks...
    if not blob_uploader.course_exists(semester, course_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course does not exist.")
    user = blob_uploader.get_user(user_meta.user_email)
    if not user or (semester, course_id) not in user.authenticated_courses:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User not found or access not allowed.")
    if not blob_uploader.assignment_exists(semester, course_id, assignment_id): # Pass str ID
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment does not exist.")

    # Get the full rubric (ensure get_rubric service method expects str ID)
    try:
        rubric = blob_uploader.get_rubric(semester, course_id, assignment_id)
        if rubric is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Rubric for assignment {assignment_id} not found.")
        return rubric
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.exception(f"Failed to get rubric for assignment {assignment_id} in {semester}/{course_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve rubric.")