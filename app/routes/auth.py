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
jwt_service = JWTService.get_instance()
blob_service = AzureBlobService.get_instance()

# Load Google OAuth client secrets
with open(os.getenv("GOOGLE_OAUTH_CLIENT_FILE", "./client_secrets.json"), "r") as f:
    google_oauth_config = json.load(f)

GOOGLE_CLIENT_ID = google_oauth_config["web"]["client_id"]
GOOGLE_CLIENT_SECRET = google_oauth_config["web"]["client_secret"]
GOOGLE_REDIRECT_URI = google_oauth_config["web"]["redirect_uris"][0]
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"

# Dummy in-memory storage for access tokens
dummy_access_tokens = [
    AccessToken(token_name="token_1", token_id="abc123", token_expiry=None)
]


@router.post(
    "/token",
    response_model=AccessToken,
    summary="Create Access Token",
    description="Creates a new access token for programmatic API access."
)
async def create_access_token(
    token_name: str = Query(..., description="Friendly name for the token.")
):
    #create a new access token and stores it in the dummy_access_tokens list

    #added checking for duplicate token names
    if any(token.token_name == token_name for token in dummy_access_tokens):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token name already exists."
        )
    new_token = AccessToken(token_name=token_name, token_id="newtoken123", token_expiry=None)
    dummy_access_tokens.append(new_token)

    # uploads the dummy data to Azure Blob Storage
    blob_service.upload_data("tokens.json", json.dumps([t.model_dump() for t in dummy_access_tokens]))

    return new_token


@router.delete(
    "/token",
    summary="Delete Access Token",
    description="Deletes an existing access token."
)
async def delete_access_token(
    token_id: str = Query(..., description="Unique identifier of the access token to delete.")
):
    blob_uploader = AzureBlobService.get_instance()
    for token in dummy_access_tokens:
        if token.token_id == token_id:
            dummy_access_tokens.remove(token)

            # Upload Azure Blob Storage
            #blob_service.upload_data("tokens.json", json.dumps([t.model_dump() for t in dummy_access_tokens]))

            return {"message": "Token deleted successfully."}

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Token not found.")

@router.get(
    "/tokens",
    response_model=List[AccessToken],
    summary="List Access Tokens",
    description="Retrieves active access tokens for the authenticated user."
)
async def list_access_tokens():
    blob_uploader = AzureBlobService.get_instance()
    return dummy_access_tokens

@router.get(
    "/google_oauth_url",
    summary="Get Google OAuth URL",
    description="Returns the Google OAuth URL for redirecting users to authentication."
)
async def get_oauth_url():
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

@router.get(
    "/google_oauth",
    summary="Google OAuth Callback",
    description="Handles Google OAuth callback and retrieves tokens."
)
async def google_oauth(
    code: str = Query(..., description="Authorization code from Google.")
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
    # We can go with the BlobUploader if you want 
    blob_service.upload_data(f"auth/{user.user_email}.json", json.dumps(user_auth_data))

    return user_auth_data
