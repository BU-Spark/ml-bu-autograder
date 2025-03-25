from typing import Optional

from fastapi import APIRouter, Body
from pydantic import BaseModel

from app.models.user import User
from app.utils.azure_blob_service import AzureBlobService


class UserPreferencesUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    dark_mode: Optional[bool] = None


router = APIRouter()

# Dummy storage for a user (simulate the currently authenticated user)
dummy_user = User(
    first_name="John",
    last_name="Doe",
    dark_mode=False,
    user_email="john.doe@example.com"
)


@router.patch(
    "/user",
    response_model=User,
    summary="Update User Preferences",
    description="Updates the authenticated user's profile preferences, including first name, last name, and dark mode "
                "settings.",
    responses={
        400: {"description": "Missing or invalid parameters."},
        401: {"description": "Requester is not authenticated."},
    }
)
async def update_user_preferences(
        preferences: UserPreferencesUpdate = Body(..., description="User preferences to update.")
):
    blob_uploader = AzureBlobService.get_instance()
    # In a real-world scenario, you'd retrieve the authenticated user from the request context
    # and update their record in your persistent datastore.
    if preferences.first_name is not None:
        dummy_user.first_name = preferences.first_name
    if preferences.last_name is not None:
        dummy_user.last_name = preferences.last_name
    if preferences.dark_mode is not None:
        dummy_user.dark_mode = preferences.dark_mode

    return dummy_user


@router.get(
    "/user",
    summary="Get User Data",
    description="Retrieves the authenticated user's profile information.",
    response_model=User,
    responses={
        401: {"description": "Requester is not authenticated."},
    }
)
async def get_user() -> User:
    blob_uploader = AzureBlobService.get_instance()
    return dummy_user
