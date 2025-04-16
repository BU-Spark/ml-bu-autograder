import re
from typing import List

from fastapi import APIRouter, HTTPException, Query, Body, Depends
from pydantic import BaseModel, Field, field_validator

from app.models import Course
from app.models.assignment import Assignment, Question
from app.utils import JWTService, UserToken
from app.utils.azure_blob_service import AzureBlobService


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
        if re.fullmatch("[a-zA-Z]{1,12}[0-9]{4}", value) is not None:
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
        if re.fullmatch("[a-zA-Z]{1,12}[0-9]{4}", value) is not None:
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
        if re.fullmatch("[a-zA-Z]{1,12}[0-9]{4}", value) is not None:
            raise ValueError("Semester is in an invalid format. "
                             "Correct format looks like: seasonYYYY. (e.g. spring2025)")
        return value.strip().lower()

router = APIRouter()
user_from_auth = JWTService.get_instance().from_authorization_header


@router.post(
    "/assignment",
    response_model=Assignment,
    summary="Create Assignment",
    description="Creates a new assignment with questions and guidelines.",
    responses={
        400: {"detail": "Missing or invalid parameters."},
        404: {"detail": "Course does not exist."},
        401: {"detail": "Requester is not authenticated."},
        403: {"detail": "Authenticated but access is not allowed."}
    }
)
async def create_assignment(
    assignment: Assignment = Body(..., description="The assignment to create."),
    user_meta: UserToken = Depends(user_from_auth),
):
    blob_uploader = AzureBlobService.get_instance()
    
    # Check if the course exists
    if not blob_uploader.course_exists(assignment.semester, assignment.course_id):
        raise HTTPException(status_code=404, detail="Course does not exist.")
    
    # Check user permissions
    user = blob_uploader.get_user(user_meta.user_email)
    if (assignment.semester, assignment.course_id) not in user.authenticated_courses:
        raise HTTPException(status_code=403, detail="Authenticated but access is not allowed.")
    
    # Determine the next assignment_id.
    # List all existing assignments for the course. Ensure that assignment_id can be parsed as integer.
    if assignment.assignment_id is None:
        # Either generate via a UUID or a sequence/querying the existing assignments.
        # Example using uuid:
        import uuid
        assignment.assignment_id = str(uuid.uuid4())
        print(f"Generated assignment_id: {assignment.assignment_id}")

    # Check that the new assignment_id isn't already used (should be redundant if our method is correct)
    if blob_uploader.assignment_exists(assignment.semester, assignment.course_id, assignment.assignment_id):
        raise HTTPException(status_code=400, detail="Assignment already exists.")
    
    # Upload assignment metadata and questions
    blob_uploader.upload_assignment_metadata(assignment)
    for i, question in enumerate(assignment.questions):
        blob_uploader.upload_question_metadata(
            assignment.semester, assignment.course_id, assignment.assignment_id, i, question
        )
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
    course_exists = blob_uploader.course_exists(add_question_request.semester, add_question_request.course_id)
    if not course_exists:
        raise HTTPException(status_code=404, detail="Course does not exist.")
    # Check if user has perms on course
    user = blob_uploader.get_user(user_meta.user_email)
    if not user.authenticated_courses.__contains__((add_question_request.semester, add_question_request.course_id)):
        raise HTTPException(status_code=403, detail="Authenticated but access is not allowed.")
    # Check if assignment exists
    if not blob_uploader.assignment_exists(add_question_request.semester, add_question_request.course_id, add_question_request.assignment_id):
        raise HTTPException(status_code=404, detail="Assignment does not exist.")
    # Figure out question index (we use zero indexing)
    question_index = blob_uploader.count_questions(add_question_request.semester, add_question_request.course_id,
                                                   add_question_request.assignment_id)
    question = Question(
        question_text=add_question_request.question.question_text,
        question_graphics_figures=add_question_request.question.question_graphics_figures
    )
    # Upload question
    blob_uploader.upload_question_metadata(
        add_question_request.semester, add_question_request.course_id, add_question_request.assignment_id, question_index, question
    )
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
        assignment_id: str = Query(..., description="Identifier of the assignment."),
        question_index: int = Query(..., description="Index of the question to remove."),
        user_meta: UserToken = Depends(user_from_auth),
):
    # validate params
    semester = Course.validate_semester(semester)
    course_id = Course.normalize_lowercase(course_id)

    blob_uploader = AzureBlobService.get_instance()
    # Check if the course exists
    course_exists = blob_uploader.course_exists(semester, course_id)
    if not course_exists:
        raise HTTPException(status_code=404, detail="Course does not exist.")
    # Check if user has perms on course
    user = blob_uploader.get_user(user_meta.user_email)
    if not user.authenticated_courses.__contains__((semester, course_id)):
        raise HTTPException(status_code=403, detail="Authenticated but access is not allowed.")
    # Check if assignment exists
    if not blob_uploader.assignment_exists(semester, course_id, assignment_id):
        raise HTTPException(status_code=404, detail="Assignment does not exist.")
    # Check if question exists
    questions = blob_uploader.list_questions(semester, course_id, assignment_id)
    question_exists = any(i == question_index for i, q in enumerate(questions))
    if not question_exists:
        raise HTTPException(status_code=404, detail="Question does not exist.")
    
    # Remove the question
    blob_uploader.delete_question_metadata(semester, course_id, assignment_id, question_index)
    
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
        edit_question: EditQuestionRequest = Body(...),
        user_meta: UserToken = Depends(user_from_auth),
):
    blob_uploader = AzureBlobService.get_instance()
    # Check if the course exists
    course_exists = blob_uploader.course_exists(edit_question.semester, edit_question.course_id)
    if not course_exists:
        raise HTTPException(status_code=404, detail="Course does not exist.")
    # Check if user has perms on course
    user = blob_uploader.get_user(user_meta.user_email)
    if not user.authenticated_courses.__contains__((edit_question.semester, edit_question.course_id)):
        raise HTTPException(status_code=403, detail="Authenticated but access is not allowed.")
    # Check if assignment exists
    if not blob_uploader.assignment_exists(edit_question.semester, edit_question.course_id, edit_question.assignment_id):
        raise HTTPException(status_code=404, detail="Assignment does not exist.")
    # Check if question exists
    questions = blob_uploader.list_questions(edit_question.semester, edit_question.course_id, edit_question.assignment_id)
    question_exists = any(i == edit_question.question_index for i, q in enumerate(questions))
    if not question_exists:
        raise HTTPException(status_code=404, detail="Question does not exist.")
    
    # Update the question
    blob_uploader.upload_question_metadata(
        edit_question.semester, edit_question.course_id, edit_question.assignment_id, edit_question.question_index, edit_question.question
    )
    
    return edit_question.question


