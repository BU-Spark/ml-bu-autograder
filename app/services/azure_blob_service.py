import json
import logging
import mimetypes
import shutil
from concurrent.futures import as_completed
from datetime import timedelta, datetime, UTC
from typing import List, Dict, Optional, Set, Tuple

import fsspec
from adlfs import AzureBlobFileSystem
from azure.identity import ChainedTokenCredential
from azure.storage.blob import ContentSettings, BlobServiceClient, generate_blob_sas, BlobSasPermissions
from fsspec import AbstractFileSystem
from pydantic import EmailStr, FilePath, BaseModel, HttpUrl

from app.models import *
from app.models.uploaded_file import UploadedFileReference, DataType, UploadedFileData
from app.utils.bytes_to_doc_util import Document, DocumentChunk
from app.utils.error_handling_tpe import ErrorHandlingThreadPool

azure_blob_uploader: Optional["AzureBlobService"] = None


class AzureBlobService:
    """
    Service class for interacting with Azure Blob Storage with caching.
    Uses filecache for reads/listings and direct ABFS for writes/modifications.
    """
    fs: AbstractFileSystem  # The filecache wrapper filesystem
    abfs: AzureBlobFileSystem  # The underlying Azure Blob filesystem
    container: str
    executor: ErrorHandlingThreadPool

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
            credential: Azure credential object.
            storage_account_name: Azure storage account name.
            container_name: Target container name.
            azure_blob_cache_dir: Local directory path for caching.
            cache_expiry: Cache time-to-live in seconds (default: 1 hour).
        """
        azure_fs_options = {
            "account_name": storage_account_name,
            "credential": credential,
        }
        azure_blob_cache_dir.mkdir(parents=True, exist_ok=True)
        self.fs = fsspec.filesystem(
            "filecache",
            target_protocol="abfs",
            target_options=azure_fs_options,
            cache_storage=str(azure_blob_cache_dir),
            expiry_time=cache_expiry
        )

        self.abfs = self.fs.fs  # Store direct filesystem access

        # TODO: there are bugs in azure's filecache system
        #  1. you cant upload files with metadata
        #  2. you cant manually invalidate cache
        self.fs = self.fs.fs

        self.account_name = self.abfs.account_name
        self.account_url = f"https://{self.account_name}.blob.core.windows.net"
        self.blob_service_client = BlobServiceClient(self.account_url, credential=self.abfs.credential)
        self.container_client = self.blob_service_client.get_container_client(container_name)

        # init a thread pool executor since there is plenty of IO-bound tasks here...
        self.executor = ErrorHandlingThreadPool(max_workers=4)

        self.container = container_name
        logging.info(f"Initialized AzureBlobService for container '{container_name}'")

    def generate_sas_url(self, blob_path: str) -> HttpUrl:
        """
        Generate a public URL for a blob with read access via a SAS token.

        Args:
            blob_path: The relative path of the blob within the container.

        Returns:
            A URL string containing a SAS token.
        """

        # Define start and expiry times for the SAS token.
        # (We set the start time a few minutes in the past to account for clock skew.)
        start_time = datetime.now(UTC) - timedelta(minutes=5)
        expiry_time = datetime.now(UTC) + timedelta(hours=24)  # Expires in 24 hour; adjust as needed.

        # Obtain a user delegation key for the time period.
        user_delegation_key = self.blob_service_client.get_user_delegation_key(start_time, expiry_time)

        # Generate the SAS token.
        sas_token = generate_blob_sas(
            account_name=self.account_name,
            container_name=self.container,
            blob_name=blob_path,
            user_delegation_key=user_delegation_key,
            permission=BlobSasPermissions(read=True),
            start=start_time,
            expiry=expiry_time
        )

        # Construct and return the full URL.
        return HttpUrl(f"{self.account_url}/{self.container}/{blob_path}?{sas_token}")

    def _full_path(self, blob_path: str) -> str:
        """Constructs full blob path by prepending container name."""
        return f"{self.container}/{blob_path}"

    def upload_binary_data(self, file_data: bytes, blob_path: str, metadata=None):
        """
        Uploads binary data to Azure Blob Storage.

        Args:
            file_data: Binary file data
            blob_path: Destination blob path.
            metadata: Optional blob metadata (key-value pairs).
        """
        assert type(file_data) is bytes
        logging.debug(f"Starting upload of binary file to {blob_path}")
        try:
            content_type = self._guess_content_type(blob_path)

            def list_to_str(l: list):
                string = ""
                for item in l:
                    string += f"{item}, "
                string = string[:-2]
                return string

            def sanitize_metadata(metadata: dict) -> dict:
                if not metadata:
                    return {}

                return {
                    str(k): list_to_str(v) if isinstance(v, list) else str(v)
                    for k, v in metadata.items()
                }

            self.container_client.get_blob_client(blob_path).upload_blob(
                data=file_data,
                overwrite=True,
                content_settings=ContentSettings(content_type=content_type),
                metadata=sanitize_metadata(metadata)
            )

            logging.debug(f"Uploaded {len(file_data)} bytes to {blob_path}, invalidated cache.")

        except Exception as e:
            logging.error(f"Upload failed for {blob_path}: {e}", exc_info=True)
            raise

    def upload_json(self, data: BaseModel, blob_path: str, exclude: Set[str] = None, metadata: Dict[str, str] = None):
        """
        Uploads JSON data from a Pydantic model.

        Args:
            data: Pydantic model instance to serialize.
            blob_path: Destination blob path.
            exclude: Fields which should be excluded from serialization.
            metadata: Optional blob metadata.
        """
        logging.debug(f"Uploading JSON to {blob_path}")
        try:
            exclude_set = set(exclude) if exclude is not None else None
            json_string = data.model_dump_json(indent=4, exclude=exclude_set)
            json_bytes = json_string.encode('utf-8')

            self.container_client.get_blob_client(blob_path).upload_blob(
                data=json_bytes,
                overwrite=True,
                content_settings=ContentSettings(content_type="application/json")
            )

            self.fs.invalidate_cache(blob_path)
            logging.info(f"Uploaded JSON to {blob_path}, invalidated cache.")  # Use relative path

        except Exception as e:
            logging.error(f"Upload JSON failed for {blob_path}: {e}", exc_info=True)
            raise

    def download_file(self, blob_path, local_file_path):
        """Downloads a blob to a local file."""
        full_path = self._full_path(blob_path)
        local_path = FilePath(local_file_path)
        logging.debug(f"Starting download of {full_path} to {local_path}")
        try:
            local_path.parent.mkdir(parents=True, exist_ok=True)
            with self.fs.open(full_path, 'rb') as remote_file, open(local_path, "wb") as local_file:
                shutil.copyfileobj(remote_file, local_file)
            logging.info(f"Downloaded {blob_path} to {local_file_path}")  # Use relative paths
        except FileNotFoundError:
            logging.error(f"Blob not found for download: {full_path}")
            raise
        except Exception as e:
            logging.error(f"Download failed for {full_path}: {e}", exc_info=True)
            raise

    def retrieve_blob_with_metadata(self, blob_path: str) -> Dict[str, str]:
        full_path = self._full_path(blob_path)
        props = self.container_client.get_blob_client(full_path).get_blob_properties()
        return props.metadata

    def get_file_bytes(self, blob_path: str) -> Optional[bytes]:
        full_path = self._full_path(blob_path)
        try:
            with self.fs.open(full_path, 'rb') as f:
                file_bytes = f.read()
            logging.debug(f"Read {len(file_bytes)} bytes from course material file {blob_path}")
            return file_bytes
        except Exception as e:
            logging.error(f"Error reading course material file {full_path}: {e}")
            return None

    def download_json(self, blob_path: str) -> Optional[dict]:
        """Downloads and parses JSON blob. Returns None on failure."""
        full_path = self._full_path(blob_path)
        logging.debug(f"Downloading JSON from {full_path}")
        try:
            with self.fs.open(full_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            logging.debug(f"Successfully parsed JSON from {blob_path}")  # Use relative path
            return data
        except FileNotFoundError:
            logging.warning(f"Blob not found for JSON download: {full_path}")
            return None
        except json.JSONDecodeError:
            logging.warning(f"Invalid JSON content in blob: {full_path}")
            return None
        except Exception as e:
            logging.error(f"Download or parse JSON failed for {full_path}: {e}", exc_info=True)
            return None

    def delete_blob(self, blob_path: str):
        """
        Deletes a blob from Azure Blob Storage.

        Args:
            blob_path: Path to the blob to delete.
        """
        full_path = self._full_path(blob_path)
        logging.debug(f"Attempting to delete blob: {full_path}")
        try:
            if self.abfs.exists(full_path):
                self.abfs.rm(full_path)
                self.fs.invalidate_cache(full_path)
                logging.info(f"Deleted blob: {blob_path}")  # Use relative path
            else:
                logging.warning(f"Blob not found for deletion, skipping: {full_path}")
        except Exception as e:
            logging.error(f"Failed to delete blob {full_path}: {e}", exc_info=True)
            raise

    def move_blob(self, old_blob_path: str, new_blob_path: str):
        """
        Renames (moves) a blob from old_blob_path to new_blob_path by copying and deleting.
        """
        full_old_path = self._full_path(old_blob_path)
        full_new_path = self._full_path(new_blob_path)
        logging.debug(f"Attempting to move blob from {full_old_path} to {full_new_path}")
        try:
            if not self.abfs.exists(full_old_path):
                logging.error(f"Source blob for move does not exist: {full_old_path}")
                raise FileNotFoundError(f"Source blob for move does not exist: {old_blob_path}")

            info = self.abfs.info(full_old_path)
            source_metadata = info.get('metadata')
            source_content_settings = info.get('content_settings')

            with self.abfs.open(full_old_path, 'rb') as src:
                with self.abfs.open(full_new_path, 'wb',
                                    metadata=source_metadata,
                                    content_settings=source_content_settings) as dst:
                    shutil.copyfileobj(src, dst)

            self.abfs.rm(full_old_path)

            # Invalidate cache for both paths
            self.fs.invalidate_cache(full_old_path)
            self.fs.invalidate_cache(full_new_path)  # Invalidate destination too

            logging.info(f"Moved blob from {old_blob_path} to {new_blob_path}")  # Use relative paths
        except Exception as e:
            logging.error(f"Failed to move blob from {full_old_path} to {full_new_path}: {e}", exc_info=True)
            raise

    def file_exists(self, blob_path: str) -> bool:
        """
        Checks if a blob exists using the cached filesystem.

        Args:
            blob_path: Path to the blob (relative to container).

        Returns:
            True if the blob exists, False otherwise.
        """
        full_path = self._full_path(blob_path)
        logging.debug(f"Checking existence of {full_path} via filecache")
        try:
            # Use self.fs for potentially cached existence check
            return self.fs.exists(full_path)
        except Exception as e:
            # Log error but return False as the existence couldn't be confirmed
            logging.error(f"Error checking existence for {full_path}: {e}", exc_info=True)
            return False

    def upload_user(self, user: User):
        """Uploads user metadata."""
        blob_path = f"user/{user.user_email}/user.json"
        self.upload_json(user, blob_path)

    def upload_token(self, user_email: EmailStr, token: PersonalAccessToken):
        """Uploads access token for specified user."""
        blob_path = f"user/{user_email}/tokens/{token.token_name}.json"
        self.upload_json(token, blob_path)

    def upload_course_metadata(self, course: Course):
        """Uploads course metadata."""
        blob_path = f"course/{course.semester}/{course.course_id}/course.json"
        self.upload_json(course, blob_path)

    def upload_assignment_metadata(self, assignment: Assignment):
        """Uploads assignment metadata."""
        blob_path = (f"course/{assignment.semester}/{assignment.course_id}/"
                     f"assignment/{assignment.assignment_id}/assignment.json")
        self.upload_json(assignment, blob_path, exclude={"questions"})

    def upload_question_metadata(self, semester_key: str, course_id: str, assignment_id: str, question_index: int,
                                 question: Question):
        """Uploads question metadata."""
        blob_path = f"course/{semester_key}/{course_id}/assignment/{assignment_id}/{question_index}/question.json"
        self.upload_json(question, blob_path)

    def upload_student_response(self, student_response: StudentResponseData):
        """Uploads student response with automatic content type detection."""
        blob_path = (
            f"course/{student_response.semester}/"
            f"{student_response.course_id}/"
            f"assignment/"
            f"{student_response.assignment_id}/"
            f"{student_response.question_index}/"
            f"student_response/"
            f"{student_response.student_id}/"
            f"response.{student_response.data.data_type.extension}"
        )
        self.upload_binary_data(
            student_response.data.content_as_bytes(),
            blob_path,
        )

    def upload_student_grade(self, semester_key: str, course_id: str,
                             assignment_id: str, question_index: int, student_id: str, grade: Grade):
        """Uploads student response's grade'."""
        blob_path = (
            f"course/{semester_key}/"
            f"{course_id}/"
            f"assignment/"
            f"{assignment_id}/"
            f"{question_index}/"
            f"student_response/"
            f"{student_id}/"
            f"grade.json"
        )
        self.upload_json(grade, blob_path)

    def upload_rubric(self, semester_key: str, course_id: str, assignment_id: str, rubric: Rubric,
                      upload_sub_rubrics=True):
        """Uploads rubric with optional sub-rubrics."""
        blob_path = f"course/{semester_key}/{course_id}/assignment/{assignment_id}/rubrics/rubric.json"

        if upload_sub_rubrics and rubric.sub_rubrics:
            logging.debug(f"Uploading {len(rubric.sub_rubrics)} sub-rubrics in parallel")
            # Submit each sub-rubric upload as a separate task
            futures = [
                self.executor.submit(self.upload_sub_rubric, semester_key, course_id, assignment_id, sub_rubric)
                for sub_rubric in rubric.sub_rubrics
            ]
            # Wait for all uploads to complete and check for errors
            for future in as_completed(futures):
                try:
                    future.result()  # Raise exceptions if any occurred during upload
                except Exception as e:
                    logging.error(f"Failed to upload a sub-rubric during parallel execution: {e}", exc_info=True)

        if upload_sub_rubrics:
            logging.debug(f"Uploading {len(rubric.sub_rubrics)} sub-rubrics")
            for sub_rubric in rubric.sub_rubrics:
                self.upload_sub_rubric(semester_key, course_id, assignment_id, sub_rubric)

        self.upload_json(rubric, blob_path, exclude={"sub_rubrics"})

    def upload_sub_rubric(self, semester_key: str, course_id: str, assignment_id: str, sub_rubric: SubRubric):
        """Uploads individual sub-rubric."""
        blob_path = (f"course/{semester_key}/{course_id}/assignment/"
                     f"{assignment_id}/rubrics/{sub_rubric.question_index}.json")
        self.upload_json(sub_rubric, blob_path)

    def get_course(self, semester_key: str, course_id: str) -> Optional[Course]:
        """Retrieves course metadata if exists."""
        blob_path = f"course/{semester_key}/{course_id}/course.json"
        data = self.download_json(blob_path)
        return Course(**data) if data else None

    def get_assignment_metadata(self, semester_key: str, course_id: str, assignment_id: str) -> Optional[Assignment]:
        """Retrieves assignment metadata if exists."""
        blob_path = f"course/{semester_key}/{course_id}/assignment/{assignment_id}/assignment.json"
        data = self.download_json(blob_path)
        return Assignment(**data, questions=[]) if data else None

    def upload_course_material(self, material: CourseMaterialData) -> CourseMaterialReference:
        """Uploads course material with automatic content type handling."""
        blob_path = (
            f"course/"
            f"{material.semester}/"
            f"{material.course_id}/"
            f"course_material/"
            f"{material.material_id}/material.{material.data.data_type.value[0]}"
        )
        # TODO: problem for later
        # self.upload_binary_data(material.data.content, blob_path, None if material.additional_notes is None else {
        #     "additional_notes": material.additional_notes
        # })
        self.upload_binary_data(material.data.content_as_bytes(), blob_path)
        reference = CourseMaterialReference(
            **material.model_dump(exclude={"data"}),
            data=UploadedFileReference(
                data_type=material.data.data_type,
                uri=self.generate_sas_url(blob_path)
            )
        )
        return reference

    def get_student_response_data(self, semester_key: str, course_id: str, assignment_id: str, question_index: int,
                                  student_id: str, data_type: str) \
            -> Optional[StudentResponseData]:
        """Retrieves student response if exists."""
        blob_path = (f"course/{semester_key}/{course_id}/assignment/{assignment_id}/"
                     f"{question_index}/student_response/{student_id}/response.{data_type.lower()}")
        full_pattern = self._full_path(blob_path)
        logging.debug(f"Retrieving student response with path: {full_pattern}")
        student_response_data = StudentResponseData(
            semester=semester_key,
            course_id=course_id,
            assignment_id=assignment_id,
            question_index=question_index,
            student_id=student_id,
            data=UploadedFileData(
                data_type=DataType.from_extension(data_type),
                content=self.get_file_bytes(full_pattern)
            )
        )
        return student_response_data

    def get_student_response_ref(self, semester_key: str, course_id: str, assignment_id: str, question_index: int,
                                 student_id: str, data_type: str, retrieve_grades=True) \
            -> Optional[GradedStudentResponseReference]:
        """Retrieves student response if exists."""
        blob_path = (f"course/{semester_key}/{course_id}/assignment/{assignment_id}/"
                     f"{question_index}/student_response/{student_id}/response.{data_type.lower()}")
        full_pattern = self._full_path(blob_path)
        logging.debug(f"Retrieving student response with path: {full_pattern}")
        student_response_ref = GradedStudentResponseReference(
            semester=semester_key,
            course_id=course_id,
            assignment_id=assignment_id,
            question_index=question_index,
            student_id=student_id,
            data=UploadedFileReference(
                data_type=DataType.from_extension(data_type),
                uri=self.generate_sas_url(blob_path)
            ),
            grade=None
        )
        if retrieve_grades:
            student_response_ref.grade = self.get_grading_details(semester_key, course_id, assignment_id,
                                                                  question_index, student_id)
        return student_response_ref

    def get_grading_details(self, semester_key: str, course_id: str, assignment_id: str, question_index: int,
                            student_id: str) -> Optional[Grade]:
        """Retrieves grading details if exists."""
        blob_path = f"course/{semester_key}/{course_id}/assignment/{assignment_id}/{question_index}/student_response/{student_id}/grade.json"
        data = self.download_json(blob_path)
        return Grade(**data) if data else None

    def get_rubric(self, semester_key: str, course_id: str, assignment_id: str,
                   include_sub_rubrics=True) -> Optional[Rubric]:
        """Retrieves rubric with optional sub-rubrics."""
        blob_path = f"course/{semester_key}/{course_id}/assignment/{assignment_id}/rubrics/rubric.json"
        data = self.download_json(blob_path)
        if not data:
            return None

        rubric = Rubric(**data)
        if include_sub_rubrics:
            logging.debug("Including sub-rubrics in response")
            rubric.sub_rubrics = self.list_sub_rubrics(semester_key, course_id, assignment_id)
        return rubric

    def get_sub_rubric(self, semester_key: str, course_id: str, assignment_id: str,
                       question_index: int) -> Optional[SubRubric]:
        """Retrieves specific sub-rubric if exists."""
        blob_path = f"course/{semester_key}/{course_id}/assignment/{assignment_id}/rubrics/{question_index}.json"
        data = self.download_json(blob_path)
        return SubRubric(**data) if data else None

    def _get_course_material(self, absolute_path: str, semester_key: str,
                             course_id: str) -> Optional[CourseMaterialReference]:

        relative_path = absolute_path.split('/', 1)[1] if '/' in absolute_path else absolute_path
        material_id_split = relative_path.split('/')[4].split(".")

        logging.debug(f"Found course material file: {relative_path}")

        # Retrieve any file metadata (e.g., additional_notes).
        try:
            info = self.fs.info(absolute_path)
            metadata = info.get("metadata", {})
            additional_notes = metadata.get("additional_notes", "")
            logging.debug(f"Retrieved metadata for {absolute_path}: {metadata}")
        except Exception as e:
            logging.warning(f"Could not retrieve metadata for {absolute_path}: {e}")
            return None

        data_type = material_id_split[-1]
        # Prepare the file data dictionary.
        file_data = UploadedFileReference(
            data_type=DataType.from_extension(data_type),
            uri=self.generate_sas_url(relative_path)
        )
        try:
            material = CourseMaterialReference(
                semester=semester_key,
                course_id=course_id,
                material_id=material_id_split[0],
                additional_notes=additional_notes,
                data=file_data
            )
            return material
        except Exception as e:
            logging.error(f"Error constructing CourseMaterialReference: {e}")
            return None

    def get_course_material(self, semester_key: str, course_id: str, material_id: str) -> Optional[
        CourseMaterialReference]:
        """Retrieves course material if it exists."""
        # Construct the search pattern with a wildcard extension.
        pattern = f"course/{semester_key}/{course_id}/course_material/{material_id}/material.*"
        full_pattern = self._full_path(pattern)
        logging.debug(f"Searching for course material with pattern: {full_pattern}")

        # List files that match the pattern.
        files = self.fs.glob(full_pattern)
        if not files:
            logging.debug(f"No course material found for material_id {material_id} in course {course_id}")
            return None

        # Assume the first matching file is the correct one.
        file_path = files[0]
        material = self._get_course_material(file_path, semester_key, course_id)

        return material

    def get_user(self, user_email: EmailStr) -> Optional[User]:
        """Retrieves user data if exists."""
        blob_path = f"user/{user_email}/user.json"
        data = self.download_json(blob_path)
        return User(**data) if data else None

    # a default user that always exists
    def get_default_user(self) -> User:
        default_user: Optional[User] = AzureBlobService.get_instance().get_user("admin@autograder.com")
        if default_user is None:
            default_user: User = User(
                user_email="admin@autograder.com",
                first_name="Admin",
                last_name="",
                authenticated_courses=set(),
                dark_mode=False,
            )
            AzureBlobService.get_instance().upload_user(default_user)
        return default_user

    def get_token(self, user_email: EmailStr, token_name: str) -> Optional[PersonalAccessToken]:
        """Retrieves access token if exists."""
        blob_path = f"user/{user_email}/tokens/{token_name}.json"
        data = self.download_json(blob_path)
        return PersonalAccessToken(**data) if data else None

    def delete_student_response(self, semester: str, course_id: str, assignment_id: str, question_index: int,
                                student_id: str):
        """Deletes a specific student response."""
        pattern = (
            f"course/{semester}/"
            f"{course_id}/"
            f"assignment/"
            f"{assignment_id}/"
            f"{question_index}/"
            f"student_response/"
            f"{student_id}/*"  # delete grade.json and the response itself
        )
        full_pattern = self._full_path(pattern)
        self.fs.rm(full_pattern, recursive=True)

    def delete_student_responses(self, semester: str, course_id: str, assignment_id: str, student_id: str):
        """Deletes all responses for a student in an assignment."""
        pattern = (
            f"course/{semester}/"
            f"{course_id}/"
            f"assignment/"
            f"{assignment_id}/"
            f"*/"
            f"student_response/"
            f"{student_id}/*"
        )
        logging.debug(f"Deleting all responses from student {student_id}")
        for file in self.fs.glob(self._full_path(pattern)):
            relative_path = file.split('/', 1)[1]
            self.delete_blob(relative_path)

    def list_personal_access_tokens(self, user_email: EmailStr) -> List[PersonalAccessToken]:
        """
        Lists all personal access tokens for a given user.

        Args:
            user_email: Email of the user.

        Returns:
            List of PersonalAccessToken objects.
        """
        pattern = f"user/{user_email}/tokens/*.json"
        tokens = []
        logging.debug(f"Listing tokens for user {user_email}")

        for file in self.fs.glob(self._full_path(pattern)):
            relative_path = file.split('/', 1)[1]
            data = self.download_json(relative_path)
            if data:
                try:
                    tokens.append(PersonalAccessToken(**data))
                except Exception as e:
                    logging.warning(f"Failed to parse token at {relative_path}: {e}")

        logging.debug(f"Found {len(tokens)} tokens for user {user_email}")
        return tokens

    def list_student_responses(self, semester: str, course_id: str, assignment_id: str,
                               student_id: Optional[str] = None,
                               question_index: Optional[int] = None,
                               include_grades: bool = False,
                               include_data=False) -> List[GradedStudentResponseReference | StudentResponseData]:
        """Lists student responses with optional question filter."""
        if question_index is not None and student_id is not None:
            pattern = (
                f"course/{semester}/"
                f"{course_id}/"
                f"assignment/"
                f"{assignment_id}/"
                f"{question_index}/"
                f"student_response/"
                f"{student_id}/"
                f"response.*"
            )
        elif question_index is not None and student_id is None:
            pattern = (
                f"course/{semester}/"
                f"{course_id}/"
                f"assignment/"
                f"{assignment_id}/"
                f"{question_index}/"
                f"student_response/*/response.*"
            )
        elif question_index is None and student_id is not None:
            pattern = (
                f"course/{semester}/"
                f"{course_id}/"
                f"assignment/"
                f"{assignment_id}/"
                f"*/"
                f"student_response/{student_id}/response.*"
            )
        else:
            pattern = (
                f"course/{semester}/"
                f"{course_id}/"
                f"assignment/"
                f"{assignment_id}/"
                f"*/"
                f"student_response/*/response.*"
            )

        responses = []
        logging.debug(f"Listing student responses for assignment {assignment_id}")

        for file in self.fs.glob(self._full_path(pattern)):
            relative_path = file.split('/', 1)[1]
            student_id = relative_path.split('/')[7]
            data_type = relative_path.split(".")[-1]
            question_index = int(relative_path.split("/")[5])
            if include_data:
                student_response_data = self.get_student_response_data(
                    semester, course_id, assignment_id,
                    question_index, student_id, data_type
                )
                if student_response_data is not None:
                    responses.append(student_response_data)
            else:
                student_response_ref = self.get_student_response_ref(semester, course_id, assignment_id,
                                                                     question_index, student_id, data_type, include_grades)
                if student_response_ref is not None:
                    responses.append(student_response_ref)

        logging.debug(f"Found {len(responses)} responses")
        return responses

    def delete_grading_details(self, semester_key: str, course_id: str, assignment_id: str, question_index: int,
                               student_id: str):
        """Deletes specific grading details."""
        blob_path = (f"course/{semester_key}/{course_id}/assignment/"
                     f"{assignment_id}/{question_index}/student_response/{student_id}/grade.json")
        self.delete_blob(blob_path)

    def delete_rubric(self, semester_key: str, course_id: str, assignment_id: str):
        """Deletes assignment rubric."""
        blob_path = f"course/{semester_key}/{course_id}/assignment/{assignment_id}/rubric.json"
        self.delete_blob(blob_path)

    def delete_course(self, semester_key: str, course_id: str) -> int:
        """
        Recursively deletes all course data.

        Returns:
            Number of blobs deleted.
        """
        prefix = f"course/{semester_key}/{course_id}/"
        full_path = self._full_path(prefix)

        logging.debug(f"Starting recursive delete for course {course_id}")

        files = self.fs.glob(full_path + "**")
        self.fs.rm(full_path, recursive=True)
        logging.info(f"Deleted {len(files)} blobs for course {course_id}")
        return len(files)

    def delete_course_material(self, semester_key: str, course_id: str, material_id: str):
        """Deletes specific course material."""
        prefix = f"course/{semester_key}/{course_id}/course_material/{material_id}/"
        full_prefix = self._full_path(prefix)
        # Even though there is only one course material, because we also store the course material's
        # processed chunks here, there can be multiple matching files
        self.fs.rm(full_prefix, recursive=True)
        logging.info(f"Deleted course material {material_id} for course {course_id}")

    def delete_question_metadata(self, semester_key: str, course_id: str, assignment_id: str, question_index: int):
        """
        Deletes metadata for a specific question.
        """
        blob_path = f"course/{semester_key}/{course_id}/assignment/{assignment_id}/{question_index}/question.json"
        self.delete_blob(blob_path)
        # re-order the succeeding indices
        questions_cnt = self.count_questions(semester_key, course_id, assignment_id)
        for question in range(question_index + 1, questions_cnt + 1):
            current_path = f"course/{semester_key}/{course_id}/assignment/{assignment_id}/{question}/question.json"
            new_path = f"course/{semester_key}/{course_id}/assignment/{assignment_id}/{question - 1}/question.json"
            self.move_blob(current_path, new_path)

    def delete_assignment(self, semester_key: str, course_id: str, assignment_id: str):
        """
        Deletes an entire assignment directory, including metadata, questions, rubrics, and other blobs.
        """
        assignment_prefix = f"course/{semester_key}/{course_id}/assignment/{assignment_id}"
        full_path = self._full_path(assignment_prefix)
        logging.debug(f"Recursively deleting all blobs under {assignment_prefix}")
        self.fs.rm(full_path, recursive=True)

    def delete_user(self, user_email: EmailStr):
        """Deletes user data."""
        user_prefix = f"user/{user_email}"
        full_path = self._full_path(user_prefix)
        logging.debug(f"Recursively deleting all user data under {user_prefix}")
        self.fs.rm(full_path, recursive=True)

    def delete_token(self, user_email: EmailStr, token_name: str):
        """Deletes specific access token."""
        blob_path = f"user/{user_email}/tokens/{token_name}.json"
        self.delete_blob(blob_path)

    def reorder_questions(self, semester_key: str, course_id: str, assignment_id: str, new_order: List[int]):
        """
        Reorders questions by moving their blobs and updating question indexes.
        """
        logging.debug(f"Reordering questions for assignment {assignment_id}: {new_order}")
        raise NotImplementedError("Reordering questions is not yet implemented.")

    def list_courses(self, user: User, semester_key: Optional[str] = None) -> List[Course]:
        """
        Gets metadata for all courses, optionally filtered by semester that the given user has access to.
        """
        pattern = f"course/{semester_key}/*/course.json" if semester_key else "course/*/*/course.json"
        courses = []
        for file in self.fs.glob(self._full_path(pattern)):
            # if user doesn't have access to this course, skip
            semester = file.split('/')[2]
            course_id = file.split('/')[3]
            if not user.authenticated_courses.__contains__((semester, course_id)):
                logging.debug(f"Skipping course {file} because {user.user_email} doesn't have access to {(semester, course_id)}")
                continue
            # Remove the container prefix before passing to download_json
            relative_path = file.split('/', 1)[1]
            data = self.download_json(relative_path)
            if data:
                courses.append(Course(**data))
        return courses

    def list_course_materials(self, semester_key: str, course_id: str) -> List[CourseMaterialReference]:
        """
        Lists all course materials for a given course.
        """
        pattern = f"course/{semester_key}/{course_id}/course_material/*/material.*"
        materials = []
        full_pattern = self._full_path(pattern)
        logging.debug(f"Listing course materials for course {course_id} using pattern: {full_pattern}")

        for file_path in self.fs.glob(full_pattern):
            material = self._get_course_material(file_path, semester_key, course_id)
            materials.append(material)

        logging.debug(f"Found {len(materials)} course materials for course {course_id}")
        return materials

    def list_assignments(self, semester_key: str, course_id: str) -> List[Assignment]:
        """Lists all assignments for a course."""
        pattern = f"course/{semester_key}/{course_id}/assignment/*/assignment.json"
        assignments = []
        logging.debug(f"Listing assignments for course {course_id}")

        for file in self.fs.glob(self._full_path(pattern)):
            relative_path = file.split('/', 1)[1]
            data = self.download_json(relative_path)
            if data:
                assignments.append(Assignment(**data, questions=[]))

        logging.debug(f"Found {len(assignments)} assignments")
        return assignments

    def list_questions(self, semester_key: str, course_id: str, assignment_id: str) -> List[Question]:
        """Lists all questions for an assignment in order."""
        pattern = f"course/{semester_key}/{course_id}/assignment/{assignment_id}/*/question.json"
        questions = []
        logging.debug(f"Listing questions for assignment {assignment_id}")

        for file in self.fs.glob(self._full_path(pattern)):
            relative_path = file.split('/', 1)[1]
            data = self.download_json(relative_path)
            if data:
                questions.append(Question(**data))

        logging.debug(f"Found {len(questions)} questions")
        return questions

    def list_sub_rubrics(self, semester_key: str, course_id: str, assignment_id: str) -> List[SubRubric]:
        """Lists all sub-rubrics for an assignment."""
        pattern = f"course/{semester_key}/{course_id}/assignment/{assignment_id}/rubrics/*.json"
        sub_rubrics = []
        logging.debug(f"Listing sub-rubrics for assignment {assignment_id}")

        for file in self.fs.glob(self._full_path(pattern)):
            relative_path = file.split('/', 1)[1]
            if relative_path.endswith("rubric.json"):
                continue  # only for the sub rubrics
            data = self.download_json(relative_path)
            if data:
                sub_rubrics.append(SubRubric(**data))

        logging.debug(f"Found {len(sub_rubrics)} sub-rubrics")
        return sub_rubrics

    def course_exists(self, semester_key: str, course_id: str) -> bool:
        """Checks if course metadata exists."""
        blob_path = f"course/{semester_key}/{course_id}/course.json"
        return self.file_exists(blob_path)

    def assignment_exists(self, semester_key: str, course_id: str, assignment_id: str) -> bool:
        """Checks if assignment metadata exists."""
        blob_path = f"course/{semester_key}/{course_id}/assignment/{assignment_id}/assignment.json"
        return self.file_exists(blob_path)

    def token_exists(self, user_email: EmailStr, token_name: str) -> bool:
        blob_path = f"user/{user_email}/tokens/{token_name}.json"
        return self.file_exists(blob_path)

    def student_response_exists(self, semester_key: str, course_id: str, assignment_id: str, question_index: int,
                                student_id: str):
        """Checks if student response exists."""
        pattern = (
            f"course/{semester_key}/"
            f"{course_id}/"
            f"assignment/"
            f"{assignment_id}/"
            f"{question_index}/"
            f"student_response/"
            f"{student_id}/*"
        )
        full_pattern = self._full_path(pattern)
        logging.debug(f"Checking for student response with pattern: {full_pattern}")

        files = self.fs.glob(full_pattern)
        logging.debug(f"Found {len(files)} files for student response {student_id}")

        return bool(files)

    def course_material_exists(self, semester_key: str, course_id: str, material_id: str) -> bool:
        """
        Checks if course material exists for the given semester, course, and material_id.
        """
        pattern = f"course/{semester_key}/{course_id}/course_material/{material_id}/material.*"
        full_pattern = self._full_path(pattern)
        logging.debug(f"Checking existence of course material with pattern: {full_pattern}")

        files = self.fs.glob(full_pattern)
        logging.debug(f"Found {len(files)} files for for material_id {material_id}")

        return bool(files)

    def count_questions(self, semester_key: str, course_id: str, assignment_id: str) -> int:
        """Counts questions for an assignment."""
        pattern = f"course/{semester_key}/{course_id}/assignment/{assignment_id}/*/question.json"
        files = self.fs.glob(self._full_path(pattern))
        count = len(files)
        logging.debug(f"Found {count} questions for assignment {assignment_id} in course {semester_key} {course_id}")
        return count

    def count_assignments(self, semester_key: str, course_id: str):
        pattern = f"course/{semester_key}/{course_id}/assignment/*/assignment.json"
        files = self.fs.glob(self._full_path(pattern))
        count = len(files)
        logging.debug(f"Found {count} questions in course {semester_key} {course_id}")
        return count

    def count_course_materials(self, semester_key: str, course_id: str) -> int:
        """Counts course materials for a given semester, course, and material_id."""
        pattern = f"course/{semester_key}/{course_id}/course_material/*/material.*"
        files = self.fs.glob(self._full_path(pattern))
        count = len(files)
        logging.debug(f"Found {count} course materials for course {course_id} in semester {semester_key}")
        return count

    def upload_material_chunks(self, semester_key: str, course_id: str, material_id: str,
                               document: Document) -> Dict[int, str]:
        base_path = f"course/{semester_key}/{course_id}/course_material/{material_id}/chunks"
        full_base_path = self._full_path(base_path)
        try:
            self.fs.rm(full_base_path, recursive=True)
        except FileNotFoundError:
            ...  # ignored

        def upload_one(chunk_id, document_chunk):
            blob_path = f"{base_path}/{chunk_id}.{document_chunk.data_type.extension}"
            self.upload_binary_data(document_chunk.content, blob_path, document_chunk.metadata)
            logging.info(f"Uploaded chunk {chunk_id} for {material_id}")
            return chunk_id, blob_path

        # This is a IO-bound task so using multiple threads speeds stuff up a lot
        results = self.executor.map(lambda args:
                                    upload_one(*args),
                                    document.contents.items())

        mappings = dict(results)

        return mappings

    def get_chunks_from_blob_path(self, blob_paths: List[str]) -> List[Tuple[str, DocumentChunk]]:
        # Helper to do the IO work for one path
        def _load_one(blob_path: str):
            file_name = blob_path.split('/')[4]
            absolute_path = self._full_path(blob_path)
            data = self.get_file_bytes(absolute_path)
            metadata = self.fs.info(absolute_path).get("metadata", {})
            if not data:
                return None
            return (
                file_name,
                DocumentChunk(
                    data_type=DataType.from_extension(blob_path.rsplit('.', 1)[-1]),
                    content=data,
                    metadata=metadata
                )
            )

        # Submit all tasks; executor.map returns results in the same order
        results = list(self.executor.map(_load_one, blob_paths))

        # Filter out any Nones (in case get_file_bytes returned falsy)
        return [r for r in results if r is not None]

    def find_chunks_paths(self, semester_key: str, course_id: str, material_id: str) -> List[str]:
        prefix = f"course/{semester_key}/{course_id}/course_material/{material_id}/chunks/*"
        return self.fs.glob(self._full_path(prefix))
    
    @staticmethod
    def _get_document_name_from_chunk_path(chunk_path: str) -> str:
        """
        Extracts the document name from a chunk path.
        """
        # Assuming the chunk path is in the format: .../chunks/<chunk_id>.<extension>
        return chunk_path.split("/")[-1].split(".")[0]


    @staticmethod
    def _guess_content_type(filename: str) -> str:
        """Guesses MIME type with fallback logging."""
        content_type, _ = mimetypes.guess_type(filename)
        if not content_type:
            logging.warning(f"Unknown content type for {filename}, using octet-stream")
            content_type = 'application/octet-stream'
        return content_type

    @staticmethod
    def init_singleton(credential: ChainedTokenCredential, storage_account_name: str,
                       container_name: str, azure_blob_cache_dir: FilePath):
        """Initializes global singleton instance."""
        global azure_blob_uploader
        azure_blob_uploader = AzureBlobService(credential, storage_account_name, container_name, azure_blob_cache_dir)

    @staticmethod
    def get_instance() -> Optional["AzureBlobService"]:
        """Retrieves global singleton instance."""
        global azure_blob_uploader
        return azure_blob_uploader
