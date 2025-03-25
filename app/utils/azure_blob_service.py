import base64
import json
import logging
import mimetypes
from typing import List, Dict, Optional

import fsspec

from app.models import Course, Assignment, Question, StudentResponse, Rubric, CourseMaterial, User, AccessToken
from app.models.student_response import GradedStudentResponse

azure_blob_uploader: Optional["AzureBlobService"] = None


class AzureBlobService:
    def __init__(self, credential, storage_account_name, container_name, cache_expiry: int = 3600,
                 cache_storage: str = "/tmp/blob_cache"):
        """
        Initialize AzureBlobUploader using AzureBlobFileSystem with configurable caching.

        :param credential: Azure Storage credential (e.g., account key, SAS token).
        :param storage_account_name: Name of the storage account.
        :param container_name: Name of the container.
        :param cache_expiry: Cache expiry time in seconds (default: 600 seconds = 10 minutes).
        :param cache_storage: Local storage path for caching metadata and files.
        """
        # Build options for the underlying Azure Blob FileSystem provided by adlfs.
        azure_fs_options = {
            "account_name": storage_account_name,
            "credential": credential,
        }
        # Wrap the adlfs filesystem using fsspec's filecache to enable caching.
        # The target_protocol here (e.g., "abfs") must match the protocol implemented by adlfs.
        self.fs = fsspec.filesystem(
            "filecache",
            target_protocol="abfs",  # adjust if needed (e.g., "az" for classic blob storage)
            target_options=azure_fs_options,
            cache_storage=cache_storage,
            expiry_time=cache_expiry
        )
        self.container = container_name

    def _full_path(self, blob_path: str) -> str:
        """Prepends the container name to the given blob path."""
        return f"{self.container}/{blob_path}"

    def upload_base64_file(self, base64_data, blob_path, metadata=None):
        """
        Uploads a base64-encoded file to Azure Blob Storage using AzureBlobFileSystem.
        """
        file_data = base64.b64decode(base64_data)
        content_type = self._guess_content_type(blob_path)
        full_path = self._full_path(blob_path)
        # The following extra kwargs (content_settings, metadata) are passed through
        with self.fs.open(full_path, 'wb',
                          content_settings={"content_type": content_type},
                          metadata=metadata) as f:
            f.write(file_data)
        logging.debug(f"Uploaded base64 data to {blob_path} with metadata: {metadata}")

    def upload_json(self, data, blob_path, metadata: Dict[str, str] = None):
        """
        Uploads JSON data to Azure Blob Storage.
        """
        json_data = json.dumps(data.dict(), indent=4)
        full_path = self._full_path(blob_path)
        with self.fs.open(full_path, 'w',
                          content_settings={"content_type": "application/json"},
                          metadata=metadata) as f:
            f.write(json_data)
        logging.debug(f"Uploaded JSON data to {blob_path} with metadata: {metadata}")

    def download_file(self, blob_path, local_file_path):
        """
        Downloads a file from Azure Blob Storage.
        """
        full_path = self._full_path(blob_path)
        with self.fs.open(full_path, 'rb') as remote_file, open(local_file_path, "wb") as local_file:
            local_file.write(remote_file.read())
        logging.debug(f"Downloaded {blob_path} to {local_file_path}")

    def download_json(self, blob_path):
        """
        Downloads JSON data from Azure Blob Storage and returns it as a Python dictionary.
        """
        full_path = self._full_path(blob_path)
        with self.fs.open(full_path, 'r') as f:
            return json.load(f)

    def delete_blob(self, blob_path: str):
        """
        Deletes a blob from Azure Blob Storage.
        """
        full_path = self._full_path(blob_path)
        self.fs.rm(full_path)
        logging.debug(f"Deleted blob: {blob_path}")

    def list_files(self, prefix=None):
        """
        Lists all files in the container with an optional prefix filter.
        """
        search_path = self._full_path(prefix) if prefix else self._full_path('')
        files = self.fs.ls(search_path)
        # Remove container prefix from results for consistency with the original implementation
        return [f.split('/', 1)[1] if '/' in f else f for f in files]

    def upload_user(self, user: User):
        blob_path = f"user/{user.user_email}.json"
        self.upload_json(user, blob_path)

    def upload_token(self, user_email: str, token: AccessToken):
        blob_path = f"user/{user_email}/tokens/{token.token_id}.json"
        self.upload_json(token, blob_path)

    def upload_course_metadata(self, course: Course):
        """
        Uploads course metadata JSON.
        """
        blob_path = f"course/{course.semester}/{course.course_id}/course.json"
        self.upload_json(course, blob_path)

    def upload_assignment_metadata(self, assignment: Assignment):
        """
        Uploads assignment metadata JSON.
        """
        blob_path = f"course/{assignment.semester}/{assignment.course_id}/assignment/{assignment.assignment_id}/assignment.json"
        self.upload_json(assignment, blob_path)

    def upload_question_metadata(self, semester_key: str, course_id: str, assignment_id: str, question: Question):
        """
        Uploads question metadata JSON.
        """
        blob_path = f"course/{semester_key}/{course_id}/assignment/{assignment_id}/{question.question_index}/question.json"
        self.upload_json(question, blob_path)

    def upload_student_response(self, student_response: GradedStudentResponse):
        """
        Uploads student response file.
        """
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
        self.upload_base64_file(student_response.data.content, blob_path, student_response.data.metadata)

    def upload_rubric(self, semester_key: str, course_id: str, assignment_id: str, rubric: Rubric):
        """
        Uploads rubric JSON. Can upload a rubric for an entire assignment including its sub rubrics.
        """
        blob_path = f"course/{semester_key}/{course_id}/assignment/{assignment_id}/rubric.json"
        self.upload_json(rubric, blob_path)

    def get_course(self, semester_key: str, course_id: str) -> Optional[Course]:
        """Fetches metadata for a specific course."""
        blob_path = f"course/{semester_key}/{course_id}/course.json"
        data = self.download_json(blob_path)
        return Course(**data) if data else None

    def get_assignment_metadata(self, semester_key: str, course_id: str, assignment_id: str) -> Optional[Assignment]:
        """Fetches the metadata for a specific assignment."""
        blob_path = f"course/{semester_key}/{course_id}/assignment/{assignment_id}/assignment.json"
        data = self.download_json(blob_path)
        return Assignment(**data) if data else None

    def upload_course_material(self, material: CourseMaterial):
        """
        Uploads course material file.
        """
        blob_path = (
            f"course/"
            f"{material.semester}/"
            f"{material.course_id}/"
            f"course_material/"
            f"{material.material_id}.{material.data.data_type}"
        )
        self.upload_base64_file(material.data.content, blob_path, material.data.metadata)

    def get_student_response(self, semester_key: str, course_id: str, assignment_id: str, question_index: str,
                             student_id: str) -> Optional[StudentResponse]:
        """Fetches student response file."""
        blob_path = f"course/{semester_key}/{course_id}/assignment/{assignment_id}/{question_index}/student_response/{student_id}/response.json"
        data = self.download_json(blob_path)
        return StudentResponse(**data) if data else None

    def get_grading_details(self, semester_key: str, course_id: str, assignment_id: str, question_index: str,
                            student_id: str) -> Optional[GradedStudentResponse]:
        """Fetches grading details for a student response."""
        blob_path = f"course/{semester_key}/{course_id}/assignment/{assignment_id}/{question_index}/student_response/{student_id}/grade.json"
        data = self.download_json(blob_path)
        return GradedStudentResponse(**data) if data else None

    def get_rubric(self, semester_key: str, course_id: str, assignment_id: str) -> Optional[Rubric]:
        """Fetches the rubric for an assignment."""
        blob_path = f"course/{semester_key}/{course_id}/assignment/{assignment_id}/rubric.json"
        data = self.download_json(blob_path)
        return Rubric(**data) if data else None

    def get_course_material(self, semester_key: str, course_id: str, material_id: str) -> Optional[CourseMaterial]:
        """Fetches course material."""
        blob_path = f"course/{semester_key}/{course_id}/course_material/{material_id}.json"
        data = self.download_json(blob_path)
        return CourseMaterial(**data) if data else None

    def get_user(self, user_email: str) -> Optional[User]:
        """Fetches user details."""
        blob_path = f"user/{user_email}.json"
        data = self.download_json(blob_path)
        return User(**data) if data else None

    def get_token(self, user_email: str, token_id: str) -> Optional[AccessToken]:
        """Fetches an authentication token."""
        blob_path = f"user/{user_email}/tokens/{token_id}.json"
        data = self.download_json(blob_path)
        return AccessToken(**data) if data else None

    def delete_student_response(self, semester_key: str, course_id: str, assignment_id: str, question_index: str,
                                student_id: str):
        """Deletes student response file."""
        blob_path = f"course/{semester_key}/{course_id}/assignment/{assignment_id}/{question_index}/student_response/{student_id}/response.json"
        self.delete_blob(blob_path)

    def delete_grading_details(self, semester_key: str, course_id: str, assignment_id: str, question_index: str,
                               student_id: str):
        """Deletes grading details for a student response."""
        blob_path = f"course/{semester_key}/{course_id}/assignment/{assignment_id}/{question_index}/student_response/{student_id}/grade.json"
        self.delete_blob(blob_path)

    def delete_rubric(self, semester_key: str, course_id: str, assignment_id: str):
        """Deletes the rubric for an assignment."""
        blob_path = f"course/{semester_key}/{course_id}/assignment/{assignment_id}/rubric.json"
        self.delete_blob(blob_path)

    def delete_course(self, semester_key: str, course_id: str) -> int:
        """
        Deletes an entire course, including all subpaths.
        :returns: the number of blobs deleted.
        """
        prefix = f"course/{semester_key}/{course_id}/"
        try:
            files = self.fs.glob(self._full_path(prefix) + "**")
            for file in files:
                self.fs.rm(file)
            logging.debug(f"Deleted {len(files)} blobs for course {course_id}")
            return len(files)
        except Exception as e:
            logging.error(f"Failed to delete course {course_id}: {e}")
            return 0

    def delete_course_material(self, semester_key: str, course_id: str, material_id: str):
        """Deletes course material."""
        blob_path = f"course/{semester_key}/{course_id}/course_material/{material_id}.json"
        self.delete_blob(blob_path)

    def delete_user(self, user_email: str):
        """Deletes user details."""
        blob_path = f"user/{user_email}.json"
        self.delete_blob(blob_path)

    def delete_token(self, user_email: str, token_id: str):
        """Deletes an authentication token."""
        blob_path = f"user/{user_email}/tokens/{token_id}.json"
        self.delete_blob(blob_path)

    def list_courses(self, user: User, semester_key: Optional[str] = None) -> List[Course]:
        """
        Gets metadata for all courses, optionally filtered by semester that the given user has access to.
        """
        pattern = f"course/{semester_key}/*/course.json" if semester_key else "course/*/*/course.json"
        courses = []
        try:
            for file in self.fs.glob(self._full_path(pattern)):
                # if user doesn't have access to this course, skip
                if not user.authenticated_courses.__contains__(file.name):
                    continue
                # Remove the container prefix before passing to download_json
                relative_path = file.split('/', 1)[1]
                data = self.download_json(relative_path)
                if data:
                    courses.append(Course(**data))
        except Exception as e:
            logging.error(f"Failed to list courses: {e}")
        return courses

    def list_assignments(self, semester_key: str, course_id: str) -> List[Assignment]:
        """Gets all assignments for a specific course and semester."""
        pattern = f"course/{semester_key}/{course_id}/assignment/*/assignment.json"
        assignments = []
        try:
            for file in self.fs.glob(self._full_path(pattern)):
                relative_path = file.split('/', 1)[1]
                data = self.download_json(relative_path)
                if data:
                    assignments.append(Assignment(**data))
        except Exception as e:
            logging.error(f"Failed to list assignments: {e}")
        return assignments

    def list_questions(self, semester_key: str, course_id: str, assignment_id: str) -> List[Question]:
        """Gets all questions for a specific assignment."""
        pattern = f"course/{semester_key}/{course_id}/assignment/{assignment_id}/*/question.json"
        questions = []
        try:
            for file in self.fs.glob(self._full_path(pattern)):
                relative_path = file.split('/', 1)[1]
                data = self.download_json(relative_path)
                if data:
                    questions.append(Question(**data))
        except Exception as e:
            logging.error(f"Failed to list questions: {e}")
        return questions

    def list_student_responses(self, semester_key: str, course_id: str, assignment_id: str,
                               question_index: Optional[str] = None) -> List[StudentResponse]:
        """Gets all student responses for a specific assignment, optionally filtered by question index."""
        if question_index:
            pattern = f"course/{semester_key}/{course_id}/assignment/{assignment_id}/{question_index}/student_response/*/response.json"
        else:
            pattern = f"course/{semester_key}/{course_id}/assignment/{assignment_id}/**/student_response/*/response.json"
        responses = []
        try:
            for file in self.fs.glob(self._full_path(pattern)):
                relative_path = file.split('/', 1)[1]
                data = self.download_json(relative_path)
                if data:
                    responses.append(StudentResponse(**data))
        except Exception as e:
            logging.error(f"Failed to list student responses: {e}")
        return responses

    def course_exists(self, semester_key: str, course_id: str) -> bool:
        """
        Checks if a course exists by verifying the presence of its metadata file.

        :param semester_key: The semester identifier.
        :param course_id: The course ID.
        :return: True if the course exists, False otherwise.
        """
        blob_path = f"course/{semester_key}/{course_id}/course.json"
        full_path = self._full_path(blob_path)
        return self.fs.exists(full_path)

    def assignment_exists(self, semester_key: str, course_id: str, assignment_id: str) -> bool:
        """
        Checks if an assignment exists by verifying the presence of its metadata file.

        :param semester_key: The semester identifier.
        :param course_id: The course ID.
        :param assignment_id: The assignment ID.
        :return: True if the assignment exists, False otherwise.
        """
        blob_path = f"course/{semester_key}/{course_id}/assignment/{assignment_id}/assignment.json"
        full_path = self._full_path(blob_path)
        return self.fs.exists(full_path)

    def count_questions(self, semester_key: str, course_id: str, assignment_id: str) -> int:
        """
        Counts the number of questions in a given assignment by checking the number of question metadata files.

        :param semester_key: The semester identifier.
        :param course_id: The course ID.
        :param assignment_id: The assignment ID.
        :return: The number of questions found.
        """
        pattern = f"course/{semester_key}/{course_id}/assignment/{assignment_id}/*/question.json"
        try:
            files = self.fs.glob(self._full_path(pattern))
            return len(files)
        except Exception as e:
            logging.error(f"Failed to count questions for {course_id}, {assignment_id}: {e}")
            return 0

    @staticmethod
    def _guess_content_type(filename: str) -> str:
        """
        Attempts to guess the content type based on the file extension.
        """
        content_type, _ = mimetypes.guess_type(filename)
        return content_type if content_type else 'application/octet-stream'

    @staticmethod
    def init_singleton(credential, storage_account_name, container_name):
        global azure_blob_uploader
        azure_blob_uploader = AzureBlobService(credential, storage_account_name, container_name)

    @staticmethod
    def get_instance() -> Optional["AzureBlobService"]:
        global azure_blob_uploader
        return azure_blob_uploader
