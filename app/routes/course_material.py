from typing import List

from fastapi import APIRouter, HTTPException, status, Query, Body

from app.models.course_material import CourseMaterial
from app.utils.azure_blob_uploader import AzureBlobUploader

router = APIRouter()

# Dummy storage for course materials
dummy_materials: List[CourseMaterial] = []


@router.get(
    "/course_materials",
    response_model=List[CourseMaterial],
    summary="Get All Course Materials",
    description="Retrieves all course materials for the specified course.",
    responses={
        404: {"description": "No matching course found."},
        401: {"description": "Requester is not authenticated."},
        403: {"description": "Authenticated but access is not allowed."}
    }
)
async def get_course_materials(
        semester: str = Query(..., description="Semester of the course material."),
        course_id: str = Query(..., description="Identifier of the course."),
):
    blob_uploader = AzureBlobUploader.get_instance()
    results = [material for material in dummy_materials if material.course_id == course_id]

    if not results:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No matching course found."
        )

    return results


@router.get(
    "/course_material",
    response_model=CourseMaterial,
    summary="Get Specific Course Material",
    description="Retrieves a specific course material for the specified course.",
    responses={
        404: {"description": "No matching course or course material found."},
        401: {"description": "Requester is not authenticated."},
        403: {"description": "Authenticated but access is not allowed."}
    }
)
async def get_course_material(
        semester: str = Query(..., description="Semester of the course material."),
        course_id: str = Query(..., description="Identifier of the course."),
        material_id: str = Query(..., description="Unique identifier of the specific material."),
):
    blob_uploader = AzureBlobUploader.get_instance()
    for material in dummy_materials:
        if material.course_id == course_id and material.material_id == material_id:
            return material

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="No matching course or course material found."
    )


@router.post(
    "/course_material",
    response_model=CourseMaterial,
    summary="Upload Course Material",
    description="Uploads new course material. The size of the data must be below a certain threshold.",
    responses={
        400: {"description": "Missing or invalid parameters."},
        409: {"description": "Material with the same identifier already exists."},
        401: {"description": "Requester is not authenticated."},
        403: {"description": "Authenticated but access is not allowed."}
    }
)
async def upload_course_material(
        material: CourseMaterial = Body(..., description="Course material object containing details and file data."),
):
    blob_uploader = AzureBlobUploader.get_instance()
    dummy_materials.append(material)
    return material


@router.delete(
    "/course_material",
    summary="Delete Course Material",
    description="Deletes specified course material.",
    responses={
        404: {"description": "Material not found."},
        401: {"description": "Requester is not authenticated."},
        403: {"description": "Authenticated but access is not allowed."}
    }
)
async def delete_course_material(
        semester: str = Query(..., description="Semester of the course material."),
        course_id: str = Query(..., description="Identifier of the course."),
        material_id: str = Query(..., description="Unique identifier of the material to delete.")
):
    blob_uploader = AzureBlobUploader.get_instance()
    for material in dummy_materials:
        if material.course_id == course_id and material.material_id == material_id:
            dummy_materials.remove(material)
            return {"message": "Course material deleted successfully."}
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Material not found.")


@router.patch(
    "/course_material",
    response_model=CourseMaterial,
    summary="Update Course Material",
    description="Updates existing course material. The size of the data must be below a certain threshold.",
    responses={
        400: {"description": "Missing or invalid parameters."},
        404: {"description": "Material to update not found."},
        401: {"description": "Requester is not authenticated."},
        403: {"description": "Authenticated but access is not allowed."}
    }
)
async def update_course_material(
        material: CourseMaterial = Body(..., description="Course material object with updated data."),
):
    blob_uploader = AzureBlobUploader.get_instance()
    for idx, existing in enumerate(dummy_materials):
        if existing.course_id == material.course_id and existing.material_id == material.material_id:
            dummy_materials[idx] = material
            return material
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Material not found.")
