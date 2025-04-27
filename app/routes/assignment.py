# assignment.py

import re
from typing import List, Optional # Ensure Optional is imported
from fastapi import APIRouter, HTTPException, Query, Body, Depends, Path # Ensure Path is imported
from pydantic import BaseModel, Field, field_validator
from app.models import Course, UserToken

# Assuming Assignment and Question models are now defined in app.models.assignment
# and Question includes 'question_index: int'
from app.models.assignment import Assignment, Question
from app.services.azure_blob_service import AzureBlobService
from azure.storage.blob import ContainerClient
import logging

from app.utils.jwt_service import JWTService

logger = logging.getLogger(__name__)

# --- Pydantic Models ---

class QuestionIndexObject(BaseModel):
    question_index: int = Field(..., description="The 0-based index of the question within the assignment.")

# Assuming Question model (imported) now includes question_index: int

class EditQuestionRequest(BaseModel):
    """ Request body is just the updated Question object """
    question: Question = Field(..., description="The updated question data, including its question_index.")

    # No need for separate semester, course_id, assignment_id, question_index here
    # as they will be path/query parameters in the endpoint.

class AddQuestionRequest(BaseModel):
    """ Request body is just the new Question object (index will be ignored/assigned) """
    # The Question model requires question_index, but it will be ignored and assigned by the backend.
    # Alternatively, make a specific AddQuestionPayload model without the index.
    # Let's assume for now the frontend sends a Question object, maybe with a placeholder index.
    question: Question = Field(..., description="The data of the new question. The provided index will be ignored.")

    # No need for semester, course_id, assignment_id here if they are path/query params

class ModifyOrderRequest(BaseModel):
    """ Request body contains the new order """
    list_of_question_indexes: List[QuestionIndexObject] = Field(..., description="List of objects, each containing the original question_index, in the desired new order.")

    # No need for semester, course_id, assignment_id here if they are path/query params

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


# --- Utility for Auth Checks (Example - Adapt as needed) ---
async def check_course_auth(
    semester: str,
    course_id: str,
    user_meta: UserToken = Depends(user_from_auth)
) -> AzureBlobService:
    """ Dependency to validate params and check user auth for a course """
    try:
        validated_semester = Course.validate_semester(semester)
        validated_course_id = Course.normalize_lowercase(course_id)
    except ValueError as e:
        logger.warning(f"Invalid semester/course format: {semester}/{course_id} - {e}")
        raise HTTPException(status_code=400, detail=str(e))

    blob_uploader = AzureBlobService.get_instance()

    if not blob_uploader.course_exists(validated_semester, validated_course_id):
        logger.warning(f"Course not found during auth check: {validated_semester}/{validated_course_id}")
        raise HTTPException(status_code=404, detail="Course does not exist.")

    user = blob_uploader.get_user(user_meta.user_email)
    if not user:
        logger.error(f"Authenticated user not found in store: {user_meta.user_email}")
        # Use 403 Forbidden as user is authenticated but lacks profile/permissions
        raise HTTPException(status_code=403, detail="User data not found.")

    if (validated_semester, validated_course_id) not in user.authenticated_courses:
        logger.warning(f"User {user_meta.user_email} forbidden access to {validated_semester}/{validated_course_id}")
        raise HTTPException(status_code=403, detail="Authenticated but access to this course is not allowed.")

    return blob_uploader # Return service instance for reuse in endpoint

# --- API Endpoints ---

