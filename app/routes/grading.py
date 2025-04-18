from typing import List, Optional
from fastapi import APIRouter, HTTPException, status, Query, Depends

from app.models import Course, GradedStudentResponseReference
from app.models.grade import Grade
from app.utils import JWTService, UserToken, llm_service
from app.utils.azure_blob_service import AzureBlobService

router = APIRouter()
user_from_auth = JWTService.get_instance().from_authorization_header
llm_service = llm_service.LLMService.get_instance()


async def grading_worker():
    # TODO: this should process a queue of pending grading responses.
    #  Step 1: Convert the student's response (which might be a pdf, txt, etc)
    #          into a Document object that we can work with.
    #  Step 2: Grab the rubric for the assignment and the question instructions
    #  Step 3: Query the vector database with the student's response grabbing all topn
    #          relevant documents.
    #  Step 4: Go grab those documents (texts and images) from Azure blob storage. It might
    #          also be possible to simply get azure to generate a URL for these documents
    #          and then send that to the LLM.
    #  Step 5: Once we have the RAG-ed documents associated with the prompt, use the
    #          assignment instructions, rubric, RAG-ed course material chunks, and student
    #          response to generate a prompt for auto-grading.
    #  Step 6: Grab the auto-graded response, upload it to Azure, and move on to the next assignment
    #          in the queue (if any).
    ...

def do_grading(responses: list[GradedStudentResponseReference]):
       from typing import List

from app.models.student_response import GradedStudentResponseReference
from app.models.grade import Grade
from app.utils.llm_service import LLMService, PromptBuilder, PromptRole


def do_grading(responses: List[GradedStudentResponseReference]) -> Grade:
    """
    Grades a list of student responses by interacting with the LLM service.

    This function:
    1. Combines the content from all provided responses.
    2. Extracts common metadata (student_id, assignment_id, question_index)
       from the first response (assuming all belong to the same student/assignment).
    3. Builds a prompt using a system instruction and the student response.
    4. Calls the LLM service's structured response method to auto-grade.
    5. Ensures any missing metadata is filled in from the original response.

    Args:
        responses (List[GradedStudentResponseReference]): List of responses for a student.

    Returns:
        Grade: A Grade object as returned by the LLM service.
    """
    # 1. Validate input
    if not responses:
        raise ValueError("No student responses provided for grading.")

    # 2. Combine all textual content into one block
    combined_content = "\n".join(
        r.content.strip() 
        for r in responses 
        if hasattr(r, "content") and r.content
    )

    # 3. Pull metadata from the first response
    first_response = responses[0]
    student_id = first_response.student_id
    assignment_id = first_response.assignment_id
    question_index = first_response.question_index
    max_score = 10  # Default max; override or fetch from rubric if available

    # 4. Create the system instruction and user prompt
    system_instruction = (
        "You are an expert auto-grader. Evaluate the following student's response "
        "based on the assignment rubric and grading criteria. Return your evaluation "
        "as a JSON object with the following keys: student_id, assignment_id, question_index, "
        "score (an integer between 0 and max_score), max_score, and feedback."
    )
    user_prompt = (
        f"Student Response:\n{combined_content}\n\n"
        "Please provide a detailed grade along with feedback."
    )

    # 5. Build a structured prompt
    prompt = (
        PromptBuilder.builder()
        .add_message(PromptRole.SYSTEM, system_instruction)
        .add_message(PromptRole.USER, user_prompt)
        .build()
    )

    # 6. Retrieve the singleton LLMService instance
    llm = LLMService.get_instance()
    if llm is None:
        raise RuntimeError("LLMService instance is not initialized.")

    # 7. Generate the grade using the LLM's structured response
    grade: Grade = llm.generate_structured_response(prompt, Grade)

    # 8. Fill in any missing metadata from the original response
    if not grade.student_id:
        grade.student_id = student_id
    if not grade.assignment_id:
        grade.assignment_id = assignment_id
    if grade.question_index is None:
        grade.question_index = question_index
    if not grade.max_score:
        grade.max_score = max_score

    return grade



