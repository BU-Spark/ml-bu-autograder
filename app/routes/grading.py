from typing import List, Optional
import re
from fastapi import APIRouter, HTTPException, status, Query, Depends
from pydantic import BaseModel, Field, field_validator

from app.models import StudentResponse, Course
from app.models.grade import Grade
from app.utils import JWTService, UserToken
from app.utils.azure_blob_service import AzureBlobService

router = APIRouter()
user_from_auth = JWTService.get_instance().from_authorization_header


class GradeBaseParams(BaseModel):
    """Base parameters for grading operations."""
    semester: str = Field(..., description="Course semester.")
    course_id: str = Field(..., description="Unique identifier of the course.")
    assignment_id: int = Field(..., description="Identifier of the assignment.")
    question_index: Optional[int] = Field(None, description="Optional index of the question.")

    @field_validator("course_id")
    def validate_course_id(cls, value: str) -> str:
        """Ensures course_id contains only lowercase letters, digits, and underscores."""
        if not re.fullmatch("[a-z0-9_]+", value):
            raise ValueError("Course ID must contain only lowercase letters, digits, and underscores")
        return value.strip().lower()

    @field_validator("semester")
    def validate_semester(cls, value: str) -> str:
        """Ensures semester follows format seasonYYYY (e.g., spring2025)."""
        if not re.fullmatch("[a-z]{1,12}[0-9]{4}", value):
            raise ValueError("Semester must follow format seasonYYYY (e.g., spring2025)")
        return value.strip().lower()

    @field_validator("question_index")
    def validate_question_index(cls, value: Optional[int]) -> Optional[int]:
        """Ensures question_index is non-negative if provided."""
        if value is not None and value < 0:
            raise ValueError("Question index must be non-negative")
        return value


class GradeSpecificParams(GradeBaseParams):
    """Parameters for grading specific student responses."""
    student_ids: List[str] = Field(..., description="List of student identifiers to grade.")

    @field_validator("student_ids")
    def validate_student_ids(cls, value: List[str]) -> List[str]:
        """Ensures all student IDs are lowercase."""
        return [id.strip().lower() for id in value]


class GradeParams(GradeBaseParams):
    """Parameters for grading all responses."""
    pass

def do_grading(r):
    ...  # TODO


