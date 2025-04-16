import uuid
from typing import List

from fastapi import APIRouter, HTTPException, Query, Body, Depends
from pydantic import FilePath

from app.models import Course
from app.models.course_material import CourseMaterialData, CourseMaterialReference
from app.utils import JWTService, UserToken, get_str_var, BackgroundJobManager
from app.utils.azure_blob_service import AzureBlobService

router = APIRouter()
user_from_auth = JWTService.get_instance().from_authorization_header


def process_course_material(json_str: str):
    # TODO: This function is called by bg_material_processor.py. It is responsible
    #       for processing the grading logic.
    #  Step 0: Convert the json string into CourseMaterialData
    #  Step 2: Convert the binary data of the course material into document chunks using
    #          bytes_to_doc_util.py.
    #  Step 3: Upload these chunks to azure and get the blob paths
    #  Step 4: Vectorize the chunks (text or images).
    #  Step 5: Take the pairs of the blob paths and vectorized chunks, and upload them
    #          to Azure's AI search. And thats it!
    ...

@router.get(
    "/course_materials",
    response_model=List[CourseMaterialReference],
    summary="Get All Course Materials",
    description="Retrieves all course materials for the specified course.",
    responses={
        404: {"detail": "Course does not exist."},
        401: {"detail": "Requester is not authenticated."},
        403: {"detail": "Authenticated but access is not allowed."}
    }
)
async def get_course_materials(
        semester: str = Query(..., description="Semester of the course."),
        course_id: str = Query(..., description="Identifier of the course."),
        user_meta: UserToken = Depends(user_from_auth),
):
    # validate params
    semester = Course.validate_semester(semester)
    course_id = Course.normalize_lowercase(course_id)

    blob_uploader = AzureBlobService.get_instance()

    # Check if the course exists
    course_exists = blob_uploader.course_exists(semester, course_id)
    if not course_exists:
        raise HTTPException(status_code=404, detail="Course does not exist.")

    # Check if user has perms on course
    user = blob_uploader.get_user(user_meta.user_email)
    if not user.authenticated_courses.__contains__((semester, course_id)):
        raise HTTPException(status_code=403, detail="Authenticated but access is not allowed.")

    # Get all course materials
    materials = blob_uploader.list_course_materials(semester, course_id)

    return materials


@router.get(
    "/course_material",
    response_model=CourseMaterialReference,
    summary="Get Specific Course Material",
    description="Retrieves a specific course material for the specified course.",
    responses={
        404: {"detail": "Course or material does not exist."},
        401: {"detail": "Requester is not authenticated."},
        403: {"detail": "Authenticated but access is not allowed."}
    }
)
async def get_course_material(
        semester: str = Query(..., description="Semester of the course."),
        course_id: str = Query(..., description="Identifier of the course."),
        material_id: str = Query(..., description="Unique identifier of the specific material."),
        user_meta: UserToken = Depends(user_from_auth),
):
    # validate params
    semester = Course.validate_semester(semester)
    course_id = Course.normalize_lowercase(course_id)

    blob_uploader = AzureBlobService.get_instance()

    # Check if the course exists
    course_exists = blob_uploader.course_exists(semester, course_id)
    if not course_exists:
        raise HTTPException(status_code=404, detail="Course does not exist.")

    # Check if user has perms on course
    user = blob_uploader.get_user(user_meta.user_email)
    if not user.authenticated_courses.__contains__((semester, course_id)):
        raise HTTPException(status_code=403, detail="Authenticated but access is not allowed.")

    # Get specific course material
    material = blob_uploader.get_course_material(semester, course_id, material_id)
    if not material:
        raise HTTPException(status_code=404, detail="Course material does not exist.")

    return material