@router.post(
    "/assignment",
    response_model=Assignment,
    summary="Create Assignment",
    description="Creates a new assignment with questions and guidelines.",
    status_code=201, # Use 201 Created for successful creation
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
    blob_uploader: AzureBlobService = Depends(check_course_auth), # Use dependency for auth
    # Note: check_course_auth implicitly depends on user_meta
):
    """
    Creates a new assignment for a course.
    Assigns sequential question_index values (0, 1, 2...) to the questions.
    If assignment_id is not provided, generates the next sequential integer ID.
    """
    # Course auth already checked by dependency
    # Validation of semester/course_id format done in dependency

    # 1. Determine/Generate assignment_id (if needed)
    if assignment.assignment_id is None or assignment.assignment_id == "":
        logger.info(f"assignment_id not provided for course {assignment.semester}/{assignment.course_id}. Generating next sequential ID.")
        try:
            # Logic to find max existing integer ID (simplified - ensure robust implementation)
            existing_assignments = blob_uploader.list_assignments(assignment.semester, assignment.course_id)
            max_id = -1
            for assign_obj in existing_assignments:
                try:
                    current_id_int = int(str(assign_obj.assignment_id))
                    max_id = max(max_id, current_id_int)
                except (ValueError, TypeError, AttributeError):
                    continue # Ignore non-integer IDs or objects without the attribute
            next_id_int = max_id + 1
            assignment.assignment_id = str(next_id_int)
            logger.info(f"Generated NEW sequential integer assignment_id: {assignment.assignment_id}")
        except Exception as e:
            logger.exception(f"Error generating next assignment ID: {e}")
            raise HTTPException(status_code=500, detail="Could not determine the next assignment ID.")

    # 2. Check for conflict with the determined ID
    if blob_uploader.assignment_exists(assignment.semester, assignment.course_id, assignment.assignment_id):
        logger.warning(f"Conflict: Assignment ID '{assignment.assignment_id}' already exists.")
        raise HTTPException(
            status_code=409,
            detail=f"Assignment with ID '{assignment.assignment_id}' already exists for this course."
        )

    # 3. Assign question_index to incoming questions
    if assignment.questions:
        for i, q in enumerate(assignment.questions):
            q.question_index = i # <<<--- Assign index based on list order
            logger.debug(f"Assigning index {i} to question: {q.question_text[:30]}...")
    else:
        logger.info(f"Creating assignment {assignment.assignment_id} with no initial questions.")

    # 4. Upload assignment data
    try:
        # Upload main metadata. Does this save questions too? Depends on implementation.
        blob_uploader.upload_assignment_metadata(assignment)

        # If questions need separate upload:
        # (Assuming upload_assignment_metadata DOES NOT save questions)
        if assignment.questions:
            logger.info(f"Uploading {len(assignment.questions)} questions individually for assignment {assignment.assignment_id}...")
            for question in assignment.questions:
                 # Ensure question_index exists before using it
                 if not hasattr(question, 'question_index') or question.question_index is None:
                      logger.error(f"Programming Error: Question index was not assigned before upload attempt for assignment {assignment.assignment_id}")
                      raise ValueError("Internal error: Question index missing before upload.")
                 blob_uploader.upload_question_metadata(
                     assignment.semester, assignment.course_id, assignment.assignment_id,
                     question.question_index, # Use the assigned index
                     question
                 )
        # (End optional separate upload block)

        logger.info(f"Successfully created assignment: {assignment.semester}/{assignment.course_id}/{assignment.assignment_id}")

        # Refetch to return the final state including potentially generated ID and assigned indices
        # Important: Ensure get_assignment_metadata + list_questions return questions WITH indices
        created_assignment = blob_uploader.get_assignment_metadata(assignment.semester, assignment.course_id, assignment.assignment_id)
        if not created_assignment:
             logger.error("Failed to retrieve assignment metadata immediately after creation.")
             raise HTTPException(status_code=500, detail="Failed to confirm assignment creation.")
        # Fetch questions which should now include the index from storage
        created_assignment.questions = blob_uploader.list_questions(assignment.semester, assignment.course_id, assignment.assignment_id)
        return created_assignment
    except HTTPException as http_exc:
        raise http_exc # Re-raise HTTP exceptions
    except Exception as e:
        logger.exception(f"Failed to upload assignment data: {e}")
        raise HTTPException(status_code=500, detail="Failed to save assignment data to storage.")


