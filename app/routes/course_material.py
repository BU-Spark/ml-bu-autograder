# course_material.py

import re
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, Body, Depends, Path # Added Path back just in case, though not used in this version
from pydantic import BaseModel, Field, field_validator # Import necessary Pydantic parts

from app.models import Course
from app.models.course_material import CourseMaterial # Import the main model
# --- CORRECTED IMPORT: Import the structure needed for the 'data' field ---
from app.models.uploaded_file import UploadedFileData # Assuming this is where UploadedFileData lives
# --- END CORRECTION ---

from app.utils import JWTService, UserToken
from azure.storage.blob import ContainerClient
from app.utils.azure_blob_service import AzureBlobService
import logging

logger = logging.getLogger(__name__)

# --- Pydantic Model specifically for the POST request body ---
class CourseMaterialCreate(BaseModel):
    """Payload for creating a new course material via POST."""
    course_id: str
    semester: str
    material_name: str
    additional_notes: Optional[str] = None
    # --- CORRECTED TYPE HINT: Use the imported model for file data ---
    data: UploadedFileData = Field(..., description="The actual file data including content and metadata.")
    # --- END CORRECTION ---

    # Optional validators (example shown)
    @field_validator("course_id", mode="before")
    def normalize_lowercase(cls, value: str) -> str:
        """Converts course_id to lowercase and trims spaces."""
        return value.strip().lower()

    @field_validator("semester", mode='before')
    def validate_semester_format(cls, value: str) -> str:
        """Validates semester format, converts to lowercase, trims spaces."""
        value = value.strip()
        # Using the regex from the CourseMaterial model itself for consistency
        if not re.fullmatch(r"[a-z]{1,12}[0-9]{4}", value.lower()):
             raise ValueError("Semester is in an invalid format. "
                              "Correct format (case-insensitive) looks like: seasonYYYY. (e.g. spring2025)")
        return value.lower()

# --- Router Setup ---
router = APIRouter()
user_from_auth = JWTService.get_instance().from_authorization_header

# --- API Endpoints ---

@router.get(
    "/course_materials",
    response_model=List[CourseMaterial],
    summary="Get All Course Materials",
    # ... (rest of definition)
)
async def get_course_materials(
        semester: str = Query(..., description="Semester of the course."),
        course_id: str = Query(..., description="Identifier of the course."),
        user_meta: UserToken = Depends(user_from_auth),
):
    # validate params
    try:
        # Use validators directly if available, otherwise use model's
        semester = Course.validate_semester(semester) # Assuming Course model has this static/class method
        course_id = Course.normalize_lowercase(course_id) # Assuming Course model has this static/class method
    except ValueError as e:
         raise HTTPException(status_code=400, detail=str(e))
    except AttributeError:
         # Fallback if Course model doesn't have the methods directly callable like that
         try:
             temp_model = CourseMaterialCreate(semester=semester, course_id=course_id, material_name="dummy", data={"data_type":"dummy","content":"dummy","metadata":{}}) # Use create model for validation
             semester = temp_model.semester
             course_id = temp_model.course_id
         except ValueError as e:
              raise HTTPException(status_code=400, detail=str(e))


    blob_uploader = AzureBlobService.get_instance()

    # Auth Checks
    if not blob_uploader.course_exists(semester, course_id): raise HTTPException(status_code=404, detail="Course does not exist.")
    user = blob_uploader.get_user(user_meta.user_email)
    if not user or (semester, course_id) not in user.authenticated_courses: raise HTTPException(status_code=403, detail="User not found or access not allowed.")

    # Get all course materials
    try:
        materials = blob_uploader.list_course_materials(semester, course_id)
        # Ensure sorting by ID if needed (IDs are integers)
        if isinstance(materials, list):
            materials.sort(key=lambda m: m.material_id if hasattr(m, 'material_id') and isinstance(m.material_id, int) else float('inf'))
        return materials
    except Exception as e:
        logger.exception(f"Failed to list materials for {semester}/{course_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve course materials.")


