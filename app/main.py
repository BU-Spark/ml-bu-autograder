import sys
import logging
import traceback

# <<< --- Add CORSMiddleware import --- >>>
from fastapi.middleware.cors import CORSMiddleware

from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv
from isapi.isapicon import HTTP_BAD_REQUEST
from pydantic import FilePath, HttpUrl, ValidationError

from app.services import AzureEmbeddingService
from app.utils import get_str_var, get_bool_var, setup_loggers, get_int_var
from app.services.bg_material_processor import BackgroundMaterialProcessor
from app.utils.jwt_service import JWTService
from app.utils.llm_service import LLMService

load_dotenv()  # Load environment variables first

from app.services.azure_blob_service import AzureBlobService
from app.services.azure_vector_service import AzureVectorService

if __name__ == "__main__":
    logging.critical("This application is not intended to be run directly. See README.md for instructions.")
    sys.exit(1)

# Load environment variables
AZURE_STORAGE_ACCOUNT_NAME = get_str_var("AZURE_STORAGE_ACCOUNT_NAME")
AZURE_CONTAINER_NAME = get_str_var("AZURE_CONTAINER_NAME")
AZURE_CLIENT_ID = get_str_var("AZURE_CLIENT_ID", allow_none=True) # Allow None if using DefaultAzureCredential implicitly
AZURE_CLIENT_SECRET = get_str_var("AZURE_CLIENT_SECRET", allow_none=True) # Allow None
AZURE_TENANT_ID = get_str_var("AZURE_TENANT_ID", allow_none=True) # Allow None
APPLICATION_VERSION = get_str_var("APPLICATION_VERSION", default="0.1.0") # Provide a default
GOOGLE_OAUTH_CLIENT_FILE = get_str_var("GOOGLE_OAUTH_CLIENT_FILE", default="client_secret.json") # Default file name
PRODUCTION = get_bool_var("PRODUCTION", default="False") # Default to False
JWT_ENCRYPTION_SECRET_FILE = FilePath(get_str_var("JWT_ENCRYPTION_SECRET_FILE"))
AZURE_BLOB_CACHE_DIR = FilePath(get_str_var("AZURE_BLOB_CACHE_DIR"))
ENV_TEST_API_KEY = get_str_var("ENV_TEST_API_KEY", allow_none=True) # Allow None if not needed for JWTService
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

# Setup logging level
setup_loggers(production=PRODUCTION)

logging.info("Loading Azure services...")
# Credentials are automatically recognized based of the values of these env variables:
# AZURE_CLIENT_ID, AZURE_TENANT_ID, and AZURE_CLIENT_SECRET
# Or other methods supported by DefaultAzureCredential (Managed Identity, CLI login, etc.)
try:
    credential = DefaultAzureCredential()
    # Test credential validity early if possible (optional, might require specific SDK call)
    # Example: BlobServiceClient(account_url=..., credential=credential).get_account_information()
except Exception as e:
    logging.error(f"Failed to obtain Azure credentials via DefaultAzureCredential: {e}", exc_info=True)
    # Handle credential failure appropriately, maybe exit or raise
    sys.exit("Azure credential configuration error.")

try:
    AzureBlobService.init_singleton(credential, AZURE_STORAGE_ACCOUNT_NAME, AZURE_CONTAINER_NAME, AZURE_BLOB_CACHE_DIR)
    JWTService.init_singleton(JWT_ENCRYPTION_SECRET_FILE, ENV_TEST_API_KEY)
except Exception as e:
     logging.error(f"Failed to initialize singleton services: {e}", exc_info=True)
     sys.exit("Service initialization error.")

credential = DefaultAzureCredential()
AzureBlobService.init_singleton(credential, AZURE_STORAGE_ACCOUNT_NAME, AZURE_CONTAINER_NAME, TEMP_FILES_DIR)
JWTService.init_singleton(JWT_ENCRYPTION_SECRET_FILE, ENV_TEST_API_KEY)
LLMService.init_singleton(AZURE_LLM_DEPLOYMENT_URL, AZURE_LLM_DEPLOYMENT_KEY)
AzureEmbeddingService.init_singleton(AZURE_EMBEDDING_DEPLOYMENT_URL, AZURE_EMBEDDING_MODEL,
                                     AZURE_EMBEDDING_DEPLOYMENT_KEY)
# AzureVectorService.init_singleton(
#     endpoint=AZURE_SEARCH_ENDPOINT,
#     api_key=AZURE_SEARCH_API_KEY,
#     index_name=AZURE_SEARCH_INDEX_NAME,
#     embedding_dims=AZURE_SEARCH_EMBEDDING_DIMS
# )
BackgroundMaterialProcessor(TEMP_FILES_DIR).start_task_scan_loop()

logging.info("Starting FastAPI server...")

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from app.routes import auth, course, assignment, student_response, grading, course_material, rubric, user

# --- Create FastAPI app instance ---
app = FastAPI(
    title="BU MET Autograder API",
    description="API for BU MET Autograder – an AI-based autograding tool. "
                "This API allows instructors to manage courses, assignments, student responses, grading, "
                "course materials, and rubrics.",
    version=APPLICATION_VERSION
)

# --- Add CORS Middleware ---
# Define allowed origins (where your frontend is running)
# IMPORTANT: Adjust this for production deployments!
origins = [
    "http://localhost:3000",  # Your Next.js frontend development server
    # "https://your-deployed-frontend.com", # Example: Add your production frontend URL
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # List of origins allowed to make requests
    allow_credentials=True,  # Allow cookies/authorization headers
    allow_methods=["*"],  # Allow all standard methods (GET, POST, PUT, DELETE, PATCH, etc.)
    allow_headers=["*"],  # Allow all headers
)
# --- End of CORS Middleware ---


# --- Include API Routers ---
# Order matters less here than middleware, but keep logical grouping
# register error handlers
@app.exception_handler(ValidationError)
async def catch_pydantic_validation_errs(request: Request, exc: ValidationError):
    tb_str = ''.join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    logging.warning("ValidationError occurred:\n%s", tb_str)
    return JSONResponse(
        status_code=HTTP_BAD_REQUEST,
        content={"detail": exc.errors()},
    )

@app.exception_handler(ValueError)
async def catch_value_errs(request: Request, exc: ValueError):
    tb_str = ''.join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    logging.warning("ValueError occurred:\n%s", tb_str)
    return JSONResponse(
        status_code=HTTP_BAD_REQUEST,
        content={"detail": str(exc)},
    )


# Include routers for modular endpoints with appropriate prefixes and tags.
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(user.router, prefix="/api/v1", tags=["User"]) # Group user near auth
app.include_router(course.router, prefix="/api/v1", tags=["Course"])
app.include_router(assignment.router, prefix="/api/v1", tags=["Assignment"])
app.include_router(course_material.router, prefix="/api/v1", tags=["Course Material"])
app.include_router(rubric.router, prefix="/api/v1", tags=["Rubric"])
app.include_router(student_response.router, prefix="/api/v1", tags=["Student Response"])
app.include_router(grading.router, prefix="/api/v1/response", tags=["Grading"]) # Keep specific prefix

logging.info(f"FastAPI application configured with allowed origins: {origins}")

# Note: You would typically run this file using an ASGI server like uvicorn:
# uvicorn your_main_module_name:app --reload --port 8000