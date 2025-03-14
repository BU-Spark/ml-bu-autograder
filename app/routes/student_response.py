from fastapi import APIRouter, HTTPException, status
from typing import Optional, List
from app.models.student_response import StudentResponse

router = APIRouter()

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
async def upload_response(response: StudentResponse):
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
async def replace_response(response: StudentResponse):
    for idx, existing in enumerate(dummy_responses):
        if (existing.student_identifier == response.student_identifier and
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
async def delete_response(student_identifier: str, assignment_id: str, question_index: Optional[int] = None):
    global dummy_responses
    if question_index is not None:
        for response in dummy_responses:
            if (response.student_identifier == student_identifier and
                response.assignment_id == assignment_id and
                response.question_index == question_index):
                dummy_responses.remove(response)
                return {"message": "Response deleted successfully."}
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Response not found.")
    else:
        dummy_responses = [r for r in dummy_responses if not (r.student_identifier == student_identifier and r.assignment_id == assignment_id)]
        return {"message": "All responses for the assignment deleted successfully."}

@router.get(
    "/responses",
    summary="Get Student Responses",
    description="Retrieves student responses (optionally including grade information) based on criteria.",
    responses={
        400: {"description": "Missing assignment_id."},
        404: {"description": "No matching responses found."},
        401: {"description": "Requester is not authenticated."},
        403: {"description": "Authenticated but access is not allowed."}
    }
)
async def get_responses(assignment_id: str, question_index: Optional[int] = None, student_identifier: Optional[str] = None):
    results = []
    for response in dummy_responses:
        if response.assignment_id == assignment_id:
            if question_index is not None and response.question_index != question_index:
                continue
            if student_identifier is not None and response.student_identifier != student_identifier:
                continue
            results.append(response)
    if results:
        return results
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No matching responses found.")
