import uuid
from typing import List, Dict

from azure.ai.inference.models import EmbeddingInputType
from fastapi import APIRouter, HTTPException, Query, Body, Depends
from pydantic import FilePath

from app.models import Course
from app.models.course_material import CourseMaterialData, CourseMaterialReference
from app.models.uploaded_file import DataType
from app.utils import JWTService, UserToken, get_str_var, AzureEmbeddingService
from app.utils.azure_blob_service import AzureBlobService
from app.utils.bytes_to_doc_util import Document

router = APIRouter()
user_from_auth = JWTService.get_instance().from_authorization_header


def process_course_material(json_str: str):
    """
    Processes submitted course material. This function is called by
    bg_material_processor.py. See its logic for more details
    """

    #  Step 0: Convert the json string into CourseMaterialData
    course_material = CourseMaterialData.model_validate_json(json_str)
    #  Step 2: Convert the binary data of the course material into document chunks using
    #          bytes_to_doc_util.py.
    to_doc_func = course_material.data.data_type.get_to_doc_func()
    document: Document = to_doc_func(
        f"{course_material.material_id}.{course_material.data.data_type.extension}",
        course_material.data.content,
        True
    )
    #  Step 3: Upload these chunks to azure and get the blob paths
    blob_uploader = AzureBlobService.get_instance()
    uploaded_chunks: Dict[int, str] = blob_uploader.upload_material_chunks(
        course_material.semester,
        course_material.course_id,
        course_material.material_id,
        document
    )
    #  Step 4: Vectorize the chunks (text or images).
    embedding_service = AzureEmbeddingService.get_instance()
    vectorized_chunks: Dict[str, List[float]] = {}  # the key is blob_path, value is vector
    text_paths: List[str] = []
    texts: List[str] = []
    for chunk_id, chunk_path in uploaded_chunks.items():
        # if the way this is handled looks a bit convoluted, just know there is logic to the madness:
        # specifically there are performance benefits to vectorizing a batch of texts together
        # but on the other hand, images cannot be batched and must be processed individually
        chunked_doc = document.get_chunk(chunk_id)
        if chunked_doc.data_type.is_image():
            vectorized_chunks[chunk_path] = embedding_service.embed_image(
                chunked_doc.data_type.mime_type, chunked_doc.get_as_bytes()
            )
        elif chunked_doc.data_type == DataType.TEXT:
            text_paths.append(chunk_path)
            texts.append(chunked_doc.get_as_string())
        else:
            # the data types should only be either image or text
            raise Exception(f"Unsupported data type: {course_material.data.data_type}")
    vectors = embedding_service.embed_texts(texts, EmbeddingInputType.TEXT)
    for blob_path, vector in zip(text_paths, vectors):
        vectorized_chunks[blob_path] = vector
    #  Step 5: Take the pairs of the blob paths and vectorized chunks, and upload them
    #          to Azure's AI search. And thats it!
    # TODO: josh you do this

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
