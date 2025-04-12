import re
# <<< --- Added Optional here --- >>>
from typing import List, Optional

# <<< --- Added status and logging --- >>>
from fastapi import APIRouter, HTTPException, Query, Body, Depends, status
# <<< --- Added Optional here --- >>>
from pydantic import BaseModel, Field, field_validator, Optional

from app.models import Course
from app.models.assignment import Assignment, Question
from app.utils import JWTService, UserToken
from app.utils.azure_blob_service import AzureBlobService
# <<< --- Added logging import --- >>>
import logging


# --- Pydantic Request Models ---

class EditQuestionRequest(BaseModel):
    semester: str = Field(..., description="Semester of the course.")
    course_id: str = Field(..., description="Identifier of the course.")
    assignment_id: int = Field(..., description="Identifier of the assignment.")
    question_index: int = Field(..., description="Index of the question.")
    question: Question = Field(..., description="The updated question data.")

    @classmethod
    @field_validator("semester", mode='before')
    def validate_semester(cls, value: str) -> str:
        """Converts to lowercase and trims spaces."""
        # NOTE: This validator logic is likely incorrect (see previous analysis)
        # It raises error on VALID format. Should likely be `is None`.
        if re.fullmatch("[a-zA-Z]{1,12}[0-9]{4}", value) is not None:
             raise ValueError("Semester is in an invalid format. "
                              "Correct format looks like: seasonYYYY. (e.g. spring2025)")
        return value.strip().lower()


class AddQuestionRequest(BaseModel):
    semester: str = Field(..., description="Semester of the course.")
    course_id: str = Field(..., description="Identifier of the course.")
    assignment_id: int = Field(..., description="Identifier of the assignment to update.")
    question: Question = Field(..., description="The data of the new question. (Notice: You cannot specify "
                                                        "the index for this question. If you wish to re-order this "
                                                        "question, you must make a separate modify order request.)")

    @classmethod
    @field_validator("semester", mode='before')
    def validate_semester(cls, value: str) -> str:
        """Converts to lowercase and trims spaces."""
        # NOTE: This validator logic is likely incorrect (see previous analysis)
        if re.fullmatch("[a-zA-Z]{1,12}[0-9]{4}", value) is not None:
            raise ValueError("Semester is in an invalid format. "
                             "Correct format looks like: seasonYYYY. (e.g. spring2025)")
        return value.strip().lower()


class ModifyOrderRequest(BaseModel):
    semester: str = Field(..., description="Semester of the course.")
    course_id: str = Field(..., description="Identifier of the course.")
    assignment_id: int = Field(..., description="Identifier of the assignment.")
    list_of_question_indexes: List[int] = Field(..., description="New order for question indexes.")

    @classmethod
    @field_validator("semester", mode='before')
    def validate_semester(cls, value: str) -> str:
        """Converts to lowercase and trims spaces."""
        # NOTE: This validator logic is likely incorrect (see previous analysis)
        if re.fullmatch("[a-zA-Z]{1,12}[0-9]{4}", value) is not None:
            raise ValueError("Semester is in an invalid format. "
                             "Correct format looks like: seasonYYYY. (e.g. spring2025)")
        return value.strip().lower()

# <<< --- NEW Pydantic Request Model for PATCH --- >>>
class AssignmentUpdateRequest(BaseModel):
    assignment_title: Optional[str] = Field(
        None, description="The new title for the assignment. If omitted, title is not changed."
    )
    assignment_guidelines: Optional[str] = Field(
        None, description="The new guidelines for the assignment. If omitted, guidelines are not changed."
    )
# <<< --- END OF NEW MODEL --- >>>


# --- Router Initialization ---
router = APIRouter()
user_from_auth = JWTService.get_instance().from_authorization_header


# --- API Endpoints ---

