import logging
import uuid
from typing import List

from fastapi import APIRouter, HTTPException, Query, Body, Depends
from pydantic import FilePath, ValidationError

from app.models import Course
from app.models.course_material import CourseMaterialData, CourseMaterialReference
from app.utils import get_str_var
from app.models import UserToken
from app.utils.jwt_service import JWTService
from app.services.azure_blob_service import AzureBlobService
from app.services.azure_vector_service import AzureVectorService

router = APIRouter()
user_from_auth = JWTService.get_instance().from_authorization_header


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
    # validate params by attempting to create a course object
    Course(semester=semester, course_id=course_id)

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
    # validate params by attempting to create a course object
    Course(semester=semester, course_id=course_id)

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
    save_path = FilePath(f"{get_str_var('TEMP_FILES_DIR')}/{random_uuid}.course_materials.json")

    # A background process will pick this up and process it trust.
    # See app/utils/bg_material_processor.py.
    with open(save_path, 'w') as f:
        f.write(material.model_dump_json(indent=4))

    return material


async def delete_course_material(
        semester: str = Query(..., description="Semester of the course."),
        course_id: str = Query(..., description="Identifier of the course."),
        material_id: str = Query(..., description="Unique identifier of the material to delete."),
        user_meta: UserToken = Depends(user_from_auth),
):
    # validate params by attempting to create a course object
    try:
        Course(semester=semester, course_id=course_id)
    except ValueError as e: # Catch potential validation errors from Course model
         raise HTTPException(status_code=400, detail=f"Invalid parameters: {e}")

    blob_uploader = AzureBlobService.get_instance()
    azure_vector_service = AzureVectorService.get_instance()

    # Check if the course exists
    course_exists = blob_uploader.course_exists(semester, course_id)
    if not course_exists:
        raise HTTPException(status_code=404, detail="Course does not exist.")

    # Check if user has perms on course
    user = blob_uploader.get_user(user_meta.user_email) # Consider error handling if user not found
    if not user or not user.authenticated_courses.__contains__((semester, course_id)):
        raise HTTPException(status_code=403, detail="Authenticated user lacks permissions for this course.")

    # Check if material exists in blob storage
    if not blob_uploader.course_material_exists(semester, course_id, material_id):
        raise HTTPException(status_code=404, detail="Course material does not exist.")

    # --- Vector Deletion Logic ---
    # Step 1: Find the IDs (chunk paths) of vectors associated with this material
    try:
        chunk_paths = blob_uploader.find_chunks_paths(
            semester_key=semester,
            course_id=course_id,
            material_id=material_id
        )
    except Exception as e:
        # Log the error but proceed to delete the blob; vector cleanup might need manual intervention
        logging.error(f"Error finding chunk paths for {semester}/{course_id}/{material_id}: {e}", exc_info=True)
        chunk_paths = [] # Ensure chunk_paths is defined

    # Step 2: Delete the associated vectors if found
    if chunk_paths:
        logging.info(f"Attempting to delete {len(chunk_paths)} vector documents associated with material ID {material_id}.")
        try:
            # Assuming delete_documents_by_ids handles the actual deletion call
            azure_vector_service.delete_documents_by_ids(chunk_paths)
            logging.info(f"Vector deletion request sent for material ID {material_id}.")
            # Note: delete_documents_by_ids might be async or batch, success here means request sent.
        except Exception as e:
             # Log the error but proceed to delete the blob; vector cleanup might need manual intervention
            logging.error(f"Error deleting vectors for material ID {material_id}: {e}", exc_info=True)
    else:
        logging.warning(f"No associated vector chunk paths found for material ID {material_id}. Skipping vector deletion.")
    # --- End Vector Deletion Logic ---

    # Step 3: Delete the material from blob storage
    try:
        blob_uploader.delete_course_material(semester, course_id, material_id)
        logging.info(f"Successfully deleted blob material: {semester}/{course_id}/{material_id}")
    except Exception as e:
         # If blob deletion fails after potential vector deletion, we might have orphaned vectors.
         logging.error(f"Failed to delete blob material {semester}/{course_id}/{material_id}: {e}", exc_info=True)
         # Depending on requirements, you might want to raise 500 here or attempt rollback (complex)
         raise HTTPException(status_code=500, detail="Failed to delete material from storage after attempting vector cleanup.")


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
    """
    Updates an existing course material.

    Workflow:
    1. Validate input and user permissions.
    2. Check if the material to update exists.
    3. Find vector IDs (chunk paths) associated with the current material version.
    4. Delete these old vectors from Azure Cognitive Search.
    5. Upload/overwrite the material content in Azure Blob Storage with the new data.
    6. Save metadata to trigger a background process to vectorize the *new* content.
    """
    blob_uploader = AzureBlobService.get_instance()
    azure_vector_service = AzureVectorService.get_instance()

    # --- Step 1: Validate input and user permissions ---
    try:
        # Validate semester/course_id structure
        Course(semester=material.semester, course_id=material.course_id)
    except (ValidationError, ValueError) as e: # Catch Pydantic and other validation errors
         raise HTTPException(status_code=400, detail=f"Invalid parameters: {e}")

    # Check if the course itself exists (optional but good practice)
    if not blob_uploader.course_exists(material.semester, material.course_id):
        # Adding this check for clarity, though the material check later might imply it.
        raise HTTPException(status_code=404, detail="Course specified does not exist.")

    # Check if user has permissions for this course
    try:
        user = blob_uploader.get_user(user_meta.user_email)
        if not user or not user.authenticated_courses.__contains__((material.semester, material.course_id)):
            raise HTTPException(status_code=403, detail="Authenticated user lacks permissions for this course.")
    except Exception as e: # Catch potential errors fetching user
        logging.error(f"Error checking user permissions for {user_meta.user_email}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error verifying user permissions.")

    # --- Step 2: Check if the specific material to update exists ---
    # Use course_material_exists, not get_course_material unless you need the old data
    if not blob_uploader.course_material_exists(material.semester, material.course_id, material.material_id):
        raise HTTPException(status_code=404, detail="Course material to be updated does not exist.")

    # --- Step 3: Find vector IDs (chunk paths) for the *current* material version ---
    old_chunk_paths: List[str] = []
    try:
        # Use the identifiers from the input 'material' as they define what we are updating
        old_chunk_paths = blob_uploader.find_chunks_paths(
            semester_key=material.semester,
            course_id=material.course_id,
            material_id=material.material_id
        )
        logging.info(f"Found {len(old_chunk_paths)} old chunk paths for material ID {material.material_id}.")
    except Exception as e:
        # Log error but proceed cautiously. We might orphan vectors if deletion fails later.
        logging.error(f"Error finding old chunk paths for updating {material.semester}/{material.course_id}/{material.material_id}: {e}", exc_info=True)
        # Decide if this error should halt the process. For now, we log and continue.

    # --- Step 4: Delete the old vectors ---
    if old_chunk_paths:
        logging.info(f"Attempting to delete {len(old_chunk_paths)} old vector documents for material ID {material.material_id}.")
        try:
            # Call the vector service to delete documents by their IDs (the chunk paths)
            azure_vector_service.delete_documents_by_ids(old_chunk_paths)
            # Note: Success here likely means the delete request was accepted, actual deletion might be async.
            logging.info(f"Old vector deletion request successful for material ID {material.material_id}.")
        except Exception as e:
             # Log the error. Decide if this failure is critical enough to stop the update.
             # If we proceed, old vectors might remain (orphaned).
             logging.error(f"Error sending deletion request for old vectors of material ID {material.material_id}: {e}", exc_info=True)
             # Optionally: raise HTTPException(status_code=500, detail="Failed to clean up old search index entries.")

    # --- Step 5: Upload/overwrite the material content in Azure Blob Storage ---
    try:
        # This method should handle overwriting the blob based on semester/course/material_id
        blob_uploader.upload_course_material(material)
        logging.info(f"Successfully uploaded updated blob content for: {material.semester}/{material.course_id}/{material.material_id}")
    except Exception as e:
        logging.error(f"Failed to upload updated blob content for {material.semester}/{material.course_id}/{material.material_id}: {e}", exc_info=True)
        # This is critical. If vectors were deleted but blob upload fails, the material is gone.
        # Consider complex rollback logic or accept data loss state and raise 500.
        raise HTTPException(status_code=500, detail="Failed to update material content in storage after cleaning up search index.")

    # --- Step 6: Save metadata to trigger background processing for *new* vectors ---
    random_uuid = uuid.uuid4()
    # Using a unique filename prevents race conditions if multiple updates happen quickly
    save_path_str = f"{get_str_var('TEMP_FILES_DIR')}/{random_uuid}.{material.material_id}.update.json"
    try:
        save_path = FilePath(save_path_str) # Validate path
        with open(save_path, 'w') as f:
            # Write the metadata of the *newly uploaded* material.
            # Ensure model_dump_json doesn't include the large binary data itself.
            f.write(material.model_dump_json(indent=4))
        logging.info(f"Saved updated metadata for background vectorization: {save_path}")
    except (IOError, ValidationError, Exception) as e: # Catch file IO, path validation or other errors
        logging.error(f"Failed to save metadata for background processing after update for {material.material_id}: {e}", exc_info=True)
        # The blob is updated, but new vectors won't be created automatically.
        # Return success but maybe include a warning, or raise 500? Let's raise 500 for clarity.
        raise HTTPException(status_code=500, detail="Material content updated, but failed to queue for search index update.")

    # --- Return reference to the updated material ---
    # Ensure CourseMaterialReference can be created from CourseMaterialData or has necessary fields
    try:
        return CourseMaterialReference(
            semester=material.semester,
            course_id=material.course_id,
            material_id=material.material_id,
            file_name=material.file_name # Make sure file_name exists on CourseMaterialData
        )
    except Exception as e:
         logging.error(f"Failed create response model for updated material {material.material_id}: {e}", exc_info=True)
         # Should ideally not happen if models are correct, but handle defensively.
         # Return a simple success message if the model fails? Or raise 500?
         # For now, let's stick to the defined response model or fail.
         raise HTTPException(status_code=500, detail="Material updated but failed to format response.")
