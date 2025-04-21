# assignment.py

import re
from typing import List, Optional # Ensure Optional is imported
from fastapi import APIRouter, HTTPException, Query, Body, Depends, Path # Ensure Path is imported
from pydantic import BaseModel, Field, field_validator

from app.models import Course
from app.models.assignment import Assignment, Question
from app.utils import JWTService, UserToken
from app.utils.azure_blob_service import AzureBlobService
from azure.storage.blob import ContainerClient
import logging

logger = logging.getLogger(__name__)

# --- Pydantic Models ---

class EditQuestionRequest(BaseModel):
    semester: str = Field(..., description="Semester of the course.")
    course_id: str = Field(..., description="Identifier of the course.")
    assignment_id: str = Field(..., description="Identifier of the assignment.")
    question_index: int = Field(..., description="Index of the question.")
    question: Question = Field(..., description="The updated question data.")

    @classmethod
    @field_validator("semester", mode='before')
    def validate_semester(cls, value: str) -> str:
        """Converts to lowercase and trims spaces."""
        # Corrected Regex Logic
        if not re.fullmatch(r"[a-zA-Z]{1,12}[0-9]{4}", value.strip()):
            raise ValueError("Semester is in an invalid format. "
                             "Correct format looks like: seasonYYYY. (e.g. spring2025)")
        return value.strip().lower()


class AddQuestionRequest(BaseModel):
    semester: str = Field(..., description="Semester of the course.")
    course_id: str = Field(..., description="Identifier of the course.")
    assignment_id: str = Field(..., description="Identifier of the assignment to update.")
    question: Question = Field(..., description="The data of the new question. (Notice: You cannot specify "
                                                        "the index for this question. If you wish to re-order this "
                                                        "question, you must make a separate modify order request.)")

    @classmethod
    @field_validator("semester", mode='before')
    def validate_semester(cls, value: str) -> str:
        """Converts to lowercase and trims spaces."""
        # Corrected Regex Logic
        if not re.fullmatch(r"[a-zA-Z]{1,12}[0-9]{4}", value.strip()):
            raise ValueError("Semester is in an invalid format. "
                             "Correct format looks like: seasonYYYY. (e.g. spring2025)")
        return value.strip().lower()


class ModifyOrderRequest(BaseModel):
    semester: str = Field(..., description="Semester of the course.")
    course_id: str = Field(..., description="Identifier of the course.")
    assignment_id: str = Field(..., description="Identifier of the assignment.")
    list_of_question_indexes: List[int] = Field(..., description="New order for question indexes.")

    @classmethod
    @field_validator("semester", mode='before')
    def validate_semester(cls, value: str) -> str:
        """Converts to lowercase and trims spaces."""
        # Corrected Regex Logic
        if not re.fullmatch(r"[a-zA-Z]{1,12}[0-9]{4}", value.strip()):
            raise ValueError("Semester is in an invalid format. "
                             "Correct format looks like: seasonYYYY. (e.g. spring2025)")
        return value.strip().lower()


class AssignmentMetadataUpdate(BaseModel):
    """Payload for updating assignment metadata."""
    assignment_guidelines: Optional[str] = Field(None, description="New guidelines for the assignment.")
    # Add other fields like assignment_name if you want to update them too:
    # assignment_name: Optional[str] = Field(None, description="New name for the assignment.")

    class Config:
        extra = 'forbid' # Prevent unexpected fields


# --- Router Setup ---
router = APIRouter()
user_from_auth = JWTService.get_instance().from_authorization_header

# Note: list_assignment_ids function is defined in the original code but not used here.
# If it's part of AzureBlobService, it doesn't need to be defined here.

# --- API Endpoints ---