@router.patch(
    "/assignment/modify_order",
    summary="Modify Question Order",
    description="Modifies the order of questions in an assignment.",
    responses={
        400: {"detail": "Missing or invalid parameters."},
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
    # Check if the course exists
    course_exists = blob_uploader.course_exists(reorder_request.semester, reorder_request.course_id)
    if not course_exists:
        raise HTTPException(status_code=404, detail="Course does not exist.")
    
    # Check if user has perms on course
    user = blob_uploader.get_user(user_meta.user_email)
    if not user.authenticated_courses.__contains__((reorder_request.semester, reorder_request.course_id)):
        raise HTTPException(status_code=403, detail="Authenticated but access is not allowed.")
    
    # Check if assignment exists
    if not blob_uploader.assignment_exists(reorder_request.semester, reorder_request.course_id, reorder_request.assignment_id):
        raise HTTPException(status_code=404, detail="Assignment does not exist.")

    # Assert the length of the list of question indices matches number of questions
    num_questions = blob_uploader.count_questions(reorder_request.semester, reorder_request.course_id, reorder_request.assignment_id)
    if num_questions != len(reorder_request.list_of_question_indexes):
        raise HTTPException(status_code=404, detail="Number of indexes must match number of questions.")

    # Assert the list contains all indices
    if sorted(reorder_request.list_of_question_indexes) != list(range(num_questions)):
        raise HTTPException(status_code=400, detail="Indexes must be a valid permutation of question indices.")
    
    # Reorder questions
    blob_uploader.reorder_questions(reorder_request.semester, reorder_request.course_id, reorder_request.assignment_id, reorder_request.list_of_question_indexes)
    
    return {"detail":  "Question order updated successfully"}


@router.get(
    "/assignment",
    response_model=Assignment,
    summary="Get Assignment",
    description="Retrieves a specific assignment by course and assignment ID.",
    responses={
        404: {"detail": "Assignment not found."},
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
    # validate params
    semester = Course.validate_semester(semester)
    course_id = Course.normalize_lowercase(course_id)

    blob_uploader = AzureBlobService.get_instance()
    # Check if the course exists
    course_exists = blob_uploader.course_exists(semester, course_id)
    if not course_exists:
        raise HTTPException(status_code=404, detail="Course does not exist.")
    
    # Check if user has perms on course
    user = blob_uploader.get_user(user_meta.user_email)
    if not user.authenticated_courses.__contains__((semester, course_id)):
        raise HTTPException(status_code=403, detail="Authenticated but access is not allowed.")
    
    # Check if assignment exists
    if not blob_uploader.assignment_exists(semester, course_id, assignment_id):
        raise HTTPException(status_code=404, detail="Assignment does not exist.")
    
    # Get assignment metadata and questions
    assignment = blob_uploader.get_assignment_metadata(semester, course_id, assignment_id)

    if include_questions:
        assignment.questions = blob_uploader.list_questions(semester, course_id, assignment_id)

    return assignment


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
    # validate params
    semester = Course.validate_semester(semester)
    course_id = Course.normalize_lowercase(course_id)

    blob_uploader = AzureBlobService.get_instance()
    # Check if the course exists
    course_exists = blob_uploader.course_exists(semester, course_id)
    if not course_exists:
        raise HTTPException(status_code=404, detail="Course does not exist.")
    
    # Check if user has perms on course
    user = blob_uploader.get_user(user_meta.user_email)
    if not user.authenticated_courses.__contains__((semester, course_id)):
        raise HTTPException(status_code=403, detail="Authenticated but access is not allowed.")
    
    # Get all assignments for the course
    assignments = blob_uploader.list_assignments(semester, course_id)
    
    # For each assignment, get its questions
    if include_questions:
        for assignment in assignments:
            assignment.questions = blob_uploader.list_questions(semester, course_id, assignment.assignment_id)
    else:
        for assignment in assignments:
            assignment.questions = None

    return assignments


@router.delete(
    "/assignment",
    summary="Delete Assignment",
    description="Deletes a specified assignment.",
    responses={
        404: {"detail": "Assignment not found."},
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
    # validate params
    semester = Course.validate_semester(semester)
    course_id = Course.normalize_lowercase(course_id)

    blob_uploader = AzureBlobService.get_instance()
    # Check if the course exists
    course_exists = blob_uploader.course_exists(semester, course_id)
    if not course_exists:
        raise HTTPException(status_code=404, detail="Course does not exist.")
    
    # Check if user has perms on course
    user = blob_uploader.get_user(user_meta.user_email)
    if not user.authenticated_courses.__contains__((semester, course_id)):
        raise HTTPException(status_code=403, detail="Authenticated but access is not allowed.")
    
    # Check if assignment exists
    if not blob_uploader.assignment_exists(semester, course_id, assignment_id):
        raise HTTPException(status_code=404, detail="Assignment does not exist.")

    # Delete assignment metadata
    blob_uploader.delete_assignment(semester, course_id, assignment_id)
    
    return {"detail":  "Assignment deleted successfully"}