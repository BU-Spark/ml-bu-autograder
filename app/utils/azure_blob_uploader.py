import base64
import json
import logging
import mimetypes
from typing import List, Dict, Optional

from azure.storage.blob import BlobServiceClient, ContentSettings

from app.models import Course, Assignment, Question, StudentResponse, Rubric, CourseMaterial, User, \
    AccessToken
from app.models.student_response import GradedStudentResponse

azure_blob_uploader: Optional["AzureBlobUploader"] = None


class AzureBlobUploader:

    def __init__(self, credential, storage_account_name, container_name):
        """
        Initialize AzureBlobUploader using SAS token authentication.
        :param sas_url: The full SAS URL for the container.
        :param container_name: The name of the container inside the storage account.
        """
        self.blob_service_client = BlobServiceClient(
            account_url=f"https://{storage_account_name}.blob.core.windows.net",
            credential=credential
        )
        self.container_client = self.blob_service_client.get_container_client(container_name)

    def upload_base64_file(self, base64_data, blob_path, metadata=None):
        """
        Uploads a base64-encoded file directly to Azure Blob Storage with optional metadata.
        """
        try:
            blob_client = self.container_client.get_blob_client(blob_path)
            file_data = base64.b64decode(base64_data)
            content_type = self._guess_content_type(blob_path)

            blob_client.upload_blob(
                file_data,
                overwrite=True,
                content_settings=ContentSettings(content_type=content_type),
                metadata=metadata
            )
            logging.debug(f"Uploaded base64 data to {blob_path} with metadata: {metadata}")
        except Exception as e:
            logging.error(f"Failed to upload base64 data to {blob_path}: {e}")

    def upload_json(self, data, blob_path, metadata: Dict[str, str] = None):
        """
        Uploads JSON data to Azure Blob Storage with optional metadata.
        """
        try:
            blob_client = self.container_client.get_blob_client(blob_path)
            json_data = json.dumps(data, indent=4)
            blob_client.upload_blob(
                json_data,
                overwrite=True,
                content_settings=ContentSettings(content_type='application/json'),
                metadata=metadata
            )

            logging.debug(f"Uploaded JSON data to {blob_path} with metadata: {metadata}")
        except Exception as e:
            logging.error(f"Failed to upload JSON to {blob_path}: {e}")

    def download_file(self, blob_path, local_file_path):
        """
        Downloads a file from Azure Blob Storage.
        """
        try:
            blob_client = self.container_client.get_blob_client(blob_path)
            with open(local_file_path, "wb") as file:
                file.write(blob_client.download_blob().readall())
            logging.debug(f"Downloaded {blob_path} to {local_file_path}")
        except Exception as e:
            logging.error(f"Failed to download {blob_path}: {e}")

    def download_json(self, blob_path):
        """
        Downloads a JSON file from Azure Blob Storage and returns it as a Python dictionary.
        """
        try:
            blob_client = self.container_client.get_blob_client(blob_path)
            json_data = blob_client.download_blob().readall()
            return json.loads(json_data)
        except Exception as e:
            logging.error(f"Failed to download JSON from {blob_path}: {e}")
            return None

    def delete_blob(self, blob_path: str):
        """Deletes a blob from Azure Blob Storage."""
        try:
            blob_client = self.container_client.get_blob_client(blob_path)
            blob_client.delete_blob()
            logging.debug(f"Deleted blob: {blob_path}")
        except Exception as e:
            logging.error(f"Failed to delete blob {blob_path}: {e}")

    def list_files(self, prefix=None):
        """
        Lists all files in the container with an optional prefix filter.
        """
        try:
            blobs = self.container_client.list_blobs(name_starts_with=prefix)
            return [blob.name for blob in blobs]
        except Exception as e:
            logging.error(f"Failed to list files: {e}")
            return []

    def upload_user(self, user: User):
        """Uploads user details."""
        blob_path = f"user/{user.user_id}.json"
        self.upload_json(user.dict(), blob_path)

    def upload_token(self, user_id: str, token: AccessToken):
        """Uploads a personal authentication token."""
        blob_path = f"user/{user_id}/tokens/{token.token_id}.json"
        self.upload_json(token.dict(), blob_path)

    def upload_course_metadata(self, course: Course):
        """
        Uploads course metadata JSON.
        """
        blob_path = f"course/{course.semester}/{course.course_id}/course.json"
        self.upload_json(course, blob_path)

    def upload_instructors(self, semester_key: str, course_id: str, instructor_details: List[str]):
        """
        Uploads instructor details JSON.
        """
        blob_path = f"course/{semester_key}/{course_id}/instructor.json"
        self.upload_json(instructor_details, blob_path)

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
        blob_path = (f"course/{student_response.semester}/"
                     f"{student_response.course_id}/"
                     f"assignment/"
                     f"{student_response.assignment_id}/"
                     f"{student_response.question_index}/"
                     f"student_response/"
                     f"{student_response.student_id}/"
                     f"response.{student_response.data.data_type}")
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

    def get_instructors(self, semester_key: str, course_id: str) -> Optional[List[str]]:
        """Fetches the list of instructors for a given course."""
        blob_path = f"course/{semester_key}/{course_id}/instructor.json"
        data = self.download_json(blob_path)
        return data if data else None

    def upload_course_material(self, material: CourseMaterial):
        """
        Uploads course material file.
        """
        blob_path = (f"course/"
                     f"{material.semester}/"
                     f"{material.course_id}/"
                     f"course_material/"
                     f"{material.material_id}.{material.data.data_type}")
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

    def get_user(self, user_id: str) -> Optional[User]:
        """Fetches user details."""
        blob_path = f"user/{user_id}.json"
        data = self.download_json(blob_path)
        return User(**data) if data else None

    def get_token(self, user_id: str, token_id: str) -> Optional[AccessToken]:
        """Fetches an authentication token."""
        blob_path = f"user/{user_id}/tokens/{token_id}.json"
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
        :returns: The number of blobs deleted.
        """
        prefix = f"course/{semester_key}/{course_id}/"
        blobs_to_delete = [blob.name for blob in self.container_client.list_blobs(name_starts_with=prefix)]
        for blob_path in blobs_to_delete:
            self.delete_blob(blob_path)
        return len(blobs_to_delete)

    def delete_course_material(self, semester_key: str, course_id: str, material_id: str):
        """Deletes course material."""
        blob_path = f"course/{semester_key}/{course_id}/course_material/{material_id}.json"
        self.delete_blob(blob_path)

    def delete_user(self, user_id: str):
        """Deletes user details."""
        blob_path = f"user/{user_id}.json"
        self.delete_blob(blob_path)

    def delete_token(self, user_id: str, token_id: str):
        """Deletes an authentication token."""
        blob_path = f"user/{user_id}/tokens/{token_id}.json"
        self.delete_blob(blob_path)

    def list_courses(self, semester_key: Optional[str] = None) -> List[Course]:
        """Gets metadata for all courses, optionally filtered by semester."""
        prefix = f"course/{semester_key}/" if semester_key else "course/"
        courses = []
        for blob in self.container_client.list_blobs(name_starts_with=prefix):
            if blob.name.endswith("course.json"):
                course_data = self.download_json(blob.name)
                if course_data:
                    courses.append(Course(**course_data))
        return courses

    def list_assignments(self, semester_key: str, course_id: str) -> List[Assignment]:
        """Gets all assignments for a specific course and semester."""
        prefix = f"course/{semester_key}/{course_id}/assignment/"
        assignments = []
        for blob in self.container_client.list_blobs(name_starts_with=prefix):
            if blob.name.endswith("assignment.json"):
                assignment_data = self.download_json(blob.name)
                if assignment_data:
                    assignments.append(Assignment(**assignment_data))
        return assignments

    def list_questions(self, semester_key: str, course_id: str, assignment_id: str) -> List[Question]:
        """Gets all questions for a specific assignment."""
        prefix = f"course/{semester_key}/{course_id}/assignment/{assignment_id}/"
        questions = []
        for blob in self.container_client.list_blobs(name_starts_with=prefix):
            if blob.name.endswith("question.json"):
                question_data = self.download_json(blob.name)
                if question_data:
                    questions.append(Question(**question_data))
        return questions

    def list_student_responses(self, semester_key: str, course_id: str, assignment_id: str,
                               question_index: Optional[str] = None) -> List[StudentResponse]:
        """Gets all student responses for a specific assignment, optionally filtered by question index."""
        prefix = f"course/{semester_key}/{course_id}/assignment/{assignment_id}/"
        if question_index:
            prefix += f"{question_index}/student_response/"
        responses = []
        for blob in self.container_client.list_blobs(name_starts_with=prefix):
            if "student_response" in blob.name and blob.name.endswith("response.json"):
                response_data = self.download_json(blob.name)
                if response_data:
                    responses.append(StudentResponse(**response_data))
        return responses

    @staticmethod
    def _guess_content_type(filename):
        """
        Attempts to guess the content type based on the file extension.
        """
        content_type, _ = mimetypes.guess_type(filename)
        return content_type if content_type else 'application/octet-stream'

    @staticmethod
    def init_singleton(credential, storage_account_name, container_name):
        global azure_blob_uploader
        azure_blob_uploader = AzureBlobUploader(credential, storage_account_name, container_name)

    @staticmethod
    def get_instance() -> Optional["AzureBlobUploader"]:
        global azure_blob_uploader
        return azure_blob_uploader
