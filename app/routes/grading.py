from typing import List, Optional
from fastapi import APIRouter, HTTPException, status, Query, Depends

from app.models import Course, GradedStudentResponseReference
from app.models.grade import Grade
from app.utils import JWTService, UserToken
from app.utils.azure_blob_service import AzureBlobService

router = APIRouter()
user_from_auth = JWTService.get_instance().from_authorization_header


def do_grading(responses: list[GradedStudentResponseReference]):
    ...  # TODO


@router.post(
    "/grade/specific",
    response_model=List[Grade],
    summary="Grade Specific Responses",
    description="Grades or regrades a specific student responses for an assignment.",
    responses={
        400: {"detail": "Missing or invalid parameters."},
        404: {"detail": "Course, assignment, rubric, or student responses not found."},
        502: {"detail": "External LLM API call failure."},
        401: {"detail": "Requester is not authenticated."},
        403: {"detail": "Authenticated but access is not allowed."}
    }
)
async def grade_specific(
        semester: str = Query(..., description="Course semester."),
        course_id: str = Query(..., description="Unique identifier of the course."),
        assignment_id: str = Query(..., description="Identifier of the assignment."),
        student_ids: List[str] = Query(..., description="List of student identifiers to grade."),
        question_index: Optional[int] = Query(None, description="Optional index of the question. Grades all questions if omitted."),
        user_meta: UserToken = Depends(user_from_auth),
):
    blob_uploader = AzureBlobService.get_instance()

    # validate params
    semester = Course.validate_semester(semester)
    course_id = Course.normalize_lowercase(course_id)

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

    # Check if the rubric exists
    rubric = None
    if question_index is not None:
        rubric = blob_uploader.get_sub_rubric(semester, course_id, assignment_id, question_index)
    else:
        rubric = blob_uploader.get_rubric(semester, course_id, assignment_id)

    if rubric is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Grading rubric does not exist.")

    # Get all responses for the specified students
    grades = []
    for student_id in student_ids:
        if question_index is not None:
            # Grade specific question
            response = blob_uploader.list_student_responses(
                semester, course_id, assignment_id, student_id,
                question_index
            )
            if response:
                grade = do_grading(response)  # This is a placeholder for the actual grading logic
                grades.append(grade)
        else:
            # Grade all questions
            responses = blob_uploader.list_student_responses(
                semester, course_id, assignment_id
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
        400: {"detail": "Missing or invalid parameters."},
        404: {"detail": "Course or assignment not found."},
        502: {"detail": "External LLM API call failure."},
        401: {"detail": "Requester is not authenticated."},
        403: {"detail": "Authenticated but access is not allowed."}
    }
)
async def grade_ungraded(
        semester: str = Query(..., description="Course semester."),
        course_id: str = Query(..., description="Unique identifier of the course."),
        assignment_id: str = Query(..., description="Identifier of the assignment."),
        question_index: Optional[int] = Query(None, description="Optional index of the question to grade. Grades all ungraded questions if omitted."),
        user_meta: UserToken = Depends(user_from_auth),
):
    blob_uploader = AzureBlobService.get_instance()

    # validate params
    semester = Course.validate_semester(semester)
    course_id = Course.normalize_lowercase(course_id)

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

    # Check if the rubric exists
    rubric = None
    if question_index is not None:
        rubric = blob_uploader.get_sub_rubric(semester, course_id, assignment_id, question_index)
    else:
        rubric = blob_uploader.get_rubric(semester, course_id, assignment_id)

    if rubric is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Grading rubric does not exist.")

    # Get all responses
    responses = blob_uploader.list_student_responses(
        semester, course_id, assignment_id, None, question_index
    )

    # Filter out already graded responses
    ungraded_responses = []
    for response in responses:
        grade = blob_uploader.get_grading_details(
            semester, course_id, assignment_id,
            response.question_index, response.student_id
        )
        if not grade:
            ungraded_responses.append(response)

    if not ungraded_responses:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No ungraded responses found.")

    # Grade ungraded responses
    grades = []
    for response in ungraded_responses:
        grade = do_grading(response)  # This is a placeholder for the actual grading logic
        grades.append(grade)

    return grades


@router.post(
    "/grade/all",
    response_model=List[Grade],
    summary="Grade/Regrade All Responses",
    description="Grades or regrades all student responses for a specific assignment (optionally for a specific question).",
    responses={
        400: {"detail": "Missing or invalid parameters."},
        404: {"detail": "Course or assignment not found."},
        502: {"detail": "External LLM API call failure."},
        401: {"detail": "Requester is not authenticated."},
        403: {"detail": "Authenticated but access is not allowed."}
    }
)
async def grade_all(
        semester: str = Query(..., description="Course semester."),
        course_id: str = Query(..., description="Unique identifier of the course."),
        assignment_id: str = Query(..., description="Identifier of the assignment."),
        question_index: Optional[int] = Query(None, description="Optional index of the question to grade or regrade. Grades all questions if omitted."),
        user_meta: UserToken = Depends(user_from_auth),
):
    blob_uploader = AzureBlobService.get_instance()

    # validate params
    semester = Course.validate_semester(semester)
    course_id = Course.normalize_lowercase(course_id)

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

    # Check if the rubric exists
    rubric = None
    if question_index is not None:
        rubric = blob_uploader.get_sub_rubric(semester, course_id, assignment_id, question_index)
    else:
        rubric = blob_uploader.get_rubric(semester, course_id, assignment_id)

    if rubric is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Grading rubric does not exist.")

    # Get all responses
    responses = blob_uploader.list_student_responses(
        semester, course_id, assignment_id, None, question_index
    )

    if not responses:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No responses found.")

    # Grade all responses
    grades = []
    for response in responses:
        grade = do_grading(response)  # This is a placeholder for the actual grading logic
        grades.append(grade)

    return grades
