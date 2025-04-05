from typing import List, Optional

from fastapi import APIRouter, Query

from app.models import StudentResponse, Course
from app.models.grade import Grade
from app.utils import JWTService
from app.utils.azure_blob_service import AzureBlobService

router = APIRouter()
user_from_auth = JWTService.get_instance().from_authorization_header


@router.post(
    "/grade/specific",
    response_model=List[Grade],
    summary="Grade Specific Responses",
    description="Grades or regrades a specific student responses for an assignment.",
    responses={
        400: {"description": "Missing or invalid parameters."},
        502: {"description": "External LLM API call failure."},
        401: {"description": "Requester is not authenticated."},
        403: {"description": "Authenticated but access is not allowed."}
    }
)
async def grade_specific(
        semester: str = Query(..., description="Course semester."),
        course_id: str = Query(..., description="Unique identifier of the course."),
        assignment_id: int = Query(..., description="Identifier of the assignment."),
        student_ids: List[str] = Query(..., description="List of student identifiers to grade."),
        question_index: Optional[int] = Query(None,
                                              description="Optional index of the question. Grades all questions if "
                                                          "omitted.")
):
    # validate params
    semester = Course.validate_semester(semester)
    course_id = Course.normalize_lowercase(course_id)

    # TODO normalize input emails
    blob_uploader = AzureBlobService.get_instance()
    return []


@router.post(
    "/grade/ungraded",
    response_model=List[Grade],
    summary="Grade Ungraded Responses",
    description="Grades all ungraded responses for a specific assignment (optionally for a specific question).",
    responses={
        400: {"description": "Missing or invalid parameters."},
        502: {"description": "External LLM API call failure."},
        401: {"description": "Requester is not authenticated."},
        403: {"description": "Authenticated but access is not allowed."}
    }
)
async def grade_ungraded(
        semester: str = Query(..., description="Course semester."),
        course_id: str = Query(..., description="Unique identifier of the course."),
        assignment_id: int = Query(..., description="Identifier of the assignment."),
        question_index: Optional[int] = Query(None,
                                              description="Optional index of the question to grade. Grades all "
                                                          "ungraded questions if omitted.")
):
    # validate params
    semester = Course.validate_semester(semester)
    course_id = Course.normalize_lowercase(course_id)

    blob_uploader = AzureBlobService.get_instance()
    return []


@router.post(
    "/grade/all",
    response_model=List[Grade],
    summary="Grade/Regrade All Responses",
    description="Grades or regrades all student responses for a specific assignment (optionally for a specific question).",
    responses={
        400: {"description": "Missing or invalid parameters."},
        502: {"description": "External LLM API call failure."},
        401: {"description": "Requester is not authenticated."},
        403: {"description": "Authenticated but access is not allowed."}
    }
)
async def grade_all(
        semester: str = Query(..., description="Course semester."),
        course_id: str = Query(..., description="Unique identifier of the course."),
        assignment_id: int = Query(..., description="Identifier of the assignment."),
        question_index: int = Query(None,
                                    description="Optional index of the question to grade or regrade. Grades all "
                                                "questions if omitted.")
):
    # validate params
    semester = Course.validate_semester(semester)
    course_id = Course.normalize_lowercase(course_id)

    blob_uploader = AzureBlobService.get_instance()
    return []
