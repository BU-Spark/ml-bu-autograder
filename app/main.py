import sys

from dotenv import load_dotenv
load_dotenv()  # Load environment variables first

from app.utils.azure_ai_service import AzureAIService
from app.utils.azure_blob_uploader import AzureBlobUploader
from fastapi import FastAPI
import os
from app.routes import auth, course, assignment, student_response, grading, course_material, rubric, user

if __name__ == "__main__":
    print("This application is not intended to be run directly. See README.md for instructions.")
    sys.exit(1)

# Load environment variables
SAS_URL = os.getenv("STORAGE_SAS_URL")
AZURE_CONTAINER_NAME = os.getenv("AZURE_CONTAINER_NAME")
APPLICATION_VERSION = os.getenv("APPLICATION_VERSION")
GOOGLE_OAUTH_CLIENT_FILE = os.getenv("GOOGLE_OAUTH_CLIENT_FILE")

if not SAS_URL or not APPLICATION_VERSION or not GOOGLE_OAUTH_CLIENT_FILE or not AZURE_CONTAINER_NAME:
    raise RuntimeError("Required environment variables are not set. Please see README.md for instructions.")

AzureBlobUploader.init_singleton(SAS_URL, AZURE_CONTAINER_NAME)
AzureAIService.init_singleton()  # TODO set up at some point

app = FastAPI(
    title="BU MET Autograder API",
    description="API for BU MET Autograder – an AI-based autograding tool. "
                "This API allows instructors to manage courses, assignments, student responses, grading, "
                "course materials, and rubrics.",
    version=APPLICATION_VERSION
)


# Include routers for modular endpoints with appropriate prefixes and tags.
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(course.router, prefix="/api/v1", tags=["Course"])
app.include_router(assignment.router, prefix="/api/v1", tags=["Assignment"])
app.include_router(student_response.router, prefix="/api/v1", tags=["Student Response"])
app.include_router(grading.router, prefix="/api/v1/response", tags=["Grading"])
app.include_router(course_material.router, prefix="/api/v1", tags=["Course Material"])
app.include_router(rubric.router, prefix="/api/v1", tags=["Rubric"])
app.include_router(user.router, prefix="/api/v1", tags=["User"])