@router.post( # Changed to POST as it creates a resource (a question)
    "/assignments/{assignment_id}/questions", # More RESTful path
    response_model=Question, # Return the created Question with its assigned index
    summary="Add Question",
    status_code=201, # Use 201 Created
    description="Adds a new question to the end of an assignment.",
    responses={
        400: {"detail": "Missing or invalid parameters."},
        404: {"detail": "Assignment not found."},
        401: {"detail": "Requester is not authenticated."},
        403: {"detail": "Authenticated but access is not allowed."}
    }
)
async def add_question(
        # Path parameters
        assignment_id: str = Path(..., description="Identifier of the assignment."),
        # Query parameters
        semester: str = Query(..., description="Semester of the course."),
        course_id: str = Query(..., description="Identifier of the course."),
        # Request body
        add_request: AddQuestionRequest = Body(...), # Contains the Question object
        # Dependencies
        blob_uploader: AzureBlobService = Depends(check_course_auth),
):
    # Auth checked by dependency
    if not blob_uploader.assignment_exists(semester, course_id, assignment_id):
        raise HTTPException(status_code=404, detail="Assignment does not exist.")

    try:
        # Determine next index
        # Ensure count_questions provides the correct next index (e.g., if indices are 0, 1, count should be 2)
        next_question_index = blob_uploader.count_questions(semester, course_id, assignment_id)
        logger.info(f"Determined next question index for {assignment_id} as {next_question_index}")

        # Prepare question object, assign the determined index
        question_to_upload = add_request.question
        question_to_upload.question_index = next_question_index # <<<--- Assign correct index

        # Upload question
        blob_uploader.upload_question_metadata(
            semester, course_id, assignment_id,
            next_question_index, # Use the determined index
            question_to_upload
        )
        logger.info(f"Added question index {next_question_index} to {semester}/{course_id}/{assignment_id}")

        # Return the complete Question object including the assigned index
        return question_to_upload

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.exception(f"Failed to add question to {semester}/{course_id}/{assignment_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to add question.")


@router.delete( # Changed to DELETE as it removes a resource
    "/assignments/{assignment_id}/questions/{question_index}", # More RESTful path
    summary="Remove Question",
    status_code=200, # OK or 204 No Content could also work
    description="Removes a question from an assignment and potentially re-indexes subsequent questions.",
    responses={
        200: {"description": "Question removed successfully", "content": {"application/json": {"example": {"detail": "Question removed successfully"}}}},
        400: {"detail": "Invalid index."},
        404: {"detail": "Assignment or question not found."},
        401: {"detail": "Requester is not authenticated."},
        403: {"detail": "Authenticated but access is not allowed."}
    }
)
async def remove_question(
        # Path parameters
        assignment_id: str = Path(..., description="Identifier of the assignment."),
        question_index: int = Path(..., description="Index of the question to remove.", ge=0), # Ensure index is non-negative
        # Query parameters
        semester: str = Query(..., description="Semester of the course."),
        course_id: str = Query(..., description="Identifier of the course."),
        # Dependencies
        blob_uploader: AzureBlobService = Depends(check_course_auth),
):
    # Auth checked by dependency
    if not blob_uploader.assignment_exists(semester, course_id, assignment_id):
        raise HTTPException(status_code=404, detail="Assignment does not exist.")

    # Check if question index exists *before* attempting delete
    # This check might be implicitly handled by delete_question_metadata if it raises errors,
    # but explicit check is safer. Depends on AzureBlobService implementation.
    if not blob_uploader.question_exists(semester, course_id, assignment_id, question_index): # Assuming question_exists method
         logger.warning(f"Attempt to delete non-existent question index {question_index} from {assignment_id}")
         raise HTTPException(status_code=404, detail=f"Question with index {question_index} does not exist.")

    try:
        # Remove the question
        blob_uploader.delete_question_metadata(semester, course_id, assignment_id, question_index)
        logger.info(f"Removed question index {question_index} from {semester}/{course_id}/{assignment_id}")

        # --- CRITICAL: Re-indexing Logic ---
        # If your storage relies on sequential indices (e.g., files named 0.json, 1.json, 2.json),
        # you MUST re-index questions with indices > deleted_index.
        # This requires listing remaining questions, updating their index, and re-saving/renaming.
        # Example (requires implementation in AzureBlobService):
        try:
            logger.info(f"Attempting to re-index questions in {assignment_id} after deleting index {question_index}")
            blob_uploader.reindex_questions_after_delete(semester, course_id, assignment_id, question_index)
            logger.info(f"Successfully re-indexed questions in {assignment_id} after delete.")
        except NotImplementedError:
             logger.warning(f"Re-indexing after delete is not implemented in AzureBlobService for {assignment_id}. Indices may now have gaps.")
             # Decide if this is acceptable or should be a 501 Not Implemented error.
        except Exception as reindex_err:
             logger.error(f"Failed to re-index questions after deleting index {question_index} from {assignment_id}: {reindex_err}")
             # This is problematic. The question is deleted, but indices are inconsistent.
             # Return success but log error? Or return 500? Depends on requirements.
             # For now, let's return success on delete but log the reindex failure.

        return {"detail":  "Question removed successfully"}
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.exception(f"Failed to remove question {question_index}: {e}")
        raise HTTPException(status_code=500, detail="Failed to remove question.")


