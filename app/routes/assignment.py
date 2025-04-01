from typing import List

from fastapi import APIRouter, HTTPException, status, Query, Body
from pydantic import BaseModel, Field

from app.models.assignment import Assignment, Question, FloatingQuestion
from app.utils import JWTService
from app.utils.azure_blob_service import AzureBlobService


class EditQuestionRequest(BaseModel):
    semester: str = Field(..., description="Semester of the course.")
    course_id: str = Field(..., description="Identifier of the course.")
    assignment_id: str = Field(..., description="Identifier of the assignment.")
    question: Question = Field(..., description="The updated question data.")


class AddQuestionRequest(BaseModel):
    semester: str = Field(..., description="Semester of the course.")
    course_id: str = Field(..., description="Identifier of the course.")
    assignment_id: str = Field(..., description="Identifier of the assignment to update.")
    question: FloatingQuestion = Field(..., description="The data of the new question. (Notice: You cannot specify "
                                                        "the index for this question. If you wish to re-order this "
                                                        "question, you must make a separate modify order request.)")


class ModifyOrderRequest(BaseModel):
    semester: str = Field(..., description="Semester of the course.")
    course_id: str = Field(..., description="Identifier of the course.")
    assignment_id: str = Field(..., description="Identifier of the assignment.")
    list_of_question_indexes: List[int] = Field(..., description="New order for question indexes.")


router = APIRouter()
user_from_authorization_header = None


@router.on_event("startup")
async def set_user_from_auth_header():
    global user_from_authorization_header
    user_from_authorization_header = JWTService.get_instance().from_authorization_header


# Dummy storage for assignments
dummy_assignments = [
    Assignment(
        assignment_id="assign1",
        course_id="cs_132",
        semester="summer_2025",
        assignment_title="Assignment 1",
        assignment_guidelines="Follow the instructions carefully.",
        questions=[Question(question_index=0, question_text="What is 2+2?")]
    )
]


@router.post(
    "/assignment",
    response_model=Assignment,
    summary="Create Assignment",
    description="Creates a new assignment with questions and guidelines.",
    responses={
        400: {"description": "Missing or invalid parameters."},
        404: {"description": "Course does not exist."},
        401: {"description": "Requester is not authenticated."},
        403: {"description": "Authenticated but access is not allowed."}
    }
)
async def create_assignment(
        assignment: Assignment = Body(..., description="The assignment which to create."),
):
    blob_uploader = AzureBlobService.get_instance()
    # Check if the course exists
    course_exists = blob_uploader.course_exists(assignment.semester, assignment.course_id)
    if not course_exists:
        raise HTTPException(status_code=404, detail="Course does not exist.")
    # Check if user has perms on course
    # TODO
    # Check if this assignment id already exists
    if not blob_uploader.assignment_exists(assignment.semester, assignment.course_id, assignment.assignment_id):
        raise HTTPException(status_code=409, detail="Assignment already exists.")
    # If the user did not specify an assignment title, figure one out now
    if assignment.assignment_title is None:
        current_assignments = blob_uploader.list_assignments(assignment.semester, assignment.course_id)
        new_title = "Assignment "
        assignment_number = None
        for current_assignment in current_assignments:
            if current_assignment.assignment_title.startswith(new_title):
                try:
                    current_assignment_number = int(current_assignment.assignment_title.split(" ")[-1])
                    assignment_number = current_assignment_number if assignment_number is None \
                        else max(assignment_number, current_assignment_number)
                except ValueError:
                    ...
        assignment_number = 1 if assignment_number is None else assignment_number + 1
        assignment.assignment_title = new_title + str(assignment_number)
    # upload assignment metadata
    blob_uploader.upload_assignment_metadata(assignment)
    # upload assignment questions
    for question in assignment.questions:
        blob_uploader.upload_question_metadata(
            assignment.semester, assignment.course_id, assignment.assignment_id, question
        )
    return assignment


@router.patch(
    "/assignment/add_question",
    summary="Add Question",
    response_model=Question,
    description="Adds a new question to an assignment.",
    responses={
        400: {"description": "Missing or invalid parameters."},
        404: {"description": "Assignment not found."},
        401: {"description": "Requester is not authenticated."},
        403: {"description": "Authenticated but access is not allowed."}
    }
)
async def add_question(
        add_question_request: AddQuestionRequest = Body(...),
):
    blob_uploader = AzureBlobService.get_instance()
    # Check if the course exists
    course_exists = blob_uploader.course_exists(add_question_request.semester, add_question_request.course_id)
    if not course_exists:
        raise HTTPException(status_code=404, detail="Course does not exist.")
    # Check if user has perms on course
    # TODO
    # Check if assignment exists
    if not blob_uploader.assignment_exists(add_question_request.semester, add_question_request.course_id):
        raise HTTPException(status_code=404, detail="Assignment does not exist.")
    # Figure out question index
    question_index = blob_uploader.count_questions(add_question_request.semester, add_question_request.course_id,
                                                   add_question_request.assignment_id) + 1
    question = Question(
        question_index=question_index,
        question_text=add_question_request.question.question_text,
        question_graphics_figures=add_question_request.question.question_graphics_figures
    )
    # Upload question
    blob_uploader.upload_question_metadata(
        add_question_request.semester, add_question_request.course_id, add_question_request.assignment_id, question
    )
    return question


