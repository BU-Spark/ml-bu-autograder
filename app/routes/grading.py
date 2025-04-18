import uuid
from typing import List, Optional

import requests
from fastapi import APIRouter, HTTPException, status, Query, Depends
from pydantic import FilePath

from app.models import Course, GradedStudentResponseReference
from app.models.grade import Grade
from app.utils import JWTService, UserToken, llm_service, get_str_var
from app.utils.azure_blob_service import AzureBlobService
from app.utils.llm_service import LLMService, PromptBuilder, PromptRole

router = APIRouter()
user_from_auth = JWTService.get_instance().from_authorization_header
llm_service = llm_service.LLMService.get_instance()


def process_grading(json_str: str):
    """
    Processes student grading for a specific student response. This function is called by
    bg_material_processor.py. See its logic for more details
    """

    #  Step 0: Convert the json string into a student response object and download raw binary content of response
    student_response = GradedStudentResponseReference.model_validate_json(json_str)
    binary_content = requests.get(student_response.data.uri).content
    #  Step 1: Convert the student's response (which might be a pdf, txt, etc)
    #          into a Document object that we can work with.
    covert_to_doc = student_response.data.data_type.get_to_doc_func()
    student_response_documents = covert_to_doc(
        f"student_response.{student_response.data.data_type.extension}",
        binary_content,
        False
    )
    #  Step 2: Grab the rubric for the assignment and the question instructions
    blob_service = AzureBlobService.get_instance()
    rubric = blob_service.get_rubric(
        student_response.semester, student_response.course_id,
        student_response.assignment_id, False
    )
    rubric.sub_rubrics = [blob_service.get_sub_rubric(
        student_response.semester, student_response.course_id,
        student_response.assignment_id, student_response.question_index
    )]
    assignment = blob_service.get_assignment_metadata(
        semester_key=student_response.semester,
        course_id=student_response.course_id,
        assignment_id=student_response.assignment_id,
    )
    assignment_question = assignment.questions[student_response.question_index]
    #  Step 3: Query the vector database with the student's response grabbing all topn
    #          relevant documents.
    # TODO: josh you do this
    relevant_document_paths: List[str] = ...
    #  Step 4: Go grab those documents (texts and images) from Azure blob storage. It might
    #          also be possible to simply get azure to generate a URL for these documents
    #          and then send that to the LLM.
    course_material_documents = blob_service.get_chunks_from_blob_path(relevant_document_paths)
    #  Step 5: Once we have the RAG-ed documents associated with the prompt, use the
    #          assignment instructions, rubric, RAG-ed course material chunks, and student
    #          response to generate a prompt for auto-grading.
    prompt = (PromptBuilder.builder()
              .add_message(PromptRole.SYSTEM, "You are a grader responsible for grading a student's response.")
              .add_message(PromptRole.USER, "Here is course material that might be relevant to this assignment."
                                            "In your grading responses, when information is relevant, please cite these"
                                            "sources including with any other relevant reference information."))

    for file_name, document in course_material_documents:
        assert document.data_type.is_fundamental()
        doc_ref_str = f"Document name: {file_name}"
        if 'page_num' in document.metadata:
            doc_ref_str += f" (page {document.metadata['page_num']})"
        prompt.add_message(PromptRole.USER, doc_ref_str)
        if document.data_type.is_image():
            prompt.add_image_bytes(PromptRole.USER, document.content, document.data_type.mime_type)
        elif document.data_type.is_text():
            prompt.add_message(PromptRole.USER, document.get_as_string())

    (prompt.add_message(PromptRole.USER, "The instructions for this assignment are as follows:")
              .add_json_input(PromptRole.USER, assignment_question, excluded_fields={"questions"})
              .add_json_input(PromptRole.USER, assignment_question)
              .add_message(PromptRole.USER, "Grading for this assignment should be"
                                            " exclusively based on the following rubric:")
              .add_json_input(PromptRole.USER, rubric))

    prompt.add_message(PromptRole.USER, "Here is the student's response:")
    for chunk_id, resp_chunk in student_response_documents.contents.items():
        if resp_chunk.data_type.is_image():
            prompt.add_image_bytes(PromptRole.USER, resp_chunk.content, resp_chunk.data_type.mime_type)
        elif resp_chunk.data_type.is_text():
            prompt.add_message(PromptRole.USER, resp_chunk.get_as_string())

    #  Step 6: Grab the auto-graded response, upload it to Azure, and move on to the next assignment
    #          in the queue (if any).
    llm = LLMService.get_instance()
    student_grade = llm.generate_structured_response(
        prompt.build(),
        Grade
    )
    blob_service.upload_student_grade(
        semester_key=student_response.semester,
        course_id=student_response.course_id,
        assignment_id=student_response.assignment_id,
        question_index=student_response.question_index,
        student_id=student_response.student_id,
        grade=student_grade
    )


@router.post(
    "/grade/specific",
    summary="Grade Specific Responses",
    description="Grades or regrades a specific student's responses for an assignment.",
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
    rubric = blob_uploader.get_rubric(semester, course_id, assignment_id)
    if rubric is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Grading rubric does not exist.")

    # Get all responses for the specified students
    grades = []
    for student_id in student_ids:
        # Grade all questions
        responses = blob_uploader.list_student_responses(
            semester, course_id, assignment_id, student_id, None, False
        )

        for response in responses:
            # A background process will pick this up and process it trust.
            # See app/utils/bg_material_processor.py.
            random_uuid = uuid.uuid4()
            save_path = FilePath(
                f"{get_str_var('AZURE_BLOB_CACHE_DIR')}/{random_uuid}.json")
            with open(save_path, 'w') as f:
                f.write(response.model_dump_json(indent=4))

    if not grades:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No matching responses found.")

    return grades


@router.post(
    "/grade/ungraded",
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
        # A background process will pick this up and process it trust.
        # See app/utils/bg_material_processor.py.
        random_uuid = uuid.uuid4()
        save_path = FilePath(
            f"{get_str_var('AZURE_BLOB_CACHE_DIR')}/{random_uuid}.student_response.json")
        with open(save_path, 'w') as f:
            f.write(response.model_dump_json(indent=4))

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
        # A background process will pick this up and process it trust.
        # See app/utils/bg_material_processor.py.
        random_uuid = uuid.uuid4()
        save_path = FilePath(
            f"{get_str_var('AZURE_BLOB_CACHE_DIR')}/{random_uuid}.json")
        with open(save_path, 'w') as f:
            f.write(response.model_dump_json(indent=4))

    return grades