@router.post(
    "/assignment",
    response_model=Assignment,
    summary="Create Assignment",
    description="Creates a new assignment with questions and guidelines.",
    responses={
        400: {"detail": "Missing or invalid parameters."},
        404: {"detail": "Course does not exist."},
        409: {"detail": "Assignment already exists."}, # Added 409
        401: {"detail": "Requester is not authenticated."},
        403: {"detail": "Authenticated but access is not allowed."}
    }
)
async def create_assignment(
        assignment: Assignment = Body(..., description="The assignment which to create."),
        user_meta: UserToken = Depends(user_from_auth),
):
    blob_uploader = AzureBlobService.get_instance()
    # Check if the course exists
    if not blob_uploader.course_exists(assignment.semester, assignment.course_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course does not exist.") # Use status module
    # Check if user has perms on course
    user = blob_uploader.get_user(user_meta.user_email)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found, authentication issue.") # Use status module
    if not user.authenticated_courses.__contains__((assignment.semester, assignment.course_id)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Authenticated but access is not allowed.") # Use status module
    # Check if this assignment id already exists
    if blob_uploader.assignment_exists(assignment.semester, assignment.course_id, assignment.assignment_id):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Assignment already exists.") # Use status module
    # If the user did not specify an assignment title, figure one out now
    if assignment.assignment_title is None:
        current_assignments = blob_uploader.list_assignments(assignment.semester, assignment.course_id)
        new_title = "Assignment "
        assignment_number = None
        # Check if current_assignments is None or empty before iterating
        if current_assignments:
            for current_assignment in current_assignments:
                # Check if assignment_title is not None before calling startswith
                if current_assignment.assignment_title and current_assignment.assignment_title.startswith(new_title):
                    try:
                        current_assignment_number = int(current_assignment.assignment_title.split(" ")[-1])
                        assignment_number = current_assignment_number if assignment_number is None \
                            else max(assignment_number, current_assignment_number)
                    except (ValueError, IndexError): # Catch potential errors splitting/converting
                        # Log this potential issue
                        logging.warning(f"Could not parse assignment number from title: {current_assignment.assignment_title}")
                        continue # Skip this assignment title
        assignment_number = 1 if assignment_number is None else assignment_number + 1
        assignment.assignment_title = new_title + str(assignment_number)
    # upload assignment metadata
    blob_uploader.upload_assignment_metadata(assignment)
    # upload assignment questions (only if provided in the initial request)
    if assignment.questions:
        for i, question in enumerate(assignment.questions):
            blob_uploader.upload_question_metadata(
                assignment.semester, assignment.course_id, assignment.assignment_id, i, question
            )
    # Return the created assignment (questions might be empty if not provided initially)
    return assignment


@router.patch(
    "/assignment/add_question",
    summary="Add Question",
    description="Adds a new question to an assignment.",
    responses={
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
    # Check if the course exists
    if not blob_uploader.course_exists(add_question_request.semester, add_question_request.course_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course does not exist.")
    # Check if user has perms on course
    user = blob_uploader.get_user(user_meta.user_email)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found, authentication issue.")
    if not user.authenticated_courses.__contains__((add_question_request.semester, add_question_request.course_id)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Authenticated but access is not allowed.")
    # Check if assignment exists
    if not blob_uploader.assignment_exists(add_question_request.semester, add_question_request.course_id, add_question_request.assignment_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment does not exist.")
    # Figure out question index (we use zero indexing)
    question_index = blob_uploader.count_questions(add_question_request.semester, add_question_request.course_id,
                                                   add_question_request.assignment_id)
    # Create Question object from request data
    question = Question(
        question_text=add_question_request.question.question_text,
        question_graphics_figures=add_question_request.question.question_graphics_figures
    )
    # Upload question
    blob_uploader.upload_question_metadata(
        add_question_request.semester, add_question_request.course_id, add_question_request.assignment_id, question_index, question
    )
    # Return the index of the added question
    return {"question_index": question_index}


@router.patch(
    "/assignment/remove_question",
    summary="Remove Question",
    description="Removes a question from an assignment.",
    responses={
        400: {"detail": "Missing or invalid parameters."},
        404: {"detail": "Assignment or question not found."},
        401: {"detail": "Requester is not authenticated."},
        403: {"detail": "Authenticated but access is not allowed."}
    }
)
async def remove_question(
        semester: str = Query(..., description="Semester of the course."),
        course_id: str = Query(..., description="Identifier of the course."),
        assignment_id: int = Query(..., description="Identifier of the assignment."),
        question_index: int = Query(..., description="Index of the question to remove."),
        user_meta: UserToken = Depends(user_from_auth),
):
    # validate params
    try:
        semester = Course.validate_semester(semester)
        course_id = Course.normalize_lowercase(course_id)
    except ValueError as e:
         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid parameter format: {e}")

    blob_uploader = AzureBlobService.get_instance()
    # Check if the course exists
    if not blob_uploader.course_exists(semester, course_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course does not exist.")
    # Check if user has perms on course
    user = blob_uploader.get_user(user_meta.user_email)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found, authentication issue.")
    if not user.authenticated_courses.__contains__((semester, course_id)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Authenticated but access is not allowed.")
    # Check if assignment exists
    if not blob_uploader.assignment_exists(semester, course_id, assignment_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment does not exist.")
    # Check if question exists using count to avoid listing all questions if possible
    num_questions = blob_uploader.count_questions(semester, course_id, assignment_id)
    if not (0 <= question_index < num_questions): # More direct check
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Question with index {question_index} does not exist.")

    # Remove the question
    try:
        blob_uploader.delete_question_metadata(semester, course_id, assignment_id, question_index)
    except Exception as e:
        logging.error(f"Failed to delete question metadata: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to remove question.")

    return {"detail":  "Question removed successfully"}


@router.patch(
    "/assignment/edit_question",
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
        edit_question_request: EditQuestionRequest = Body(...), # Renamed for clarity
        user_meta: UserToken = Depends(user_from_auth),
):
    blob_uploader = AzureBlobService.get_instance()
    # Check if the course exists
    if not blob_uploader.course_exists(edit_question_request.semester, edit_question_request.course_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course does not exist.")
    # Check if user has perms on course
    user = blob_uploader.get_user(user_meta.user_email)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found, authentication issue.")
    if not user.authenticated_courses.__contains__((edit_question_request.semester, edit_question_request.course_id)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Authenticated but access is not allowed.")
    # Check if assignment exists
    if not blob_uploader.assignment_exists(edit_question_request.semester, edit_question_request.course_id, edit_question_request.assignment_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment does not exist.")
    # Check if question exists using count
    num_questions = blob_uploader.count_questions(edit_question_request.semester, edit_question_request.course_id, edit_question_request.assignment_id)
    if not (0 <= edit_question_request.question_index < num_questions):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Question with index {edit_question_request.question_index} does not exist.")

    # Update the question
    try:
        blob_uploader.upload_question_metadata(
            edit_question_request.semester,
            edit_question_request.course_id,
            edit_question_request.assignment_id,
            edit_question_request.question_index,
            edit_question_request.question # Pass the Question object directly
        )
    except Exception as e:
        logging.error(f"Failed to upload updated question metadata: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update question.")

    # Return the updated question data as sent in the request
    return edit_question_request.question


@router.patch(
    "/assignment/modify_order",
    summary="Modify Question Order",
    description="Modifies the order of questions in an assignment.",
    responses={
        400: {"detail": "Invalid parameters (e.g., invalid permutation, incorrect count)."}, # Changed 404 to 400
        404: {"detail": "Course or Assignment not found."}, # Changed description
        401: {"detail": "Requester is not authenticated."},
        403: {"detail": "Authenticated but access is not allowed."}
    }
)
async def modify_order(
        reorder_request: ModifyOrderRequest = Body(...),
        user_meta: UserToken = Depends(user_from_auth),
):
    blob_uploader = AzureBlobService.get_instance()
    # Check if the course exists
    if not blob_uploader.course_exists(reorder_request.semester, reorder_request.course_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course does not exist.")

    # Check if user has perms on course
    user = blob_uploader.get_user(user_meta.user_email)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found, authentication issue.")
    if not user.authenticated_courses.__contains__((reorder_request.semester, reorder_request.course_id)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Authenticated but access is not allowed.")

    # Check if assignment exists
    if not blob_uploader.assignment_exists(reorder_request.semester, reorder_request.course_id, reorder_request.assignment_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment does not exist.")

    # Assert the length of the list of question indices matches number of questions
    num_questions = blob_uploader.count_questions(reorder_request.semester, reorder_request.course_id, reorder_request.assignment_id)
    # --- Corrected Logic for length check ---
    if num_questions != len(reorder_request.list_of_question_indexes):
        # Use 400 Bad Request for invalid input data
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Number of indexes ({len(reorder_request.list_of_question_indexes)}) must match number of questions ({num_questions}).")

    # Assert the list contains all indices from 0 to num_questions - 1 exactly once
    if sorted(reorder_request.list_of_question_indexes) != list(range(num_questions)):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="list_of_question_indexes must be a valid permutation of existing question indices (0 to N-1).")

    # Reorder questions
    try:
        blob_uploader.reorder_questions(reorder_request.semester, reorder_request.course_id, reorder_request.assignment_id, reorder_request.list_of_question_indexes)
    except Exception as e:
        logging.error(f"Failed during question reordering: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to reorder questions.")

    return {"detail":  "Question order updated successfully"}


# --- Operations on a Single Assignment Resource ---

@router.get(
    "/assignment",
    response_model=Assignment,
    summary="Get Assignment",
    description="Retrieves a specific assignment by course and assignment ID.",
    responses={
        400: {"detail": "Invalid parameters."}, # Added 400
        404: {"detail": "Course or Assignment not found."}, # Changed description
        401: {"detail": "Requester is not authenticated."},
        403: {"detail": "Authenticated but access is not allowed."}
    }
)
async def get_assignment(
        semester: str = Query(..., description="Semester of the course."),
        course_id: str = Query(..., description="Identifier of the course."),
        assignment_id: int = Query(..., description="Identifier of the assignment."),
        include_questions: bool = Query(False, description="Whether to include questions in the response."),
        user_meta: UserToken = Depends(user_from_auth),
):
    # validate params
    try:
        semester = Course.validate_semester(semester)
        course_id = Course.normalize_lowercase(course_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid parameter format: {e}")

    blob_uploader = AzureBlobService.get_instance()
    # Check if the course exists
    if not blob_uploader.course_exists(semester, course_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course does not exist.")

    # Check if user has perms on course
    user = blob_uploader.get_user(user_meta.user_email)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found, authentication issue.")
    if not user.authenticated_courses.__contains__((semester, course_id)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Authenticated but access is not allowed.")

    # Check if assignment exists & get metadata
    assignment = blob_uploader.get_assignment_metadata(semester, course_id, assignment_id)
    if not assignment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found.")

    # Fetch and add questions if requested
    if include_questions:
        assignment.questions = blob_uploader.list_questions(semester, course_id, assignment_id)
    else:
         assignment.questions = [] # Ensure questions list exists but is empty if not included

    return assignment


# <<< --- NEW PATCH ENDPOINT for updating assignment metadata --- >>>
@router.patch(
    "/assignment",
    response_model=Assignment,
    summary="Update Assignment Metadata",
    description="Partially updates the title and/or guidelines of an existing assignment.",
    responses={
        400: {"detail": "Invalid parameters or no update data provided."},
        404: {"detail": "Course or Assignment not found."},
        401: {"detail": "Requester is not authenticated."},
        403: {"detail": "Authenticated but access is not allowed."},
        500: {"detail": "Failed to save assignment update."} # Added 500
    }
)
async def update_assignment_metadata(
        semester: str = Query(..., description="Semester of the course."),
        course_id: str = Query(..., description="Identifier of the course."),
        assignment_id: int = Query(..., description="Identifier of the assignment to update."),
        update_data: AssignmentUpdateRequest = Body(..., description="Fields to update."),
        user_meta: UserToken = Depends(user_from_auth),
):
    # --- Validation and Authorization ---
    try:
        semester = Course.validate_semester(semester)
        course_id = Course.normalize_lowercase(course_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid parameter format: {e}")

    blob_uploader = AzureBlobService.get_instance()

    # Check if the course exists
    if not blob_uploader.course_exists(semester, course_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course does not exist.")

    # Check if user has permissions on course
    user = blob_uploader.get_user(user_meta.user_email)
    # Ensure user exists before checking permissions
    if not user:
         raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found, authentication issue.")
    if not user.authenticated_courses.__contains__((semester, course_id)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Authenticated user does not have access to this course.")

    # Check if assignment exists and get current metadata
    existing_assignment = blob_uploader.get_assignment_metadata(semester, course_id, assignment_id)
    if not existing_assignment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found.")

    # --- Apply Updates ---
    updated = False
    if update_data.assignment_title is not None:
        # Basic validation for title if needed (e.g., not empty)
        if not update_data.assignment_title.strip():
             raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Assignment title cannot be empty.")
        existing_assignment.assignment_title = update_data.assignment_title
        updated = True
    if update_data.assignment_guidelines is not None:
        # Allow empty string for guidelines, but assign it if provided
        existing_assignment.assignment_guidelines = update_data.assignment_guidelines
        updated = True

    if not updated:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No update data provided (assignment_title or assignment_guidelines).")

    # --- Save Updated Data ---
    # The upload_assignment_metadata method should already handle excluding questions
    try:
        blob_uploader.upload_assignment_metadata(existing_assignment)
    except Exception as e:
        # Log the actual error for debugging
        logging.error(f"Failed to upload updated assignment metadata: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to save assignment update.")

    # --- Return Updated Assignment (excluding questions unless fetched separately) ---
    # Note: We return the assignment object *without* questions, as we only updated the metadata file.
    # The frontend might need to re-fetch if it needs the full object including questions.
    existing_assignment.questions = [] # Ensure questions list exists but is empty
    return existing_assignment
# <<< --- END OF NEW PATCH ENDPOINT --- >>>


@router.delete(
    "/assignment",
    summary="Delete Assignment",
    description="Deletes a specified assignment.",
    responses={
        400: {"detail": "Invalid parameters."}, # Added 400
        404: {"detail": "Course or Assignment not found."}, # Changed description
        401: {"detail": "Requester is not authenticated."},
        403: {"detail": "Authenticated but access is not allowed."},
        500: {"detail": "Failed to delete assignment."} # Added 500
    }
)
async def delete_assignment(
        semester: str = Query(..., description="Semester of the course."),
        course_id: str = Query(..., description="Identifier of the course."),
        assignment_id: int = Query(..., description="Identifier of the assignment to delete."),
        user_meta: UserToken = Depends(user_from_auth),
):
    # validate params
    try:
        semester = Course.validate_semester(semester)
        course_id = Course.normalize_lowercase(course_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid parameter format: {e}")

    blob_uploader = AzureBlobService.get_instance()
    # Check if the course exists
    if not blob_uploader.course_exists(semester, course_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course does not exist.")

    # Check if user has perms on course
    user = blob_uploader.get_user(user_meta.user_email)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found, authentication issue.")
    if not user.authenticated_courses.__contains__((semester, course_id)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Authenticated but access is not allowed.")

    # Check if assignment exists *before* trying to delete
    if not blob_uploader.assignment_exists(semester, course_id, assignment_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found.")

    # Delete assignment (includes metadata and all related sub-folders like questions/rubrics)
    try:
        blob_uploader.delete_assignment(semester, course_id, assignment_id)
    except Exception as e:
        logging.error(f"Failed during assignment deletion: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete assignment.")

    # Return standard success message on successful deletion
    return {"detail":  "Assignment deleted successfully"}


# --- Operations on Collections of Assignments ---

@router.get(
    "/assignments",
    response_model=List[Assignment],
    summary="List Assignments",
    description="Retrieves all assignments associated with a course.",
    responses={
        400: {"detail": "Invalid parameters."}, # Added 400
        404: {"detail": "Course not found."},
        401: {"detail": "Requester is not authenticated."},
        403: {"detail": "Authenticated but access is not allowed."}
    }
)
async def list_assignments(
        semester: str = Query(..., description="Semester of the course."),
        course_id: str = Query(..., description="Identifier of the course."),
        include_questions: bool = Query(False, description="Whether to include questions in the response."),
        user_meta: UserToken = Depends(user_from_auth),
):
    # validate params
    try:
        semester = Course.validate_semester(semester)
        course_id = Course.normalize_lowercase(course_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid parameter format: {e}")

    blob_uploader = AzureBlobService.get_instance()
    # Check if the course exists
    if not blob_uploader.course_exists(semester, course_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found.")

    # Check if user has perms on course
    user = blob_uploader.get_user(user_meta.user_email)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found, authentication issue.")
    if not user.authenticated_courses.__contains__((semester, course_id)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Authenticated but access is not allowed.")

    # Get all assignments for the course
    assignments = blob_uploader.list_assignments(semester, course_id)

    # For each assignment, get its questions if requested
    if include_questions:
        for assignment in assignments:
            # Fetch questions for each assignment individually
            assignment.questions = blob_uploader.list_questions(semester, course_id, assignment.assignment_id)
    else:
        # Ensure questions list exists but is empty if not included
        for assignment in assignments:
            assignment.questions = []

    return assignments