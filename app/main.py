import sys
import logging

from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv
from pydantic import FilePath

from app.utils import get_str_var, get_bool_var, setup_loggers, JWTService

load_dotenv()  # Load environment variables first

from app.utils.azure_blob_service import AzureBlobService

if __name__ == "__main__":
    logging.critical("This application is not intended to be run directly. See README.md for instructions.")
    sys.exit(1)

# Load environment variables
AZURE_STORAGE_ACCOUNT_NAME = get_str_var("AZURE_STORAGE_ACCOUNT_NAME")
AZURE_CONTAINER_NAME = get_str_var("AZURE_CONTAINER_NAME")
AZURE_CLIENT_ID = get_str_var("AZURE_CLIENT_ID")
AZURE_CLIENT_SECRET = get_str_var("AZURE_CLIENT_SECRET")
AZURE_TENANT_ID = get_str_var("AZURE_TENANT_ID")
APPLICATION_VERSION = get_str_var("APPLICATION_VERSION")
GOOGLE_OAUTH_CLIENT_FILE = get_str_var("GOOGLE_OAUTH_CLIENT_FILE")
PRODUCTION = get_bool_var("PRODUCTION")
JWT_ENCRYPTION_SECRET_FILE = FilePath(get_str_var("JWT_ENCRYPTION_SECRET_FILE"))
AZURE_BLOB_CACHE_DIR = FilePath(get_str_var("AZURE_BLOB_CACHE_DIR"))
ENV_TEST_API_KEY = get_str_var("ENV_TEST_API_KEY")

# Setup logging level
setup_loggers(production=PRODUCTION)

logging.info("Loading Azure services...")
# Credentials are automatically recognized based of the values of these env variables:
# AZURE_CLIENT_ID, AZURE_TENANT_ID, and AZURE_CLIENT_SECRET
credential = DefaultAzureCredential()
AzureBlobService.init_singleton(credential, AZURE_STORAGE_ACCOUNT_NAME, AZURE_CONTAINER_NAME, AZURE_BLOB_CACHE_DIR)
JWTService.init_singleton(JWT_ENCRYPTION_SECRET_FILE, ENV_TEST_API_KEY)

logging.info("Starting FastAPI server...")

from fastapi import FastAPI
from app.routes import auth, course, assignment, student_response, grading, course_material, rubric, user
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
