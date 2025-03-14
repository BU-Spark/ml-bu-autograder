from fastapi import APIRouter, HTTPException, status
from typing import List
from app.models.course_material import CourseMaterial

router = APIRouter()

# Dummy storage for course materials
dummy_materials: List[CourseMaterial] = []

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
async def upload_course_material(material: CourseMaterial, semester: str):
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
async def delete_course_material(course_id: str, semester: str, material_id: str):
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
async def update_course_material(material: CourseMaterial, semester: str):
    for idx, existing in enumerate(dummy_materials):
        if existing.course_id == material.course_id and existing.material_id == material.material_id:
            dummy_materials[idx] = material
            return material
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Material not found.")
