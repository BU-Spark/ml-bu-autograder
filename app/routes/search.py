from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, HttpUrl

from app.models.course import Course
from app.services.azure_blob_service import AzureBlobService
from app.services.azure_embedding_service import CohereEmbeddingService, EmbeddingInputType
from app.services.vector_db_service import ChromaDBService
from app.utils.jwt_service import JWTService


router = APIRouter()
get_user = JWTService.get_instance().from_authorization_header


class MaterialSearchHit(BaseModel):
    id: str = Field(..., description="Blob path of the chunk (vector ID)")
    semester: str
    course_id: str
    material_id: str
    chunk_id: str
    data_type: str = Field(..., description="Chunk type (e.g., txt, png)")
    page_num: Optional[List[int]] = Field(default=None, description="Page numbers associated with this chunk if any")
    preview_text: Optional[str] = Field(default=None, description="Short text preview if text chunk")
    sas_url: HttpUrl = Field(..., description="Time-limited URL to fetch the chunk")


@router.get(
    "/search/materials",
    response_model=List[MaterialSearchHit],
    summary="search course stuff",
    description="finds relevant course material chunks using vector search"
)
async def search_materials(
    semester: str = Query(..., description="Semester (e.g., fall2024)"),
    course_id: str = Query(..., description="Course identifier (e.g., cs101)"),
    q: str = Query(..., description="Search query"),
    top_k: int = Query(5, ge=1, le=50, description="Number of results to return"),
    include_preview: bool = Query(True, description="Include short text preview for text chunks"),
    user_meta=Depends(get_user),
):
    # check if course is valid first
    Course(semester=semester, course_id=course_id)

    blob_svc = AzureBlobService.get_instance()
    usr = blob_svc.get_user(user_meta.user_email)
    if usr is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found.")
    if (semester, course_id) not in usr.authenticated_courses:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="nope, not allowed")

    # turn query into vector
    embed_svc = CohereEmbeddingService.get_instance()
    if embed_svc is None:
        raise HTTPException(status_code=500, detail="embedding thing broke")
    qvec = embed_svc.embed_text(q, EmbeddingInputType.SEARCH_QUERY)

    # find similar vectors
    db = ChromaDBService.get_instance()
    if db is None:
        raise HTTPException(status_code=500, detail="vector db not working")
    res = db.search(semester, course_id, [qvec], top_k=top_k) or []
    if not res:
        return []
    ids = res[0] if isinstance(res[0], list) else res
    if not ids:
        return []

    # get the actual chunks
    chunks = blob_svc.get_chunks_from_blob_path(ids)
    hits = []

    for i, path in enumerate(ids):
        if i >= len(chunks) or chunks[i] is None:
            continue
        fname, chunk = chunks[i]

        # parse the blob path - should be like course/sem/course/course_material/mat_id/chunks/chunk.ext
        parts = path.split("/")
        if len(parts) < 7 or parts[0] != "course" or parts[3] != "course_material":
            continue  # skip weird paths
        sem = parts[1]
        cid = parts[2]
        mat_id = parts[4]
        chunk_file = parts[6]
        chnk_id = chunk_file.split(".")[0]

        # get downloadable url
        sas_url = blob_svc.generate_sas_url(path)

        # try to get preview text
        prev = None
        if include_preview and getattr(chunk.data_type, "is_text", lambda: False)():
            try:
                txt = chunk.get_as_string()
                prev = txt[:200]  # first 200 chars
            except:
                prev = None

        # try to get page numbers if they exist
        pages = None
        try:
            meta = getattr(chunk, "metadata", None) or {}
            pages = meta.get("page_num") if isinstance(meta, dict) else None
        except:
            pages = None

        hits.append(MaterialSearchHit(
            id=path,
            semester=sem,
            course_id=cid,
            material_id=mat_id,
            chunk_id=chnk_id,
            data_type=getattr(chunk.data_type, "extension", str(chunk.data_type)),
            page_num=pages,
            preview_text=prev,
            sas_url=sas_url,
        ))

    return hits