@router.put( # Changed to PUT as it replaces the resource at the given index
    "/assignments/{assignment_id}/questions/{question_index}", # More RESTful path
    response_model=Question, # Return the updated Question object
    summary="Edit Question",
    description="Edits an existing question in an assignment by replacing it.",
    responses={
        400: {"detail": "Missing or invalid parameters."},
        404: {"detail": "Assignment or question not found."},
        401: {"detail": "Requester is not authenticated."},
        403: {"detail": "Authenticated but access is not allowed."}
    }
)
async def edit_question(
        # Path parameters
        assignment_id: str = Path(..., description="Identifier of the assignment."),
        question_index: int = Path(..., description="Index of the question to edit.", ge=0),
        # Query parameters
        semester: str = Query(..., description="Semester of the course."),
        course_id: str = Query(..., description="Identifier of the course."),
        # Request body
        edit_request: EditQuestionRequest = Body(...), # Contains the updated Question object
        # Dependencies
        blob_uploader: AzureBlobService = Depends(check_course_auth),
):
    # Auth checked by dependency
    if not blob_uploader.assignment_exists(semester, course_id, assignment_id):
        raise HTTPException(status_code=404, detail="Assignment does not exist.")

    # --- Validation ---
    # Ensure the index in the path matches the index in the payload
    if edit_request.question.question_index != question_index:
        logger.warning(f"Index mismatch in edit request: Path={question_index}, Payload={edit_request.question.question_index}")
        raise HTTPException(status_code=400, detail="Question index in request body must match the index in the URL path.")

    # Check if the question index actually exists for this assignment
    if not blob_uploader.question_exists(semester, course_id, assignment_id, question_index): # Assuming question_exists method
         logger.warning(f"Attempt to edit non-existent question index {question_index} in {assignment_id}")
         raise HTTPException(status_code=404, detail=f"Question with index {question_index} does not exist.")
    # --- End Validation ---

    try:
        # Prepare question object for upload (already validated)
        question_to_upload = edit_request.question

        # Update the question metadata - Use the index from the path/payload
        blob_uploader.upload_question_metadata(
            semester, course_id, assignment_id,
            question_index, # Use the validated index
            question_to_upload
        )
        logger.info(f"Edited question index {question_index} in {semester}/{course_id}/{assignment_id}")

        # Return the updated question object
        return question_to_upload

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.exception(f"Failed to edit question {question_index}: {e}")
        raise HTTPException(status_code=500, detail="Failed to edit question.")


