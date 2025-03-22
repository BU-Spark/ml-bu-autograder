from typing import List, Optional

from fastapi import APIRouter, HTTPException, status, Query, Depends

from app.models.course import Course
from app.utils.azure_blob_uploader import AzureBlobUploader

router = APIRouter()


@router.post(
    "/course",
    response_model=Course,
    summary="Create Course",
    description="Creates a new course.",
    responses={
        400: {"description": "Missing or invalid parameters."},
        409: {"description": "A course with the same name and semester already exists."}
    }
)
async def create_course(
        course: Course,
):
    blob_uploader = AzureBlobUploader.get_instance()
    blob_uploader.upload_course_metadata(course)
    return course


@router.delete(
    "/course",
    summary="Delete Course",
    description="Deletes an existing course.",
    responses={
        404: {"description": "Course does not exist."},
        401: {"description": "Requester is not authenticated."},
        403: {"description": "Authenticated but access is not allowed."}
    }
)
async def delete_course(
        semester: str = Query(..., description="Semester of the course to delete."),
        course_id: str = Query(..., description="Unique identifier of the course to delete."),
):
    blob_uploader = AzureBlobUploader.get_instance()
    blobs_deleted = blob_uploader.delete_course(semester, course_id)
    if blobs_deleted == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found.")


@router.patch(
    "/course/transfer",
    summary="Transfer Course Materials",
    description="Transfers course materials and rubric data from a previous semester to a new one.",
    responses={
        404: {"description": "Source or destination course not found."},
        400: {"description": "Invalid parameters."},
        401: {"description": "Requester is not authenticated."},
        403: {"description": "Authenticated but access is not allowed."}
    }
)
async def transfer_course(
        current_course_id: str = Query(..., description="ID of the course being updated."),
        current_semester: str = Query(..., description="Current semester of the course."),
        copy_from_course_id: str = Query(..., description="ID of the course to copy from."),
        copy_from_course_semester: str = Query(..., description="Semester of the source course."),
):
    blob_uploader = AzureBlobUploader.get_instance()
    raise NotImplementedError()  # TODO: not worth implementing rn


@router.get(
    "/course",
    response_model=Course,
    summary="Get Specific Course",
    description="Retrieves a specific course object based on course_id and semester.",
    responses={
        404: {"description": "Course not found."},
        400: {"description": "Invalid parameters."},
        401: {"description": "Requester is not authenticated."},
        403: {"description": "Authenticated but access is not allowed."}
    }
)
async def get_course(
        semester: str = Query(..., description="Course semester."),
        course_id: str = Query(..., description="Unique identifier of the course."),
):
    blob_uploader = AzureBlobUploader.get_instance()
    # TODO: add logic to make sure user is allowed to access this course
    course = blob_uploader.get_course(semester, course_id)
    if course is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found.")
    instructors = blob_uploader.get_instructors(semester, course_id)
    # TODO: instructors.__contains__("TODO")
    #  add logic to make sure instructor can access this course
    if instructors is None or True:
        return course
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="You are not allowed to access this course.")


@router.get(
    "/courses",
    response_model=List[Course],
    summary="List Courses",
    description="Retrieves all courses accessible by the authenticated user optionally filtered by semester.",
    responses={
        401: {"description": "Requester is not authenticated."}
    }
)
async def list_courses(
        semester: Optional[str] = Query(None, description="The semester for which to list the courses for."),
):
    blob_uploader = AzureBlobUploader.get_instance()
    return blob_uploader.list_courses(semester)


@router.post(
    "/course/instructor",
    summary="Add Instructor to Course",
    description="Adds an instructor to a course.",
    responses={
        400: {"description": "Missing or invalid parameters."},
        404: {"description": "Course not found."},
        401: {"description": "Requester is not authenticated."},
        403: {"description": "Authenticated but access is not allowed."},
        409: {"description": "Instructor is already assigned to the course."}
    }
)
async def add_course_instructor(
        semester: str = Query(..., description="Semester of the course."),
        course_id: str = Query(..., description="Unique identifier of the course."),
        instructor: str = Query(..., description="Email of the instructor to add."),
):
    blob_uploader = AzureBlobUploader.get_instance()
    instructors = blob_uploader.get_instructors(semester, course_id)
    if instructors is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found.")

    if instructors.__contains__(instructor):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Instructor is already assigned to the course.")

    instructors.append(instructor)
    blob_uploader.upload_instructors(semester, course_id, instructors)

@router.delete(
    "/course/instructor",
    summary="Remove Instructor from Course",
    description="Removes an instructor from a course.",
    responses={
        400: {"description": "Missing or invalid parameters (i.e. can't remove yourself)."},
        404: {"description": "Course or instructor assignment not found."},
        401: {"description": "Requester is not authenticated."},
        403: {"description": "Authenticated but access is not allowed."}
    }
)
async def remove_course_instructor(
        course_id: str = Query(..., description="Unique identifier of the course."),
        semester: str = Query(..., description="Semester of the course."),
        instructor: str = Query(..., description="Email of the instructor to remove."),
):
    blob_uploader = AzureBlobUploader.get_instance()
    instructors = blob_uploader.get_instructors(semester, course_id)
    if instructors is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found.")

    if not instructors.__contains__(instructor):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Instructor not assigned to the course.")

    if instructor == "TODO":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot remove yourself from the course.")

    instructors.remove(instructor)
    blob_uploader.upload_instructors(semester, course_id, instructors)
