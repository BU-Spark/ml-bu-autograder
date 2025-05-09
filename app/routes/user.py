from typing import Optional

from fastapi import APIRouter, Body, Depends
from pydantic import BaseModel

from app.models.user import User
from app.models import UserToken
from app.utils.jwt_service import JWTService
from app.services.azure_blob_service import AzureBlobService


class UserPreferencesUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    dark_mode: Optional[bool] = None


router = APIRouter()
user_from_auth = JWTService.get_instance().from_authorization_header

@router.patch(
    "/user",
    response_model=User,
    summary="Update User Preferences",
    description="Updates the authenticated user's profile preferences, including first name, last name, and dark mode "
                "settings.",
    responses={
        401: {"detail": "Requester is not authenticated."},
    }
)
async def update_user_preferences(
        preferences: UserPreferencesUpdate = Body(..., description="User preferences to update."),
        user_meta: UserToken = Depends(user_from_auth),
):
    blob_uploader = AzureBlobService.get_instance()
    user = blob_uploader.get_user(user_meta.user_email)
    updated = False
    if preferences.dark_mode is not None:
        user.dark_mode = preferences.dark_mode
        updated = True
    if preferences.first_name is not None:
        user.first_name = preferences.first_name
        updated = True
    if preferences.last_name is not None:
        user.last_name = preferences.last_name
        updated = True

    if updated:
        blob_uploader.upload_user(user)

    return user


@router.get(
    "/user",
    summary="Get User Data",
    description="Retrieves the authenticated user's profile information.",
    response_model=User,
    responses={
        401: {"detail": "Requester is not authenticated."},
    }
)
async def get_user(
    user_meta: UserToken = Depends(user_from_auth),
):
    blob_uploader = AzureBlobService.get_instance()
    return blob_uploader.get_user(user_meta.user_email)