@router.get(
    "/course_material",
    response_model=CourseMaterial,
    summary="Get Specific Course Material",
     # ... (rest of definition)
)
async def get_course_material(
        semester: str = Query(..., description="Semester of the course."),
        course_id: str = Query(..., description="Identifier of the course."),
        material_id: int = Query(..., description="Unique identifier of the specific material."),
        user_meta: UserToken = Depends(user_from_auth),
):
    # validate params (similar validation logic as above)
    try:
        semester = Course.validate_semester(semester)
        course_id = Course.normalize_lowercase(course_id)
    except ValueError as e:
         raise HTTPException(status_code=400, detail=str(e))
    except AttributeError:
         try:
             temp_model = CourseMaterialCreate(semester=semester, course_id=course_id, material_name="dummy", data={"data_type":"dummy","content":"dummy","metadata":{}})
             semester = temp_model.semester
             course_id = temp_model.course_id
         except ValueError as e:
              raise HTTPException(status_code=400, detail=str(e))

    blob_uploader = AzureBlobService.get_instance()

    # Auth Checks
    if not blob_uploader.course_exists(semester, course_id): raise HTTPException(status_code=404, detail="Course does not exist.")
    user = blob_uploader.get_user(user_meta.user_email)
    if not user or (semester, course_id) not in user.authenticated_courses: raise HTTPException(status_code=403, detail="User not found or access not allowed.")

    # Get specific course material
    try:
        material = blob_uploader.get_course_material(semester, course_id, material_id)
        if not material:
            raise HTTPException(status_code=404, detail="Course material does not exist.")
        return material
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
         logger.exception(f"Failed to get material {material_id} for {semester}/{course_id}: {e}")
         raise HTTPException(status_code=500, detail="Failed to retrieve course material.")


@router.post(
    "/course_material",
    response_model=CourseMaterial,
    summary="Upload Course Material",
    description="Uploads new course material. A unique integer ID will be generated.",
    # ... (rest of definition)
)
async def upload_course_material(
        # Use the corrected Create model
        material_data: CourseMaterialCreate = Body(..., description="Course material details and file data (without material_id)."),
        user_meta: UserToken = Depends(user_from_auth),
):
    blob_uploader = AzureBlobService.get_instance()
    # Semester/Course ID are validated by the Pydantic model now
    semester = material_data.semester
    course_id = material_data.course_id

    # Auth Checks
    if not blob_uploader.course_exists(semester, course_id):
        raise HTTPException(status_code=404, detail="Course does not exist.")
    user = blob_uploader.get_user(user_meta.user_email)
    if not user or (semester, course_id) not in user.authenticated_courses:
        raise HTTPException(status_code=403, detail="User not found or access not allowed.")

    try:
        # --- Generate Next Integer ID ---
        logger.info(f"Generating next material ID for {semester}/{course_id}")
        existing_materials = blob_uploader.list_course_materials(semester, course_id)
        max_id = -1
        if isinstance(existing_materials, list):
            for mat in existing_materials:
                if hasattr(mat, 'material_id') and mat.material_id is not None:
                    try:
                        current_id_int = int(str(mat.material_id))
                        if current_id_int > max_id:
                            max_id = current_id_int
                    except (ValueError, TypeError):
                        logger.warning(f"Ignoring non-integer material ID '{mat.material_id}' while calculating max ID for {semester}/{course_id}")
                else:
                     logger.warning(f"Existing material object missing 'material_id': {mat}")
        else:
            logger.error(f"list_course_materials did not return a list for {semester}/{course_id}. Type: {type(existing_materials)}")

        next_material_id = max_id + 1
        logger.info(f"Generated material_id: {next_material_id} for {semester}/{course_id}")
        # --- End ID Generation ---

        # --- Create the full CourseMaterial object ---
        # Use the fields from the validated material_data and the generated ID
        full_material = CourseMaterial(
            material_id=next_material_id,
            course_id=material_data.course_id, # Already validated
            semester=material_data.semester, # Already validated
            material_name=material_data.material_name,
            additional_notes=material_data.additional_notes,
            data=material_data.data # The nested data object is passed directly
        )
        # --- End Object Creation ---

        # Upload the material using the full object
        blob_uploader.upload_course_material(full_material)
        logger.info(f"Successfully uploaded material {next_material_id} for {semester}/{course_id}")

        # Return the complete object, including the generated ID
        return full_material

    except Exception as e:
        logger.exception(f"Failed during material upload or ID generation for {semester}/{course_id}: {e}")
        if isinstance(e, HTTPException): raise e
        raise HTTPException(status_code=500, detail="Failed to save course material.")