@router.post(
    "/grade/specific",
    response_model=List[Grade],
    summary="Grade Specific Responses",
    description="Grades or regrades a specific student responses for an assignment.",
    responses={
        400: {"detail": "Missing or invalid parameters."},
        404: {"detail": "Course, assignment, rubric, or student responses not found."},
        502: {"detail": "External LLM API call failure."},
        401: {"detail": "Requester is not authenticated."},
        403: {"detail": "Authenticated but access is not allowed."}
    }
)
async def grade_specific(
        semester: str = Query(..., description="Course semester."),
        course_id: str = Query(..., description="Unique identifier of the course."),
        assignment_id: str = Query(..., description="Identifier of the assignment."),
        student_ids: List[str] = Query(..., description="List of student identifiers to grade."),
        question_index: Optional[int] = Query(None, description="Optional index of the question. Grades all questions if omitted."),
        user_meta: UserToken = Depends(user_from_auth),
):
    blob_uploader = AzureBlobService.get_instance()

    # validate params
    semester = Course.validate_semester(semester)
    course_id = Course.normalize_lowercase(course_id)

    # Check if course exists
    if not blob_uploader.course_exists(semester, course_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course does not exist.")

    # Check if user has permissions on course
    user = blob_uploader.get_user(user_meta.user_email)
    if not user.authenticated_courses.__contains__((semester, course_id)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Authenticated but access is not allowed.")

    # Check if assignment exists
    if not blob_uploader.assignment_exists(semester, course_id, assignment_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment does not exist.")

    # Check if the rubric exists
    rubric = None
    if question_index is not None:
        rubric = blob_uploader.get_sub_rubric(semester, course_id, assignment_id, question_index)
    else:
        rubric = blob_uploader.get_rubric(semester, course_id, assignment_id)

    if rubric is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Grading rubric does not exist.")

    # Get all responses for the specified students
    grades = []
    for student_id in student_ids:
        if question_index is not None:
            # Grade specific question
            response = blob_uploader.list_student_responses(
                semester, course_id, assignment_id, student_id,
                question_index
            )
            if response:
                grade = do_grading(response)  # This is a placeholder for the actual grading logic
                grades.append(grade)
        else:
            # Grade all questions
            responses = blob_uploader.list_student_responses(
                semester, course_id, assignment_id
            )
            student_responses = [r for r in responses if r.student_id == student_id]
            for response in student_responses:
                grade = do_grading(response)  # This is a placeholder for the actual grading logic
                grades.append(grade)

    if not grades:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No matching responses found.")

    return grades


@router.post(
    "/grade/ungraded",
    response_model=List[Grade],
    summary="Grade Ungraded Responses",
    description="Grades all ungraded responses for a specific assignment (optionally for a specific question).",
    responses={
        400: {"detail": "Missing or invalid parameters."},
        404: {"detail": "Course or assignment not found."},
        502: {"detail": "External LLM API call failure."},
        401: {"detail": "Requester is not authenticated."},
        403: {"detail": "Authenticated but access is not allowed."}
    }
)
async def grade_ungraded(
        semester: str = Query(..., description="Course semester."),
        course_id: str = Query(..., description="Unique identifier of the course."),
        assignment_id: str = Query(..., description="Identifier of the assignment."),
        question_index: Optional[int] = Query(None, description="Optional index of the question to grade. Grades all ungraded questions if omitted."),
        user_meta: UserToken = Depends(user_from_auth),
):
    blob_uploader = AzureBlobService.get_instance()

    # validate params
    semester = Course.validate_semester(semester)
    course_id = Course.normalize_lowercase(course_id)

    # Check if course exists
    if not blob_uploader.course_exists(semester, course_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course does not exist.")

    # Check if user has permissions on course
    user = blob_uploader.get_user(user_meta.user_email)
    if not user.authenticated_courses.__contains__((semester, course_id)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Authenticated but access is not allowed.")

    # Check if assignment exists
    if not blob_uploader.assignment_exists(semester, course_id, assignment_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment does not exist.")

    # Check if the rubric exists
    rubric = None
    if question_index is not None:
        rubric = blob_uploader.get_sub_rubric(semester, course_id, assignment_id, question_index)
    else:
        rubric = blob_uploader.get_rubric(semester, course_id, assignment_id)

    if rubric is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Grading rubric does not exist.")

    # Get all responses
    responses = blob_uploader.list_student_responses(
        semester, course_id, assignment_id, None, question_index
    )

    # Filter out already graded responses
    ungraded_responses = []
    for response in responses:
        grade = blob_uploader.get_grading_details(
            semester, course_id, assignment_id,
            response.question_index, response.student_id
        )
        if not grade:
            ungraded_responses.append(response)

    if not ungraded_responses:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No ungraded responses found.")

    # Grade ungraded responses
    grades = []
    for response in ungraded_responses:
        grade = do_grading(response)  # This is a placeholder for the actual grading logic
        grades.append(grade)

    return grades


@router.post(
    "/grade/all",
    response_model=List[Grade],
    summary="Grade/Regrade All Responses",
    description="Grades or regrades all student responses for a specific assignment (optionally for a specific question).",
    responses={
        400: {"detail": "Missing or invalid parameters."},
        404: {"detail": "Course or assignment not found."},
        502: {"detail": "External LLM API call failure."},
        401: {"detail": "Requester is not authenticated."},
        403: {"detail": "Authenticated but access is not allowed."}
    }
)
async def grade_all(
        semester: str = Query(..., description="Course semester."),
        course_id: str = Query(..., description="Unique identifier of the course."),
        assignment_id: str = Query(..., description="Identifier of the assignment."),
        question_index: Optional[int] = Query(None, description="Optional index of the question to grade or regrade. Grades all questions if omitted."),
        user_meta: UserToken = Depends(user_from_auth),
):
    blob_uploader = AzureBlobService.get_instance()

    # validate params
    semester = Course.validate_semester(semester)
    course_id = Course.normalize_lowercase(course_id)

    # Check if course exists
    if not blob_uploader.course_exists(semester, course_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course does not exist.")

    # Check if user has permissions on course
    user = blob_uploader.get_user(user_meta.user_email)
    if not user.authenticated_courses.__contains__((semester, course_id)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Authenticated but access is not allowed.")

    # Check if assignment exists
    if not blob_uploader.assignment_exists(semester, course_id, assignment_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment does not exist.")

    # Check if the rubric exists
    rubric = None
    if question_index is not None:
        rubric = blob_uploader.get_sub_rubric(semester, course_id, assignment_id, question_index)
    else:
        rubric = blob_uploader.get_rubric(semester, course_id, assignment_id)

    if rubric is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Grading rubric does not exist.")

    # Get all responses
    responses = blob_uploader.list_student_responses(
        semester, course_id, assignment_id, None, question_index
    )

    if not responses:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No responses found.")

    # Grade all responses
    grades = []
    for response in responses:
        grade = do_grading(response)  # This is a placeholder for the actual grading logic
        grades.append(grade)

    return grades
