from typing import List, Optional

from fastapi import APIRouter, HTTPException, status, Query, Depends
from pydantic import EmailStr

from app.models.course import Course
from app.utils import JWTService, UserToken
from app.utils.azure_blob_service import AzureBlobService

router = APIRouter()
user_from_auth = JWTService.get_instance().from_authorization_header


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
        user_meta: UserToken = Depends(user_from_auth),
):
    if user_meta is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="You are not authenticated.")
    blob_uploader = AzureBlobService.get_instance()
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
        user_meta: UserToken = Depends(user_from_auth),
):
    if user_meta is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="You are not authenticated.")
    blob_uploader = AzureBlobService.get_instance()
    # Normalize query params
    semester = semester.strip().lower()
    course_id = course_id.strip().lower()
    # Check if course exists
    course = blob_uploader.get_course(semester, course_id)
    if course is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course does not exist.")
    # Check if user has perms
    if user_meta.user_email not in course.instructors:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not authorized on this course.")
    # Carry out the operation
    blobs_deleted = blob_uploader.delete_course(semester, course_id)
    if blobs_deleted == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found.")

    return {"message": "The course was successfully deleted."}


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
        current_semester: str = Query(..., description="Current semester of the course."),
        current_course_id: str = Query(..., description="ID of the course being updated."),
        copy_from_course_semester: str = Query(..., description="Semester of the source course."),
        copy_from_course_id: str = Query(..., description="ID of the course to copy from."),
        user_meta: UserToken = Depends(user_from_auth),
):
    blob_uploader = AzureBlobService.get_instance()
    # normalize query params
    current_semester = current_semester.strip().lower()
    current_semester = current_course_id.strip().lower()
    copy_from_course_semester = copy_from_course_semester.strip().lower()
    copy_from_course_id = copy_from_course_id.strip().lower()

    # TODO: not worth implementing rn
    raise NotImplementedError()


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
        user_meta: UserToken = Depends(user_from_auth),
):
    blob_uploader = AzureBlobService.get_instance()

    # normalize query params
    semester = semester.strip().lower()
    course_id = course_id.strip().lower()
    # Get the course
    course = blob_uploader.get_course(semester, course_id)
    if course is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found.")
    # Make sure user is authorized on the course
    if user_meta.user_email not in course.instructors:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not authorized on this course.")
    return course


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
        user_meta: UserToken = Depends(user_from_auth),
):
    blob_uploader = AzureBlobService.get_instance()
    semester = None if semester is None else semester.strip().lower()
    user = blob_uploader.get_user(user_meta.user_email)
    return blob_uploader.list_courses(user, semester)


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
        instructor: EmailStr = Query(..., description="Email of the instructor to add."),
        user_meta: UserToken = Depends(user_from_auth),
):
    blob_uploader = AzureBlobService.get_instance()
    # normalize query params
    semester = semester.strip().lower()
    course_id = course_id.strip().lower()
    instructor = instructor.strip().lower()

    course = blob_uploader.get_course(semester, course_id)
    if course is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found.")

    # Check if user has perms
    if user_meta.user_email not in course.instructors:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not authorized on this course.")

    if course.instructors.__contains__(instructor):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail="Instructor is already assigned to the course.")

    course.instructors.append(instructor)
    blob_uploader.upload_course_metadata(course)

    instructor_user = blob_uploader.get_user(instructor)
    instructor_user.authenticated_courses.append((semester, course_id))
    blob_uploader.upload_user(instructor_user)

    return {"message": "The instructor was successfully added to the course!"}


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
        instructor: EmailStr = Query(..., description="Email of the instructor to remove."),
        user_meta: UserToken = Depends(user_from_auth),
):
    blob_uploader = AzureBlobService.get_instance()
    # normalize query params
    semester = semester.strip().lower()
    course_id = course_id.strip().lower()
    instructor = instructor.strip().lower()

    course = blob_uploader.get_course(semester, course_id)
    if course is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found.")

    # Check if user has perms
    if user_meta.user_email not in course.instructors:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not authorized on this course.")

    # Check if this instructor is even assigned to this course
    if not course.__contains__(instructor):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Instructor not assigned to the course.")

    # Cant remove self from course!
    if instructor == user_meta.user_email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="You cannot remove yourself from the course.")

    course.instructors.remove(instructor)
    blob_uploader.upload_course_metadata(course)

    instructor_user = blob_uploader.get_user(instructor)
    instructor_user.authenticated_courses.remove((semester, course_id))
    blob_uploader.upload_user(instructor_user)

    return {"message": "The instructor was successfully removed from the course!"}
