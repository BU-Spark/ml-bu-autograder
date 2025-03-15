from typing import List

from fastapi import APIRouter, HTTPException, status, Query

from app.models.course import Course

router = APIRouter()

# Dummy storage for courses
dummy_courses = [
    Course(course_id="cs_132", course_name="Intro to CS", semester="Fall 2024", instructors=["instructor@example.com"])
]


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
        semester: str = Query(..., description="Semester during which the course is offered.")
):
    dummy_courses.append(course)
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
        course_id: str = Query(..., description="Unique identifier of the course to delete."),
        semester: str = Query(..., description="Semester of the course to delete.")
):
    for course in dummy_courses:
        if course.course_id == course_id and course.semester == semester:
            dummy_courses.remove(course)
            return {"message": "Course deleted successfully."}
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
        copy_from_course_semester: str = Query(..., description="Semester of the source course.")
):
    updated_course = {"course_id": current_course_id, "course_name": "Transferred Course", "semester": current_semester,
                      "instructors": ["instructor@example.com"]}
    return {"message": "Course transfer successful.", "updated_course": updated_course}


@router.get(
    "/courses",
    response_model=List[Course],
    summary="List Courses",
    description="Retrieves all courses accessible by the authenticated user.",
    responses={
        401: {"description": "Requester is not authenticated."}
    }
)
async def list_courses():
    return dummy_courses


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
        course_id: str = Query(..., description="Unique identifier of the course."),
        semester: str = Query(..., description="Semester of the course."),
        instructor: str = Query(..., description="Email of the instructor to add.")
):
    for course in dummy_courses:
        if course.course_id == course_id and course.semester == semester:
            if instructor in course.instructors:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                                    detail="Instructor already assigned to course.")
            course.instructors.append(instructor)
            return {"message": "Instructor added successfully."}
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found.")


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
        instructor: str = Query(..., description="Email of the instructor to remove.")
):
    for course in dummy_courses:
        if course.course_id == course_id and course.semester == semester:
            if instructor not in course.instructors:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Instructor not found in course.")
            course.instructors.remove(instructor)
            return {"message": "Instructor removed successfully."}
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found.")
