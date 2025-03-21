from typing import List

from fastapi import APIRouter, HTTPException, status, Query, Body
from pydantic import BaseModel, Field

from app.models.assignment import Assignment, Question


class OptionalQuestionIndex(Question):
    question_index: int = Field(..., description="Index of the question. If not specified, it is set to the next "
                                                 "available question index.")


class EditQuestionRequest(BaseModel):
    semester: str = Field(..., description="Semester of the course.")
    course_id: str = Field(..., description="Identifier of the course.")
    assignment_id: str = Field(..., description="Identifier of the assignment.")
    question: Question = Field(..., description="The updated question data.")


class AddQuestionRequest(BaseModel):
    semester: str = Field(..., description="Semester of the course.")
    course_id: str = Field(..., description="Identifier of the course.")
    assignment_id: str = Field(..., description="Identifier of the assignment to update.")
    question: OptionalQuestionIndex = Field(..., description="The data of the new question.")


class ModifyOrderRequest(BaseModel):
    semester: str = Field(..., description="Semester of the course.")
    course_id: str = Field(..., description="Identifier of the course.")
    assignment_id: str = Field(..., description="Identifier of the assignment.")
    list_of_question_indexes: List[int] = Field(..., description="New order for question indexes.")


router = APIRouter()

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
        404: {"description": "Associated course not found."},
        401: {"description": "Requester is not authenticated."},
        403: {"description": "Authenticated but access is not allowed."}
    }
)
async def create_assignment(assignment: Assignment = Body(..., description="The assignment which to create.")):
    dummy_assignments.append(assignment)
    return assignment


@router.patch(
    "/assignment/add_question",
    summary="Add Question",
    description="Adds a new question to an assignment.",
    responses={
        400: {"description": "Missing or invalid parameters."},
        404: {"description": "Assignment not found."},
        401: {"description": "Requester is not authenticated."},
        403: {"description": "Authenticated but access is not allowed."}
    }
)
async def add_question(
        question: AddQuestionRequest = Body(...)
):
    for assignment in dummy_assignments:
        if assignment.assignment_id == question.assignment_id:
            new_question = question.question
            assignment.questions.append(new_question)
            return {"new_question_index": len(assignment.questions) - 1}
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found.")


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
        assignment_id: str = Query(..., description="Identifier of the assignment."),
        question_index: int = Query(..., description="Index of the question to remove.")
):
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
        question: EditQuestionRequest = Body(...)
):
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
        question: ModifyOrderRequest = Body(...)
):
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
        course_id: str = Query(..., description="Identifier of the course."),
        semester: str = Query(..., description="Semester of the course."),
        assignment_id: str = Query(..., description="Identifier of the assignment.")
):
    for assignment in dummy_assignments:
        if assignment.assignment_id == assignment_id and assignment.course_id == course_id:
            return assignment
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found.")


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
        course_id: str = Query(..., description="Identifier of the course."),
        semester: str = Query(..., description="Semester of the course.")
):
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
        assignment_id: str = Query(..., description="Identifier of the assignment to delete.")
):
    for assignment in dummy_assignments:
        if assignment.assignment_id == assignment_id:
            dummy_assignments.remove(assignment)
            return {"message": "Assignment deleted successfully."}
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found.")
