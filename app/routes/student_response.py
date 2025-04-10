from typing import Optional, List

from fastapi import APIRouter, HTTPException, status, Query, Body, Depends

from app.models import Course
from app.models.student_response import StudentResponse, GradedStudentResponse
from app.utils import JWTService, UserToken
from app.utils.azure_blob_service import AzureBlobService

router = APIRouter()
user_from_auth = JWTService.get_instance().from_authorization_header


# Dummy storage for student responses
dummy_responses: List[StudentResponse] = []


@router.post(
    "/response",
    summary="Upload Student Response",
    description="Uploads a student response for an assignment question. The size of the data must be below a certain threshold.",
    responses={
        400: {"detail": "Missing or invalid parameters."},
        404: {"detail": "Assignment or question not found."},
        401: {"detail": "Requester is not authenticated."},
        403: {"detail": "Authenticated but access is not allowed."}
    }
)
async def upload_response(
        response: StudentResponse = Body(..., description="Student response object containing the answer data."),
        user_meta: UserToken = Depends(user_from_auth),
):
    blob_uploader = AzureBlobService.get_instance()

    # Check if course exists
    if not blob_uploader.course_exists(response.semester, response.course_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course does not exist.")

    # Check if user has permissions on course
    user = blob_uploader.get_user(user_meta.user_email)
    if not user.authenticated_courses.__contains__((response.semester, response.course_id)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Authenticated but access is not allowed.")

    # Check if assignment exists
    if not blob_uploader.assignment_exists(response.semester, response.course_id, response.assignment_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment does not exist.")

    # Upload the response
    blob_uploader.upload_student_response(response)
    return {"detail":  "Response uploaded successfully."}


@router.put(
    "/response",
    summary="Replace Student Response",
    description="Replaces an existing student response. The size of the data must be below a certain threshold.",
    responses={
        400: {"detail": "Missing or invalid parameters."},
        404: {"detail": "Existing response not found."},
        401: {"detail": "Requester is not authenticated."},
        403: {"detail": "Authenticated but access is not allowed."}
    }
)
async def replace_response(
        response: StudentResponse = Body(..., description="Student response object with the updated answer data."),
        user_meta: UserToken = Depends(user_from_auth),
):
    blob_uploader = AzureBlobService.get_instance()

    # Check if course exists
    if not blob_uploader.course_exists(response.semester, response.course_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course does not exist.")

    # Check if user has permissions on course
    user = blob_uploader.get_user(user_meta.user_email)
    if not user.authenticated_courses.__contains__((response.semester, response.course_id)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Authenticated but access is not allowed.")

    # Check if assignment exists
    if not blob_uploader.assignment_exists(response.semester, response.course_id, response.assignment_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment does not exist.")

    # Check if response exists
    existing_response = blob_uploader.get_student_response(
        response.semester, response.course_id, response.assignment_id, response.question_index, response.student_id
    )
    if not existing_response:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Response not found.")

    # Upload the updated response
    blob_uploader.upload_student_response(response)
    return {"detail":  "Response replaced successfully."}


@router.delete(
    "/response",
    summary="Delete Student Response",
    description="Deletes a student response. If question_index is omitted, deletes all responses for that assignment and student.",
    responses={
        400: {"detail": "Missing required parameters."},
        404: {"detail": "Specified response not found."},
        401: {"detail": "Requester is not authenticated."},
        403: {"detail": "Authenticated but access is not allowed."}
    }
)
async def delete_response(
        student_id: str = Query(..., description="Student's unique identifier usually their email."),
        semester: str = Query(..., description="Semester of the course."),
        course_id: str = Query(..., description="Identifier of the course."),
        assignment_id: int = Query(..., description="Identifier of the assignment."),
        question_index: Optional[int] = Query(None,
                                              description="Optional index of the question. If omitted, all responses for the assignment are deleted."),
        user_meta: UserToken = Depends(user_from_auth),
):
    # validate params
    semester = Course.validate_semester(semester)
    course_id = Course.normalize_lowercase(course_id)

    blob_uploader = AzureBlobService.get_instance()

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

    if question_index is not None:
        # Check if specific response exists
        existing_response = blob_uploader.get_student_response(
            semester, course_id, assignment_id, question_index, student_id
        )
        if not existing_response:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Response not found.")

        # Delete specific response
        blob_uploader.delete_student_response(semester, course_id, assignment_id, question_index, student_id)
        return {"detail":  "Response deleted successfully."}
    else:
        # Delete all responses for the student in this assignment
        blob_uploader.delete_student_responses(semester, course_id, assignment_id, student_id)
        return {"detail":  "All responses for the assignment deleted successfully."}


@router.get(
    "/responses",
    summary="Get Student Responses",
    description="Retrieves student responses (possibly including grade information) based on criteria.",
    response_model=List[GradedStudentResponse],
    responses={
        400: {"detail": "Missing assignment_id."},
        404: {"detail": "No matching responses found."},
        401: {"detail": "Requester is not authenticated."},
        403: {"detail": "Authenticated but access is not allowed."}
    }
)
async def get_responses(
        semester: str = Query(..., description="Semester of the course."),
        course_id: str = Query(..., description="Identifier of the course."),
        assignment_id: int = Query(..., description="Identifier of the assignment."),
        question_index: Optional[int] = Query(None, description="Optional index of the question."),
        student_id: Optional[str] = Query(None, description="Optional unique identifier for the student."),
        user_meta: UserToken = Depends(user_from_auth),
):
    # validate params
    semester = Course.validate_semester(semester)
    course_id = Course.normalize_lowercase(course_id)

    blob_uploader = AzureBlobService.get_instance()

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

    # Get all responses for the assignment
    responses = blob_uploader.list_student_responses(semester, course_id, assignment_id, question_index)

    # Filter by student_id if provided
    if student_id is not None:
        responses = [r for r in responses if r.student_id == student_id]

    if not responses:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No matching responses found.")

    graded_responses = []
    for response in responses:
        graded_response = blob_uploader.get_student_response(semester, course_id, assignment_id,
                                                             response.question_index, student_id)
        graded_responses.append(graded_response)

    return graded_responses