@router.patch( # Stays PATCH as it modifies the order property of the assignment
    "/assignments/{assignment_id}/questions/order", # More specific path
    summary="Modify Question Order",
    description="Modifies the order of questions in an assignment based on original indices.",
    responses={
        200: {"description": "Order updated successfully", "content": {"application/json": {"example": {"detail": "Question order updated successfully"}}}},
        400: {"detail": "Missing, invalid parameters or index mismatch."},
        404: {"detail": "Assignment not found."},
        401: {"detail": "Requester is not authenticated."},
        403: {"detail": "Authenticated but access is not allowed."}
    }
)
async def modify_order(
        # Path parameters
        assignment_id: str = Path(..., description="Identifier of the assignment."),
        # Query parameters
        semester: str = Query(..., description="Semester of the course."),
        course_id: str = Query(..., description="Identifier of the course."),
        # Request body
        reorder_request: ModifyOrderRequest = Body(...),
        # Dependencies
        blob_uploader: AzureBlobService = Depends(check_course_auth),
):
    # Auth checked by dependency
    if not blob_uploader.assignment_exists(semester, course_id, assignment_id):
        raise HTTPException(status_code=404, detail="Assignment does not exist.")

    new_order = reorder_request.list_of_question_indexes

    try:
        # Validate the new order list against existing questions
        # Ensure count_questions and list_questions provide reliable info
        current_questions = blob_uploader.list_questions(semester, course_id, assignment_id)
        current_indices = sorted([q.question_index for q in current_questions]) # Get existing indices

        num_questions = len(current_indices)

        if num_questions != len(new_order):
            logger.warning(f"Order modification length mismatch for {assignment_id}. Expected {num_questions}, got {len(new_order)}")
            raise HTTPException(status_code=400, detail="Number of indexes in list must match the current number of questions.")

        # Check if the submitted list contains exactly the same set of indices as currently exist
        if set(new_order) != set(current_indices):
            logger.warning(f"Invalid index set for order modification in {assignment_id}. Expected indices: {current_indices}, Received: {new_order}")
            raise HTTPException(status_code=400, detail="List of indexes must contain exactly the same indexes as the existing questions.")

        # Reorder questions - This function needs careful implementation in AzureBlobService
        # It should likely fetch all questions, reassign their question_index based on the new order,
        # and re-save/rename them.
        blob_uploader.reorder_questions(semester, course_id, assignment_id, new_order)
        logger.info(f"Reordered questions for {semester}/{course_id}/{assignment_id} according to original indices: {new_order}")

        return {"detail":  "Question order updated successfully"}
    except HTTPException as http_exc:
        raise http_exc
    except NotImplementedError:
        logger.error(f"Question reordering is not implemented in AzureBlobService for {assignment_id}.")
        raise HTTPException(status_code=501, detail="Question reordering functionality is not implemented.")
    except Exception as e:
        logger.exception(f"Failed to modify question order for {assignment_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to modify question order.")


@router.patch(
    "/assignments/{assignment_id}", # Existing endpoint
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
    blob_uploader: AzureBlobService = Depends(check_course_auth), # Use dependency
):
    """ Handles PATCH requests to update assignment metadata (e.g., guidelines). """
    # Auth checked by dependency
    if not blob_uploader.assignment_exists(semester, course_id, assignment_id):
        raise HTTPException(status_code=404, detail="Assignment does not exist.")

    try:
        # Get current data
        current_assignment = blob_uploader.get_assignment_metadata(semester, course_id, assignment_id)
        if not current_assignment:
             raise HTTPException(status_code=404, detail="Assignment metadata could not be retrieved for update.")

        update_data = payload.model_dump(exclude_unset=True) # Get only fields provided in payload
        updated_assignment = current_assignment.model_copy(update=update_data) # Create updated copy (Pydantic v2+)
        # updated_assignment = current_assignment.copy(update=update_data) # Pydantic v1

        # Check if anything actually changed
        if current_assignment == updated_assignment:
             logger.info(f"No actual metadata changes detected for assignment {assignment_id}")
        else:
            logger.info(f"Saving updated metadata for assignment {assignment_id}")
            blob_uploader.upload_assignment_metadata(updated_assignment) # Overwrite/update

        # Return the potentially updated assignment object
        # Fetch fresh data again to ensure response reflects saved state
        final_assignment = blob_uploader.get_assignment_metadata(semester, course_id, assignment_id)
        if not final_assignment:
             raise HTTPException(status_code=500, detail="Failed to retrieve updated assignment details.")

        # Populate questions if requested (ensure list_questions returns index)
        if include_questions_in_response:
            final_assignment.questions = blob_uploader.list_questions(semester, course_id, assignment_id)
        else:
            final_assignment.questions = [] # Return empty list or None? Consistent response is good.

        return final_assignment

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.exception(f"Unexpected error updating assignment metadata: {e}")
        raise HTTPException(status_code=500, detail="An internal server error occurred while updating assignment metadata.")


