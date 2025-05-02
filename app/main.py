import sys
import logging
import traceback

from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv
from pydantic import FilePath, HttpUrl, ValidationError

from app.services import AzureEmbeddingService
from app.services.azure_embedding_service import CohereEmbeddingService
from app.services.vector_db_service import ChromaDBService
from app.utils import get_str_var, get_bool_var, setup_loggers, get_int_var
from app.services.bg_material_processor import BackgroundMaterialProcessor
from app.utils.jwt_service import JWTService
from app.utils.llm_service import LLMService

load_dotenv()  # Load environment variables first

from app.services.azure_blob_service import AzureBlobService

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
TEMP_FILES_DIR = FilePath(get_str_var("TEMP_FILES_DIR"))
ENV_TEST_API_KEY = get_str_var("ENV_TEST_API_KEY")
AZURE_LLM_DEPLOYMENT_URL = HttpUrl(get_str_var("AZURE_LLM_DEPLOYMENT_URL"))
AZURE_LLM_DEPLOYMENT_KEY = get_str_var("AZURE_LLM_DEPLOYMENT_KEY")
AZURE_EMBEDDING_DEPLOYMENT_URL = HttpUrl(get_str_var("AZURE_EMBEDDING_DEPLOYMENT_URL"))
AZURE_EMBEDDING_MODEL = get_str_var("AZURE_EMBEDDING_MODEL")
AZURE_EMBEDDING_DEPLOYMENT_KEY = get_str_var("AZURE_EMBEDDING_DEPLOYMENT_KEY")
#added intializations for azure search endpoints
AZURE_SEARCH_ENDPOINT = HttpUrl(get_str_var("AZURE_SEARCH_ENDPOINT"))
AZURE_SEARCH_API_KEY = get_str_var("AZURE_SEARCH_API_KEY")
AZURE_SEARCH_INDEX_NAME = get_str_var("AZURE_SEARCH_INDEX_NAME")
AZURE_SEARCH_EMBEDDING_DIMS = get_int_var("AZURE_SEARCH_EMBEDDING_DIMS")
DEPLOYMENT_URL = get_str_var("DEPLOYMENT_URL")
COHERE_API_KEY = get_str_var("COHERE_EMBEDDING_KEY")

# Setup logging level
setup_loggers(production=PRODUCTION)

logging.info("Loading Azure services...")
# Credentials are automatically recognized based of the values of these env variables:
# AZURE_CLIENT_ID, AZURE_TENANT_ID, and AZURE_CLIENT_SECRET
credential = DefaultAzureCredential()
AzureBlobService.init_singleton(credential, AZURE_STORAGE_ACCOUNT_NAME, AZURE_CONTAINER_NAME, TEMP_FILES_DIR)
JWTService.init_singleton(JWT_ENCRYPTION_SECRET_FILE, ENV_TEST_API_KEY)
LLMService.init_singleton(AZURE_LLM_DEPLOYMENT_URL, AZURE_LLM_DEPLOYMENT_KEY)
# AzureEmbeddingService.init_singleton(AZURE_EMBEDDING_DEPLOYMENT_URL, AZURE_EMBEDDING_MODEL,
#                                      AZURE_EMBEDDING_DEPLOYMENT_KEY)
CohereEmbeddingService.init_singleton(COHERE_API_KEY)
ChromaDBService.init_singleton()
BackgroundMaterialProcessor(TEMP_FILES_DIR).start_task_scan_loop()

logging.info("Starting FastAPI server...")

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.routes import auth, course, assignment, student_response, grading, course_material, rubric, user

app = FastAPI(
    title="BU MET Autograder API",
    description="API for BU MET Autograder – an AI-based autograding tool. "
                "This API allows instructors to manage courses, assignments, student responses, grading, "
                "course materials, and rubrics.",
    version=APPLICATION_VERSION
)


# register error handlers
@app.exception_handler(ValidationError)
async def catch_pydantic_validation_errs(request: Request, exc: ValidationError):
    tb_str = ''.join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    logging.warning("ValidationError occurred:\n%s", tb_str)
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": exc.errors()},
    )

@app.exception_handler(ValueError)
async def catch_value_errs(request: Request, exc: ValueError):
    tb_str = ''.join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    logging.warning("ValueError occurred:\n%s", tb_str)
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": str(exc)},
    )

# --- Add CORS Middleware ---
# Define allowed origins (where your frontend is running)
# IMPORTANT: Adjust this for production deployments!
origins = [
    "http://localhost:3000",  # Your Next.js frontend development server
    DEPLOYMENT_URL
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # List of origins allowed to make requests
    allow_credentials=True,  # Allow cookies/authorization headers
    allow_methods=["*"],  # Allow all standard methods (GET, POST, PUT, DELETE, PATCH, etc.)
    allow_headers=["*"],  # Allow all headers
)
# --- End of CORS Middleware ---

# Include routers for modular endpoints with appropriate prefixes and tags.
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(course.router, prefix="/api/v1", tags=["Course"])
app.include_router(assignment.router, prefix="/api/v1", tags=["Assignment"])
app.include_router(student_response.router, prefix="/api/v1", tags=["Student Response"])
app.include_router(grading.router, prefix="/api/v1/response", tags=["Grading"])
app.include_router(course_material.router, prefix="/api/v1", tags=["Course Material"])
app.include_router(rubric.router, prefix="/api/v1", tags=["Rubric"])
app.include_router(user.router, prefix="/api/v1", tags=["User"])
