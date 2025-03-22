import sys

from dotenv import load_dotenv

from app.utils.azure_blob_uploader import AzureBlobUploader

load_dotenv()  # Load environment variables first
from fastapi import FastAPI, Depends
import os
from app.routes import auth, course, assignment, student_response, grading, course_material, rubric, user

if __name__ == "__main__":
    print("This application is not intended to be run directly. See README.md for instructions.")
    sys.exit(1)


def blob_uploader(sas_url, container_name) -> AzureBlobUploader:
    """
    Creates an AzureBlobUploader instance using the provided SAS URL and container name.
    :param sas_url: The full SAS URL for the container.
    :param container_name: The name of the container inside the storage account.
    :return: AzureBlobUploader instance.
    """
    return AzureBlobUploader(sas_url, container_name)


# Load environment variables
SAS_URL = os.getenv("STORAGE_SAS_URL")
APPLICATION_VERSION = os.getenv("APPLICATION_VERSION")
GOOGLE_OAUTH_CLIENT_FILE = os.getenv("GOOGLE_OAUTH_CLIENT_FILE")

# Hard fail if required environment variables are not set
if not SAS_URL or not APPLICATION_VERSION or not GOOGLE_OAUTH_CLIENT_FILE:
    print("Required environment variables are not set. Please see README.md for instructions.")
    sys.exit(1)

app = FastAPI(
    title="BU MET Autograder API",
    description="API for BU MET Autograder – an AI-based autograding tool. "
                "This API allows instructors to manage courses, assignments, student responses, grading, "
                "course materials, and rubrics.",
    version=APPLICATION_VERSION
)

# Include routers for modular endpoints with appropriate prefixes and tags.
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"], dependencies=[Depends(blob_uploader)])
app.include_router(course.router, prefix="/api/v1", tags=["Course"], dependencies=[Depends(blob_uploader)])
app.include_router(assignment.router, prefix="/api/v1", tags=["Assignment"], dependencies=[Depends(blob_uploader)])
app.include_router(student_response.router, prefix="/api/v1", tags=["Student Response"], dependencies=[Depends(blob_uploader)])
app.include_router(grading.router, prefix="/api/v1/response", tags=["Grading"], dependencies=[Depends(blob_uploader)])
app.include_router(course_material.router, prefix="/api/v1", tags=["Course Material"], dependencies=[Depends(blob_uploader)])
app.include_router(rubric.router, prefix="/api/v1", tags=["Rubric"], dependencies=[Depends(blob_uploader)])
app.include_router(user.router, prefix="/api/v1", tags=["User"], dependencies=[Depends(blob_uploader)])
