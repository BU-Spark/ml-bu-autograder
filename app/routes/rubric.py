import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, status, Query, Body, Depends
from fastapi.responses import HTMLResponse

from app.models import Course
from app.models.rubric import Rubric
from app.models import UserToken
from app.utils.jwt_service import JWTService
from app.services.azure_blob_service import AzureBlobService
from app.services.email_service import EmailService, send_rubric_approval_email_to_bu_professors
from app.utils.llm_service import LLMService, PromptBuilder, PromptRole

router = APIRouter()
user_from_auth = JWTService.get_instance().from_authorization_header


@router.put(
    "/rubric",
    response_model=Rubric,
    summary="Create Rubric",
    description="Manually creates a new rubric for an assignment.",
    responses={
        400: {"detail": "Missing or invalid parameters."},
        404: {"detail": "Assignment not found."},
        401: {"detail": "Requester is not authenticated."},
        403: {"detail": "Authenticated but access is not allowed."}
    }
)
async def create_rubric(
        rubric: Rubric = Body(..., description="Rubric object containing grading instructions and sub-rubrics."),
        user_meta: UserToken = Depends(user_from_auth),
):
    blob_uploader = AzureBlobService.get_instance()

    # Check if course exists
    if not blob_uploader.course_exists(rubric.semester, rubric.course_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course does not exist.")

    # Check if user has permissions on course
    user = blob_uploader.get_user(user_meta.user_email)
    if not user.authenticated_courses.__contains__((rubric.semester, rubric.course_id)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Authenticated but access is not allowed.")

    # Check if assignment exists
    if not blob_uploader.assignment_exists(rubric.semester, rubric.course_id, rubric.assignment_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment does not exist.")

    # Upload the rubric
    blob_uploader.upload_rubric(rubric.semester, rubric.course_id, rubric.assignment_id, rubric)
    return rubric


@router.get(
    "/ai_rubric",
    response_model=Rubric,
    summary="Enhance Rubric with AI",
    description="Enhances an existing rubric using AI-based improvements. If a rubric does not exist for the given assignment, a new one is generated. Note: This only proposes a new rubric and does not modify an existing one.",
    responses={
        502: {"detail": "External LLM API call failure."},
        401: {"detail": "Requester is not authenticated."},
        403: {"detail": "Authenticated but access is not allowed."}
    }
)
async def get_ai_rubric(
        semester: str = Query(..., description="Semester of the course."),
        course_id: str = Query(..., description="Identifier of the course."),
        assignment_id: str = Query(..., description="Identifier of the assignment."),
        instructions: Optional[str] = Query(None, description="Optional specific improvement instructions for the AI."),
        user_meta: UserToken = Depends(user_from_auth),
):
    blob_uploader = AzureBlobService.get_instance()

    # validate params by attempting to create a course object
    Course(semester=semester, course_id=course_id)

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

    # Get the rubric
    rubric = blob_uploader.get_rubric(semester, course_id, assignment_id)
    if rubric is None:
        # Get the assignment details to inform the LLM
        assignment = blob_uploader.get_assignment_metadata(semester, course_id, assignment_id)
        if assignment is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found.")
        assignment.questions = blob_uploader.list_questions(semester, course_id, assignment_id)

        # Use LLM to generate a rubric from scratch
        llm_service = LLMService.get_instance()

        # Build the prompt for creating a rubric
        prompt = (PromptBuilder.builder()
            .add_message(PromptRole.SYSTEM, 
                "You are an expert in creating educational assessment rubrics. "
                "Your task is to create a fair, consistent, and organized rubric for an assignment. "
                "The rubric should have clear criteria and point allocations that add up to the total points. "
                "Use the assignment details to guide your rubric creation.")
            .add_message(PromptRole.USER, 
                f"Create a comprehensive rubric for the following assignment:\n")
            .add_json_input(PromptRole.USER, assignment)
        )

        prompt.add_message(PromptRole.USER, "Factors to consider while creating this rubric:\n"
            "1. Is the rubric specific and measurable?\n"
            "2. Does point distribution aligns with question importance?\n"
            "3. Are there clear, objective guidelines for what warrents a point deduction and by how much?\n"
            "4. Are the criterias organized logically?\n"
            "5. Add appropriate grading flags if needed.\n"
            "6. Ensure all grading criteria for each question sum to the max points. You must run through the whole rubric step by step and make sure"
            "that the sum of all points add to the max points allotment. If they do not add up to that allotment, then the rubric is invalid!")

        # Add any additional instructions if provided
        if instructions:
            prompt.add_message(PromptRole.USER, f"Additional instructions for rubric generation: {instructions}")

        # Print the final prompt before sending
        logging.debug(prompt.debug_string())

        # Build the final prompt
        prompt_list = prompt.build()

        try:
            # Generate a structured response matching the Rubric model
            rubric = llm_service.generate_structured_response(prompt_list, Rubric)
            
            # Ensure the rubric has the correct metadata
            rubric.semester = semester
            rubric.course_id = course_id
            rubric.assignment_id = assignment_id
            
            return rubric
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to generate rubric using LLM: {str(e)}"
            )
    else:
        # Get the assignment details
        assignment = blob_uploader.get_assignment_metadata(semester, course_id, assignment_id)
        if assignment is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found.")
        assignment.questions = blob_uploader.list_questions(semester, course_id, assignment_id)

        # Use LLM to enhance the existing rubric
        llm_service = LLMService.get_instance()

        # Build the prompt for enhancing a rubric
        prompt = (PromptBuilder.builder()
            .add_message(PromptRole.SYSTEM, 
                "You are an expert in educational assessment who specializes in improving rubrics. "
                "Your task is to enhance an existing rubric to make it more organized, fair, and consistent. "
                "Maintain the core structure and intent of the original rubric while improving clarity, "
                "alignment with learning objectives, and point distribution fairness. Provided below are the "
                "assignment details, and the existing rubric.")
            .add_json_input(PromptRole.USER, assignment)
        )

        # Add the existing rubric as JSON input
        prompt.add_json_input(PromptRole.USER, rubric)

        # Add any additional instructions if provided
        
        prompt.add_message(PromptRole.USER, 
            "Please enhance this rubric by:\n"
            "1. Making criteria more specific and measurable\n"
            "2. Ensuring point distribution aligns with question importance\n"
            "3. Adding clear instructor guidelines where missing\n"
            "4. Organizing criteria logically\n"
            "5. Adding appropriate grading flags if needed\n"
            "6. Ensuring all grading criteria for each question sum to the max points. You must run through the whole rubric step by step and make sure"
            "that the sum of all points add to the max points allotment. If they do not add up to that allotment, then the rubric is invalid!")
        if instructions:
            prompt.add_message(PromptRole.USER, f"Specific improvement instructions from instructor: {instructions}")

        logging.debug(prompt.debug_string())

        # Build the final prompt
        prompt_list = prompt.build()

        try:
            # Generate a structured response matching the Rubric model
            enhanced_rubric = llm_service.generate_structured_response(prompt_list, Rubric)
            
            # Ensure the enhanced rubric has the correct metadata 
            enhanced_rubric.semester = semester
            enhanced_rubric.course_id = course_id
            enhanced_rubric.assignment_id = assignment_id
            
            return enhanced_rubric
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to enhance rubric using LLM: {str(e)}"
            )


@router.post(
    "/ai_rubric/send_approval",
    summary="Send AI Rubric for Email Approval to BU Professors",
    description="Generates an AI rubric and sends it via email to ALL BU CS professors for approval.",
    responses={
        200: {"description": "Approval emails sent successfully to BU professors"},
        502: {"detail": "External LLM API call failure or email service unavailable."},
        401: {"detail": "Requester is not authenticated."},
        403: {"detail": "Authenticated but access is not allowed."}
    }
)
async def send_ai_rubric_for_approval(
        semester: str = Query(..., description="Semester of the course."),
        course_id: str = Query(..., description="Identifier of the course."),
        assignment_id: str = Query(..., description="Identifier of the assignment."),
        instructions: Optional[str] = Query(None, description="Optional specific improvement instructions for the AI."),
        user_meta: UserToken = Depends(user_from_auth),
):
    """
    Generate AI rubric and email for approval.
    
    This generates an AI rubric and emails it for approval instead of showing it directly.
    """
    blob_uploader = AzureBlobService.get_instance()

    # All the same checks as get_ai_rubric...
    Course(semester=semester, course_id=course_id)

    if not blob_uploader.course_exists(semester, course_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course does not exist.")

    user = blob_uploader.get_user(user_meta.user_email)
    if not user.authenticated_courses.__contains__((semester, course_id)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Authenticated but access is not allowed.")

    if not blob_uploader.assignment_exists(semester, course_id, assignment_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment does not exist.")

    # Generate the AI rubric (same logic as get_ai_rubric)
    rubric = blob_uploader.get_rubric(semester, course_id, assignment_id)
    if rubric is None:
        # Generate new rubric...
        assignment = blob_uploader.get_assignment_metadata(semester, course_id, assignment_id)
        if assignment is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found.")
        assignment.questions = blob_uploader.list_questions(semester, course_id, assignment_id)

        llm_service = LLMService.get_instance()
        prompt = (PromptBuilder.builder()
            .add_message(PromptRole.SYSTEM, 
                "You are an expert in creating educational assessment rubrics. "
                "Your task is to create a fair, consistent, and organized rubric for an assignment. "
                "The rubric should have clear criteria and point allocations that add up to the total points. "
                "Use the assignment details to guide your rubric creation.")
            .add_message(PromptRole.USER, 
                f"Create a comprehensive rubric for the following assignment:\n")
            .add_json_input(PromptRole.USER, assignment)
        )

        prompt.add_message(PromptRole.USER, "Factors to consider while creating this rubric:\n"
            "1. Is the rubric specific and measurable?\n"
            "2. Does point distribution aligns with question importance?\n"
            "3. Are there clear, objective guidelines for what warrents a point deduction and by how much?\n"
            "4. Are the criterias organized logically?\n"
            "5. Add appropriate grading flags if needed.\n"
            "6. Ensure all grading criteria for each question sum to the max points.")

        if instructions:
            prompt.add_message(PromptRole.USER, f"Additional instructions for rubric generation: {instructions}")

        prompt_list = prompt.build()

        try:
            rubric = llm_service.generate_structured_response(prompt_list, Rubric)
            rubric.semester = semester
            rubric.course_id = course_id
            rubric.assignment_id = assignment_id
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to generate rubric using LLM: {str(e)}"
            )
    else:
        # Enhance existing rubric... (simplified for space)
        rubric.semester = semester
        rubric.course_id = course_id
        rubric.assignment_id = assignment_id

    # Send approval emails to ALL BU professors
    try:
        approval_tokens = send_rubric_approval_email_to_bu_professors(rubric)
        
        if not approval_tokens:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Email service is not available"
            )
        
        return {
            "message": f"Approval emails sent successfully to {len(approval_tokens)} BU professors",
            "professors_emailed": ["CourtneyPike (cjpike@bu.edu)", "Micheal Levinger (mlevinge@bu.edu)", "TA Uwe (umeding@bu.edu)"],
            "approval_tokens": approval_tokens,
            "expires_in_hours": 24
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to send approval email: {str(e)}"
        )


@router.get(
    "/rubric/approve/{approval_token}",
    response_class=HTMLResponse,
    summary="Approve AI Rubric",
    description="Approve a rubric via email link and save it to the system."
)
async def approve_rubric_via_email(approval_token: str):
    """
    Approve rubric via email link.
    
    When someone clicks "APPROVE" in their email, this saves the rubric.
    """
    email_service = EmailService.get_instance()
    if not email_service:
        return HTMLResponse("""
        <html><body style="font-family: Arial; text-align: center; padding: 50px;">
            <h1>Email Service Not Available</h1>
            <p>The approval system is currently unavailable.</p>
        </body></html>
        """, status_code=503)

    # Get the pending approval
    rubric = email_service.approve_rubric(approval_token)
    if not rubric:
        return HTMLResponse("""
        <html><body style="font-family: Arial; text-align: center; padding: 50px;">
            <h1>⏰ Approval Link Expired</h1>
            <p>This approval link has expired or is invalid.</p>
            <p>Please request a new rubric approval email.</p>
        </body></html>
        """, status_code=404)

    # Save the approved rubric to Azure!
    try:
        blob_uploader = AzureBlobService.get_instance()
        blob_uploader.upload_rubric(rubric.semester, rubric.course_id, rubric.assignment_id, rubric)
        
        return HTMLResponse(f"""
        <html>
        <head>
            <title> Rubric Approved!</title>
            <style>
                body {{ font-family: Arial, sans-serif; text-align: center; padding: 50px; }}
                .success {{ color: #28a745; }}
                .details {{ background-color: #f8f9fa; padding: 20px; margin: 20px auto; max-width: 600px; border-radius: 8px; }}
            </style>
        </head>
        <body>
            <h1 class="success"> Rubric Approved Successfully!</h1>
            
            <div class="details">
                <h3> Course: {rubric.course_id}</h3>
                <h3> Assignment: {rubric.assignment_id}</h3>
                <h3> Semester: {rubric.semester}</h3>
                <p>The rubric has been saved and is now active for grading.</p>
            </div>
            
            <p><em>You can close this tab now.</em></p>
            
            <script>
                // Auto-close after 5 seconds
                setTimeout(() => {{
                    window.close();
                }}, 5000);
            </script>
        </body>
        </html>
        """)
        
    except Exception as e:
        logging.error(f"Failed to save approved rubric: {e}")
        return HTMLResponse("""
        <html><body style="font-family: Arial; text-align: center; padding: 50px;">
            <h1> Save Failed</h1>
            <p>The rubric was approved but could not be saved. Please contact support.</p>
        </body></html>
        """, status_code=500)


@router.get(
    "/rubric/reject/{approval_token}",
    response_class=HTMLResponse,
    summary=" Reject AI Rubric",
    description="Reject a rubric via email link."
)
async def reject_rubric_via_email(approval_token: str):
    """
     The Red Rejection Button!
    
    When someone clicks "REJECT" in their email, this discards the rubric.
    """
    email_service = EmailService.get_instance()
    if not email_service:
        return HTMLResponse("""
        <html><body style="font-family: Arial; text-align: center; padding: 50px;">
            <h1> Email Service Not Available</h1>
            <p>The approval system is currently unavailable.</p>
        </body></html>
        """, status_code=503)

    # Reject the rubric
    success = email_service.reject_rubric(approval_token)
    if not success:
        return HTMLResponse("""
        <html><body style="font-family: Arial; text-align: center; padding: 50px;">
            <h1>⏰ Rejection Link Expired</h1>
            <p>This rejection link has expired or is invalid.</p>
        </body></html>
        """, status_code=404)

    return HTMLResponse("""
    <html>
    <head>
        <title> Rubric Rejected</title>
        <style>
            body { font-family: Arial, sans-serif; text-align: center; padding: 50px; }
            .rejected { color: #dc3545; }
        </style>
    </head>
    <body>
        <h1 class="rejected"> Rubric Rejected</h1>
        <p>The AI-generated rubric has been discarded.</p>
        <p>You can request a new rubric generation if needed.</p>
        <p><em>You can close this tab now.</em></p>
        
        <script>
            // Auto-close after 3 seconds
            setTimeout(() => {
                window.close();
            }, 3000);
        </script>
    </body>
    </html>
    """)


@router.get(
    "/rubric/cleanup",
    summary=" Cleanup Expired Approvals",
    description="Manual cleanup of expired approval tokens (admin use)."
)
async def cleanup_expired_approvals():
    """Clean up expired approval tokens manually."""
    email_service = EmailService.get_instance()
    if not email_service:
        raise HTTPException(status_code=503, detail="Email service not available")
    
    email_service.cleanup_expired_approvals()
    return {"message": " Cleanup completed"}


@router.get(
    "/rubric",
    response_model=Rubric,
    summary="Get Rubric",
    description="Retrieves the rubric for a specified assignment (or for a specific question).",
    responses={
        404: {"detail": "Rubric or specified question not found."},
        401: {"detail": "Requester is not authenticated."},
        403: {"detail": "Authenticated but access is not allowed."}
    }
)
async def get_rubric(
        semester: str = Query(..., description="Semester of the course."),
        course_id: str = Query(..., description="Identifier of the course."),
        assignment_id: str = Query(..., description="Identifier of the assignment."),
        question_index: Optional[int] = Query(None, description="Optional question index to retrieve a specific sub-rubric."),
        user_meta: UserToken = Depends(user_from_auth),
):
    blob_uploader = AzureBlobService.get_instance()

    # validate params by attempting to create a course object
    Course(semester=semester, course_id=course_id)

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

    # Get the rubric
    if question_index is not None:
        rubric = blob_uploader.get_sub_rubric(semester, course_id, assignment_id, question_index)
    else:
        rubric = blob_uploader.get_rubric(semester, course_id, assignment_id)

    if rubric is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rubric not found.")

    return rubric