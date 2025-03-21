from typing import List, Optional

from fastapi import APIRouter, Query

from app.models.grade import Grade

router = APIRouter()

# Dummy storage for grades
dummy_grades: List[Grade] = []


@router.post(
    "/grade/specific",
    response_model=List[Grade],
    summary="Grade Specific Responses",
    description="Grades or regrades a specific student responses for an assignment.",
    responses={
        400: {"description": "Missing or invalid parameters."},
        502: {"description": "External LLM API call failure."},
        401: {"description": "Requester is not authenticated."},
        403: {"description": "Authenticated but access is not allowed."}
    }
)
async def grade_specific(
        student_identifiers: List[str] = Query(..., description="List of student identifiers to grade."),
        assignment_id: str = Query(..., description="Identifier of the assignment."),
        question_index: Optional[int] = Query(None,
                                    description="Optional index of the question. Grades all questions if omitted.")
):
    grades = []
    for student in student_identifiers:
        grade_obj = Grade(student_identifier=student, assignment_id=assignment_id, question_index=question_index or 0,
                          grade=90.0, explanation="Dummy grade.")
        dummy_grades.append(grade_obj)
        grades.append(grade_obj)
    return grades


@router.post(
    "/grade/ungraded",
    response_model=List[Grade],
    summary="Grade Ungraded Responses",
    description="Grades all ungraded responses for a specific assignment (optionally for a specific question).",
    responses={
        400: {"description": "Missing or invalid parameters."},
        502: {"description": "External LLM API call failure."},
        401: {"description": "Requester is not authenticated."},
        403: {"description": "Authenticated but access is not allowed."}
    }
)
async def grade_ungraded(
        assignment_id: str = Query(..., description="Identifier of the assignment."),
        question_index: Optional[int] = Query(None,
                                    description="Optional index of the question to grade. Grades all ungraded questions if omitted.")
):
    grade_obj = Grade(student_identifier="student123", assignment_id=assignment_id, question_index=question_index or 0,
                      grade=85.0, explanation="Dummy grade for ungraded response.")
    dummy_grades.append(grade_obj)
    return [grade_obj]


@router.post(
    "/grade/all",
    response_model=List[Grade],
    summary="Grade/Regrade All Responses",
    description="Grades or regrades all student responses for a specific assignment (optionally for a specific question).",
    responses={
        400: {"description": "Missing or invalid parameters."},
        502: {"description": "External LLM API call failure."},
        401: {"description": "Requester is not authenticated."},
        403: {"description": "Authenticated but access is not allowed."}
    }
)
async def grade_all(
        assignment_id: str = Query(..., description="Identifier of the assignment."),
        question_index: int = Query(None,
                                    description="Optional index of the question to grade or regrade. Grades all questions if omitted.")
):
    grade_obj = Grade(student_identifier="student123", assignment_id=assignment_id, question_index=question_index or 0,
                      grade=88.0, explanation="Dummy grade for all responses.")
    dummy_grades.append(grade_obj)
    return [grade_obj]