@router.post(
    "/grade/specific",
    response_model=List[Grade],
    summary="Grade Specific Responses",
    description="Grades or regrades a specific student responses for an assignment.",
    responses={
        400: {"description": "Missing or invalid parameters."},
        404: {"description": "Course, assignment, rubric, or student responses not found."},
        502: {"description": "External LLM API call failure."},
        401: {"description": "Requester is not authenticated."},
        403: {"description": "Authenticated but access is not allowed."}
    }
)
async def grade_specific(
        params: GradeSpecificParams = Depends(),
        user_meta: UserToken = Depends(user_from_auth),
):
    blob_uploader = AzureBlobService.get_instance()

    # Check if course exists
    if not blob_uploader.course_exists(params.semester, params.course_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course does not exist.")

    # Check if user has permissions on course
    user = blob_uploader.get_user(user_meta.user_email)
    if not user.authenticated_courses.__contains__((params.semester, params.course_id)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Authenticated but access is not allowed.")

    # Check if assignment exists
    if not blob_uploader.assignment_exists(params.semester, params.course_id, params.assignment_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment does not exist.")

    # Check if the rubric exists
    rubric = None
    if params.question_index is not None:
        rubric = blob_uploader.get_sub_rubric(params.semester, params.course_id, params.assignment_id, params.question_index)
    else:
        rubric = blob_uploader.get_rubric(params.semester, params.course_id, params.assignment_id, params.question_index)

    if rubric is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Grading rubric does not exist.")

    # Get all responses for the specified students
    grades = []
    for student_id in params.student_ids:
        if params.question_index is not None:
            # Grade specific question
            response = blob_uploader.get_student_response(
                params.semester, params.course_id, params.assignment_id,
                params.question_index, student_id
            )
            if response:
                # TODO
                grade = do_grading(response)  # This is a placeholder for the actual grading logic
                grades.append(grade)
        else:
            # Grade all questions
            responses = blob_uploader.list_student_responses(
                params.semester, params.course_id, params.assignment_id
            )
            student_responses = [r for r in responses if r.student_id == student_id]
            for response in student_responses:
                grade = do_grading(response)  # This is a placeholder for the actual grading logic
                grades.append(grade)

    if not grades:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No matching responses found.")

    return grades


@router.post(
    "/grade/ungraded",
    response_model=List[Grade],
    summary="Grade Ungraded Responses",
    description="Grades all ungraded responses for a specific assignment (optionally for a specific question).",
    responses={
        400: {"description": "Missing or invalid parameters."},
        404: {"description": "Course or assignment not found."},
        502: {"description": "External LLM API call failure."},
        401: {"description": "Requester is not authenticated."},
        403: {"description": "Authenticated but access is not allowed."}
    }
)
async def grade_ungraded(
        params: GradeParams = Depends(),
        user_meta: UserToken = Depends(user_from_auth),
):
    blob_uploader = AzureBlobService.get_instance()

    # Check if course exists
    if not blob_uploader.course_exists(params.semester, params.course_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course does not exist.")

    # Check if user has permissions on course
    user = blob_uploader.get_user(user_meta.user_email)
    if not user.authenticated_courses.__contains__((params.semester, params.course_id)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Authenticated but access is not allowed.")

    # Check if assignment exists
    if not blob_uploader.assignment_exists(params.semester, params.course_id, params.assignment_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment does not exist.")

    # Check if the rubric exists
    rubric = None
    if params.question_index is not None:
        rubric = blob_uploader.get_sub_rubric(params.semester, params.course_id, params.assignment_id,
                                              params.question_index)
    else:
        rubric = blob_uploader.get_rubric(params.semester, params.course_id, params.assignment_id,
                                          params.question_index)
    if rubric is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Grading rubric does not exist.")

    # Get all responses
    responses = blob_uploader.list_student_responses(
        params.semester, params.course_id, params.assignment_id, params.question_index
    )

    # Filter out already graded responses
    ungraded_responses = []
    for response in responses:
        grade = blob_uploader.get_grading_details(
            params.semester, params.course_id, params.assignment_id,
            response.question_index, response.student_id
        )
        if not grade:
            ungraded_responses.append(response)

    if not ungraded_responses:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No ungraded responses found.")

    # Grade ungraded responses
    grades = []
    for response in ungraded_responses:
        grade = do_grading(response)
        grades.append(grade)

    return grades


@router.post(
    "/grade/all",
    response_model=List[Grade],
    summary="Grade/Regrade All Responses",
    description="Grades or regrades all student responses for a specific assignment (optionally for a specific question).",
    responses={
        400: {"description": "Missing or invalid parameters."},
        404: {"description": "Course or assignment not found."},
        502: {"description": "External LLM API call failure."},
        401: {"description": "Requester is not authenticated."},
        403: {"description": "Authenticated but access is not allowed."}
    }
)
async def grade_all(
        params: GradeParams = Depends(),
        user_meta: UserToken = Depends(user_from_auth),
):
    blob_uploader = AzureBlobService.get_instance()

    # Check if course exists
    if not blob_uploader.course_exists(params.semester, params.course_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course does not exist.")

    # Check if user has permissions on course
    user = blob_uploader.get_user(user_meta.user_email)
    if not user.authenticated_courses.__contains__((params.semester, params.course_id)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Authenticated but access is not allowed.")

    # Check if assignment exists
    if not blob_uploader.assignment_exists(params.semester, params.course_id, params.assignment_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment does not exist.")

    # Check if the rubric exists
    rubric = None
    if params.question_index is not None:
        rubric = blob_uploader.get_sub_rubric(params.semester, params.course_id, params.assignment_id,
                                              params.question_index)
    else:
        rubric = blob_uploader.get_rubric(params.semester, params.course_id, params.assignment_id,
                                          params.question_index)
    if rubric is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Grading rubric does not exist.")

    # Get all responses
    responses = blob_uploader.list_student_responses(
        params.semester, params.course_id, params.assignment_id, params.question_index
    )

    if not responses:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No responses found.")

    # Grade all responses
    grades = []
    for response in responses:
        grade = do_grading(response)
        grades.append(grade)

    return grades