@router.patch(
    "/assignment/remove_question",
    summary="Remove Question",
    description="Removes a question from an assignment.",
    responses={
        400: {"description": "Missing or invalid parameters."},
        404: {"description": "Assignment or question not found."},
        401: {"description": "Requester is not authenticated."},
        403: {"description": "Authenticated but access is not allowed."}
    }
)
async def remove_question(
        semester: str = Query(..., description="Semester of the course."),
        course_id: str = Query(..., description="Identifier of the course."),
        assignment_id: str = Query(..., description="Identifier of the assignment."),
        question_index: int = Query(..., description="Index of the question to remove."),
):
    blob_uploader = AzureBlobService.get_instance()
    for assignment in dummy_assignments:
        if assignment.assignment_id == assignment_id:
            try:
                assignment.questions.pop(question_index)
                return {"message": "Question removed successfully."}
            except IndexError:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found.")
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found.")


@router.patch(
    "/assignment/edit_question",
    summary="Edit Question",
    description="Edits an existing question in an assignment.",
    responses={
        400: {"description": "Missing or invalid parameters."},
        404: {"description": "Assignment or question not found."},
        401: {"description": "Requester is not authenticated."},
        403: {"description": "Authenticated but access is not allowed."}
    }
)
async def edit_question(
        question: EditQuestionRequest = Body(...),
):
    blob_uploader = AzureBlobService.get_instance()
    for assignment in dummy_assignments:
        if assignment.assignment_id == question.assignment_id:
            try:
                # do something
                return {"message": "Question updated successfully."}
            except IndexError:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found.")
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found.")


@router.patch(
    "/assignment/modify_order",
    summary="Modify Question Order",
    description="Modifies the order of questions in an assignment.",
    responses={
        400: {"description": "Missing or invalid parameters."},
        404: {"description": "Assignment not found."},
        401: {"description": "Requester is not authenticated."},
        403: {"description": "Authenticated but access is not allowed."}
    }
)
async def modify_order(
        question: ModifyOrderRequest = Body(...),
):
    blob_uploader = AzureBlobService.get_instance()
    for assignment in dummy_assignments:
        if assignment.assignment_id == question.assignment_id:
            if sorted(question.list_of_question_indexes) != list(range(len(assignment.questions))):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                    detail="Invalid question indexes provided.")
            assignment.questions = [assignment.questions[i] for i in question.list_of_question_indexes]
            return assignment
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found.")


@router.get(
    "/assignment",
    response_model=Assignment,
    summary="Get Assignment",
    description="Retrieves a specific assignment by course and assignment ID.",
    responses={
        404: {"description": "Assignment not found."},
        401: {"description": "Requester is not authenticated."},
        403: {"description": "Authenticated but access is not allowed."}
    }
)
async def get_assignment(
        semester: str = Query(..., description="Semester of the course."),
        course_id: str = Query(..., description="Identifier of the course."),
        assignment_id: str = Query(..., description="Identifier of the assignment."),
):
    blob_uploader = AzureBlobService.get_instance()
    # TODO: error handling
    assignment = blob_uploader.get_assignment_metadata(semester, course_id, assignment_id)
    assignment.questions = blob_uploader.list_questions(semester, course_id, assignment_id)
    return assignment


@router.get(
    "/assignments",
    response_model=List[Assignment],
    summary="List Assignments",
    description="Retrieves all assignments associated with a course.",
    responses={
        401: {"description": "Requester is not authenticated."},
        403: {"description": "Authenticated but access is not allowed."}
    }
)
async def list_assignments(
        semester: str = Query(..., description="Semester of the course."),
        course_id: str = Query(..., description="Identifier of the course."),
):
    blob_uploader = AzureBlobService.get_instance()
    assignments = [a for a in dummy_assignments if a.course_id == course_id]
    if assignments:
        return assignments
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No assignments found.")


@router.delete(
    "/assignment",
    summary="Delete Assignment",
    description="Deletes a specified assignment.",
    responses={
        404: {"description": "Assignment not found."},
        401: {"description": "Requester is not authenticated."},
        403: {"description": "Authenticated but access is not allowed."}
    }
)
async def delete_assignment(
        semester: str = Query(..., description="Semester of the course."),
        course_id: str = Query(..., description="Identifier of the course."),
        assignment_id: str = Query(..., description="Identifier of the assignment to delete.")
):
    blob_uploader = AzureBlobService.get_instance()
    for assignment in dummy_assignments:
        if assignment.assignment_id == assignment_id:
            dummy_assignments.remove(assignment)
            return {"message": "Assignment deleted successfully."}
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found.")
