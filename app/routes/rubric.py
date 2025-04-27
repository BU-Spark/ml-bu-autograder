# app/routes/rubric.py

import re
from typing import Optional, List
from fastapi import APIRouter, HTTPException, status, Query, Body, Depends
import logging

from app.models import Course
from app.models.rubric import Rubric
from app.models import UserToken
from app.utils.jwt_service import JWTService
from app.services.azure_blob_service import AzureBlobService
from app.utils.llm_service import LLMService, PromptBuilder, PromptRole

router = APIRouter()
user_from_auth = JWTService.get_instance().from_authorization_header

logger = logging.getLogger(__name__)


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
    summary="Enhance Rubric with AI",
    description="Enhances an existing rubric using AI-based improvements. If a rubric does not exist for the given assignment, a new one is generated. Note: This only proposes a new rubric and does not modify an existing one.",
    responses={
        502: {"detail": "External LLM API call failure."},
        401: {"detail": "Requester is not authenticated."},
        403: {"detail": "Authenticated but access is not allowed."}
    }
)
async def get_ai_rubric(
        semester: str = Query(..., description="Semester of the course."),
        course_id: str = Query(..., description="Identifier of the course."),
        assignment_id: str = Query(..., description="Identifier of the assignment."),
        instructions: Optional[str] = Query(None, description="Optional specific improvement instructions for the AI."),
        user_meta: UserToken = Depends(user_from_auth),
):
    blob_uploader = AzureBlobService.get_instance()

    # validate params by attempting to create a course object
    Course(semester=semester, course_id=course_id)

    # Check if course exists
    if not blob_uploader.course_exists(semester, course_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course does not exist.")

    # Check if user has permissions on course
    user = blob_uploader.get_user(user_meta.user_email)
    if not user.authenticated_courses.__contains__((semester, course_id)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Authenticated but access is not allowed.")

    # Check if assignment exists
    if not blob_uploader.assignment_exists(semester, course_id, assignment_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment does not exist.")

    # Get the rubric
    rubric = blob_uploader.get_rubric(semester, course_id, assignment_id)
    if rubric is None:
        # Get the assignment details to inform the LLM
        assignment = blob_uploader.get_assignment_metadata(semester, course_id, assignment_id)
        if assignment is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found.")

        # Use LLM to generate a rubric from scratch
        llm_service = LLMService.get_instance()

        # Build the prompt for creating a rubric
        prompt = (PromptBuilder.builder()
            .add_message(PromptRole.SYSTEM, 
                "You are an expert in creating educational assessment rubrics. "
                "Your task is to create a fair, consistent, and organized rubric for an assignment. "
                "The rubric should have clear criteria and point allocations that add up to the total points. "
                "Use the assignment details to guide your rubric creation.")
            .add_message(PromptRole.USER, 
                f"Create a comprehensive rubric for the following assignment:\n\n"
                f"Course: {course_id.upper()}, Semester: {semester}\n"
                f"Assignment ID: {assignment_id}\n"
                #f"Assignment Details: {assignment.title} - {assignment.description}\n\n"
                f"Number of questions: {len(assignment.questions)}")
        )

        # Add each question to the prompt
        for i, question in enumerate(assignment.questions):
            prompt.add_message(PromptRole.USER, 
                f"Question {i+1}: {question.text}\n"
                f"Points: {question.max_points}")

        # Add any additional instructions if provided
        if instructions:
            prompt.add_message(PromptRole.USER, f"Additional instructions: {instructions}")

        # Build the final prompt
        prompt_list = prompt.build()

        try:
            # Generate a structured response matching the Rubric model
            rubric = llm_service.generate_structured_response(prompt_list, Rubric)
            
            # Ensure the rubric has the correct metadata
            rubric.semester = semester
            rubric.course_id = course_id
            rubric.assignment_id = assignment_id
            
            # Upload the generated rubric
            blob_uploader.upload_rubric(semester, course_id, assignment_id, rubric)
            
            return rubric
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to generate rubric using LLM: {str(e)}"
            )
    else:
        # Get the assignment details
        assignment = blob_uploader.get_assignment_metadata(semester, course_id, assignment_id)
        if assignment is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found.")

        # Use LLM to enhance the existing rubric
        llm_service = LLMService.get_instance()

        # Build the prompt for enhancing a rubric
        prompt = (PromptBuilder.builder()
            .add_message(PromptRole.SYSTEM, 
                "You are an expert in educational assessment who specializes in improving rubrics. "
                "Your task is to enhance an existing rubric to make it more organized, fair, and consistent. "
                "Maintain the core structure and intent of the original rubric while improving clarity, "
                "alignment with learning objectives, and point distribution fairness.")
            .add_message(PromptRole.USER, 
                f"Enhance the following rubric for this assignment:\n\n"
                f"Course: {course_id.upper()}, Semester: {semester}\n"
                f"Assignment ID: {assignment_id}\n"
            )
                #f"Assignment Details: {assignment.title} - {assignment.description}")
        )

        # Add the existing rubric as JSON input
        prompt.add_json_input(PromptRole.USER, rubric)

        # Add any additional instructions if provided
        
        prompt.add_message(PromptRole.USER, 
            "Please enhance this rubric by:\n"
            "1. Making criteria more specific and measurable\n"
            "2. Ensuring point distribution aligns with question importance\n"
            "3. Adding clear instructor guidelines where missing\n"
            "4. Organizing criteria logically\n"
            "5. Adding appropriate grading flags if needed\n"
            "6. Ensuring all grading criteria for each question sum to the max points. You must run through the whole rubric step by step and make sure"
            "that the sum of all points add to the max points allotment. If they do not add up to that allotment, then the rubric is invalid!")
        if instructions:
            prompt.add_message(PromptRole.USER, f"Specific improvement instructions from instructor: {instructions}")

        # Build the final prompt
        prompt_list = prompt.build()

        try:
            # Generate a structured response matching the Rubric model
            enhanced_rubric = llm_service.generate_structured_response(prompt_list, Rubric)
            
            # Ensure the enhanced rubric has the correct metadata 
            enhanced_rubric.semester = semester
            enhanced_rubric.course_id = course_id
            enhanced_rubric.assignment_id = assignment_id
            
            return enhanced_rubric
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to enhance rubric using LLM: {str(e)}"
        )


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
        #question_index: Optional[int] = Query(..., description="Question index."),
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