@router.get(
    "/assignments/{assignment_id}", # Use path parameter
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
        # Path parameter
        assignment_id: str = Path(..., description="Identifier of the assignment."),
        # Query parameters
        semester: str = Query(..., description="Semester of the course."),
        course_id: str = Query(..., description="Identifier of the course."),
        include_questions: bool = Query(True, description="Whether to include questions in the response."),
        # Dependencies
        blob_uploader: AzureBlobService = Depends(check_course_auth),
):
    # Auth checked by dependency
    if not blob_uploader.assignment_exists(semester, course_id, assignment_id):
        raise HTTPException(status_code=404, detail="Assignment does not exist.")

    try:
        # Get assignment metadata
        assignment = blob_uploader.get_assignment_metadata(semester, course_id, assignment_id)
        if not assignment:
             # This case should ideally be caught by assignment_exists, but double-check
             raise HTTPException(status_code=404, detail="Assignment metadata could not be retrieved.")

        # Fetch questions (which should include index) if requested
        if include_questions:
            assignment.questions = blob_uploader.list_questions(semester, course_id, assignment_id)
            logger.debug(f"Retrieved {len(assignment.questions)} questions for assignment {assignment_id}")
        else:
            assignment.questions = [] # Return empty list if not included

        return assignment
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.exception(f"Failed to get assignment {assignment_id}: {e}")
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
        # Query parameters
        semester: str = Query(..., description="Semester of the course."),
        course_id: str = Query(..., description="Identifier of the course."),
        include_questions: bool = Query(False, description="Whether to include questions details for each assignment."), # Default False for list view efficiency
        # Dependencies
        blob_uploader: AzureBlobService = Depends(check_course_auth),
):
    # Auth checked by dependency
    try:
        # Get all assignment metadata objects
        assignments = blob_uploader.list_assignments(semester, course_id)
        logger.info(f"Found {len(assignments)} assignments for {semester}/{course_id}")

        # If questions requested, fetch them for each assignment
        if include_questions:
            logger.info(f"Fetching questions for {len(assignments)} assignments...")
            for assignment in assignments:
                if hasattr(assignment, 'assignment_id') and assignment.assignment_id is not None:
                     # Ensure list_questions returns questions with index
                     assignment.questions = blob_uploader.list_questions(semester, course_id, assignment.assignment_id)
                else:
                     assignment.questions = []
                     logger.warning(f"Assignment object missing ID when listing questions: {assignment}")
        else:
            # Explicitly set questions to empty list if not included
            for assignment in assignments:
                 assignment.questions = []

        return assignments
    except Exception as e:
        logger.exception(f"Failed to list assignments for {semester}/{course_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve assignments list.")


@router.delete(
    "/assignments/{assignment_id}", # Use path parameter
    summary="Delete Assignment",
    status_code=200, # Or 204 No Content
    description="Deletes a specified assignment and all its contents.",
    responses={
        200: {"description": "Assignment deleted successfully", "content": {"application/json": {"example": {"detail": "Assignment deleted successfully"}}}},
        404: {"detail": "Assignment or Course not found."},
        401: {"detail": "Requester is not authenticated."},
        403: {"detail": "Authenticated but access is not allowed."}
    }
)
async def delete_assignment(
        # Path parameter
        assignment_id: str = Path(..., description="Identifier of the assignment to delete."),
        # Query parameters
        semester: str = Query(..., description="Semester of the course."),
        course_id: str = Query(..., description="Identifier of the course."),
        # Dependencies
        blob_uploader: AzureBlobService = Depends(check_course_auth),
):
    # Auth checked by dependency
    if not blob_uploader.assignment_exists(semester, course_id, assignment_id):
        raise HTTPException(status_code=404, detail="Assignment does not exist.")

    try:
        # Delete assignment - This should handle deleting questions, responses etc. within AzureBlobService
        blob_uploader.delete_assignment(semester, course_id, assignment_id)
        logger.info(f"Deleted assignment {semester}/{course_id}/{assignment_id}")

        return {"detail":  "Assignment deleted successfully"}
    except Exception as e:
        logger.exception(f"Failed to delete assignment {assignment_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete assignment.")