# BU MET Autograder - Technical Manifest

**Version:** 1.1  
**Last Updated:** 2025-12-09 
**Project:** Boston University SPARK - MET ETI Autograder

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Architecture Overview](#architecture-overview)
3. [System Components](#system-components)
4. [Dependencies](#dependencies)
5. [Data Flow](#data-flow)
6. [Assumptions](#assumptions)
7. [Edge Cases & Error Handling](#edge-cases--error-handling)
8. [Deployment Notes](#deployment-notes)
9. [Improvement Opportunities](#improvement-opportunities)
10. [Context & Background](#context--background)

---

## Executive Summary

The BU MET Autograder is a comprehensive AI-powered grading system designed for Boston University's Metropolitan College. It provides automated grading of student quiz answers using Large Language Models (LLMs), with capabilities for rubric refinement, batch processing, and integration with Azure cloud services.

**Key Capabilities:**
- AI-powered rubric refinement through iterative LLM critique
- Automated grading of student responses using refined rubrics
- RESTful API for course, assignment, and grading management
- Vector database integration for Retrieval-Augmented Generation (RAG)
- Multi-format file processing (PDF, images, audio, video)
- Azure Blob Storage for persistent data management

**Technology Stack:**
- **Backend:** Python 3.10+, FastAPI, Azure OpenAI
- **Frontend:** Next.js, Material-UI
- **Storage:** Azure Blob Storage, ChromaDB (vector database)
- **Authentication:** JWT, Google OAuth 2.0

---

## Architecture Overview

### High-Level Architecture

The system follows a **layered architecture** with clear separation of concerns:

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (Next.js)                       │
│              React Components + Material-UI                  │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTP/REST
┌──────────────────────▼──────────────────────────────────────┐
│              FastAPI Application Layer                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │
│  │  Routes  │  │  Models  │  │ Services │  │  Utils   │    │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘    │
└──────────────────────┬──────────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
┌───────▼──────┐ ┌─────▼─────┐ ┌─────▼──────┐
│ Azure OpenAI │ │ Azure Blob│ │  ChromaDB   │
│    (LLM)     │ │  Storage   │ │  (Vector)   │
└──────────────┘ └────────────┘ └────────────┘
```

### Application Structure

The codebase is organized into two main applications:

1. **Main API Application** (`app/`): FastAPI-based REST API
2. **Grading Pipeline Application** (`ai-baseline/app/`): Standalone grading pipeline

### Design Patterns

- **Singleton Pattern**: Services (LLMService, AzureBlobService, JWTService) use singleton initialization
- **Factory Pattern**: Service initialization functions create service instances
- **Repository Pattern**: AzureBlobService acts as repository for data persistence
- **Strategy Pattern**: Multiple embedding services (Cohere, Azure) with interchangeable implementations
- **Observer Pattern**: Background material processor scans and processes files asynchronously

---

## System Components

### 1. API Application (`app/`)

#### 1.1 Routes (`app/routes/`)

**Authentication Routes** (`auth.py`):
- `POST /api/v1/auth/token` - Create personal access token
- `DELETE /api/v1/auth/token` - Revoke token
- `GET /api/v1/auth/tokens` - List user tokens
- `GET /api/v1/auth/google_oauth` - OAuth initiation
- `POST /api/v1/auth/google_oauth` - OAuth callback

**Course Routes** (`course.py`):
- `POST /api/v1/course` - Create course
- `GET /api/v1/course` - Get course details
- `GET /api/v1/courses` - List courses
- `DELETE /api/v1/course` - Delete course
- `PATCH /api/v1/course/transfer` - Transfer course between semesters
- `POST /api/v1/course/instructor` - Add instructor
- `DELETE /api/v1/course/instructor` - Remove instructor

**Assignment Routes** (`assignment.py`):
- `POST /api/v1/assignment` - Create assignment
- `GET /api/v1/assignment` - Get assignment
- `GET /api/v1/assignments` - List assignments
- `DELETE /api/v1/assignment` - Delete assignment
- `PATCH /api/v1/assignment/add_question` - Add question
- `PATCH /api/v1/assignment/remove_question` - Remove question
- `PATCH /api/v1/assignment/edit_question` - Edit question
- `PATCH /api/v1/assignment/modify_order` - Reorder questions

**Grading Routes** (`grading.py`):
- `POST /api/v1/grade/specific` - Grade specific students
- `POST /api/v1/grade/ungraded` - Grade all ungraded responses
- `POST /api/v1/grade/all` - Regrade all responses

**Rubric Routes** (`rubric.py`, `rubric_review.py`):
- `POST /api/v1/rubric` - Create/update rubric
- `GET /api/v1/rubric` - Get rubric
- `GET /api/v1/ai_rubric` - Generate rubric using AI
- `POST /api/v1/rubric/audit_and_refine` - Refine rubric iteratively

**Student Response Routes** (`student_response.py`):
- `POST /api/v1/response` - Submit student response
- `PUT /api/v1/response` - Update response
- `DELETE /api/v1/response` - Delete response
- `GET /api/v1/responses` - List responses

**Course Material Routes** (`course_material.py`):
- `POST /api/v1/course_material` - Upload material
- `GET /api/v1/course_material` - Get material
- `GET /api/v1/course_materials` - List materials
- `DELETE /api/v1/course_material` - Delete material
- `PATCH /api/v1/course_material` - Update material

#### 1.2 Models (`app/models/`)

**Core Data Models:**
- `User` - Instructor/user information
- `Course` - Course metadata (semester, course_id)
- `Assignment` - Assignment details with questions
- `Question` - Individual question within assignment
- `Rubric` - Grading rubric with sub-rubrics
- `SubRubric` - Per-question grading criteria
- `GradingCriteria` - Individual grading criterion
- `StudentResponse` - Student answer submission
- `Grade` - Grading result with score and feedback
- `CourseMaterial` - Supplemental course materials
- `PersonalAccessToken` - API access tokens
- `WebsiteAccessToken` - Web session tokens

**Model Characteristics:**
- All models use Pydantic for validation
- Models support JSON serialization
- Field validators ensure data integrity
- Nested models for complex structures

#### 1.3 Services (`app/services/`)

**AzureBlobService** (`azure_blob_service.py`):
- Manages Azure Blob Storage operations
- Handles file uploads/downloads
- Implements caching layer (fsspec filecache)
- Provides CRUD operations for courses, assignments, rubrics
- Singleton pattern with thread-safe initialization

**LLMService** (`utils/llm_service.py`):
- Wrapper around Azure OpenAI API
- Supports structured output generation
- Handles prompt building with multiple content types
- Manages API versioning and endpoint configuration
- Singleton pattern

**RubricRefinementService** (`rubric_refinement_service.py`):
- Orchestrates rubric critique and refinement
- Uses LLM to analyze rubric quality
- Generates improved rubric versions
- Supports iterative refinement

**VectorDBService** (`vector_db_service.py`):
- ChromaDB integration for vector storage
- Embedding storage and retrieval
- RAG (Retrieval-Augmented Generation) support

**CohereEmbeddingService** (`azure_embedding_service.py`):
- Cohere API integration for embeddings
- Text-to-vector conversion
- Used for semantic search

**BackgroundMaterialProcessor** (`bg_material_processor.py`):
- Asynchronous file processing
- Scans temp directory for new files
- Processes course materials and student responses
- Thread pool executor for concurrent processing

#### 1.4 Utilities (`app/utils/`)

**JWTService** (`jwt_service.py`):
- JWT token generation and validation
- User authentication token management
- Token expiration handling

**LLMService** (`llm_service.py`):
- Azure OpenAI client wrapper
- Prompt building utilities
- Structured response generation
- Multi-modal content support (text, images, audio)

**BytesToDocUtil** (`bytes_to_doc_util.py`):
- File type detection
- MIME type handling
- Document conversion utilities

**ErrorHandlingTPE** (`error_handling_tpe.py`):
- Thread pool executor with error handling
- Graceful failure handling for background tasks

**LoggingUtil** (`logging_util.py`):
- Centralized logging configuration
- Production vs development logging levels
- Color-coded console output

### 2. Grading Pipeline Application (`ai-baseline/app/`)

#### 2.1 Main Pipeline (`main.py`)

**Workflow:**
1. **Rubric Refinement**: Iteratively improves rubric using LLM critique
2. **Rubric Loading**: Loads refined or original rubric
3. **Student Answer Loading**: Parses CSV with flexible column detection
4. **Grading**: Grades each student answer using LLM
5. **Result Export**: Saves graded results to CSV

**Key Functions:**
- `refine_rubric()` - Orchestrates rubric refinement
- `load_refined_rubric()` - Loads rubric text
- `get_grading_system_prompt()` - Builds grading prompt
- `load_student_answers()` - Parses CSV with auto-detection
- `grade_student_answer()` - Grades individual answer
- `save_grades_to_csv()` - Exports results

#### 2.2 Core Components (`core/`)

**RubricFileParser** (`parser.py`):
- Uses LLM to parse rubric text files
- Extracts structured data (questions, criteria, points)
- Converts to Assignment and Rubric models
- Handles various rubric formats

**RubricTestRunner** (`runner.py`):
- Orchestrates rubric refinement workflow
- Manages iterative refinement loop
- Handles critique and refinement cycles
- Saves refined rubrics

**Models** (`models.py`):
- `ExtractedRubricData` - LLM-extracted rubric structure
- `ExtractedSubRubric` - Per-question rubric data
- `ExtractedGradingCriteria` - Individual criteria

#### 2.3 Utilities (`utils/`)

**RubricStorage** (`storage.py`):
- Saves refined rubrics (text and JSON)
- Manages file paths and directory structure
- Formats rubrics for human readability

**RubricFormatter** (`formatter.py`):
- Formats rubrics for display
- Prints critique results
- Formats grading output

**CSVParser** (`csv_parser.py`):
- Parses student answer CSVs
- Handles multiple column name formats
- Validates data integrity

**PathUtils** (`path_utils.py`):
- Resolves relative/absolute paths
- Gets project root directory
- Cross-platform path handling

---

## Dependencies

### Python Dependencies (`app/requirements.txt`)

**Web Framework:**
- `fastapi==0.115.11` - Modern web framework
- `uvicorn==0.34.0` - ASGI server

**Data Validation:**
- `pydantic[email]` - Data validation and settings

**Azure Services:**
- `azure-storage-blob==12.25.0` - Blob storage client
- `azure-identity==1.21.0` - Azure authentication
- `azure-ai-ml==1.26.0` - Azure ML services
- `azure-search==1.0.0b2` - Azure Search (beta)
- `azure-search-documents==11.5.2` - Search documents
- `azure-ai-inference==1.0.0b9` - AI inference (beta)
- `adlfs==2024.12.0` - Azure Data Lake filesystem

**LLM & AI:**
- `openai==1.69.0` - OpenAI/Azure OpenAI client
- `langchain==0.3.22` - LLM framework
- `cohere==5.15.0` - Cohere embeddings

**Vector Database:**
- `chromadb==0.6.3` - Vector database

**File Processing:**
- `pymupdf==1.25.5` - PDF processing
- `openpyxl==3.1.2` - Excel file handling
- `pydub==0.25.1` - Audio processing
- `bs4==0.0.1` - HTML parsing

**Utilities:**
- `dotenv==0.9.9` - Environment variable management
- `colorlog==6.9.0` - Colored logging
- `portalocker==3.1.1` - File locking
- `weave==0.51.39` - ML observability
- `notebook==7.3.3` - Jupyter notebook support (dev only)

### Environment Variables

**Azure Configuration:**
- `AZURE_STORAGE_ACCOUNT_NAME` - Blob storage account
- `AZURE_CONTAINER_NAME` - Storage container name
- `AZURE_CLIENT_ID` - Service principal client ID
- `AZURE_CLIENT_SECRET` - Service principal secret
- `AZURE_TENANT_ID` - Azure tenant ID
- `AZURE_LLM_DEPLOYMENT_URL` - OpenAI endpoint URL
- `AZURE_LLM_DEPLOYMENT_KEY` - OpenAI API key
- `AZURE_OPENAI_API_VERSION` - API version (e.g., "2024-02-15-preview")
- `AZURE_OPENAI_DEPLOYMENT_NAME` - Deployment name
- `AZURE_EMBEDDING_DEPLOYMENT_URL` - Embedding service URL
- `AZURE_EMBEDDING_MODEL` - Embedding model name
- `AZURE_EMBEDDING_DEPLOYMENT_KEY` - Embedding API key
- `AZURE_SEARCH_ENDPOINT` - Azure Search endpoint
- `AZURE_SEARCH_API_KEY` - Search API key
- `AZURE_SEARCH_INDEX_NAME` - Search index name
- `AZURE_SEARCH_EMBEDDING_DIMS` - Embedding dimensions

**Application Configuration:**
- `APPLICATION_VERSION` - Application version string
- `PRODUCTION` - Boolean flag for production mode
- `TEMP_FILES_DIR` - Directory for temporary files
- `JWT_ENCRYPTION_SECRET_FILE` - Path to JWT secret file
- `ENV_TEST_API_KEY` - Test API key for development

**OAuth Configuration:**
- `GOOGLE_OAUTH_CLIENT_FILE` - Path to Google OAuth credentials JSON

**Third-Party Services:**
- `COHERE_EMBEDDING_KEY` - Cohere API key
- `DEPLOYMENT_URL` - General deployment URL

### System Requirements

- **Python:** 3.10+ (tested with 3.10)
- **Operating System:** Windows, Linux, macOS
- **Memory:** Minimum 4GB RAM (8GB+ recommended)
- **Storage:** Sufficient space for temporary files and ChromaDB
- **Network:** Internet connection for Azure services

---

## Data Flow

### 1. Rubric Refinement Flow

```
Instructor Request
    │
    ▼
POST /api/v1/rubric/audit_and_refine
    │
    ▼
RubricRefinementService.critique_rubric()
    │
    ▼
LLMService.generate_structured_response()
    │
    ▼
Azure OpenAI API
    │
    ▼
RubricCritique (structured response)
    │
    ▼
RubricRefinementService.refine_rubric()
    │
    ▼
LLMService.generate_structured_response()
    │
    ▼
Azure OpenAI API
    │
    ▼
Improved Rubric
    │
    ▼
AzureBlobService.save_rubric()
    │
    ▼
Azure Blob Storage
```

### 2. Student Response Grading Flow

```
Student Response Submission
    │
    ▼
POST /api/v1/response
    │
    ▼
AzureBlobService.save_student_response()
    │
    ▼
Azure Blob Storage
    │
    ▼
BackgroundMaterialProcessor (async)
    │
    ▼
Process grading request
    │
    ▼
Load Rubric from Azure Blob
    │
    ▼
Build grading prompt
    │
    ▼
LLMService.generate_structured_response()
    │
    ▼
Azure OpenAI API
    │
    ▼
Grade (structured response)
    │
    ▼
AzureBlobService.save_grade()
    │
    ▼
Azure Blob Storage
```

### 3. Batch Grading Pipeline Flow

```
CSV File Input
    │
    ▼
main.py --quiz-id <quiz_id>
    │
    ▼
refine_rubric() [if needed]
    │
    ▼
load_refined_rubric()
    │
    ▼
load_student_answers() [CSV parsing]
    │
    ▼
For each student:
    │
    ├─► grade_student_answer()
    │   │
    │   ├─► Build system prompt
    │   │
    │   ├─► Azure OpenAI API call
    │   │
    │   └─► Extract JSON response
    │
    ▼
save_grades_to_csv()
    │
    ▼
Output CSV with grades
```

### 4. Course Material Processing Flow

```
File Upload
    │
    ▼
POST /api/v1/course_material
    │
    ▼
Save to temp directory
    │
    ▼
BackgroundMaterialProcessor (async)
    │
    ▼
Detect file type
    │
    ├─► PDF → Extract text
    ├─► Image → Vision API
    ├─► Audio → Speech API
    └─► Video → Extract frames + audio
    │
    ▼
Generate embeddings (Cohere)
    │
    ▼
Store in ChromaDB
    │
    ▼
Save metadata to Azure Blob
```

### 5. Authentication Flow

```
User Login Request
    │
    ▼
GET /api/v1/auth/google_oauth
    │
    ▼
Redirect to Google OAuth
    │
    ▼
User authenticates
    │
    ▼
POST /api/v1/auth/google_oauth (callback)
    │
    ▼
Exchange code for token
    │
    ▼
Get user info from Google
    │
    ▼
Create/update User in Azure Blob
    │
    ▼
Generate JWT token
    │
    ▼
Return token to frontend
```

---

## Assumptions

### Technical Assumptions

1. **Azure Services Availability:**
   - Azure OpenAI endpoints are accessible and properly configured
   - Azure Blob Storage has sufficient capacity
   - Network connectivity to Azure services is stable

2. **Data Format Assumptions:**
   - Rubric files follow expected text format structure
   - CSV files contain required columns (flexible naming supported)
   - Student identifiers are unique within a course/assignment

3. **LLM Behavior:**
   - LLM responses follow expected JSON schema
   - LLM can parse rubric text files accurately
   - LLM grading is consistent with human grading (93% target)

4. **File System:**
   - Temporary directory is writable
   - Sufficient disk space for processing
   - File permissions allow read/write operations

5. **Python Environment:**
   - Python 3.10+ is available
   - All dependencies can be installed
   - Virtual environment is properly activated

### Business Assumptions

1. **Grading Context:**
   - Quizzes are NOT submitted late (no administrative penalties)
   - Partial credit is appropriate and expected
   - Conceptual understanding is prioritized over writing quality

2. **User Behavior:**
   - Instructors have valid Azure/Google credentials
   - Users follow expected workflow patterns
   - CSV files are properly formatted

3. **Data Integrity:**
   - Rubrics are complete and well-structured
   - Student answers are in expected format
   - Course/assignment metadata is accurate

### Security Assumptions

1. **Authentication:**
   - JWT tokens are properly secured
   - OAuth credentials are valid and not compromised
   - API keys are stored securely in environment variables

2. **Authorization:**
   - Users only access courses they're authorized for
   - Token validation is performed on every request
   - File access is restricted to authorized users

---

## Edge Cases & Error Handling

### 1. LLM API Failures

**Scenario:** Azure OpenAI API is unavailable or returns errors

**Handling:**
- Retry logic with exponential backoff (planned improvement)
- Graceful degradation: log error and continue with other students
- Return partial results if some grades succeed
- Clear error messages in logs

**Code Location:** `app/utils/llm_service.py`, `ai-baseline/app/main.py`

### 2. Invalid LLM Responses

**Scenario:** LLM returns malformed JSON or unexpected format

**Handling:**
- Multiple JSON extraction strategies:
  - Direct JSON parsing
  - Markdown code block extraction
  - Pattern-based JSON extraction
- Fallback to empty grade if extraction fails
- Log warning with response preview

**Code Location:** `ai-baseline/app/main.py::_extract_json_from_response()`

### 3. Missing or Invalid CSV Columns

**Scenario:** CSV file has unexpected column names or missing data

**Handling:**
- Automatic column name detection (multiple variations)
- Fallback to first column if standard names not found
- Skip rows with missing required data
- Log which columns are detected
- Clear error messages listing available columns

**Code Location:** `ai-baseline/app/main.py::load_student_answers()`

### 4. File Not Found Errors

**Scenario:** Required files (rubric, CSV) don't exist

**Handling:**
- Check multiple possible paths (refined vs original rubric)
- Clear error messages with searched paths
- FileNotFoundError with helpful context
- Graceful failure with informative logging

**Code Location:** `ai-baseline/app/main.py::load_refined_rubric()`, `load_student_answers()`

### 5. Azure Blob Storage Failures

**Scenario:** Azure Blob operations fail (network, permissions, quota)

**Handling:**
- Exception handling in service methods
- HTTP 502 errors for external service failures
- Retry logic in Azure SDK (automatic)
- Logging of all failures

**Code Location:** `app/services/azure_blob_service.py`

### 6. Authentication/Authorization Failures

**Scenario:** Invalid tokens, expired sessions, unauthorized access

**Handling:**
- JWT validation on every request
- HTTP 401 for authentication failures
- HTTP 403 for authorization failures
- Token expiration checking
- Clear error messages

**Code Location:** `app/utils/jwt_service.py`, `app/routes/*.py`

### 7. Concurrent File Processing

**Scenario:** Multiple background processes accessing same files

**Handling:**
- File locking with portalocker
- UUID-based file naming to prevent conflicts
- Thread-safe operations
- Background processor scans with delays

**Code Location:** `app/services/bg_material_processor.py`

### 8. Large File Processing

**Scenario:** Very large PDFs, videos, or course materials

**Handling:**
- Streaming file uploads
- Chunked processing for large files
- Memory-efficient operations
- Timeout handling

**Code Location:** `app/services/azure_blob_service.py`, `app/routes/course_material.py`

### 9. Python Version Compatibility

**Scenario:** Running on Python < 3.10 or > 3.11

**Handling:**
- `timezone.utc` instead of `datetime.UTC` (Python 3.10 compatibility)
- Type hints compatible with Python 3.10
- Fallback imports for different Python versions

**Code Location:** `app/services/azure_blob_service.py` (UTC fix)

### 10. Empty or Invalid Student Responses

**Scenario:** Student answer is empty, too short, or malformed

**Handling:**
- Validation in CSV loading (skip empty answers)
- Minimum length checks
- Graceful handling in grading (may result in low score)
- Logging of skipped responses

**Code Location:** `ai-baseline/app/main.py::load_student_answers()`

---

## Deployment Notes

### Development Deployment

**Local Setup:**
1. Clone repository
2. Create virtual environment: `python -m venv venv`
3. Activate virtual environment
4. Install dependencies: `pip install -r app/requirements.txt`
5. Configure `.env` file with all required variables
6. Generate JWT secret: `python generate_jwt_secret.py`
7. Start server: `uvicorn app.main:app --reload --port 8000`

**Environment Variables Required:**
- All Azure service credentials
- OAuth client configuration
- JWT secret file path
- Temporary directory path

### Production Deployment

**Recommended Setup:**
1. Use production-grade ASGI server (Uvicorn with multiple workers)
2. Configure reverse proxy (nginx, Apache)
3. Enable HTTPS/TLS
4. Set up monitoring and logging
5. Configure auto-scaling if needed
6. Use managed Azure services

**Production Command:**
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

**Security Considerations:**
- Store secrets in Azure Key Vault or secure environment
- Enable CORS only for trusted domains
- Use production-grade JWT secrets
- Enable rate limiting
- Monitor for suspicious activity
- Regular security updates

### Azure Deployment

**Recommended Services:**
- **Azure App Service** or **Azure Container Instances** for API
- **Azure Blob Storage** for persistent data
- **Azure OpenAI** for LLM services
- **Azure Key Vault** for secrets management
- **Application Insights** for monitoring

**Configuration:**
- Set `PRODUCTION=true` in environment
- Configure managed identity for Azure services
- Set up proper networking and firewall rules
- Enable backup and disaster recovery

### Docker Deployment (Future)

**Potential Dockerfile Structure:**
```dockerfile
FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app/ ./app/
COPY ai-baseline/ ./ai-baseline/
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Database Considerations

**Current State:**
- No traditional database (uses Azure Blob Storage as document store)
- ChromaDB for vector storage (local or can be containerized)
- File-based storage for temporary processing

**Future Considerations:**
- Consider migrating to Azure Cosmos DB for better querying
- Use managed ChromaDB service if available
- Implement database connection pooling if needed

---

## Improvement Opportunities

### High Priority

1. **Retry Logic for API Failures**
   - Implement exponential backoff for Azure OpenAI calls
   - Add circuit breaker pattern
   - **Impact:** Improved reliability and resilience
   - **Effort:** Medium

2. **Progress Tracking for Batch Operations**
   - Add progress bars for long-running grading operations
   - WebSocket support for real-time updates
   - **Impact:** Better user experience
   - **Effort:** Medium-High

3. **Batch Processing Optimization**
   - Process multiple students in parallel
   - Implement queue system for grading requests
   - **Impact:** Faster grading, better scalability
   - **Effort:** High

4. **Enhanced Error Recovery**
   - Resume interrupted batch operations
   - Checkpoint system for long-running tasks
   - **Impact:** Reduced rework, better reliability
   - **Effort:** Medium

5. **Comprehensive Testing**
   - Unit tests for all services
   - Integration tests for API endpoints
   - End-to-end tests for grading pipeline
   - **Impact:** Higher code quality, fewer bugs
   - **Effort:** High

### Medium Priority

6. **Caching Layer**
   - Cache rubric refinements
   - Cache frequently accessed course materials
   - **Impact:** Reduced API calls, lower costs
   - **Effort:** Medium

7. **Custom Grading Prompts**
   - Per-quiz customizable prompts
   - Template system for prompts
   - **Impact:** More flexibility for instructors
   - **Effort:** Low-Medium

8. **Analytics and Reporting**
   - Grading statistics dashboard
   - Performance metrics
   - Cost tracking
   - **Impact:** Better insights, cost optimization
   - **Effort:** Medium

9. **Multi-Quiz Batch Processing**
   - Process multiple quizzes in single run
   - Parallel quiz processing
   - **Impact:** Improved efficiency
   - **Effort:** Medium

10. **Enhanced CSV Support**
    - Support for more CSV formats
    - Excel file import
    - **Impact:** Easier data import
    - **Effort:** Low

### Low Priority / Future Enhancements

11. **Real-time Collaboration**
    - Multiple instructors working simultaneously
    - Live rubric editing
    - **Impact:** Better collaboration
    - **Effort:** High

12. **Advanced RAG Features**
    - Better context retrieval
    - Multi-document reasoning
    - **Impact:** More accurate grading
    - **Effort:** High

13. **Mobile Support**
    - Responsive frontend improvements
    - Mobile app (future)
    - **Impact:** Better accessibility
    - **Effort:** High

14. **Internationalization**
    - Multi-language support
    - Localized error messages
    - **Impact:** Broader usability
    - **Effort:** Medium-High

15. **Advanced Analytics**
    - Student performance trends
    - Rubric effectiveness analysis
    - **Impact:** Data-driven improvements
    - **Effort:** Medium-High

### Technical Debt

1. **Code Organization:**
   - Some duplicate code between `app/` and `ai-baseline/app/`
   - Consider consolidating shared utilities
   - **Effort:** Medium

2. **Documentation:**
   - More inline code documentation
   - API documentation improvements
   - Architecture diagrams
   - **Effort:** Low-Medium

3. **Dependency Management:**
   - Some beta/experimental packages (azure-search, azure-ai-inference)
   - Consider stable alternatives when available
   - **Effort:** Low

4. **Error Messages:**
   - More user-friendly error messages
   - Better error context in responses
   - **Effort:** Low

---

## Context & Background

### Project Origin

The BU MET Autograder was developed as part of a **Boston University SPARK project** for the **Metropolitan College Office of Education Technology and Innovation (MET ETI)**. The project aims to automate and improve the grading process for CS 581 quizzes and assignments.

### Problem Statement

**Manual Grading Challenges:**
- Time-consuming for instructors
- Inconsistent grading across multiple graders
- Difficulty maintaining fairness and objectivity
- High workload during peak grading periods

**Solution Goals:**
- Achieve 93%+ consistency with human grading
- Reduce instructor workload
- Maintain fairness and objectivity
- Support various question types and formats

### Current State

**Achievements:**
- ✅ Functional API for course/assignment management
- ✅ AI-powered rubric refinement
- ✅ Automated grading pipeline
- ✅ Flexible CSV processing
- ✅ Azure cloud integration
- ✅ Frontend interface (Next.js)

**Limitations:**
- Batch processing is sequential (not parallel)
- Limited retry logic for API failures
- No progress tracking for long operations
- Some hardcoded assumptions about grading context

### Use Cases

1. **Instructor Workflow:**
   - Create course and assignments
   - Upload rubrics or generate AI rubrics
   - Refine rubrics using AI critique
   - Upload student responses
   - Grade responses automatically
   - Review and adjust grades as needed

2. **Batch Grading:**
   - Export student responses to CSV
   - Run grading pipeline: `python main.py --quiz-id quiz_1`
   - Review graded results in CSV
   - Import grades back to system

3. **Rubric Improvement:**
   - Upload initial rubric
   - Run iterative refinement
   - Review critique and improvements
   - Use refined rubric for grading

### Integration Points

**External Systems:**
- **Blackboard** (future): Direct integration for grade import/export
- **Azure Services**: Blob Storage, OpenAI, Search
- **Google OAuth**: User authentication
- **Cohere API**: Embedding generation

**Internal Systems:**
- Frontend (Next.js) communicates via REST API
- Background processors handle async tasks
- Vector database for RAG capabilities

### Performance Characteristics

**Grading Speed:**
- ~1-3 seconds per student answer (depends on LLM response time)
- Batch of 100 students: ~2-5 minutes
- Rubric refinement: ~30-60 seconds per iteration

**Scalability:**
- API can handle multiple concurrent requests
- Background processing handles file operations
- Azure Blob Storage scales automatically
- LLM API rate limits may be bottleneck

**Cost Considerations:**
- Azure OpenAI API costs per token
- Blob Storage costs per GB
- Embedding generation costs
- Optimization opportunities in caching and batching

### Success Metrics

**Target Metrics:**
- 93%+ grading consistency with human graders
- <5% error rate in grading operations
- <3 second average response time for API calls
- 99%+ uptime for production deployment

**Current Performance:**
- Grading consistency: ~90-95% (varies by assignment)
- Error rate: <2% (mostly API timeouts)
- API response time: ~1-2 seconds average
- Uptime: Not yet measured in production

---

## Appendix

### File Structure Reference

```
ml-bu-autograder/
├── app/                          # Main API application
│   ├── main.py                   # FastAPI application entry
│   ├── models/                   # Pydantic data models
│   ├── routes/                   # API route handlers
│   ├── services/                 # Business logic services
│   └── utils/                    # Utility functions
├── ai-baseline/
│   ├── app/                      # Grading pipeline application
│   │   ├── main.py              # Pipeline entry point
│   │   ├── core/                # Core grading logic
│   │   ├── services/            # Service initialization
│   │   └── utils/               # Pipeline utilities
│   └── data/                     # Quiz data and rubrics
├── frontend/                     # Next.js frontend
├── design/                       # Design documents
└── README.md                     # Project overview
```

### Key Configuration Files

- `app/requirements.txt` - Python dependencies
- `.env` - Environment variables (not in repo)
- `jwt_secret.json` - JWT encryption keys
- `generate_jwt_secret.py` - JWT secret generator

### Contact & Support

For questions, issues, or contributions:
- **Project Repository:** [GitHub URL]
- **Team Members:** See README.md
- **Documentation:** See `ai-baseline/app/README.md`

---

**Document Version:** 1.0  
**Last Updated:** 2025-01-01  
**Maintained By:** BU MET Autograder Development Team

