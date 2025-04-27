# In app/routes/user.py
import logging # Add import
from typing import Optional

from fastapi import APIRouter, Body, Depends, HTTPException, status # Add status
from pydantic import BaseModel

from app.models.user import User
<<<<<<< HEAD
# <<<--- Corrected: Import JWTService directly if needed, or rely on singleton --- >>>
from app.utils import JWTService
from app.utils.azure_blob_service import AzureBlobService
=======
from app.models import UserToken
from app.utils.jwt_service import JWTService
from app.services.azure_blob_service import AzureBlobService
>>>>>>> 1e49de1db1886ead0ccd3ca3b8f1f43b7dedf5fb

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
   # <<< --- ADD LOGGING --- >>>
    logging.info(f"PATCH /user requested by: {user_meta.user_email}")
    blob_uploader = AzureBlobService.get_instance()

    logging.debug(f"Fetching user data for update: {user_meta.user_email}")
    user = blob_uploader.get_user(user_meta.user_email) # get_user now has logging

    if not user:
         logging.error(f"User {user_meta.user_email} not found during PATCH /user request!")
         # Should not happen if token is valid, but good check
         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User profile not found.")

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
        logging.info(f"Updating user preferences for {user_meta.user_email}")
        try:
            blob_uploader.upload_user(user)
        except Exception as e:
             logging.error(f"Failed to upload updated user preferences for {user_meta.user_email}: {e}", exc_info=True)
             raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to save preferences.")
    else:
         logging.info(f"No preferences provided to update for {user_meta.user_email}")

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
    # <<< --- ADD LOGGING --- >>>
    logging.info(f"GET /user requested by: {user_meta.user_email}")
    blob_uploader = AzureBlobService.get_instance()

    logging.debug(f"Fetching user data for profile view: {user_meta.user_email}")
    user = blob_uploader.get_user(user_meta.user_email) # get_user now has logging

    if not user:
        logging.error(f"User {user_meta.user_email} not found during GET /user request!")
        # Return 404 if the user associated with a valid token doesn't exist in storage
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User profile not found.")

    return user