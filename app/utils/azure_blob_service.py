import base64
import json
import logging
import mimetypes
from typing import List, Dict, Optional, Set

import fsspec
# <<< --- ADDED IMPORT for azure.core.exceptions --- >>>
from azure.core.exceptions import ResourceNotFoundError
from azure.identity import ChainedTokenCredential
from pydantic import EmailStr, FilePath

from app.models import Course, Assignment, Question, StudentResponse, Rubric, CourseMaterial, User, PersonalAccessToken, \
    SubRubric, Grade # Keep SubRubric import for type hinting if needed elsewhere
from app.models.student_response import GradedStudentResponse

azure_blob_uploader: Optional["AzureBlobService"] = None

logger = logging.getLogger(__name__)


class AzureBlobService:
    def __init__(self,
                 credential: ChainedTokenCredential,
                 storage_account_name: str,
                 container_name: str,
                 azure_blob_cache_dir: FilePath,
                 cache_expiry: int = 3600,
                 ):
        """
        Initializes Azure Blob Storage service with configurable caching.

        Args:
            credential: Azure credential (account key, SAS token).
            storage_account_name: Azure storage account name.
            container_name: Target container name.
            azure_blob_cache_dir: Local cache directory.
            cache_expiry: Cache TTL in seconds (default: 1 hour).
        """
        azure_fs_options = {
            "account_name": storage_account_name,
            "credential": credential,
        }
        azure_blob_cache_dir.mkdir(parents=True, exist_ok=True)
        # <<< --- STORE container_name --- >>>
        self.container_name = container_name # Store for use in list_files
        # --- END CHANGE ---
        self.fs = fsspec.filesystem(
            "filecache",
            target_protocol="abfs",
            target_options=azure_fs_options,
            cache_storage=str(azure_blob_cache_dir),
            expiry_time=cache_expiry
        )
        # Deprecated: use self.container_name
        # self.container = container_name
        logging.debug(f"Initialized AzureBlobService for container {self.container_name}") # Use self.container_name

    def _full_path(self, blob_path: str) -> str:
        """Constructs full blob path by prepending container name."""
        # Ensure no leading/trailing slashes issues
        clean_container = self.container_name.strip('/')
        clean_blob_path = blob_path.strip('/')
        return f"{clean_container}/{clean_blob_path}"

    # --- upload_base64_file (no changes needed) ---
    def upload_base64_file(self, base64_data, blob_path, metadata=None):
        logging.debug(f"Starting upload of base64 file to {blob_path}")
        file_data = base64.b64decode(base64_data)
        logging.debug(f"Decoded {len(file_data)} bytes for {blob_path}")
        content_type = self._guess_content_type(blob_path)
        full_path = self._full_path(blob_path)

        with self.fs.open(full_path, 'wb',
                          content_settings={"content_type": content_type},
                          metadata=metadata) as f:
            f.write(file_data)
        logging.debug(f"Uploaded {len(file_data)} bytes to {blob_path}")

    # --- upload_json (no changes needed) ---
    def upload_json(self, data, blob_path, exclude: Set[str] = None, metadata: Dict[str, str] = None):
        logging.debug(f"Serializing JSON data for {blob_path}")
        # Use model_dump_json which is the newer method in Pydantic v2
        json_data = data.model_dump_json(indent=4, exclude=exclude)
        full_path = self._full_path(blob_path)

        logging.debug(f"Uploading JSON to {blob_path}")
        with self.fs.open(full_path, 'w',
                          content_settings={"content_type": "application/json"},
                          metadata=metadata) as f:
            f.write(json_data)
        logging.info(f"Uploaded JSON to {blob_path}")

    # --- download_file (no changes needed) ---
    def download_file(self, blob_path, local_file_path):
        logging.debug(f"Starting download of {blob_path} to {local_file_path}")
        full_path = self._full_path(blob_path)
        try: # Add try block
            with self.fs.open(full_path, 'rb') as remote_file, open(local_file_path, "wb") as local_file:
                local_file.write(remote_file.read())
            logging.info(f"Downloaded {blob_path} to {local_file_path}")
        except FileNotFoundError: # Catch specific error
            logging.warning(f"Download failed: Blob not found at {full_path}")
            raise # Re-raise if needed, or handle differently

    # --- download_json (Improved Error Handling) ---
    def download_json(self, blob_path) -> Optional[dict]:
        logging.debug(f"Attempting to download JSON from relative path: {blob_path}")
        full_path = self._full_path(blob_path)
        logging.debug(f"Full storage path for download: {full_path}")
        try:
            with self.fs.open(full_path, 'r') as f:
                content = f.read() # Read content first
                # Check for empty content which json.load would fail on
                if not content:
                    logging.warning(f"Downloaded file from {full_path} is empty.")
                    return None
                data = json.loads(content) # Use json.loads
            logging.debug(f"Successfully parsed JSON from {full_path}")
            return data
        except json.JSONDecodeError as e:
            logging.error(f"Invalid JSON content in {full_path}: {e}", exc_info=True) # Log full error
            return None
        # <<< --- CATCH ResourceNotFoundError for fsspec/abfs --- >>>
        except FileNotFoundError:
             logging.warning(f"JSON download failed: Blob not found at {full_path} (FileNotFoundError)")
             return None
        # Catch Azure specific error if directly using SDK or if fsspec raises it
        except ResourceNotFoundError:
            logging.warning(f"JSON download failed: Blob not found at {full_path} (ResourceNotFoundError)")
            return None
        except Exception as e: # Catch other potential errors (permissions, network, etc.)
            logging.error(f"Unexpected error downloading JSON from {full_path}: {e}", exc_info=True)
            return None

    # --- get_user (Improved Logging/Validation) ---
    def get_user(self, user_email: EmailStr) -> Optional[User]:
        """Retrieves user data if exists."""
        blob_path = f"user/{user_email}/user.json"
        logging.info(f"Attempting to retrieve user data for '{user_email}' from '{blob_path}'")
        data = self.download_json(blob_path) # Relies on improved download_json logging
        if data:
            logging.info(f"User data found for '{user_email}'. Validating model...")
            try:
                # Use model_validate for Pydantic v2
                user_obj = User.model_validate(data)
                logging.info(f"Successfully validated and created User object for '{user_email}'.")
                return user_obj
            except Exception as e: # Catch potential Pydantic validation errors
                 logging.error(f"Failed to validate User data for '{user_email}' from '{blob_path}': {e}", exc_info=True)
                 return None # Return None if data is invalid
        else:
            # download_json already logged the specific reason (NotFound or InvalidJSON)
            logging.warning(f"User data retrieval failed for '{user_email}' (file not found, empty, or invalid JSON).")
            return None

    # --- delete_blob (no changes needed) ---
    def delete_blob(self, blob_path: str):
        logging.debug(f"Attempting to delete blob: {blob_path}")
        full_path = self._full_path(blob_path)
        try: # Add try-except
            self.fs.rm(full_path)
            logging.info(f"Deleted blob: {blob_path}")
        except FileNotFoundError:
             logging.warning(f"Delete failed: Blob not found at {full_path}")
        except Exception as e:
             logging.error(f"Error deleting blob {full_path}: {e}", exc_info=True)
             raise # Re-raise unexpected errors

    # --- move_blob (no changes needed) ---
    def move_blob(self, old_blob_path: str, new_blob_path: str):
        full_old_path = self._full_path(old_blob_path)
        full_new_path = self._full_path(new_blob_path)
        logging.debug(f"Attempting to move blob from {old_blob_path} to {new_blob_path}")
        if not self.fs.exists(full_old_path):
            logging.warning(f"Source blob does not exist, cannot move: {old_blob_path}")
            return
        try:
            self.fs.mv(full_old_path, full_new_path) # Use mv if available and atomic
            logging.info(f"Moved blob from {old_blob_path} to {new_blob_path}")
        except Exception as e:
             logging.warning(f"fs.mv failed for {old_blob_path}, falling back to copy/delete: {e}")
             # Fallback to copy and delete if mv fails or is not available
             try:
                with self.fs.open(full_old_path, 'rb') as src:
                    with self.fs.open(full_new_path, 'wb') as dst:
                        dst.write(src.read())
                self.fs.rm(full_old_path)
                logging.info(f"Moved blob (copy/delete) from {old_blob_path} to {new_blob_path}")
             except Exception as fallback_e:
                 logging.error(f"Fallback copy/delete failed when moving {old_blob_path} to {new_blob_path}: {fallback_e}", exc_info=True)
                 raise # Re-raise critical failure

    # --- list_files (Improved handling) ---
    def list_files(self, prefix: str = "") -> List[str]:
        search_path = self._full_path(prefix)
        logger.debug(f"Attempting to list files/blobs at storage path: {search_path}")
        files = []
        try:
            raw_paths = self.fs.ls(search_path, detail=False)
            logger.debug(f"Raw list result for {search_path}: {raw_paths}")
            if isinstance(raw_paths, list):
                # Process paths to make them relative to container
                container_prefix = f"{self.container_name}/"
                for full_path in raw_paths:
                    if isinstance(full_path, str) and full_path.startswith(container_prefix):
                        # Remove container name and leading slash
                        relative_path = full_path[len(container_prefix):]
                        files.append(relative_path)
                    else:
                        logging.warning(f"Unexpected item format in listing for {search_path}: {full_path}")
            else:
                 logging.warning(f"Listing for {search_path} did not return a list: {type(raw_paths)}")
        except FileNotFoundError:
            logger.warning(f"Path not found during listing, returning empty list for prefix: '{prefix}' (search path: {search_path})")
            files = [] # Return empty list if prefix doesn't exist
        except Exception as e:
            logger.exception(f"Unexpected error listing files with prefix '{prefix}' (search path: {search_path}): {e}")
            raise HTTPException(status_code=500, detail=f"Server error accessing storage.") from e # Use FastAPI's HTTPException

        logging.debug(f"list_files returning {len(files)} paths for prefix '{prefix}'")
        return files

    # --- upload_user (no changes) ---
    def upload_user(self, user: User):
        blob_path = f"user/{user.user_email}/user.json"
        logging.debug(f"Uploading user {user.user_email}")
        self.upload_json(user, blob_path)

    # --- upload_token (no changes) ---
    def upload_token(self, user_email: EmailStr, token: PersonalAccessToken):
        blob_path = f"user/{user_email}/tokens/{token.token_name}.json"
        logging.debug(f"Uploading token {token.token_name} for user {user_email}")
        self.upload_json(token, blob_path)

    # --- upload_course_metadata (no changes) ---
    def upload_course_metadata(self, course: Course):
        blob_path = f"course/{course.semester}/{course.course_id}/course.json"
        logging.debug(f"Uploading metadata for course {course.course_id}")
        self.upload_json(course, blob_path)

    # --- upload_assignment_metadata (no changes) ---
    def upload_assignment_metadata(self, assignment: Assignment):
        blob_path = f"course/{assignment.semester}/{assignment.course_id}/assignment/{assignment.assignment_id}/assignment.json"
        logging.debug(f"Uploading metadata for assignment {assignment.assignment_id}")
        self.upload_json(assignment, blob_path, exclude={"questions"})

    # --- upload_question_metadata (no changes) ---
    def upload_question_metadata(self, semester_key: str, course_id: str, assignment_id: str, question_index: int, question: Question):
        blob_path = f"course/{semester_key}/{course_id}/assignment/{assignment_id}/{question_index}/question.json"
        logging.debug(f"Uploading question {question_index} for assignment {assignment_id}")
        self.upload_json(question, blob_path)

    # --- upload_student_response (no changes) ---
    def upload_student_response(self, student_response: StudentResponse):
        blob_path = (
            f"course/{student_response.semester}/"
            f"{student_response.course_id}/"
            f"assignment/"
            f"{student_response.assignment_id}/"
            f"{student_response.question_index}/"
            f"student_response/"
            f"{student_response.student_id}/"
            f"response.{student_response.data.data_type}"
        )
        logging.debug(f"Uploading response from student {student_response.student_id}")
        self.upload_base64_file(
            student_response.data.content,
            blob_path,
            student_response.data.metadata
        )

    # --- upload_student_grade (no changes) ---
    def upload_student_grade(self, graded_student_response: GradedStudentResponse):
        blob_path = (
            f"course/{graded_student_response.semester}/"
            f"{graded_student_response.course_id}/"
            f"assignment/"
            f"{graded_student_response.assignment_id}/"
            f"{graded_student_response.question_index}/"
            f"student_response/"
            f"{graded_student_response.student_id}/"
            f"grade.json"
        )
        logging.debug(f"Fetching grades for student {graded_student_response.student_id}")
        self.upload_json(graded_student_response.grade, blob_path)

    # === MODIFIED upload_rubric ===
    def upload_rubric(self, semester_key: str, course_id: str, assignment_id: str, rubric: Rubric):
        """Uploads the entire rubric object to a single file."""
        # Define the path for the single rubric file
        blob_path = f"course/{semester_key}/{course_id}/assignment/{assignment_id}/rubric.json"
        logging.info(f"Uploading entire rubric (including sub-rubrics) for assignment {assignment_id} to {blob_path}")

        # Upload the complete rubric object, do NOT exclude sub_rubrics
        self.upload_json(rubric, blob_path) # Removed exclude={"sub_rubrics"}

        # The loop saving individual sub-rubrics is now removed.
        # Optional: Consider deleting old individual sub-rubric files if they exist
        # self.delete_old_sub_rubric_files(semester_key, course_id, assignment_id) # Example helper

    # === REMOVED upload_sub_rubric ===
    # def upload_sub_rubric(self, semester_key: str, course_id: str, assignment_id: str, sub_rubric: SubRubric):
    #     """Uploads individual sub-rubric. (REMOVED - Now part of upload_rubric)"""
    #     # blob_path = f"course/{semester_key}/{course_id}/assignment/{assignment_id}/rubrics/{sub_rubric.question_index}.json"
    #     # logging.debug(f"Uploading sub-rubric for question {sub_rubric.question_index}")
    #     # self.upload_json(sub_rubric, blob_path)
    #     pass # No longer used directly

    # --- get_course (no changes) ---
    def get_course(self, semester_key: str, course_id: str) -> Optional[Course]:
        blob_path = f"course/{semester_key}/{course_id}/course.json"
        logging.debug(f"Fetching course {course_id}")
        data = self.download_json(blob_path)
        # Use model_validate for Pydantic v2
        return Course.model_validate(data) if data else None

    # --- get_assignment_metadata (no changes) ---
    def get_assignment_metadata(self, semester_key: str, course_id: str, assignment_id: str) -> Optional[Assignment]:
        blob_path = f"course/{semester_key}/{course_id}/assignment/{assignment_id}/assignment.json"
        logging.debug(f"Fetching assignment {assignment_id}")
        data = self.download_json(blob_path)
        # Use model_validate for Pydantic v2
        return Assignment.model_validate(data) if data else None

    # --- upload_course_material (no changes) ---
    def upload_course_material(self, material: CourseMaterial):
        blob_path = (
            f"course/"
            f"{material.semester}/"
            f"{material.course_id}/"
            f"course_material/"
            f"{material.material_id}.{material.data.data_type}" # Assuming ID includes extension logic
        )
        logging.debug(f"Uploading course material {material.material_id}")
        # Ensure material_id is just the base name if needed, or path construction is correct
        self.upload_base64_file(material.data.content, blob_path, material.data.metadata)


    # --- get_student_response (Model validation) ---
    def get_student_response(self, semester_key: str, course_id: str, assignment_id: str, question_index: int,
                             student_id: str, retrieve_grades=True) -> Optional[GradedStudentResponse]:
        # NOTE: Path assumes response metadata is stored in JSON. Adjust if needed.
        # This likely needs adjustment based on how responses are actually saved (upload_student_response saves raw data)
        # You might need to LIST blobs for the student response first to find the actual file name.
        blob_path = f"course/{semester_key}/{course_id}/assignment/{assignment_id}/{question_index}/student_response/{student_id}/response.json" # Example: Assumes JSON metadata
        logging.warning(f"Fetching student response metadata (assuming JSON at {blob_path}). Actual response data likely separate.")
        data = self.download_json(blob_path) # Fetch metadata
        if data is not None:
             try:
                # Validate the response metadata part
                student_response = GradedStudentResponse.model_validate(data) # Validate metadata
                # TODO: Separately fetch the actual response content (base64) using the path from metadata if needed
                if retrieve_grades:
                    grade = self.get_grading_details(semester_key, course_id, assignment_id, question_index, student_id)
                    student_response.grade = grade # Assign Grade object
                return student_response
             except Exception as e:
                 logging.error(f"Failed to validate GradedStudentResponse data from {blob_path}: {e}", exc_info=True)
                 return None
        return None


    # --- get_grading_details (Model validation) ---
    def get_grading_details(self, semester_key: str, course_id: str, assignment_id: str, question_index: int,
                            student_id: str) -> Optional[Grade]:
        """Retrieves grading details if exists."""
        blob_path = f"course/{semester_key}/{course_id}/assignment/{assignment_id}/{question_index}/student_response/{student_id}/grade.json"
        logging.debug(f"Fetching grades for student {student_id} from {blob_path}")
        data = self.download_json(blob_path)
        if data:
            try:
                # Validate using the Grade model directly
                return Grade.model_validate(data)
            except Exception as e:
                 logging.error(f"Failed to validate Grade data from {blob_path}: {e}", exc_info=True)
                 return None
        return None


    # === MODIFIED get_rubric ===
    def get_rubric(self, semester_key: str, course_id: str, assignment_id: str) -> Optional[Rubric]:
        """Retrieves the entire rubric from a single file."""
        # Define the path for the single rubric file
        blob_path = f"course/{semester_key}/{course_id}/assignment/{assignment_id}/rubric.json"
        logging.info(f"Attempting to fetch entire rubric for assignment {assignment_id} from single file: {blob_path}")

        data = self.download_json(blob_path) # download_json handles not found, empty, invalid JSON

        if data:
            try:
                # Validate the entire structure using the Rubric model
                rubric = Rubric.model_validate(data)
                logging.info(f"Successfully fetched and validated rubric from {blob_path}")
                return rubric
            except Exception as e:
                logging.error(f"Failed to validate Rubric data from {blob_path}: {e}", exc_info=True)
                return None # Return None if validation fails
        else:
            # download_json would have logged the reason (NotFound, empty, invalid)
            logging.warning(f"Failed to retrieve rubric data for {assignment_id} from {blob_path}.")
            return None

        # The logic fetching individual sub_rubrics is now removed.

    # === REMOVED get_sub_rubric ===
    # def get_sub_rubric(self, semester_key: str, course_id: str, assignment_id: str, question_index: int) -> Optional[SubRubric]:
    #     """Retrieves specific sub-rubric if exists. (REMOVED - Now part of get_rubric)"""
    #     # blob_path = f"course/{semester_key}/{course_id}/assignment/{assignment_id}/rubrics/{question_index}.json"
    #     # logging.debug(f"Fetching sub-rubric for question {question_index}")
    #     # data = self.download_json(blob_path)
    #     # return SubRubric(**data) if data else None
    #     pass # No longer used

    # --- get_course_material (Model validation) ---
    def get_course_material(self, semester_key: str, course_id: str, material_id: str) -> Optional[CourseMaterial]: # Assuming material_id is str like 'lecture1.pdf'
        """Retrieves course material if exists."""
         # Adjust path logic if material_id doesn't include extension
        blob_path = f"course/{semester_key}/{course_id}/course_material/{material_id}" # Example path
        logging.debug(f"Fetching course material {material_id} metadata (assuming JSON at {blob_path}.json)")
        # This likely needs adjustment - how is material metadata stored?
        # Assuming metadata is in a corresponding .json file
        metadata_path = blob_path + ".json" # Hypothetical metadata path
        data = self.download_json(metadata_path)
        if data:
            try:
                # TODO: Fetch the actual content separately if needed
                return CourseMaterial.model_validate(data)
            except Exception as e:
                logging.error(f"Failed to validate CourseMaterial data from {metadata_path}: {e}", exc_info=True)
                return None
        return None


    # --- get_default_user (no changes) ---
    def get_default_user(self) -> User:
        default_user: Optional[User] = self.get_user("admin@autograder.com") # Call self.get_user
        if default_user is None:
            logging.warning("Default admin user not found, creating one.")
            default_user: User = User(
                user_email="admin@autograder.com",
                first_name="Admin",
                last_name="",
                authenticated_courses=[],
                dark_mode=False,
            )
            self.upload_user(default_user) # Call self.upload_user
        return default_user

    # --- get_token (Model validation) ---
    def get_token(self, user_email: EmailStr, token_name: str) -> Optional[PersonalAccessToken]:
        blob_path = f"user/{user_email}/tokens/{token_name}.json"
        logging.debug(f"Fetching token {token_name} for user {user_email}")
        data = self.download_json(blob_path)
        if data:
             try:
                return PersonalAccessToken.model_validate(data)
             except Exception as e:
                logging.error(f"Failed to validate PersonalAccessToken data from {blob_path}: {e}", exc_info=True)
                return None
        return None

    # --- delete_student_response (Needs adjustment based on actual storage) ---
    def delete_student_response(self, semester: str, course_id: str, assignment_id: str, question_index: int, student_id: str):
        # This needs to know the actual file extension/name used in upload_student_response
        # Using glob to find the file is safer
        pattern = (
            f"course/{semester}/"
            f"{course_id}/"
            f"assignment/"
            f"{assignment_id}/"
            f"{question_index}/"
            f"student_response/"
            f"{student_id}/"
            f"response.*" # Glob pattern
        )
        logging.debug(f"Attempting to delete response file(s) for student {student_id} matching pattern {pattern}")
        full_pattern_path = self._full_path(pattern)
        files_to_delete = self.fs.glob(full_pattern_path)
        if not files_to_delete:
            logging.warning(f"No response files found to delete for student {student_id} with pattern {pattern}")
            return
        for file_path_with_container in files_to_delete:
             relative_path = file_path_with_container.split('/', 1)[1] # Make relative
             self.delete_blob(relative_path) # delete_blob handles logging and errors

    # --- delete_student_responses (no changes needed) ---
    def delete_student_responses(self, semester: str, course_id: str, assignment_id: str, student_id: str):
        pattern = (
            f"course/{semester}/"
            f"{course_id}/"
            f"assignment/"
            f"{assignment_id}/"
            f"*/" # Any question index
            f"student_response/"
            f"{student_id}/"
            f"response.*" # Any response file
        )
        logging.debug(f"Deleting all response files from student {student_id} in assignment {assignment_id}")
        full_pattern_path = self._full_path(pattern)
        files_deleted_count = 0
        for file_path_with_container in self.fs.glob(full_pattern_path):
            relative_path = file_path_with_container.split('/', 1)[1]
            self.delete_blob(relative_path) # delete_blob handles logging/errors
            files_deleted_count += 1
        logging.info(f"Deleted {files_deleted_count} response files for student {student_id} in assignment {assignment_id}")


    # --- list_personal_access_tokens (Model validation) ---
    def list_personal_access_tokens(self, user_email: EmailStr) -> List[PersonalAccessToken]:
        pattern = f"user/{user_email}/tokens/*.json"
        tokens = []
        logging.debug(f"Listing tokens for user {user_email}")
        full_pattern_path = self._full_path(pattern)

        for file_path_with_container in self.fs.glob(full_pattern_path):
            relative_path = file_path_with_container.split('/', 1)[1]
            data = self.download_json(relative_path)
            if data:
                try:
                    tokens.append(PersonalAccessToken.model_validate(data)) # Use model_validate
                except Exception as e:
                    logging.warning(f"Failed to parse token at {relative_path}: {e}")

        logging.debug(f"Found {len(tokens)} tokens for user {user_email}")
        return tokens

    # --- list_student_responses (Needs adjustment) ---
    def list_student_responses(self, semester: str, course_id: str, assignment_id: str,
                             question_index: Optional[int] = None) -> List[StudentResponse]:
        # This lists response METADATA assuming it's in JSON. Adjust if needed.
        if question_index is not None:
            pattern = f"course/{semester}/{course_id}/assignment/{assignment_id}/{question_index}/student_response/*/response.json" # Assumes JSON metadata
        else:
            pattern = f"course/{semester}/{course_id}/assignment/{assignment_id}/*/student_response/*/response.json" # Assumes JSON metadata

        responses = []
        logging.warning(f"Listing student response metadata (assuming JSON files matching {pattern}). Actual response data is separate.")
        full_pattern_path = self._full_path(pattern)

        for file_path_with_container in self.fs.glob(full_pattern_path):
            relative_path = file_path_with_container.split('/', 1)[1]
            data = self.download_json(relative_path)
            if data:
                 try:
                    responses.append(StudentResponse.model_validate(data)) # Validate metadata
                 except Exception as e:
                     logging.warning(f"Failed to validate StudentResponse data from {relative_path}: {e}")

        logging.debug(f"Found {len(responses)} student response metadata entries")
        return responses

    # --- delete_grading_details (no changes needed) ---
    def delete_grading_details(self, semester_key: str, course_id: str, assignment_id: str, question_index: int,
                               student_id: str):
        blob_path = f"course/{semester_key}/{course_id}/assignment/{assignment_id}/{question_index}/student_response/{student_id}/grade.json"
        logging.debug(f"Deleting grades for student {student_id}")
        self.delete_blob(blob_path)

    # --- delete_rubric (Updated path) ---
    def delete_rubric(self, semester_key: str, course_id: str, assignment_id: str):
        """Deletes the single assignment rubric file."""
        # Path now points to the single rubric file
        blob_path = f"course/{semester_key}/{course_id}/assignment/{assignment_id}/rubric.json"
        logging.info(f"Attempting to delete single rubric file for assignment {assignment_id} at {blob_path}")
        self.delete_blob(blob_path) # delete_blob handles not found

        # Optional: Clean up old individual sub-rubric files if they might exist from previous versions
        # self.delete_old_sub_rubric_files(semester_key, course_id, assignment_id)

    # --- delete_course (no changes) ---
    def delete_course(self, semester_key: str, course_id: str) -> int:
        prefix = f"course/{semester_key}/{course_id}/"
        full_path = self._full_path(prefix)
        logging.info(f"Starting recursive delete for course '{prefix}'")
        try:
            # Use recursive=True with rm
            self.fs.rm(full_path, recursive=True)
            logging.info(f"Completed recursive delete for course path {full_path}")
            # Note: fs.glob might be inefficient/slow for counting on large directories after deletion.
            # Counting before deletion might be better if needed, but rm doesn't typically return count.
            return -1 # Indicate success, but count isn't reliable post-delete this way
        except FileNotFoundError:
             logging.warning(f"Course path not found, nothing to delete: {full_path}")
             return 0
        except Exception as e:
             logging.error(f"Error during recursive delete of {full_path}: {e}", exc_info=True)
             raise # Re-raise unexpected errors

    # --- delete_course_material (Needs adjustment) ---
    def delete_course_material(self, semester_key: str, course_id: str, material_id: str): # Assuming ID includes extension
        """Deletes specific course material."""
        # Need to know the actual path used in upload_course_material
        blob_path = f"course/{semester_key}/{course_id}/course_material/{material_id}" # Example path
        logging.debug(f"Attempting to delete course material: {blob_path}")
        self.delete_blob(blob_path)
        # Also delete metadata if stored separately?
        # self.delete_blob(blob_path + ".json")


    # --- delete_question_metadata (no changes) ---
    def delete_question_metadata(self, semester_key: str, course_id: str, assignment_id: str, question_index: int):
        blob_path = f"course/{semester_key}/{course_id}/assignment/{assignment_id}/{question_index}/question.json"
        logging.debug(f"Deleting metadata for question {question_index}")
        self.delete_blob(blob_path)
        # TODO: Re-ordering logic might need review/adjustment depending on requirements
        # questions_cnt = self.count_questions(semester_key, course_id, assignment_id)
        # for question_idx in range(question_index + 1, questions_cnt + 1): # Adjust range if needed
        #     current_path = f"course/{semester_key}/{course_id}/assignment/{assignment_id}/{question_idx}/question.json"
        #     new_path = f"course/{semester_key}/{course_id}/assignment/{assignment_id}/{question_idx - 1}/question.json"
        #     self.move_blob(current_path, new_path)

    # --- delete_assignment (no changes) ---
    def delete_assignment(self, semester_key: str, course_id: str, assignment_id: str):
        assignment_prefix = f"course/{semester_key}/{course_id}/assignment/{assignment_id}"
        full_path = self._full_path(assignment_prefix)
        logging.info(f"Recursively deleting all blobs under {assignment_prefix}")
        try:
            self.fs.rm(full_path, recursive=True)
            logging.info(f"Completed recursive delete for assignment path {full_path}")
        except FileNotFoundError:
             logging.warning(f"Assignment path not found, nothing to delete: {full_path}")
        except Exception as e:
             logging.error(f"Error during recursive delete of assignment {full_path}: {e}", exc_info=True)
             raise

    # --- delete_user (no changes) ---
    def delete_user(self, user_email: EmailStr):
        user_prefix = f"user/{user_email}"
        full_path = self._full_path(user_prefix)
        logging.info(f"Recursively deleting all user data under {user_prefix}")
        try:
            self.fs.rm(full_path, recursive=True)
            logging.info(f"Completed recursive delete for user path {full_path}")
        except FileNotFoundError:
             logging.warning(f"User path not found, nothing to delete: {full_path}")
        except Exception as e:
             logging.error(f"Error during recursive delete of user {full_path}: {e}", exc_info=True)
             raise

    # --- delete_token (no changes) ---
    def delete_token(self, user_email: EmailStr, token_name: str):
        blob_path = f"user/{user_email}/tokens/{token_name}.json"
        logging.debug(f"Deleting token {token_name} for user {user_email}")
        self.delete_blob(blob_path)

    # --- reorder_questions (Needs review - might need to update indices within the SINGLE rubric.json now) ---
    def reorder_questions(self, semester_key: str, course_id: str, assignment_id: str, new_order: List[int]):
        """
        Reorders questions by updating their indexes within the assignment metadata
        and potentially within the single rubric file. Blob movement is no longer needed
        for the question metadata itself if it's part of assignment.json,
        but RUBRIC sub-rubrics might need reordering within rubric.json.
        """
        logging.warning(f"Reordering questions for assignment {assignment_id}: {new_order}. NOTE: This implementation might need adjustment for Option 1 rubric storage.")

        # 1. Update Assignment Metadata (if questions are stored there)
        assignment = self.get_assignment_metadata(semester_key, course_id, assignment_id)
        if assignment and hasattr(assignment, 'questions') and assignment.questions:
            # Create a map of old index to question object
            question_map = {q.question_index: q for q in assignment.questions}
            reordered_questions = []
            for new_index, old_index in enumerate(new_order):
                question = question_map.get(old_index)
                if question:
                    question.question_index = new_index # Update index
                    reordered_questions.append(question)
                else:
                     logging.warning(f"Question with old index {old_index} not found in assignment metadata during reorder.")
            assignment.questions = reordered_questions
            # Save the updated assignment metadata
            self.upload_assignment_metadata(assignment)
            logging.info(f"Updated question order in assignment metadata for {assignment_id}")
        else:
            logging.warning(f"Assignment metadata not found or no questions attribute for {assignment_id}, skipping metadata reorder.")


        # 2. Update Rubric (Reorder sub_rubrics within the single rubric.json)
        rubric = self.get_rubric(semester_key, course_id, assignment_id)
        if rubric and rubric.sub_rubrics:
             # Create a map of old index to sub-rubric object
             sub_rubric_map = {sr.question_index: sr for sr in rubric.sub_rubrics}
             reordered_sub_rubrics = []
             for new_index, old_index in enumerate(new_order):
                 sub_rubric = sub_rubric_map.get(old_index)
                 if sub_rubric:
                     sub_rubric.question_index = new_index # Update index
                     reordered_sub_rubrics.append(sub_rubric)
                 else:
                     logging.warning(f"Sub-rubric with old index {old_index} not found during reorder.")
             rubric.sub_rubrics = reordered_sub_rubrics
             # Save the updated rubric back to the single file
             self.upload_rubric(semester_key, course_id, assignment_id, rubric)
             logging.info(f"Updated sub-rubric order in rubric.json for {assignment_id}")
        else:
            logging.warning(f"Rubric not found or no sub-rubrics for {assignment_id}, skipping rubric reorder.")

        # Blob movement is no longer the primary mechanism for reordering questions metadata/rubrics
        logging.info(f"Completed reordering attempt for assignment {assignment_id}")


    # --- list_courses (Model validation) ---
    def list_courses(self, user: User, semester_key: Optional[str] = None) -> List[Course]:
        pattern = f"course/{semester_key}/*/course.json" if semester_key else "course/*/*/course.json"
        courses = []
        logging.info(f"User '{user.user_email}' listing courses (Semester: {semester_key}). Authenticated: {user.authenticated_courses}")
        full_pattern_path = self._full_path(pattern)
        logging.info(f"Using glob pattern: {full_pattern_path}")
        try:
            files_found = self.fs.glob(full_pattern_path)
            logging.info(f"Glob found {len(files_found)} potential course files.")
            for file_path_with_container in files_found:
                logging.debug(f"Processing potential course file: {file_path_with_container}")
                parts = file_path_with_container.split('/')
                if len(parts) >= 5 and parts[1] == 'course' and parts[-1] == 'course.json':
                    semester = parts[2]
                    course_id = parts[3]
                    course_tuple = (semester, course_id)
                    logging.debug(f"Parsed path: semester='{semester}', course_id='{course_id}'")
                    if course_tuple in user.authenticated_courses:
                        logging.debug(f"User authorized for {course_tuple}. Downloading...")
                        relative_path = '/'.join(parts[1:])
                        data = self.download_json(relative_path)
                        if data:
                            try:
                                courses.append(Course.model_validate(data)) # Use model_validate
                            except Exception as pydantic_error:
                                logging.error(f"Failed to validate Course data from {relative_path}: {pydantic_error}", exc_info=True)
                        # else: download_json logs failure
                    else:
                        logging.debug(f"User not authorized for {course_tuple}.")
                else:
                    logging.warning(f"Skipping file with unexpected path structure: {file_path_with_container}")
            logging.info(f"Returning {len(courses)} authorized courses for user {user.user_email}.")
            return courses
        except Exception as e:
            logging.error(f"Error during list_courses with pattern '{full_pattern_path}': {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Failed to list courses.") from e # Use FastAPI HTTPException


    # --- list_course_materials (Model validation) ---
    def list_course_materials(self, semester_key: str, course_id: str) -> List[CourseMaterial]:
        # Needs adjustment based on how materials are stored (metadata vs content)
        pattern = f"course/{semester_key}/{course_id}/course_material/*.json" # Assumes JSON metadata files
        materials = []
        logging.debug(f"Listing course materials metadata for course {course_id} (pattern: {pattern})")
        full_pattern_path = self._full_path(pattern)

        for file_path_with_container in self.fs.glob(full_pattern_path):
            relative_path = file_path_with_container.split('/', 1)[1]
            data = self.download_json(relative_path)
            if data:
                 try:
                    materials.append(CourseMaterial.model_validate(data)) # Validate metadata
                 except Exception as e:
                    logging.warning(f"Failed to validate CourseMaterial data from {relative_path}: {e}")

        logging.debug(f"Found {len(materials)} course material metadata entries")
        return materials

    # --- list_assignments (Model validation) ---
    def list_assignments(self, semester_key: str, course_id: str) -> List[Assignment]:
        pattern = f"course/{semester_key}/{course_id}/assignment/*/assignment.json"
        assignments = []
        logging.debug(f"Listing assignments for course {course_id}")
        full_pattern_path = self._full_path(pattern)

        for file_path_with_container in self.fs.glob(full_pattern_path):
            relative_path = file_path_with_container.split('/', 1)[1]
            data = self.download_json(relative_path)
            if data:
                 try:
                    assignments.append(Assignment.model_validate(data)) # Use model_validate
                 except Exception as e:
                     logging.warning(f"Failed to validate Assignment data from {relative_path}: {e}")

        logging.debug(f"Found {len(assignments)} assignments")
        return assignments

    # --- list_questions (Model validation) ---
    def list_questions(self, semester_key: str, course_id: str, assignment_id: str) -> List[Question]:
        pattern = f"course/{semester_key}/{course_id}/assignment/{assignment_id}/*/question.json"
        questions = []
        logging.debug(f"Listing questions for assignment {assignment_id}")
        full_pattern_path = self._full_path(pattern)

        question_data_list = []
        for file_path_with_container in self.fs.glob(full_pattern_path):
            relative_path = file_path_with_container.split('/', 1)[1]
            data = self.download_json(relative_path)
            if data:
                 try:
                    # Validate first before adding to temp list
                    question = Question.model_validate(data)
                    question_data_list.append(question)
                 except Exception as e:
                     logging.warning(f"Failed to validate Question data from {relative_path}: {e}")

        # Sort by question_index before returning
        questions = sorted(question_data_list, key=lambda q: q.question_index)
        logging.debug(f"Found and sorted {len(questions)} questions")
        return questions


    # === REMOVED list_sub_rubrics ===
    # def list_sub_rubrics(self, semester_key: str, course_id: str, assignment_id: str) -> List[SubRubric]:
    #     """Lists all sub-rubrics for an assignment. (REMOVED - Now part of get_rubric)"""
    #     # pattern = f"course/{semester_key}/{course_id}/assignment/{assignment_id}/rubrics/*.json"
    #     # sub_rubrics = []
    #     # logging.debug(f"Listing sub-rubrics for assignment {assignment_id}")
    #     # ... (glob and download logic) ...
    #     # return sub_rubrics
    #     return [] # No longer used

    # --- course_exists (no changes) ---
    def course_exists(self, semester_key: str, course_id: str) -> bool:
        blob_path = f"course/{semester_key}/{course_id}/course.json"
        full_path = self._full_path(blob_path)
        exists = self.fs.exists(full_path)
        logging.debug(f"Course existence check for {course_id}: {exists}")
        return exists

    # --- question_exists (no changes) ---
    def question_exists(self, semester_key: str, course_id: str, assignment_id: str, question_index: int) -> bool:
        blob_path = f"course/{semester_key}/{course_id}/assignment/{assignment_id}/{question_index}/question.json"
        full_path = self._full_path(blob_path)
        exists = self.fs.exists(full_path)
        logging.debug(f"Question existence check for {question_index}: {exists}")
        return exists

    # --- assignment_exists (no changes) ---
    def assignment_exists(self, semester_key: str, course_id: str, assignment_id: str) -> bool:
        blob_path = f"course/{semester_key}/{course_id}/assignment/{assignment_id}/assignment.json"
        full_path = self._full_path(blob_path)
        exists = self.fs.exists(full_path)
        logging.debug(f"Assignment existence check for {assignment_id}: {exists}")
        return exists

    # --- token_exists (no changes) ---
    def token_exists(self, user_email: EmailStr, token_name: str) -> bool:
        blob_path = f"user/{user_email}/tokens/{token_name}.json"
        full_path = self._full_path(blob_path)
        exists = self.fs.exists(full_path)
        logging.debug(f"Token existence check for {token_name}: {exists}")
        return exists

    # --- count_questions (no changes) ---
    def count_questions(self, semester_key: str, course_id: str, assignment_id: str) -> int: # Assuming assignment_id is str
        pattern = f"course/{semester_key}/{course_id}/assignment/{assignment_id}/*/question.json"
        full_pattern_path = self._full_path(pattern)
        try:
            files = self.fs.glob(full_pattern_path)
            count = len(files)
            logging.debug(f"Found {count} question files for assignment {assignment_id}")
            return count
        except Exception as e:
             logging.error(f"Error counting questions for assignment {assignment_id} with pattern {full_pattern_path}: {e}", exc_info=True)
             return 0 # Return 0 on error

    # --- _guess_content_type (no changes) ---
    @staticmethod
    def _guess_content_type(filename: str) -> str:
        content_type, _ = mimetypes.guess_type(filename)
        if not content_type:
            logging.warning(f"Unknown content type for {filename}, using octet-stream")
            content_type = 'application/octet-stream'
        return content_type

    # --- init_singleton / get_instance (no changes) ---
    @staticmethod
    def init_singleton(credential: ChainedTokenCredential, storage_account_name: str,
                       container_name: str, azure_blob_cache_dir: FilePath):
        global azure_blob_uploader
        if azure_blob_uploader is None:
             azure_blob_uploader = AzureBlobService(credential, storage_account_name, container_name, azure_blob_cache_dir)
             logging.info("AzureBlobService singleton initialized.")
        else:
             logging.warning("AzureBlobService singleton already initialized.")


    @staticmethod
    def get_instance() -> "AzureBlobService": # Add quotes for forward reference
        global azure_blob_uploader
        if azure_blob_uploader is None:
            # Optionally raise an error or handle the case where it's not initialized
            logging.error("AzureBlobService singleton accessed before initialization.")
            raise RuntimeError("AzureBlobService has not been initialized. Call init_singleton first.")
        return azure_blob_uploader