import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, status, Query, Depends

from app.models import Course, UserToken
from app.models.rubric import Rubric
from app.models.rubric_review import RubricRefinementResponse
from app.services.azure_blob_service import AzureBlobService
from app.services.rubric_refinement_service import RubricRefinementService
from app.utils.jwt_service import JWTService

router = APIRouter()
user_from_auth = JWTService.get_instance().from_authorization_header


@router.post(
    "/ai_rubric_refine",
    response_model=RubricRefinementResponse,
    summary="Audit and improve rubric with AI",
    description=(
        "Audits the existing rubric for weaknesses, then revises it to address those issues. "
        "Saves the improved rubric (and the critique) by default."
    ),
    responses={
        404: {"detail": "Course/Assignment/Rubric not found."},
        401: {"detail": "Requester is not authenticated."},
        403: {"detail": "Authenticated but access is not allowed."},
        502: {"detail": "External LLM API call failure."},
    },
)
async def audit_and_refine_rubric(
    semester: str = Query(..., description="Semester of the course."),
    course_id: str = Query(..., description="Identifier of the course."),
    assignment_id: str = Query(..., description="Identifier of the assignment."),
    instructions: Optional[str] = Query(None, description="Optional instructor notes to steer the review/refinement."),
    save: bool = Query(True, description="If true, saves the improved rubric and the critique."),
    user_meta: UserToken = Depends(user_from_auth),
) -> RubricRefinementResponse:
    blob = AzureBlobService.get_instance()

    # validate params by attempting to create a course object
    Course(semester=semester, course_id=course_id)

    # Course must exist
    if not blob.course_exists(semester, course_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course does not exist.")

    # User must have access
    user = blob.get_user(user_meta.user_email)
    if (semester, course_id) not in user.authenticated_courses:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Authenticated but access is not allowed.")

    # Assignment must exist
    if not blob.assignment_exists(semester, course_id, assignment_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment does not exist.")

    # Rubric must already exist
    original_rubric = blob.get_rubric(semester, course_id, assignment_id)
    if original_rubric is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rubric does not exist.")

    # Get assignment details (with questions) for LLM context
    assignment = blob.get_assignment_metadata(semester, course_id, assignment_id)
    if assignment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found.")
    assignment.questions = blob.list_questions(semester, course_id, assignment_id)

    service = RubricRefinementService()

    try:
        critique = service.critique_rubric(assignment, original_rubric, instructions)
        improved: Rubric = service.refine_rubric(assignment, original_rubric, critique, instructions)

        # Ensure metadata integrity
        improved.semester = semester
        improved.course_id = course_id
        improved.assignment_id = assignment_id

        did_save = False
        if save:
            # Save improved rubric and store the critique alongside it
            blob.upload_rubric(semester, course_id, assignment_id, improved)
            try:
                blob.upload_json(
                    critique,
                    f"course/{semester}/{course_id}/assignment/{assignment_id}/rubrics/review.json",
                )
            except Exception as e:
                # Saving the critique is helpful but non-fatal if rubric saved
                logging.warning("Failed to save rubric critique JSON: %s", str(e))
            did_save = True

        return RubricRefinementResponse(saved=did_save, critique=critique, improved_rubric=improved)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to audit/refine rubric using LLM: {str(e)}",
        )

