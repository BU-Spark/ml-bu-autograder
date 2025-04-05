import base64
import json
import logging
import mimetypes
from typing import List, Dict, Optional

import fsspec
from azure.identity import ChainedTokenCredential
from pydantic import EmailStr

from app.models import Course, Assignment, Question, StudentResponse, Rubric, CourseMaterial, User, AccessToken, \
    SubRubric, Grade
from app.models.student_response import GradedStudentResponse

azure_blob_uploader: Optional["AzureBlobService"] = None


class AzureBlobService:
    def __init__(self, credential: ChainedTokenCredential, storage_account_name: str, container_name: str, cache_expiry: int = 3600,
                 cache_storage: str = "/tmp/blob_cache"):
        """
        Initializes Azure Blob Storage service with configurable caching.

        Args:
            credential: Azure credential (account key, SAS token).
            storage_account_name: Azure storage account name.
            container_name: Target container name.
            cache_expiry: Cache TTL in seconds (default: 1 hour).
            cache_storage: Local cache directory (default: /tmp/blob_cache).
        """
        azure_fs_options = {
            "account_name": storage_account_name,
            "credential": credential,
        }
        self.fs = fsspec.filesystem(
            "filecache",
            target_protocol="abfs",
            target_options=azure_fs_options,
            cache_storage=cache_storage,
            expiry_time=cache_expiry
        )
        self.container = container_name
        logging.debug(f"Initialized AzureBlobService for container {container_name}")

    def _full_path(self, blob_path: str) -> str:
        """Constructs full blob path by prepending container name."""
        return f"{self.container}/{blob_path}"

    def upload_base64_file(self, base64_data, blob_path, metadata=None):
        """
        Uploads base64-encoded data to Azure Blob Storage.

        Args:
            base64_data: Base64-encoded file content.
            blob_path: Destination blob path.
            metadata: Optional blob metadata (key-value pairs).
        """
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

    def upload_json(self, data, blob_path, metadata: Dict[str, str] = None):
        """
        Uploads JSON data from a Pydantic model.

        Args:
            data: Pydantic model instance to serialize.
            blob_path: Destination blob path.
            metadata: Optional blob metadata.
        """
        logging.debug(f"Serializing JSON data for {blob_path}")
        json_data = data.json(indent=4)  # Requires Pydantic model
        full_path = self._full_path(blob_path)

        logging.debug(f"Uploading JSON to {blob_path}")
        with self.fs.open(full_path, 'w',
                          content_settings={"content_type": "application/json"},
                          metadata=metadata) as f:
            f.write(json_data)
        logging.info(f"Uploaded JSON to {blob_path}")

    def download_file(self, blob_path, local_file_path):
        """Downloads a blob to a local file."""
        logging.debug(f"Starting download of {blob_path} to {local_file_path}")
        full_path = self._full_path(blob_path)
        with self.fs.open(full_path, 'rb') as remote_file, open(local_file_path, "wb") as local_file:
            local_file.write(remote_file.read())
        logging.info(f"Downloaded {blob_path} to {local_file_path}")

    def download_json(self, blob_path) -> Optional[dict]:
        """Downloads and parses JSON blob. Returns None on failure."""
        logging.debug(f"Downloading JSON from {blob_path}")
        full_path = self._full_path(blob_path)
        try:
            with self.fs.open(full_path, 'r') as f:
                data = json.load(f)
            logging.debug(f"Successfully parsed JSON from {blob_path}")
            return data
        except json.JSONDecodeError:
            logging.warning(f"Invalid JSON in {blob_path}")
            return None

    def delete_blob(self, blob_path: str):
        """
        Deletes a blob from Azure Blob Storage.

        Args:
            blob_path: Path to the blob to delete.
        """
        logging.debug(f"Attempting to delete blob: {blob_path}")
        full_path = self._full_path(blob_path)
        self.fs.rm(full_path)
        logging.info(f"Deleted blob: {blob_path}")

    def move_blob(self, old_blob_path: str, new_blob_path: str):
        """
        Renames (moves) a blob from old_blob_path to new_blob_path by copying and deleting.
        """
        full_old_path = self._full_path(old_blob_path)
        full_new_path = self._full_path(new_blob_path)

        logging.debug(f"Attempting to move blob from {old_blob_path} to {new_blob_path}")

        if not self.fs.exists(full_old_path):
            logging.warning(f"Source blob does not exist: {old_blob_path}")
            return

        # Copy contents
        with self.fs.open(full_old_path, 'rb') as src:
            with self.fs.open(full_new_path, 'wb') as dst:
                dst.write(src.read())

        # Delete old blob
        self.fs.rm(full_old_path)
        logging.info(f"Moved blob from {old_blob_path} to {new_blob_path}")

    def list_files(self, prefix=None) -> List[str]:
        """
        Lists files in container with optional prefix filter.

        Args:
            prefix: Optional path prefix to filter results.

        Returns:
            List of relative blob paths.
        """
        search_path = self._full_path(prefix) if prefix else self._full_path('')
        logging.debug(f"Listing files with prefix: {prefix}")
        files = self.fs.ls(search_path)
        # Remove container prefix from results
        result = [f.split('/', 1)[1] if '/' in f else f for f in files]
        logging.debug(f"Found {len(result)} files matching prefix")
        return result

    def upload_user(self, user: User):
        """Uploads user metadata."""
        blob_path = f"user/{user.user_email}.json"
        logging.debug(f"Uploading user {user.user_email}")
        self.upload_json(user, blob_path)

    def upload_token(self, user_email: str, token: AccessToken):
        """Uploads access token for specified user."""
        blob_path = f"user/{user_email}/tokens/{token.token_name}.json"
        logging.debug(f"Uploading token {token.token_name} for user {user_email}")
        self.upload_json(token, blob_path)

    def upload_course_metadata(self, course: Course):
        """Uploads course metadata."""
        blob_path = f"course/{course.semester}/{course.course_id}/course.json"
        logging.debug(f"Uploading metadata for course {course.course_id}")
        self.upload_json(course, blob_path)

    def upload_assignment_metadata(self, assignment: Assignment):
        """Uploads assignment metadata."""
        blob_path = f"course/{assignment.semester}/{assignment.course_id}/assignment/{assignment.assignment_id}/assignment.json"
        logging.debug(f"Uploading metadata for assignment {assignment.assignment_id}")
        self.upload_json(assignment, blob_path)

    def upload_question_metadata(self, semester_key: str, course_id: str, assignment_id: int, question_index: int, question: Question):
        """Uploads question metadata."""
        blob_path = f"course/{semester_key}/{course_id}/assignment/{assignment_id}/{question_index}/question.json"
        logging.debug(f"Uploading question {question_index} for assignment {assignment_id}")
        self.upload_json(question, blob_path)

    def upload_student_response(self, student_response: StudentResponse):
        """Uploads student response with automatic content type detection."""
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

    def upload_student_grade(self, graded_student_response: GradedStudentResponse):
        """Uploads student response's grade'."""
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

    def upload_rubric(self, semester_key: str, course_id: str, assignment_id: int, rubric: Rubric,
                      upload_sub_rubrics=True):
        """Uploads rubric with optional sub-rubrics."""
        blob_path = f"course/{semester_key}/{course_id}/assignment/{assignment_id}/rubrics/assignment.json"
        logging.debug(f"Uploading rubric for assignment {assignment_id}")

        if upload_sub_rubrics:
            logging.debug(f"Uploading {len(rubric.sub_rubrics)} sub-rubrics")
            for sub_rubric in rubric.sub_rubrics:
                self.upload_sub_rubric(semester_key, course_id, assignment_id, sub_rubric)

        self.upload_json(rubric, blob_path)

    def upload_sub_rubric(self, semester_key: str, course_id: str, assignment_id: int, sub_rubric: SubRubric):
        """Uploads individual sub-rubric."""
        blob_path = f"course/{semester_key}/{course_id}/assignment/{assignment_id}/rubrics/{sub_rubric.question_index}.json"
        logging.debug(f"Uploading sub-rubric for question {sub_rubric.question_index}")
        self.upload_json(sub_rubric, blob_path)

    def get_course(self, semester_key: str, course_id: str) -> Optional[Course]:
        """Retrieves course metadata if exists."""
        blob_path = f"course/{semester_key}/{course_id}/course.json"
        logging.debug(f"Fetching course {course_id}")
        data = self.download_json(blob_path)
        return Course(**data) if data else None

    def get_assignment_metadata(self, semester_key: str, course_id: str, assignment_id: int) -> Optional[Assignment]:
        """Retrieves assignment metadata if exists."""
        blob_path = f"course/{semester_key}/{course_id}/assignment/{assignment_id}/assignment.json"
        logging.debug(f"Fetching assignment {assignment_id}")
        data = self.download_json(blob_path)
        return Assignment(**data) if data else None

    def upload_course_material(self, material: CourseMaterial):
        """Uploads course material with automatic content type handling."""
        blob_path = (
            f"course/"
            f"{material.semester}/"
            f"{material.course_id}/"
            f"course_material/"
            f"{material.material_id}.{material.data.data_type}"
        )
        logging.debug(f"Uploading course material {material.material_id}")
        self.upload_base64_file(material.data.content, blob_path, material.data.metadata)

    def get_student_response(self, semester_key: str, course_id: str, assignment_id: int, question_index: int,
                             student_id: str, retrieve_grades=True) -> Optional[GradedStudentResponse]:
        """Retrieves student response if exists."""
        blob_path = f"course/{semester_key}/{course_id}/assignment/{assignment_id}/{question_index}/student_response/{student_id}/response.json"
        logging.debug(f"Fetching response from student {student_id}")
        data = self.download_json(blob_path)
        if data is not None:
            student_response = GradedStudentResponse(**data)
            if retrieve_grades:
                grade = self.get_grading_details(semester_key, course_id, assignment_id, question_index, student_id)
                student_response.grade = grade
            return student_response
        return None

    def get_grading_details(self, semester_key: str, course_id: str, assignment_id: int, question_index: int,
                            student_id: str) -> Optional[Grade]:
        """Retrieves grading details if exists."""
        blob_path = f"course/{semester_key}/{course_id}/assignment/{assignment_id}/{question_index}/student_response/{student_id}/grade.json"
        logging.debug(f"Fetching grades for student {student_id}")
        data = self.download_json(blob_path)
        return GradedStudentResponse(**data) if data else None

    def get_rubric(self, semester_key: str, course_id: str, assignment_id: int, include_sub_rubrics=True) -> Optional[
        Rubric]:
        """Retrieves rubric with optional sub-rubrics."""
        blob_path = f"course/{semester_key}/{course_id}/assignment/{assignment_id}/rubric.json"
        logging.debug(f"Fetching rubric for assignment {assignment_id}")
        data = self.download_json(blob_path)
        if not data:
            return None

        rubric = Rubric(**data)
        if include_sub_rubrics:
            logging.debug("Including sub-rubrics in response")
            rubric.sub_rubrics = self.list_sub_rubrics(semester_key, course_id, assignment_id)
        return rubric

    def get_sub_rubric(self, semester_key: str, course_id: str, assignment_id: int, question_index: int) -> Optional[
        SubRubric]:
        """Retrieves specific sub-rubric if exists."""
        blob_path = f"course/{semester_key}/{course_id}/assignment/{assignment_id}/rubrics/{question_index}.json"
        logging.debug(f"Fetching sub-rubric for question {question_index}")
        data = self.download_json(blob_path)
        return SubRubric(**data) if data else None

    def get_course_material(self, semester_key: str, course_id: str, material_id: int) -> Optional[CourseMaterial]:
        """Retrieves course material if exists."""
        blob_path = f"course/{semester_key}/{course_id}/course_material/{material_id}.json"
        logging.debug(f"Fetching course material {material_id}")
        data = self.download_json(blob_path)
        return CourseMaterial(**data) if data else None

    def get_user(self, user_email: EmailStr) -> Optional[User]:
        """Retrieves user data if exists."""
        blob_path = f"user/{user_email}.json"
        logging.debug(f"Fetching user {user_email}")
        data = self.download_json(blob_path)
        return User(**data) if data else None

    def get_token(self, user_email: str, token_name: str) -> Optional[AccessToken]:
        """Retrieves access token if exists."""
        blob_path = f"user/{user_email}/tokens/{token_name}.json"
        logging.debug(f"Fetching token {token_name} for user {user_email}")
        data = self.download_json(blob_path)
        return AccessToken(**data) if data else None

    def delete_student_response(self, semester: str, course_id: str, assignment_id: int, question_index: int, student_id: str):
        """Deletes a specific student response."""
        blob_path = (
            f"course/{semester}/"
            f"{course_id}/"
            f"assignment/"
            f"{assignment_id}/"
            f"{question_index}/"
            f"student_response/"
            f"{student_id}/"
            f"response.*"
        )
        logging.debug(f"Deleting response from student {student_id}")
        self.delete_blob(blob_path)

    def delete_student_responses(self, semester: str, course_id: str, assignment_id: int, student_id: str):
        """Deletes all responses for a student in an assignment."""
        pattern = (
            f"course/{semester}/"
            f"{course_id}/"
            f"assignment/"
            f"{assignment_id}/"
            f"*/"
            f"student_response/"
            f"{student_id}/"
            f"response.*"
        )
        logging.debug(f"Deleting all responses from student {student_id}")
        for file in self.fs.glob(self._full_path(pattern)):
            relative_path = file.split('/', 1)[1]
            self.delete_blob(relative_path)

    def list_student_responses(self, semester: str, course_id: str, assignment_id: int,
                             question_index: Optional[int] = None) -> List[StudentResponse]:
        """Lists student responses with optional question filter."""
        if question_index is not None:
            pattern = (
                f"course/{semester}/"
                f"{course_id}/"
                f"assignment/"
                f"{assignment_id}/"
                f"{question_index}/"
                f"student_response/*/response.*"
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
            data = self.download_json(relative_path)
            if data:
                responses.append(StudentResponse(**data))

        logging.debug(f"Found {len(responses)} responses")
        return responses

    def delete_grading_details(self, semester_key: str, course_id: str, assignment_id: int, question_index: int,
                               student_id: str):
        """Deletes specific grading details."""
        blob_path = f"course/{semester_key}/{course_id}/assignment/{assignment_id}/{question_index}/student_response/{student_id}/grade.json"
        logging.debug(f"Deleting grades for student {student_id}")
        self.delete_blob(blob_path)

    def delete_rubric(self, semester_key: str, course_id: str, assignment_id: int):
        """Deletes assignment rubric."""
        blob_path = f"course/{semester_key}/{course_id}/assignment/{assignment_id}/rubric.json"
        logging.debug(f"Deleting rubric for assignment {assignment_id}")
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

    def delete_course_material(self, semester_key: str, course_id: str, material_id: int):
        """Deletes specific course material."""
        blob_path = f"course/{semester_key}/{course_id}/course_material/{material_id}.json"
        logging.debug(f"Deleting course material {material_id}")
        self.delete_blob(blob_path)

    def delete_question_metadata(self, semester_key: str, course_id: str, assignment_id: int, question_index: int):
        """
        Deletes metadata for a specific question.
        """
        blob_path = f"course/{semester_key}/{course_id}/assignment/{assignment_id}/{question_index}/question.json"
        logging.debug(f"Deleting metadata for question {question_index}")
        self.delete_blob(blob_path)
        # re-order the succeeding indices
        questions_cnt = self.count_questions(semester_key, course_id, assignment_id)
        for question in range(question_index, questions_cnt):
            current_path = f"course/{semester_key}/{course_id}/assignment/{assignment_id}/{question_index}/question.json"
            new_path = f"course/{semester_key}/{course_id}/assignment/{assignment_id}/{question_index - 1}/question.json"
            self.move_blob(current_path, new_path)

    def delete_assignment(self, semester_key: str, course_id: str, assignment_id: int):
        """
        Deletes an entire assignment directory, including metadata, questions, rubrics, and other blobs.
        """
        assignment_prefix = f"course/{semester_key}/{course_id}/assignment/{assignment_id}"
        full_path = self._full_path(assignment_prefix)
        logging.debug(f"Recursively deleting all blobs under {assignment_prefix}")
        self.fs.rm(full_path, recursive=True)

    def delete_user(self, user_email: str):
        """Deletes user data."""
        blob_path = f"user/{user_email}.json"
        logging.debug(f"Deleting user {user_email}")
        self.delete_blob(blob_path)

    def delete_token(self, user_email: str, token_name: str):
        """Deletes specific access token."""
        blob_path = f"user/{user_email}/tokens/{token_name}.json"
        logging.debug(f"Deleting token {token_name} for user {user_email}")
        self.delete_blob(blob_path)

    def reorder_questions(self, semester_key: str, course_id: str, assignment_id: int, new_order: List[int]):
        """
        Reorders questions by moving their blobs and updating question indexes.
        """
        logging.debug(f"Reordering questions for assignment {assignment_id}: {new_order}")

        for new_index, old_index in enumerate(new_order):
            old_blob_path = f"course/{semester_key}/{course_id}/assignment/{assignment_id}/{old_index}/question.json"
            new_blob_path = f"course/{semester_key}/{course_id}/assignment/{assignment_id}/{new_index}/question.json"

            # Download and update the metadata first
            data = self.download_json(old_blob_path)
            if not data:
                logging.warning(f"Skipping missing question metadata at index {old_index}")
                continue

            # Move the blob (rename on storage layer)
            self.move_blob(old_blob_path, new_blob_path)

            logging.info(f"Reordered question: {old_index} → {new_index}")

        logging.info(f"Completed reordering of questions for assignment {assignment_id}")

    def list_courses(self, user: User, semester_key: Optional[str] = None) -> List[Course]:
        """
        Gets metadata for all courses, optionally filtered by semester that the given user has access to.
        """
        pattern = f"course/{semester_key}/*/course.json" if semester_key else "course/*/*/course.json"
        courses = []
        for file in self.fs.glob(self._full_path(pattern)):
            # if user doesn't have access to this course, skip
            if not user.authenticated_courses.__contains__(file.name):
                continue
            # Remove the container prefix before passing to download_json
            relative_path = file.split('/', 1)[1]
            data = self.download_json(relative_path)
            if data:
                courses.append(Course(**data))
        return courses

    def list_course_materials(self, semester_key: str, course_id: str) -> List[CourseMaterial]:
        """
        Lists all course materials for a given course.
        """
        pattern = f"course/{semester_key}/{course_id}/course_material/*.json"
        materials = []
        logging.debug(f"Listing course materials for course {course_id}")

        for file in self.fs.glob(self._full_path(pattern)):
            relative_path = file.split('/', 1)[1]
            data = self.download_json(relative_path)
            if data:
                materials.append(CourseMaterial(**data))

        logging.debug(f"Found {len(materials)} course materials")
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
                assignments.append(Assignment(**data))

        logging.debug(f"Found {len(assignments)} assignments")
        return assignments

    def list_questions(self, semester_key: str, course_id: str, assignment_id: int) -> List[Question]:
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

    def list_sub_rubrics(self, semester_key: str, course_id: str, assignment_id: int) -> List[SubRubric]:
        """Lists all sub-rubrics for an assignment."""
        pattern = f"course/{semester_key}/{course_id}/assignment/{assignment_id}/rubrics/*.json"
        sub_rubrics = []
        logging.debug(f"Listing sub-rubrics for assignment {assignment_id}")

        for file in self.fs.glob(self._full_path(pattern)):
            relative_path = file.split('/', 1)[1]
            data = self.download_json(relative_path)
            if data:
                sub_rubrics.append(SubRubric(**data))

        logging.debug(f"Found {len(sub_rubrics)} sub-rubrics")
        return sub_rubrics

    def course_exists(self, semester_key: str, course_id: str) -> bool:
        """Checks if course metadata exists."""
        blob_path = f"course/{semester_key}/{course_id}/course.json"
        full_path = self._full_path(blob_path)
        exists = self.fs.exists(full_path)
        logging.debug(f"Course existence check for {course_id}: {exists}")
        return exists

    def assignment_exists(self, semester_key: str, course_id: str, assignment_id: int) -> bool:
        """Checks if assignment metadata exists."""
        blob_path = f"course/{semester_key}/{course_id}/assignment/{assignment_id}/assignment.json"
        full_path = self._full_path(blob_path)
        exists = self.fs.exists(full_path)
        logging.debug(f"Assignment existence check for {assignment_id}: {exists}")
        return exists

    def count_questions(self, semester_key: str, course_id: str, assignment_id: int) -> int:
        """Counts questions for an assignment."""
        pattern = f"course/{semester_key}/{course_id}/assignment/{assignment_id}/*/question.json"
        files = self.fs.glob(self._full_path(pattern))
        count = len(files)
        logging.debug(f"Found {count} questions for assignment {assignment_id}")
        return count

    @staticmethod
    def _guess_content_type(filename: str) -> str:
        """Guesses MIME type with fallback logging."""
        content_type, _ = mimetypes.guess_type(filename)
        if not content_type:
            logging.warning(f"Unknown content type for {filename}, using octet-stream")
            content_type = 'application/octet-stream'
        return content_type

    @staticmethod
    def init_singleton(credential: ChainedTokenCredential, storage_account_name: str, container_name: str):
        """Initializes global singleton instance."""
        global azure_blob_uploader
        azure_blob_uploader = AzureBlobService(credential, storage_account_name, container_name)

    @staticmethod
    def get_instance() -> Optional["AzureBlobService"]:
        """Retrieves global singleton instance."""
        global azure_blob_uploader
        return azure_blob_uploader
