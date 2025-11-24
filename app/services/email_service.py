#!/usr/bin/env python3
"""
Email Service

This service sends approval emails for AI-generated rubrics using SendGrid.
"""

import logging
import secrets
import json
from datetime import datetime, timedelta, UTC
from typing import Optional, Dict, Any
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import smtplib
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content

from app.models.rubric import Rubric
from app.utils.env_var_util import get_str_var, get_bool_var, get_int_var

# Global email service instance
email_service_instance: Optional["EmailService"] = None


class EmailService:
    """
    Email service for sending rubric approval notifications.
    """

    # HARDCODE YOUR PROFESSOR EMAIL ADDRESSES HERE!
    # ================================================
    DEFAULT_PROFESSOR_EMAILS = [
        "cjpike@bu.edu",        # CourtneyPike
        "mlevinge@bu.edu",      # Micheal Levinger  
        "umeding@bu.edu"        # TA Uwe
    ]

    def __init__(self, 
                 smtp_host: str,
                 smtp_port: int, 
                 smtp_username: str,
                 smtp_password: str,
                 smtp_use_tls: bool = True,
                 from_email: str = "noreply@autograder.bu.edu",
                 base_url: str = "http://localhost:8000"):
        """
        Initialize the email service.
        
        Args:
            smtp_host: SMTP server hostname
            smtp_port: SMTP server port
            smtp_username: SMTP username
            smtp_password: SMTP password (SendGrid API key)
            smtp_use_tls: Whether to use TLS encryption
            from_email: Email address to send from
            base_url: Base URL for approval links
        """
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_username = smtp_username
        self.smtp_password = smtp_password
        self.smtp_use_tls = smtp_use_tls
        self.from_email = from_email
        self.base_url = base_url
        
        # Store pending approvals (in production, use Redis or database)
        self.pending_approvals: Dict[str, Dict[str, Any]] = {}
        
        logging.info(f"Email service initialized with host: {smtp_host}:{smtp_port}")

    def get_course_emails(self, course_id: str) -> list[str]:
        """
        Get hardcoded email list - same emails for all courses.
        No terminal prompts - emails are configured in code!
        """
        logging.info(f"Using professor emails for {course_id}: {self.DEFAULT_PROFESSOR_EMAILS}")
        return self.DEFAULT_PROFESSOR_EMAILS.copy()
    
    def send_to_all_course_professors(self, course_id: str, rubric_data: dict) -> list[str]:
        """
        Send approval email to ALL configured professors for a course.
        Returns list of approval tokens generated.
        """
        professor_emails = self.get_course_emails(course_id)
        tokens = []
        
        logging.info(f"Sending rubric approval to {len(professor_emails)} professors for {course_id}")
        
        for email in professor_emails:
            try:
                # Create a temporary rubric object for this email
                from app.models.rubric import Rubric
                temp_rubric = Rubric(
                    course_id=course_id,
                    assignment_id=rubric_data.get("assignment_id", "Assignment"),
                    semester=rubric_data.get("semester", "current"),
                    sub_rubrics=[]
                )
                
                token = self.send_rubric_approval_email(temp_rubric, email, f"Professor ({email})")
                tokens.append(token)
                logging.info(f"Sent to {email} with token {token}")
                
            except Exception as e:
                logging.error(f"Failed to send to {email}: {e}")
        
        return tokens

    def generate_approval_token(self) -> str:
        """Generate a secure random token for approval links."""
        return secrets.token_urlsafe(32)

    def send_rubric_approval_email(self, 
                                   rubric: Rubric,
                                   instructor_email: str,
                                   instructor_name: Optional[str] = None) -> str:
        """
        Send an approval email for an AI-generated rubric.
        
        Args:
            rubric: The rubric to approve
            instructor_email: Email of the instructor
            instructor_name: Name of the instructor (optional)
            
        Returns:
            str: The approval token for tracking
        """
        # Generate unique approval token
        approval_token = self.generate_approval_token()
        
        # Store rubric data temporarily
        self.pending_approvals[approval_token] = {
            "rubric": rubric.model_dump(),
            "instructor_email": instructor_email,
            "instructor_name": instructor_name,
            "created_at": datetime.now(UTC),
            "expires_at": datetime.now(UTC) + timedelta(hours=24)  # 24 hour expiry
        }
        
        # Create approval URLs
        approve_url = f"{self.base_url}/api/v1/rubric/approve/{approval_token}"
        reject_url = f"{self.base_url}/api/v1/rubric/reject/{approval_token}"
        
        # Create email content
        subject = f"AI Rubric Approval Required - {rubric.course_id} {rubric.assignment_id}"
        
        html_content = self._create_approval_email_html(
            rubric=rubric,
            instructor_name=instructor_name or instructor_email,
            approve_url=approve_url,
            reject_url=reject_url
        )
        
        text_content = self._create_approval_email_text(
            rubric=rubric,
            instructor_name=instructor_name or instructor_email,
            approve_url=approve_url,
            reject_url=reject_url
        )
        
        # Send the email
        try:
            self._send_email(
                to_email=instructor_email,
                subject=subject,
                html_content=html_content,
                text_content=text_content
            )
            
            logging.info(f"Approval email sent to {instructor_email} for rubric {approval_token}")
            return approval_token
            
        except Exception as e:
            logging.error(f"Failed to send approval email: {e}")
            # Clean up the pending approval
            if approval_token in self.pending_approvals:
                del self.pending_approvals[approval_token]
            raise

    def _create_approval_email_html(self, 
                                    rubric: Rubric,
                                    instructor_name: str,
                                    approve_url: str,
                                    reject_url: str) -> str:
        """Create HTML email content for rubric approval."""
        
        # Calculate total points
        total_points = sum(sub.max_points for sub in rubric.sub_rubrics)
        
        # Create sub-rubrics summary
        sub_rubrics_html = ""
        for sub in rubric.sub_rubrics:
            criteria_html = ""
            if sub.grading_criteria:
                for criteria in sub.grading_criteria:
                    criteria_html += f"""
                    <li><strong>{criteria.criteria_id}:</strong> {criteria.criteria} ({criteria.points} pts)</li>
                    """
            
            sub_rubrics_html += f"""
            <div style="margin: 15px 0; padding: 15px; background-color: #f8f9fa; border-left: 4px solid #007bff;">
                <h4>Question {sub.question_index} ({sub.max_points} points)</h4>
                {f'<p><em>Guidelines:</em> {sub.instructor_guideline}</p>' if sub.instructor_guideline else ''}
                {f'<ul>{criteria_html}</ul>' if criteria_html else ''}
            </div>
            """
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Rubric Approval Required</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; }}
                .header {{ background-color: #007bff; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; }}
                .button {{ display: inline-block; padding: 12px 24px; margin: 10px 5px; text-decoration: none; border-radius: 5px; font-weight: bold; }}
                .approve {{ background-color: #28a745; color: white; }}
                .reject {{ background-color: #dc3545; color: white; }}
                .footer {{ background-color: #f8f9fa; padding: 15px; font-size: 12px; color: #666; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>AI Rubric Approval Required</h1>
            </div>
            
            <div class="content">
                <p>Hello {instructor_name},</p>
                
                <p>An AI-generated rubric is ready for your review and approval:</p>
                
                <div style="background-color: #e9ecef; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <h3>Course: {rubric.course_id}</h3>
                    <h3>Assignment: {rubric.assignment_id}</h3>
                    <h3>Semester: {rubric.semester}</h3>
                    <h3>Total Points: {total_points}</h3>
                </div>
                
                <h3>Rubric Details:</h3>
                
                {f'<p><strong>Overall Guidelines:</strong> {rubric.overall_instructor_guidelines}</p>' if rubric.overall_instructor_guidelines else ''}
                
                {f'<p><strong>Grading Flags:</strong> {", ".join([flag.value for flag in rubric.grading_flags])}</p>' if rubric.grading_flags else ''}
                
                <h4>Questions:</h4>
                {sub_rubrics_html}
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{approve_url}" class="button approve">APPROVE RUBRIC</a>
                    <a href="{reject_url}" class="button reject">REJECT RUBRIC</a>
                </div>
                
                <p><small><em>This approval link will expire in 24 hours. If you don't take action, the rubric will need to be regenerated.</em></small></p>
            </div>
            
            <div class="footer">
                <p>This is an automated message from the BU MET Autograder system.</p>
                <p>Please do not reply to this email.</p>
            </div>
        </body>
        </html>
        """
        return html

    def _create_approval_email_text(self, 
                                    rubric: Rubric,
                                    instructor_name: str,
                                    approve_url: str,
                                    reject_url: str) -> str:
        """Create plain text email content for rubric approval."""
        
        total_points = sum(sub.max_points for sub in rubric.sub_rubrics)
        
        sub_rubrics_text = ""
        for sub in rubric.sub_rubrics:
            sub_rubrics_text += f"\nQuestion {sub.question_index} ({sub.max_points} points)\n"
            if sub.instructor_guideline:
                sub_rubrics_text += f"Guidelines: {sub.instructor_guideline}\n"
            
            if sub.grading_criteria:
                for criteria in sub.grading_criteria:
                    sub_rubrics_text += f"  - {criteria.criteria_id}: {criteria.criteria} ({criteria.points} pts)\n"
        
        text = f"""
AI Rubric Approval Required

Hello {instructor_name},

An AI-generated rubric is ready for your review and approval:

Course: {rubric.course_id}
Assignment: {rubric.assignment_id}
Semester: {rubric.semester}
Total Points: {total_points}

RUBRIC DETAILS:
{f'Overall Guidelines: {rubric.overall_instructor_guidelines}' if rubric.overall_instructor_guidelines else ''}

{f'Grading Flags: {", ".join([flag.value for flag in rubric.grading_flags])}' if rubric.grading_flags else ''}

Questions:{sub_rubrics_text}

ACTIONS:
To APPROVE this rubric, click: {approve_url}
To REJECT this rubric, click: {reject_url}

This approval link will expire in 24 hours.

---
This is an automated message from the BU MET Autograder system.
Please do not reply to this email.
        """
        return text.strip()

    def _send_email(self, 
                    to_email: str,
                    subject: str,
                    html_content: str,
                    text_content: str):
        """Send email using SendGrid or SMTP."""
        
        try:
            # Try SendGrid first (if password looks like SendGrid API key)
            if self.smtp_password.startswith('SG.'):
                self._send_via_sendgrid(to_email, subject, html_content, text_content)
            else:
                self._send_via_smtp(to_email, subject, html_content, text_content)
                
        except Exception as e:
            logging.error(f"Email sending failed: {e}")
            raise

    def _send_via_sendgrid(self, 
                           to_email: str,
                           subject: str,
                           html_content: str,
                           text_content: str):
        """Send email using SendGrid API."""
        
        sg = SendGridAPIClient(api_key=self.smtp_password)
        
        message = Mail(
            from_email=Email(self.from_email),
            to_emails=To(to_email),
            subject=subject,
            html_content=Content("text/html", html_content),
            plain_text_content=Content("text/plain", text_content)
        )
        
        response = sg.send(message)
        logging.info(f"SendGrid email sent: {response.status_code}")

    def _send_via_smtp(self, 
                       to_email: str,
                       subject: str,
                       html_content: str,
                       text_content: str):
        """Send email using SMTP."""
        
        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = self.from_email
        msg['To'] = to_email
        
        # Add text and HTML parts
        msg.attach(MIMEText(text_content, 'plain'))
        msg.attach(MIMEText(html_content, 'html'))
        
        # Send via SMTP
        with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
            if self.smtp_use_tls:
                server.starttls()
            server.login(self.smtp_username, self.smtp_password)
            server.send_message(msg)
            
        logging.info(f"SMTP email sent to {to_email}")

    def get_pending_approval(self, token: str) -> Optional[Dict[str, Any]]:
        """Get pending approval data by token."""
        approval = self.pending_approvals.get(token)
        
        if not approval:
            return None
        
        # Check if expired
        if datetime.now(UTC) > approval['expires_at']:
            del self.pending_approvals[token]
            return None
        
        return approval

    def approve_rubric(self, token: str) -> Optional[Rubric]:
        """Approve a rubric and return it for saving."""
        approval = self.get_pending_approval(token)
        if not approval:
            return None
        
        # Convert back to Rubric object
        rubric = Rubric(**approval['rubric'])
        
        # Clean up
        del self.pending_approvals[token]
        
        logging.info(f"Rubric approved with token {token}")
        return rubric

    def reject_rubric(self, token: str) -> bool:
        """Reject a rubric and clean up."""
        if token not in self.pending_approvals:
            return False
        
        del self.pending_approvals[token]
        logging.info(f"Rubric rejected with token {token}")
        return True

    def cleanup_expired_approvals(self):
        """Remove expired approval tokens."""
        current_time = datetime.now(UTC)
        expired_tokens = [
            token for token, data in self.pending_approvals.items()
            if current_time > data['expires_at']
        ]
        
        for token in expired_tokens:
            del self.pending_approvals[token]
            
        if expired_tokens:
            logging.info(f"Cleaned up {len(expired_tokens)} expired approval tokens")

    @staticmethod
    def init_singleton():
        """Initialize the global email service instance with BU professor emails."""
        global email_service_instance
        
        try:
            smtp_host = get_str_var("SMTP_HOST")
            smtp_port = get_int_var("SMTP_PORT") 
            smtp_username = get_str_var("SMTP_USERNAME")
            smtp_password = get_str_var("SMTP_PASSWORD")  # SendGrid API key
            smtp_use_tls = get_bool_var("SMTP_USE_TLS")
            from_email = get_str_var("EMAIL_FROM")
            deployment_url = get_str_var("DEPLOYMENT_URL", default="http://localhost:8000")
            
            email_service_instance = EmailService(
                smtp_host=smtp_host,
                smtp_port=smtp_port,
                smtp_username=smtp_username,
                smtp_password=smtp_password,
                smtp_use_tls=smtp_use_tls,
                from_email=from_email,
                base_url=deployment_url
            )
            
            logging.info("Email service initialized with BU professor recipients!")
            logging.info(f"Configured to send from: {from_email}")
            logging.info(f"Will send to: {EmailService.DEFAULT_PROFESSOR_EMAILS}")
            
        except Exception as e:
            logging.warning(f"Email service initialization failed: {e}")
            # Create a minimal instance so the app doesn't crash
            email_service_instance = None
            email_service_instance = None

    @staticmethod
    def get_instance() -> Optional["EmailService"]:
        """Get the global email service instance."""
        return email_service_instance


# Convenience function for BU integration
def send_rubric_approval_email_to_bu_professors(rubric: Rubric) -> Optional[list[str]]:
    """
    Send rubric approval email to ALL BU professors (hardcoded).
    No need to specify emails - automatically sends to CourtneyPike, Micheal, and TA Uwe!
    
    Returns:
        list[str]: List of approval tokens if successful, None if email service not available
    """
    service = EmailService.get_instance()
    if not service:
        logging.warning("Email service not available - skipping approval email")
        return None
    
    # Send to all BU professors
    tokens = []
    for email in service.DEFAULT_PROFESSOR_EMAILS:
        try:
            # Determine name from email
            if "cjpike" in email:
                name = "CourtneyPike"
            elif "mlevinge" in email:
                name = "Micheal Levinger"
            elif "umeding" in email:
                name = "TA Uwe"
            else:
                name = "Professor"
            
            token = service.send_rubric_approval_email(rubric, email, name)
            if token:
                tokens.append(token)
                logging.info(f"Sent approval email to {name} ({email}) - Token: {token}")
        except Exception as e:
            logging.error(f"Failed to send to {email}: {e}")
    
    logging.info(f"Sent rubric approval to {len(tokens)} BU professors")
    return tokens if tokens else None

# Legacy function for backward compatibility  
def send_rubric_approval_email(rubric: Rubric, 
                               instructor_email: str = None,
                               instructor_name: Optional[str] = None) -> Optional[str]:
    """
    Legacy function - now automatically sends to BU professors if no email specified.
    """
    if instructor_email:
        # Use specific email if provided
        service = EmailService.get_instance()
        if not service:
            return None
        return service.send_rubric_approval_email(rubric, instructor_email, instructor_name)
    else:
        # Send to all BU professors
        tokens = send_rubric_approval_email_to_bu_professors(rubric)
        return tokens[0] if tokens else None