@router.delete(
    "/course_material",
    summary="Delete Course Material",
    # ... (rest of definition)
)
async def delete_course_material(
        semester: str = Query(..., description="Semester of the course."),
        course_id: str = Query(..., description="Identifier of the course."),
        material_id: int = Query(..., description="Unique identifier of the material to delete."),
        user_meta: UserToken = Depends(user_from_auth),
):
    # validate params (similar validation logic)
    try:
        semester = Course.validate_semester(semester)
        course_id = Course.normalize_lowercase(course_id)
    except ValueError as e:
         raise HTTPException(status_code=400, detail=str(e))
    except AttributeError:
        try:
             temp_model = CourseMaterialCreate(semester=semester, course_id=course_id, material_name="dummy", data={"data_type":"dummy","content":"dummy","metadata":{}})
             semester = temp_model.semester
             course_id = temp_model.course_id
        except ValueError as e:
             raise HTTPException(status_code=400, detail=str(e))

    blob_uploader = AzureBlobService.get_instance()

    # Auth Checks
    if not blob_uploader.course_exists(semester, course_id): raise HTTPException(status_code=404, detail="Course does not exist.")
    user = blob_uploader.get_user(user_meta.user_email)
    if not user or (semester, course_id) not in user.authenticated_courses: raise HTTPException(status_code=403, detail="User not found or access not allowed.")

    # Check if material exists before deleting
    try:
        material = blob_uploader.get_course_material(semester, course_id, material_id)
        if not material:
            logger.warning(f"Attempt to delete non-existent material {material_id} from {semester}/{course_id}")
            raise HTTPException(status_code=404, detail="Course material does not exist.")

        # Delete the material
        blob_uploader.delete_course_material(semester, course_id, material_id)
        logger.info(f"Deleted material {material_id} from {semester}/{course_id}")

        return {"detail":  "Course material deleted successfully."}
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.exception(f"Failed to delete material {material_id} from {semester}/{course_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete course material.")


@router.patch(
    "/course_material",
    response_model=CourseMaterial,
    summary="Update Course Material",
    description="Updates existing course material (name, notes). Does not re-upload file data.",
    # ... (rest of definition) ...
)
async def update_course_material(
        # --- CORRECTED: Expect the full CourseMaterial object directly ---
        material_update: CourseMaterial = Body(..., description="Full course material object with updated name/notes."),
        # --- END CORRECTION ---
        user_meta: UserToken = Depends(user_from_auth),
):
    blob_uploader = AzureBlobService.get_instance()

    # --- CORRECTED: Access fields directly from the input 'material_update' object ---
    semester = material_update.semester
    course_id = material_update.course_id
    material_id = material_update.material_id
    # --- END CORRECTION ---

    # Validate semester/course_id from payload
    try:
        # Use validators from the model itself if possible
        semester = material_update.__class__.validate_semester(semester)
        course_id = material_update.__class__.normalize_lowercase(course_id)
    except ValueError as e:
         raise HTTPException(status_code=400, detail=str(e))
    except AttributeError: # Fallback validation
        try:
             temp_model = CourseMaterialCreate(semester=semester, course_id=course_id, material_name=material_update.material_name, data=material_update.data)
             semester = temp_model.semester
             course_id = temp_model.course_id
        except ValueError as e:
             raise HTTPException(status_code=400, detail=str(e))


    # Auth Checks
    if not blob_uploader.course_exists(semester, course_id): raise HTTPException(status_code=404, detail="Course does not exist.")
    user = blob_uploader.get_user(user_meta.user_email)
    if not user or (semester, course_id) not in user.authenticated_courses: raise HTTPException(status_code=403, detail="User not found or access not allowed.")

    # Check if material exists using the ID from the payload
    try:
        existing_material = blob_uploader.get_course_material(semester, course_id, material_id)
        if not existing_material:
             logger.warning(f"Attempt to update non-existent material {material_id} in {semester}/{course_id}")
             raise HTTPException(status_code=404, detail="Course material does not exist.")

        # --- Logic Update: Avoid re-uploading file data if possible ---
        # If upload_course_material *only* updates based on ID and overwrites everything,
        # you might need a more specific update function in AzureBlobService
        # that only changes metadata fields without touching the blob content itself.
        # Assuming upload_course_material handles overwrite correctly for now:

        # Compare only the fields that *can* be updated (name, notes)
        # to avoid unnecessary writes if only the data object differs slightly (e.g., URL)
        if (existing_material.material_name != material_update.material_name or
                existing_material.additional_notes != material_update.additional_notes):

            logger.info(f"Updating metadata for material {material_id} in {semester}/{course_id}")
            # If your service function can update metadata separately:
            # blob_uploader.update_course_material_metadata(material_update)
            # If not, use the existing upload which overwrites:
            blob_uploader.upload_course_material(material_update) # Pass the full object from the request
        else:
            logger.info(f"No relevant metadata changes detected for material {material_id}. Skipping update.")
            # Return the existing material data if no changes were made to relevant fields
            return existing_material

        # --- End Logic Update ---


        # Return the updated material object (refetch for consistency if update was performed)
        updated_material = blob_uploader.get_course_material(semester, course_id, material_id)
        return updated_material if updated_material else material_update # Fallback to input if refetch fails

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.exception(f"Failed to update material {material_id} in {semester}/{course_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update course material.")