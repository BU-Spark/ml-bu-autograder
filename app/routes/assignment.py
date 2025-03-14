from fastapi import APIRouter, HTTPException, status
from typing import List
from app.models.assignment import Assignment, Question

router = APIRouter()

# Dummy storage for assignments
dummy_assignments = [
    Assignment(
        assignment_id="assign1",
        course_id="cs_132",
        assignment_title="Assignment 1",
        assignment_guidelines="Follow the instructions carefully.",
        ordered_list=[Question(question_text="What is 2+2?")]
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
async def create_assignment(assignment: Assignment, semester: str):
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
async def add_question(assignment_id: str, question_text: str, question_graphics_figures: str = None):
    for assignment in dummy_assignments:
        if assignment.assignment_id == assignment_id:
            new_question = Question(question_text=question_text, question_graphics_figures=question_graphics_figures)
            assignment.ordered_list.append(new_question)
            return {"new_question_index": len(assignment.ordered_list) - 1}
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
async def remove_question(assignment_id: str, question_index: int):
    for assignment in dummy_assignments:
        if assignment.assignment_id == assignment_id:
            try:
                assignment.ordered_list.pop(question_index)
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
async def edit_question(assignment_id: str, question_index: int, new_question_text: str, new_question_graphics_figures: str = None):
    for assignment in dummy_assignments:
        if assignment.assignment_id == assignment_id:
            try:
                assignment.ordered_list[question_index].question_text = new_question_text
                assignment.ordered_list[question_index].question_graphics_figures = new_question_graphics_figures
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
async def modify_order(assignment_id: str, list_of_question_indexes: List[int]):
    for assignment in dummy_assignments:
        if assignment.assignment_id == assignment_id:
            if sorted(list_of_question_indexes) != list(range(len(assignment.ordered_list))):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid question indexes provided.")
            assignment.ordered_list = [assignment.ordered_list[i] for i in list_of_question_indexes]
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
async def get_assignment(course_id: str, assignment_id: str):
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
async def list_assignments(course_id: str):
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
async def delete_assignment(assignment_id: str):
    for assignment in dummy_assignments:
        if assignment.assignment_id == assignment_id:
            dummy_assignments.remove(assignment)
            return {"message": "Assignment deleted successfully."}
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found.")