@router.post(
    "/assignment",
    response_model=Assignment,
    summary="Create Assignment",
    description="Creates a new assignment with questions and guidelines.",
    responses={
        400: {"detail": "Missing or invalid parameters."},
        404: {"detail": "Course does not exist."},
        401: {"detail": "Requester is not authenticated."},
        403: {"detail": "Authenticated but access is not allowed."},
        409: {"detail": "Assignment with the specified ID already exists."}
    }
)
async def create_assignment(
    assignment: Assignment = Body(..., description="The assignment to create."),
    user_meta: UserToken = Depends(user_from_auth),
):
    """
    Creates a new assignment for a course.
    If assignment_id is not provided, generates the next sequential integer ID.
    """
    blob_uploader: AzureBlobService = AzureBlobService.get_instance()

    # 1. Validate & Auth Checks
    try:
        assignment.semester = Course.validate_semester(assignment.semester)
        assignment.course_id = Course.normalize_lowercase(assignment.course_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not blob_uploader.course_exists(assignment.semester, assignment.course_id):
        logger.warning(f"Attempt to create assignment for non-existent course: {assignment.semester}/{assignment.course_id}")
        raise HTTPException(status_code=404, detail="Course does not exist.")

    user = blob_uploader.get_user(user_meta.user_email)
    if not user:
         logger.error(f"Authenticated user not found in user store: {user_meta.user_email}")
         raise HTTPException(status_code=403, detail="User data not found.")
    if (assignment.semester, assignment.course_id) not in user.authenticated_courses:
        logger.warning(f"User {user_meta.user_email} forbidden access to {assignment.semester}/{assignment.course_id}")
        raise HTTPException(status_code=403, detail="Authenticated but access to this course is not allowed.")

    # 2. Determine/Generate assignment_id
    if assignment.assignment_id is None or assignment.assignment_id == "":
        logger.info(f"assignment_id not provided for course {assignment.semester}/{assignment.course_id}. Generating next sequential ID.")
        try:
            existing_assignment_objects = blob_uploader.list_assignments(assignment.semester, assignment.course_id)
            logger.debug(f"list_assignments returned {len(existing_assignment_objects)} assignment objects.")

            max_id = -1
            if isinstance(existing_assignment_objects, list):
                for assign_obj in existing_assignment_objects:
                    if hasattr(assign_obj, 'assignment_id') and assign_obj.assignment_id is not None:
                        try:
                            current_id_int = int(str(assign_obj.assignment_id))
                            if current_id_int > max_id:
                                max_id = current_id_int
                        except (ValueError, TypeError):
                            logger.debug(f"Ignoring non-integer assignment ID '{assign_obj.assignment_id}' while calculating max integer ID.")
                    else:
                        logger.warning(f"Object found via list_assignments missing 'assignment_id' or it's None: {assign_obj}")
            else:
                logger.error(f"list_assignments for {assignment.semester}/{assignment.course_id} did not return a list. Type: {type(existing_assignment_objects)}")
                # Consider how critical this is. Maybe default to 0 or raise 500.
                raise ValueError("Internal server error: Failed to retrieve existing assignments.")

            next_id_int = max_id + 1
            assignment.assignment_id = str(next_id_int)
            logger.info(f"Generated NEW sequential integer assignment_id: {assignment.assignment_id} for course {assignment.semester}/{assignment.course_id}")

        except Exception as e:
            logger.exception(f"Error generating next assignment ID for {assignment.semester}/{assignment.course_id}: {e}")
            raise HTTPException(status_code=500, detail="Could not determine the next assignment ID.")

    # 3. Check for conflict with the determined ID
    if blob_uploader.assignment_exists(assignment.semester, assignment.course_id, assignment.assignment_id):
        logger.warning(f"Attempt to create assignment with existing ID: {assignment.semester}/{assignment.course_id}/{assignment.assignment_id}")
        raise HTTPException(
            status_code=409,
            detail=f"Assignment with ID '{assignment.assignment_id}' already exists for this course."
        )

    # 4. Upload assignment data
    try:
        # Assign indices to questions before upload if needed
        if assignment.questions:
             for i, q in enumerate(assignment.questions):
                 if hasattr(q, 'question_index'): # Check if Question model has the field
                    q.question_index = i

        blob_uploader.upload_assignment_metadata(assignment) # Upload main metadata + potentially questions if model includes them

        # If questions are NOT saved by upload_assignment_metadata, upload them individually:
        # (Comment this block out if upload_assignment_metadata saves the whole object including questions)
        if assignment.questions:
             for i, question in enumerate(assignment.questions):
                 q_index = question.question_index if hasattr(question, 'question_index') and question.question_index is not None else i
                 blob_uploader.upload_question_metadata(
                     assignment.semester, assignment.course_id, assignment.assignment_id, q_index, question
                 )

        logger.info(f"Successfully created assignment: {assignment.semester}/{assignment.course_id}/{assignment.assignment_id}")

        # Refetch the created assignment to include final state in response
        created_assignment = blob_uploader.get_assignment_metadata(assignment.semester, assignment.course_id, assignment.assignment_id)
        if not created_assignment:
             logger.error(f"Failed to retrieve assignment metadata immediately after creation: {assignment.semester}/{assignment.course_id}/{assignment.assignment_id}")
             raise HTTPException(status_code=500, detail="Failed to confirm assignment creation.")
        created_assignment.questions = blob_uploader.list_questions(assignment.semester, assignment.course_id, assignment.assignment_id)
        return created_assignment
    except Exception as e:
        logger.exception(f"Failed to upload assignment data for {assignment.semester}/{assignment.course_id}/{assignment.assignment_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to save assignment data to storage.")


@router.patch(
    "/assignment/add_question",
    # response_model=Question, # Or just index { "question_index": int }
    summary="Add Question",
    description="Adds a new question to an assignment.",
    responses={
        200: {"description": "Question added successfully", "content": {"application/json": {"example": {"question_index": 5}}}},
        400: {"detail": "Missing or invalid parameters."},
        404: {"detail": "Assignment not found."},
        401: {"detail": "Requester is not authenticated."},
        403: {"detail": "Authenticated but access is not allowed."}
    }
)
async def add_question(
        add_question_request: AddQuestionRequest = Body(...),
        user_meta: UserToken = Depends(user_from_auth),
):
    blob_uploader = AzureBlobService.get_instance()
    semester = add_question_request.semester
    course_id = add_question_request.course_id
    assignment_id = add_question_request.assignment_id

    # Auth Checks (condensed)
    if not blob_uploader.course_exists(semester, course_id): raise HTTPException(status_code=404, detail="Course does not exist.")
    user = blob_uploader.get_user(user_meta.user_email)
    if not user or (semester, course_id) not in user.authenticated_courses: raise HTTPException(status_code=403, detail="User not found or access not allowed.")
    if not blob_uploader.assignment_exists(semester, course_id, assignment_id): raise HTTPException(status_code=404, detail="Assignment does not exist.")

    try:
        # Determine next index
        question_index = blob_uploader.count_questions(semester, course_id, assignment_id)

        # Prepare question object
        question_to_upload = add_question_request.question
        if hasattr(question_to_upload, 'question_index'):
            question_to_upload.question_index = question_index

        # Upload question
        blob_uploader.upload_question_metadata(
            semester, course_id, assignment_id, question_index, question_to_upload
        )
        logger.info(f"Added question index {question_index} to {semester}/{course_id}/{assignment_id}")
        return {"question_index": question_index} # Return new index
    except Exception as e:
        logger.exception(f"Failed to add question to {semester}/{course_id}/{assignment_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to add question.")


@router.patch(
    "/assignment/remove_question",
    summary="Remove Question",
    description="Removes a question from an assignment.",
    responses={
        200: {"description": "Question removed successfully", "content": {"application/json": {"example": {"detail": "Question removed successfully"}}}},
        400: {"detail": "Missing or invalid parameters."},
        404: {"detail": "Assignment or question not found."},
        401: {"detail": "Requester is not authenticated."},
        403: {"detail": "Authenticated but access is not allowed."}
    }
)
async def remove_question(
        semester: str = Query(..., description="Semester of the course."),
        course_id: str = Query(..., description="Identifier of the course."),
        assignment_id: str = Query(..., description="Identifier of the assignment."),
        question_index: int = Query(..., description="Index of the question to remove."),
        user_meta: UserToken = Depends(user_from_auth),
):
    # Validate params
    try:
        semester = Course.validate_semester(semester)
        course_id = Course.normalize_lowercase(course_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    blob_uploader = AzureBlobService.get_instance()

    # Auth Checks
    if not blob_uploader.course_exists(semester, course_id): raise HTTPException(status_code=404, detail="Course does not exist.")
    user = blob_uploader.get_user(user_meta.user_email)
    if not user or (semester, course_id) not in user.authenticated_courses: raise HTTPException(status_code=403, detail="User not found or access not allowed.")
    if not blob_uploader.assignment_exists(semester, course_id, assignment_id): raise HTTPException(status_code=404, detail="Assignment does not exist.")

    # Check if question index is valid
    try:
        num_questions = blob_uploader.count_questions(semester, course_id, assignment_id)
        if question_index < 0 or question_index >= num_questions:
            logger.warning(f"Invalid question index {question_index} for removal in {semester}/{course_id}/{assignment_id}. Total questions: {num_questions}")
            raise HTTPException(status_code=404, detail=f"Question with index {question_index} does not exist.")

        # Remove the question
        blob_uploader.delete_question_metadata(semester, course_id, assignment_id, question_index)
        logger.info(f"Removed question index {question_index} from {semester}/{course_id}/{assignment_id}")

        # Optional: Add logic here to re-index subsequent questions if your storage requires sequential numbering without gaps.

        return {"detail":  "Question removed successfully"}
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.exception(f"Failed to remove question {question_index} from {semester}/{course_id}/{assignment_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to remove question.")


@router.patch(
    "/assignment/edit_question",
    response_model=Question, # Return the updated Question object
    summary="Edit Question",
    description="Edits an existing question in an assignment.",
    responses={
        400: {"detail": "Missing or invalid parameters."},
        404: {"detail": "Assignment or question not found."},
        401: {"detail": "Requester is not authenticated."},
        403: {"detail": "Authenticated but access is not allowed."}
    }
)
async def edit_question(
        edit_question_request: EditQuestionRequest = Body(...),
        user_meta: UserToken = Depends(user_from_auth),
):
    blob_uploader = AzureBlobService.get_instance()
    semester = edit_question_request.semester
    course_id = edit_question_request.course_id
    assignment_id = edit_question_request.assignment_id
    question_index = edit_question_request.question_index

    # Auth Checks
    if not blob_uploader.course_exists(semester, course_id): raise HTTPException(status_code=404, detail="Course does not exist.")
    user = blob_uploader.get_user(user_meta.user_email)
    if not user or (semester, course_id) not in user.authenticated_courses: raise HTTPException(status_code=403, detail="User not found or access not allowed.")
    if not blob_uploader.assignment_exists(semester, course_id, assignment_id): raise HTTPException(status_code=404, detail="Assignment does not exist.")

    try:
        # Check if question index is valid
        num_questions = blob_uploader.count_questions(semester, course_id, assignment_id)
        if question_index < 0 or question_index >= num_questions:
            logger.warning(f"Invalid question index {question_index} for edit in {semester}/{course_id}/{assignment_id}. Total questions: {num_questions}")
            raise HTTPException(status_code=404, detail=f"Question with index {question_index} does not exist.")

        # Prepare question object for upload
        question_to_upload = edit_question_request.question
        if hasattr(question_to_upload, 'question_index'):
            question_to_upload.question_index = question_index

        # Update the question metadata
        blob_uploader.upload_question_metadata(
            semester, course_id, assignment_id, question_index, question_to_upload
        )
        logger.info(f"Edited question index {question_index} in {semester}/{course_id}/{assignment_id}")

        # Return the updated question object
        # It might be safer to refetch the question data after upload if upload doesn't return it
        # updated_question = blob_uploader.get_question_metadata(semester, course_id, assignment_id, question_index) # If such a function exists
        # return updated_question
        return question_to_upload # Return the object that was sent for upload

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.exception(f"Failed to edit question {question_index} in {semester}/{course_id}/{assignment_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to edit question.")


@router.patch(
    "/assignment/modify_order",
    summary="Modify Question Order",
    description="Modifies the order of questions in an assignment.",
    responses={
        200: {"description": "Order updated successfully", "content": {"application/json": {"example": {"detail": "Question order updated successfully"}}}},
        400: {"detail": "Missing, invalid parameters or index mismatch."},
        404: {"detail": "Assignment not found."},
        401: {"detail": "Requester is not authenticated."},
        403: {"detail": "Authenticated but access is not allowed."}
    }
)
async def modify_order(
        reorder_request: ModifyOrderRequest = Body(...),
        user_meta: UserToken = Depends(user_from_auth),
):
    blob_uploader = AzureBlobService.get_instance()
    semester = reorder_request.semester
    course_id = reorder_request.course_id
    assignment_id = reorder_request.assignment_id
    new_order = reorder_request.list_of_question_indexes

    # Auth Checks
    if not blob_uploader.course_exists(semester, course_id): raise HTTPException(status_code=404, detail="Course does not exist.")
    user = blob_uploader.get_user(user_meta.user_email)
    if not user or (semester, course_id) not in user.authenticated_courses: raise HTTPException(status_code=403, detail="User not found or access not allowed.")
    if not blob_uploader.assignment_exists(semester, course_id, assignment_id): raise HTTPException(status_code=404, detail="Assignment does not exist.")

    try:
        # Validate the new order list
        num_questions = blob_uploader.count_questions(semester, course_id, assignment_id)
        if num_questions != len(new_order):
            logger.warning(f"Order modification length mismatch for {semester}/{course_id}/{assignment_id}. Expected {num_questions}, got {len(new_order)}")
            raise HTTPException(status_code=400, detail="Number of indexes in list must match the current number of questions.")
        if sorted(new_order) != list(range(num_questions)):
            logger.warning(f"Invalid index permutation for order modification in {semester}/{course_id}/{assignment_id}. Received: {new_order}")
            raise HTTPException(status_code=400, detail="List of indexes must be a valid permutation of existing question indices (0 to N-1).")

        # Reorder questions
        blob_uploader.reorder_questions(semester, course_id, assignment_id, new_order)
        logger.info(f"Reordered questions for {semester}/{course_id}/{assignment_id} to: {new_order}")

        return {"detail":  "Question order updated successfully"}
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.exception(f"Failed to modify question order for {semester}/{course_id}/{assignment_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to modify question order.")


# === NEW METADATA UPDATE ENDPOINT ===
@router.patch(
    "/assignments/{assignment_id}", # Use Path parameter for ID
    response_model=Assignment,
    summary="Update Assignment Metadata",
    description="Updates top-level assignment details like guidelines.",
    responses={
        400: {"detail": "Invalid payload."},
        404: {"detail": "Assignment not found."},
        401: {"detail": "Requester is not authenticated."},
        403: {"detail": "Authenticated but access is not allowed."}
    }
)
async def update_assignment_metadata(
    payload: AssignmentMetadataUpdate = Body(..., description="The metadata fields to update."),
    semester: str = Query(..., description="Semester of the course."),
    course_id: str = Query(..., description="Identifier of the course."),
    assignment_id: str = Path(..., description="Identifier of the assignment to update."),
    include_questions_in_response: bool = Query(True, description="Whether to include questions in the response."),
    user_meta: UserToken = Depends(user_from_auth),
):
    """
    Handles PATCH requests to update assignment metadata (e.g., guidelines).
    """
    logger.debug(f"Received PATCH request for /assignments/{assignment_id} with payload: {payload.model_dump()}") # Pydantic v2+
    # logger.debug(f"Received PATCH request for /assignments/{assignment_id} with payload: {payload.dict()}") # Pydantic v1

    # Basic validation
    try:
        semester = Course.validate_semester(semester)
        course_id = Course.normalize_lowercase(course_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    blob_uploader = AzureBlobService.get_instance()

    # --- Authentication & Authorization ---
    if not blob_uploader.course_exists(semester, course_id):
        logger.warning(f"Course not found: {semester}/{course_id} for PATCH /assignments/{assignment_id}")
        raise HTTPException(status_code=404, detail="Course does not exist.")

    user = blob_uploader.get_user(user_meta.user_email)
    if not user:
        logger.error(f"User not found in store: {user_meta.user_email} for PATCH /assignments/{assignment_id}")
        raise HTTPException(status_code=403, detail="User data not found.")
    if (semester, course_id) not in user.authenticated_courses:
        logger.warning(f"User {user_meta.user_email} forbidden access for PATCH /assignments/{assignment_id} on {semester}/{course_id}")
        raise HTTPException(status_code=403, detail="Authenticated but access to this course is not allowed.")

    if not blob_uploader.assignment_exists(semester, course_id, assignment_id):
        logger.warning(f"Assignment not found: {semester}/{course_id}/{assignment_id} for PATCH")
        raise HTTPException(status_code=404, detail="Assignment does not exist.")
    # --- End Auth/Authz ---

    try:
        # Get current data
        current_assignment = blob_uploader.get_assignment_metadata(semester, course_id, assignment_id)
        if not current_assignment:
             logger.error(f"Assignment existed but failed to retrieve metadata: {semester}/{course_id}/{assignment_id}")
             raise HTTPException(status_code=404, detail="Assignment metadata could not be retrieved for update.")

        updated = False
        # Apply updates ONLY if field is present in payload and different
        # Use model_dump(exclude_unset=True) to check only provided fields in Pydantic v2+
        payload_data = payload.model_dump(exclude_unset=True)
        # payload_data = payload.dict(exclude_unset=True) # Use this for Pydantic v1

        if 'assignment_guidelines' in payload_data:
            # Check if value is actually different before marking as updated
            if current_assignment.assignment_guidelines != payload_data['assignment_guidelines']:
                logger.info(f"Updating guidelines for assignment {assignment_id}")
                current_assignment.assignment_guidelines = payload_data['assignment_guidelines']
                updated = True

        # Add similar checks for other potential fields like assignment_name
        # if 'assignment_name' in payload_data:
        #     if current_assignment.assignment_name != payload_data['assignment_name']:
        #         logger.info(f"Updating name for assignment {assignment_id}")
        #         current_assignment.assignment_name = payload_data['assignment_name']
        #         updated = True

        if updated:
            logger.info(f"Saving updated metadata for assignment {assignment_id} in {semester}/{course_id}")
            blob_uploader.upload_assignment_metadata(current_assignment) # Overwrite/update the metadata file
        else:
            logger.info(f"No metadata changes submitted or detected for assignment {assignment_id} in {semester}/{course_id}")

        # Return the potentially updated assignment object
        # Fetch fresh data again to ensure response reflects saved state
        final_assignment = blob_uploader.get_assignment_metadata(semester, course_id, assignment_id)
        if not final_assignment:
             logger.error(f"Failed to retrieve final assignment metadata after potential update: {semester}/{course_id}/{assignment_id}")
             raise HTTPException(status_code=500, detail="Failed to retrieve updated assignment details.")

        if include_questions_in_response:
            final_assignment.questions = blob_uploader.list_questions(semester, course_id, assignment_id)
        else:
            final_assignment.questions = None # Explicitly clear if not requested
        return final_assignment

    except HTTPException as http_exc:
        raise http_exc # Re-raise FastAPI's expected exceptions
    except Exception as e:
        logger.exception(f"Unexpected error updating assignment metadata for {semester}/{course_id}/{assignment_id}: {e}")
        raise HTTPException(status_code=500, detail="An internal server error occurred while updating assignment metadata.")
# === END NEW METADATA UPDATE ENDPOINT ===


@router.get(
    "/assignment",
    response_model=Assignment,
    summary="Get Assignment",
    description="Retrieves a specific assignment by course and assignment ID.",
    responses={
        404: {"detail": "Assignment or Course not found."},
        401: {"detail": "Requester is not authenticated."},
        403: {"detail": "Authenticated but access is not allowed."}
    }
)
async def get_assignment(
        semester: str = Query(..., description="Semester of the course."),
        course_id: str = Query(..., description="Identifier of the course."),
        assignment_id: str = Query(..., description="Identifier of the assignment."),
        include_questions: bool = Query(True, description="Whether to include questions in the response."),
        user_meta: UserToken = Depends(user_from_auth),
):
    # Validate params
    try:
        semester = Course.validate_semester(semester)
        course_id = Course.normalize_lowercase(course_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    blob_uploader = AzureBlobService.get_instance()

    # Auth Checks
    if not blob_uploader.course_exists(semester, course_id): raise HTTPException(status_code=404, detail="Course does not exist.")
    user = blob_uploader.get_user(user_meta.user_email)
    if not user or (semester, course_id) not in user.authenticated_courses: raise HTTPException(status_code=403, detail="User not found or access not allowed.")
    if not blob_uploader.assignment_exists(semester, course_id, assignment_id): raise HTTPException(status_code=404, detail="Assignment does not exist.")

    try:
        # Get assignment metadata
        assignment = blob_uploader.get_assignment_metadata(semester, course_id, assignment_id)
        if not assignment:
            logger.error(f"Assignment existed but failed to get metadata: {semester}/{course_id}/{assignment_id}")
            raise HTTPException(status_code=404, detail="Assignment metadata could not be retrieved.")

        if include_questions:
            assignment.questions = blob_uploader.list_questions(semester, course_id, assignment_id)
        else:
            assignment.questions = None # Explicitly set if not included

        return assignment
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.exception(f"Failed to get assignment {semester}/{course_id}/{assignment_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve assignment details.")


@router.get(
    "/assignments",
    response_model=List[Assignment],
    summary="List Assignments",
    description="Retrieves all assignments associated with a course.",
    responses={
        404: {"detail": "Course not found."},
        401: {"detail": "Requester is not authenticated."},
        403: {"detail": "Authenticated but access is not allowed."}
    }
)
async def list_assignments(
        semester: str = Query(..., description="Semester of the course."),
        course_id: str = Query(..., description="Identifier of the course."),
        include_questions: bool = Query(True, description="Whether to include questions in the response."),
        user_meta: UserToken = Depends(user_from_auth),
):
    # Validate params
    try:
        semester = Course.validate_semester(semester)
        course_id = Course.normalize_lowercase(course_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    blob_uploader = AzureBlobService.get_instance()

    # Auth Checks
    if not blob_uploader.course_exists(semester, course_id): raise HTTPException(status_code=404, detail="Course does not exist.")
    user = blob_uploader.get_user(user_meta.user_email)
    if not user or (semester, course_id) not in user.authenticated_courses: raise HTTPException(status_code=403, detail="User not found or access not allowed.")

    try:
        # Get all assignments for the course
        assignments = blob_uploader.list_assignments(semester, course_id)

        # For each assignment, get its questions if requested
        if include_questions:
            for assignment in assignments:
                # Ensure assignment_id exists before trying to list questions
                if hasattr(assignment, 'assignment_id') and assignment.assignment_id is not None:
                     assignment.questions = blob_uploader.list_questions(semester, course_id, assignment.assignment_id)
                else:
                     assignment.questions = [] # Assign empty list if ID is missing
                     logger.warning(f"Assignment object missing ID when listing questions for {semester}/{course_id}: {assignment}")
        else:
            for assignment in assignments:
                assignment.questions = None # Explicitly set to None

        return assignments
    except Exception as e:
        logger.exception(f"Failed to list assignments for {semester}/{course_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve assignments list.")


@router.delete(
    "/assignment",
    summary="Delete Assignment",
    description="Deletes a specified assignment.",
    responses={
        200: {"description": "Assignment deleted successfully", "content": {"application/json": {"example": {"detail": "Assignment deleted successfully"}}}},
        404: {"detail": "Assignment or Course not found."},
        401: {"detail": "Requester is not authenticated."},
        403: {"detail": "Authenticated but access is not allowed."}
    }
)
async def delete_assignment(
        semester: str = Query(..., description="Semester of the course."),
        course_id: str = Query(..., description="Identifier of the course."),
        assignment_id: str = Query(..., description="Identifier of the assignment to delete."),
        user_meta: UserToken = Depends(user_from_auth),
):
    # Validate params
    try:
        semester = Course.validate_semester(semester)
        course_id = Course.normalize_lowercase(course_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    blob_uploader = AzureBlobService.get_instance()

    # Auth Checks
    if not blob_uploader.course_exists(semester, course_id): raise HTTPException(status_code=404, detail="Course does not exist.")
    user = blob_uploader.get_user(user_meta.user_email)
    if not user or (semester, course_id) not in user.authenticated_courses: raise HTTPException(status_code=403, detail="User not found or access not allowed.")
    if not blob_uploader.assignment_exists(semester, course_id, assignment_id): raise HTTPException(status_code=404, detail="Assignment does not exist.")

    try:
        # Delete assignment
        blob_uploader.delete_assignment(semester, course_id, assignment_id)
        logger.info(f"Deleted assignment {semester}/{course_id}/{assignment_id}")

        return {"detail":  "Assignment deleted successfully"}
    except Exception as e:
        logger.exception(f"Failed to delete assignment {semester}/{course_id}/{assignment_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete assignment.")