import json
import os
import requests
from typing import List

from fastapi import APIRouter, HTTPException, Query, status

from app.models.token import AccessToken
from app.models.user import User, PersonalAuthenticationToken
from app.utils import JWTService
from app.utils.azure_blob_service import AzureBlobService

router = APIRouter()
user_from_auth = JWTService.get_instance().from_authorization_header

jwt_service = JWTService.get_instance()
blob_service = AzureBlobService.get_instance()

# Load Google OAuth client secrets
with open(os.getenv("GOOGLE_OAUTH_CLIENT_FILE", "client_secret.json"), "r") as f:
    google_oauth_config = json.load(f)

GOOGLE_CLIENT_ID = google_oauth_config["web"]["client_id"]
GOOGLE_CLIENT_SECRET = google_oauth_config["web"]["client_secret"]
GOOGLE_REDIRECT_URI = google_oauth_config["web"]["redirect_uris"][0]
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"

# Dummy in-memory storage for access tokens
dummy_access_tokens = [
    AccessToken(token_name="token_1", token_expiry=None)
]

#TODO
@router.post(
    "/token",
    response_model=AccessToken,
    summary="Create Access Token",
    description="Creates a new access token for programmatic API access for the authenticated user.",
    responses={
        400: {"description": "Invalid parameters."},
        401: {"description": "Requester is not authenticated."},
    }
)
async def create_access_token(
        token_name: str = Query(...,
                                description="Friendly name for the token.  "
                                            "Only alphanumeric characters and underscores are allowed."
                                            "Defaults to 'token_n' (where n is a number).")
):
    #create a new access token and stores it in the dummy_access_tokens list

    #added checking for duplicate token names
    if any(token.token_name == token_name for token in dummy_access_tokens):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token name already exists."
        )
    new_token = AccessToken(token_name=token_name, token_expiry=None)
    dummy_access_tokens.append(new_token)

    # uploads the dummy data to Azure Blob Storage
    return new_token


@router.delete(
    "/token",
    summary="Delete Access Token",
    description="Deletes an existing access token.",
    responses={
        400: {"description": "token_name is missing or invalid."},
        404: {"description": "Token not found."},
        403: {"description": "Authenticated but access is not allowed."}
    }
)
async def delete_access_token(
        token_name: str = Query(..., description="Unique identifier of the access token to delete.")
):
    blob_uploader = AzureBlobService.get_instance()
    for token in dummy_access_tokens:
        if token.token_name == token_name:
            dummy_access_tokens.remove(token)
            return {"message": "Token deleted successfully."}
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Token not found.")


@router.get(
    "/tokens",
    response_model=List[AccessToken],
    summary="List Access Tokens",
    description="Retrieves active access tokens for the authenticated user.",
    responses={
        401: {"description": "Requester is not authenticated."},
        403: {"description": "Authenticated but access is not allowed."}
    }
)
async def list_access_tokens():
    blob_uploader = AzureBlobService.get_instance()
    return dummy_access_tokens


@router.get(
    "/google_oauth",
    summary="Google OAuth Callback",
    description="Callback endpoint for processing Google OAuth and extracting the authentication token.",
    responses={
        400: {"description": "Missing required OAuth parameters."},
        401: {"description": "Invalid OAuth parameters or unauthorized access to Google authentication endpoints."}
    }
)
async def google_oauth(
        access_token: str = Query(..., description="Access token provided by Google."),
        expires_in: int = Query(..., description="Token expiry time in seconds."),
        refresh_token: str = Query(..., description="Refresh token provided by Google."),
        scope: str = Query(..., description="Scope of the access token."),
        token_type: str = Query(..., description="Type of the token, usually 'Bearer'."),
        id_token: str = Query(..., description="ID token provided by Google.")
):
    """
    Exchanges the authorization code for an access token and ID token.
    """
    # Exchange authorization code for tokens
    token_data = {
        "code": code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "grant_type": "authorization_code"
    }

    response = requests.post(GOOGLE_TOKEN_URL, data=token_data)
    if response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization code or token exchange failed."
        )

    tokens = response.json()
    access_token = tokens["access_token"]
    id_token = tokens.get("id_token")

    # Decode ID token (JWT)
    user_info = jwt_service.decode_jwt(id_token)
    if not user_info:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Failed to verify ID token."
        )

    # Create user object
    user = User(
        first_name=user_info.get("given_name", ""),
        last_name=user_info.get("family_name", ""),
        user_email=user_info.get("email")
    )

    # Generate a JWT token for user authentication
    jwt_token = jwt_service.create_jwt({"email": user.user_email})
    personal_auth_token = PersonalAuthenticationToken(
        user_email=user.user_email,
        authentication_token=jwt_token
    )

    # Store user authentication details in Azure Blob Storage

    user_auth_data = {
        "user": user.model_dump(),
        "authentication_token": personal_auth_token.model_dump(),
        "google_tokens": tokens
    }
    # Upload user data to Azure Blob Storage
    #blob_service.upload_user(user_auth_data.user)

    return user_auth_data

@router.get(
    "/google_oauth_url",
    summary="Get Google OAuth URL",
    description="Returns the Google OAuth URL for redirecting users to authentication.",
)
async def get_oauth_url():
    client_id = "your_google_client_id"
    redirect_uri = "your_redirect_uri"
    scope = "openid email profile"
    oauth_url = (
        f"https://accounts.google.com/o/oauth2/auth?"
        f"client_id={GOOGLE_CLIENT_ID}&"
        f"redirect_uri={GOOGLE_REDIRECT_URI}&"
        f"response_type=code&"
        f"scope={scope}&"
        f"access_type=offline&"
        f"prompt=consent"
    )
    return {"oauth_url": oauth_url}
