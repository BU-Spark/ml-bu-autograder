from typing import List

from fastapi import APIRouter, HTTPException, status, Query

from app.models.token import AccessToken
from app.models.user import User, PersonalAuthenticationToken
from app.utils.azure_blob_service import AzureBlobService

router = APIRouter()

# Dummy in-memory storage for access tokens
dummy_access_tokens = [
    AccessToken(token_name="token_1", token_id="abc123", token_expiry=None)
]


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
        token_name: str = Query(..., description="Friendly name for the token. Defaults to 'token_n' (where n is a number).")
):
    new_token = AccessToken(token_name=token_name, token_id="newtoken123", token_expiry=None)
    dummy_access_tokens.append(new_token)
    return new_token


@router.delete(
    "/token",
    summary="Delete Access Token",
    description="Deletes an existing access token.",
    responses={
        400: {"description": "token_id is missing or invalid."},
        404: {"description": "Token not found."},
        403: {"description": "Authenticated but access is not allowed."}
    }
)
async def delete_access_token(
        token_id: str = Query(..., description="Unique identifier of the access token to delete.")
):
    blob_uploader = AzureBlobService.get_instance()
    for token in dummy_access_tokens:
        if token.token_id == token_id:
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
    dummy_user = User(first_name="John", last_name="Doe", user_email="john.doe@example.com")
    dummy_pat = PersonalAuthenticationToken(user_email="user123@example.com", authentication_token="dummy_jwt_token")
    return {"user": dummy_user, "personal_authentication_token": dummy_pat}


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
        f"client_id={client_id}&"
        f"redirect_uri={redirect_uri}&"
        f"response_type=code&"
        f"scope={scope}&"
        f"access_type=offline&"
        f"prompt=consent"
    )
    return {"oauth_url": oauth_url}
