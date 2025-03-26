from typing import Optional, List

from fastapi import APIRouter, HTTPException, status, Query, Body

from app.models.student_response import StudentResponse, GradedStudentResponse
from app.utils import JWTService
from app.utils.azure_blob_service import AzureBlobService

router = APIRouter()
user_from_authorization_header = JWTService.get_instance().from_authorization_header

# Dummy storage for student responses
dummy_responses: List[StudentResponse] = []


@router.post(
    "/response",
    summary="Upload Student Response",
    description="Uploads a student response for an assignment question. The size of the data must be below a certain threshold.",
    responses={
        400: {"description": "Missing or invalid parameters."},
        404: {"description": "Assignment or question not found."},
        401: {"description": "Requester is not authenticated."},
        403: {"description": "Authenticated but access is not allowed."}
    }
)
async def upload_response(
        response: StudentResponse = Body(..., description="Student response object containing the answer data.")
):
    blob_uploader = AzureBlobService.get_instance()
    dummy_responses.append(response)
    return {"message": "Response uploaded successfully."}


@router.put(
    "/response",
    summary="Replace Student Response",
    description="Replaces an existing student response. The size of the data must be below a certain threshold.",
    responses={
        400: {"description": "Missing or invalid parameters."},
        404: {"description": "Existing response not found."},
        401: {"description": "Requester is not authenticated."},
        403: {"description": "Authenticated but access is not allowed."}
    }
)
async def replace_response(
        response: StudentResponse = Body(..., description="Student response object with the updated answer data.")
):
    blob_uploader = AzureBlobService.get_instance()
    for idx, existing in enumerate(dummy_responses):
        if (existing.student_id == response.student_id and
                existing.assignment_id == response.assignment_id and
                existing.question_index == response.question_index):
            dummy_responses[idx] = response
            return {"message": "Response replaced successfully."}
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Response not found.")


@router.delete(
    "/response",
    summary="Delete Student Response",
    description="Deletes a student response. If question_index is omitted, deletes all responses for that assignment and student.",
    responses={
        400: {"description": "Missing required parameters."},
        404: {"description": "Specified response not found."},
        401: {"description": "Requester is not authenticated."},
        403: {"description": "Authenticated but access is not allowed."}
    }
)
async def delete_response(
        student_id: str = Query(..., description="Unique identifier for the student."),
        semester: str = Query(..., description="Semester of the course."),
        assignment_id: str = Query(..., description="Identifier of the assignment."),
        question_index: Optional[int] = Query(None,
                                              description="Optional index of the question. If omitted, all responses "
                                                          "for the assignment are deleted.")
):
    blob_uploader = AzureBlobService.get_instance()
    global dummy_responses
    if question_index is not None:
        for response in dummy_responses:
            if (response.student_id == student_id and
                    response.assignment_id == assignment_id and
                    response.question_index == question_index):
                dummy_responses.remove(response)
                return {"message": "Response deleted successfully."}
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Response not found.")
    else:
        dummy_responses = [r for r in dummy_responses if
                           not (r.student_id == student_id and r.assignment_id == assignment_id)]
        return {"message": "All responses for the assignment deleted successfully."}


@router.get(
    "/responses",
    summary="Get Student Responses",
    description="Retrieves student responses (possibly including grade information) based on criteria.",
    response_model=List[GradedStudentResponse],
    responses={
        400: {"description": "Missing assignment_id."},
        404: {"description": "No matching responses found."},
        401: {"description": "Requester is not authenticated."},
        403: {"description": "Authenticated but access is not allowed."}
    }
)
async def get_responses(
        semester: str = Query(..., description="Semester of the course."),
        assignment_id: str = Query(..., description="Identifier of the assignment."),
        question_index: Optional[int] = Query(None, description="Optional index of the question."),
        student_id: Optional[str] = Query(None, description="Optional unique identifier for the student.")
):
    blob_uploader = AzureBlobService.get_instance()
    results = []
    for response in dummy_responses:
        if response.assignment_id == assignment_id:
            if question_index is not None and response.question_index != question_index:
                continue
            if student_id is not None and response.student_id != student_id:
                continue
            results.append(response)
    if results:
        return results
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No matching responses found.")
