import datetime
import json
import os
import requests
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, status, Depends
from pydantic import EmailStr

from app.models.token import PersonalAccessToken, UserToken, WebsiteAccessToken
from app.models.user import User
from app.services.azure_blob_service import AzureBlobService
from app.utils.jwt_service import JWTService

router = APIRouter()
user_from_auth = JWTService.get_instance().from_authorization_header

jwt_service = JWTService.get_instance()
blob_service = AzureBlobService.get_instance()

# TODO FAHIM: USE ENVIRONMENT VARIABLES DONT HARDCODE
# Load Google OAuth client secrets
with open(os.getenv("GOOGLE_OAUTH_CLIENT_FILE", "client_secret.json"), "r") as f:
    google_oauth_config = json.load(f)

GOOGLE_CLIENT_ID = google_oauth_config["web"]["client_id"]
GOOGLE_CLIENT_SECRET = google_oauth_config["web"]["client_secret"]
GOOGLE_REDIRECT_URI = google_oauth_config["web"]["redirect_uris"][0]
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"

#TODO
@router.post(
    "/token",
    response_model=PersonalAccessToken,
    summary="Create Access Token",
    description="Creates a new access token for programmatic API access for the authenticated user.",
    responses={
        400: {"detail": "Invalid parameters."},
        401: {"detail": "Requester is not authenticated."},
    }
)
async def create_access_token(
        token_name: Optional[str] = Query(...,
                                description="Friendly name for the token.  "
                                            "Only alphanumeric characters and underscores are allowed."
                                            "Defaults to 'token_n' (where n is a number)."),
        token_expiry: Optional[datetime.datetime] = Query(...),
        user_meta: UserToken = Depends(user_from_auth),
):
    if isinstance(user_meta, WebsiteAccessToken):
        ...  # good
    elif isinstance(user_meta, PersonalAccessToken):
        # not allowed
        raise HTTPException(status_code=403, detail="Personal Access Tokens are not permitted to access this endpoint.")

    # normalize token name
    token_name = PersonalAccessToken.validate_identifier(token_name) if token_name is not None else token_name

    # get blob service
    blob_uploader = AzureBlobService.get_instance()
    # get jwt service
    jwt_service = JWTService.get_instance()

    if token_expiry is None:
        token_expiry = datetime.datetime.max

    # Added checking for duplicate token names OR create a unique token name
    existing_tokens = blob_uploader.list_personal_access_tokens(user_meta.user_email)
    if token_name is not None:
        if any(token.token_name == token_name for token in existing_tokens):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token name already exists."
            )
    else:
        # generate a unique token name
        i = 0
        while True:
            token_name = 'token_{}'.format(i)
            # yeah yeah, this is kinda inefficient but computers are
            # fast and WHOSE GONNA HAVE 1000 tokens??
            if token_name not in existing_tokens:
                break

    new_token = PersonalAccessToken(user_email=user_meta.user_email, token_name=token_name, token_expiry=token_expiry)
    blob_uploader.upload_token(user_meta.user_email, new_token)

    jwt_secret = jwt_service.create_access_token(new_token)

    return {
        "access_token": new_token,
        "secret": jwt_secret
    }


@router.delete(
    "/token",
    summary="Delete Access Token",
    description="Deletes an existing access token.",
    responses={
        400: {"detail": "token_name is missing or invalid."},
        404: {"detail": "Token not found."},
        403: {"detail": "Authenticated but access is not allowed."}
    }
)
async def delete_access_token(
        token_name: str = Query(..., description="Unique identifier of the access token to delete."),
        user_meta: UserToken = Depends(user_from_auth),
):
    if isinstance(user_meta, WebsiteAccessToken):
        ...  # good
    elif isinstance(user_meta, PersonalAccessToken):
        # not allowed
        raise HTTPException(status_code=403, detail="Personal Access Tokens are not permitted to access this endpoint.")
    blob_uploader = AzureBlobService.get_instance()

    if not blob_uploader.token_exists(user_meta.user_email, token_name):
        raise HTTPException(status_code=404, detail="Token not found.")

    blob_uploader.delete_token(user_meta.user_email, token_name)

    return {"detail":  "The access token has been deleted."}


@router.get(
    "/tokens",
    response_model=List[PersonalAccessToken],
    summary="List Access Tokens",
    description="Retrieves active access tokens for the authenticated user.",
    responses={
        401: {"detail": "Requester is not authenticated."},
        403: {"detail": "Authenticated but access is not allowed."}
    }
)
async def list_access_tokens(user_meta: UserToken = Depends(user_from_auth)):
    if isinstance(user_meta, WebsiteAccessToken):
        ...  # good
    elif isinstance(user_meta, PersonalAccessToken):
        # not allowed
        raise HTTPException(status_code=403, detail="Personal Access Tokens are not permitted to access this endpoint.")
    blob_uploader = AzureBlobService.get_instance()
    return blob_uploader.list_personal_access_tokens(user_meta.user_email)


@router.get(
    "/google_oauth",
    summary="Google OAuth Callback",
    description="Callback endpoint for processing Google OAuth and extracting the authentication token.",
    responses={
        400: {"detail": "Missing required OAuth parameters."},
        401: {"detail": "Invalid OAuth parameters or unauthorized access to Google authentication endpoints."}
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
    # TODO FAHIM: make sure this code works too
    #  Exchange authorization code for tokens
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

    # TODO FAHIM: query google api to get their email
    #  make sure to handle any errors properly
    email: EmailStr = ...

    azure_blob_uploader = AzureBlobService.get_instance().get_instance()
    user = azure_blob_uploader.get_user(email)

    if user is None:
        # TODO FAHIM: get user's first and last name from google api
        #  make sure to handle any errors properly
        first_name = ...
        last_name = ...
        user = User(
            user_email=email,
            first_name=first_name,
            last_name=last_name,
        )

    # Generate a JWT token for user authentication
    jwt_token = jwt_service.create_user_jwt(user)

    return {"authentication_token": jwt_token, "user": user}

@router.get(
    "/google_oauth_url",
    summary="Get Google OAuth URL",
    description="Returns the Google OAuth URL for redirecting users to authentication.",
)
async def get_oauth_url():
    # TODO FAHIM: complete this
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