@router.post(
    "/course_material",
    response_model=CourseMaterialReference,
    summary="Upload Course Material",
    description="Uploads new course material. The size of the data must be below a certain threshold.",
    responses={
        400: {"detail": "Missing or invalid parameters."},
        409: {"detail": "Material with the same identifier already exists."},
        401: {"detail": "Requester is not authenticated."},
        403: {"detail": "Authenticated but access is not allowed."}
    }
)
async def upload_course_material(
        material: CourseMaterialData = Body(..., description="Course material object containing details and file data."),
        user_meta: UserToken = Depends(user_from_auth),
):
    blob_uploader = AzureBlobService.get_instance()

    # Check if the course exists
    course_exists = blob_uploader.course_exists(material.semester, material.course_id)
    if not course_exists:
        raise HTTPException(status_code=404, detail="Course does not exist.")

    # Check if user has perms on course
    user = blob_uploader.get_user(user_meta.user_email)
    if not user.authenticated_courses.__contains__((material.semester, material.course_id)):
        raise HTTPException(status_code=403, detail="Authenticated but access is not allowed.")

    # Check if material already exists
    if blob_uploader.course_material_exists(material.semester, material.course_id, material.material_id):
        raise HTTPException(status_code=409, detail="Material with this ID already exists.")

    # Upload the material
    blob_uploader.upload_course_material(material)

    # Save object to file otherwise if too many requests
    # accumulate we will run out of ram very quick
    random_uuid = uuid.uuid4()
    save_path = FilePath(f"{get_str_var('AZURE_BLOB_CACHE_DIR')}/{random_uuid}.course_materials.json")

    # A background process will pick this up and process it trust.
    # See app/utils/bg_material_processor.py.
    with open(save_path, 'w') as f:
        f.write(material.model_dump_json(indent=4))

    return material


@router.delete(
    "/course_material",
    summary="Delete Course Material",
    description="Deletes specified course material.",
    responses={
        404: {"detail": "Course or material does not exist."},
        401: {"detail": "Requester is not authenticated."},
        403: {"detail": "Authenticated but access is not allowed."}
    }
)
async def delete_course_material(
        semester: str = Query(..., description="Semester of the course."),
        course_id: str = Query(..., description="Identifier of the course."),
        material_id: str = Query(..., description="Unique identifier of the material to delete."),
        user_meta: UserToken = Depends(user_from_auth),
):
    # validate params
    semester = Course.validate_semester(semester)
    course_id = Course.normalize_lowercase(course_id)

    blob_uploader = AzureBlobService.get_instance()

    # Check if the course exists
    course_exists = blob_uploader.course_exists(semester, course_id)
    if not course_exists:
        raise HTTPException(status_code=404, detail="Course does not exist.")

    # Check if user has perms on course
    user = blob_uploader.get_user(user_meta.user_email)
    if not user.authenticated_courses.__contains__((semester, course_id)):
        raise HTTPException(status_code=403, detail="Authenticated but access is not allowed.")

    # Check if material exists
    material = blob_uploader.course_material_exists(semester, course_id, material_id)
    if not material:
        raise HTTPException(status_code=404, detail="Course material does not exist.")

    # Delete the material
    blob_uploader.delete_course_material(semester, course_id, material_id)

    return {"detail": "Course material deleted successfully."}


@router.patch(
    "/course_material",
    response_model=CourseMaterialReference,
    summary="Update Course Material",
    description="Updates existing course material. The size of the data must be below a certain threshold.",
    responses={
        400: {"detail": "Missing or invalid parameters."},
        404: {"detail": "Course or material does not exist."},
        401: {"detail": "Requester is not authenticated."},
        403: {"detail": "Authenticated but access is not allowed."}
    }
)
async def update_course_material(
        material: CourseMaterialData = Body(..., description="Course material object with updated data."),
        user_meta: UserToken = Depends(user_from_auth),
):
    blob_uploader = AzureBlobService.get_instance()

    # Check if the course exists
    course_exists = blob_uploader.course_exists(material.semester, material.course_id)
    if not course_exists:
        raise HTTPException(status_code=404, detail="Course does not exist.")

    # Check if user has perms on course
    user = blob_uploader.get_user(user_meta.user_email)
    if not user.authenticated_courses.__contains__((material.semester, material.course_id)):
        raise HTTPException(status_code=403, detail="Authenticated but access is not allowed.")

    # Check if material exists
    existing_material = blob_uploader.course_material_exists(material.semester, material.course_id,
                                                             material.material_id)
    if not existing_material:
        raise HTTPException(status_code=404, detail="Course material does not exist.")

    # Update the material
    blob_uploader.upload_course_material(material)

    # Save object to file otherwise if too many requests
    # accumulate we will run out of ram very quick
    random_uuid = uuid.uuid4()
    save_path = FilePath(f"{get_str_var('AZURE_BLOB_CACHE_DIR')}/{random_uuid}.{material.data.data_type.extension}")

    # A background process will pick this up and process it trust
    with open(save_path, 'w') as f:
        f.write(material.model_dump_json(indent=4))

    return material
