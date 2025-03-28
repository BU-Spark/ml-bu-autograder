from typing import List
from fastapi import APIRouter, HTTPException, status, Depends, Request
from authlib.integrations.starlette_client import OAuth
import os

from app.models.token import AccessToken
from app.models.user import User, PersonalAuthenticationToken
from app.utils import JWTService

router = APIRouter()

# Google OAuth Configuration
oauth = OAuth()
oauth.register(
    name="google",
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    authorize_url=os.getenv("GOOGLE_AUTHORIZATION_URL", "https://accounts.google.com/o/oauth2/auth"),
    token_url=os.getenv("GOOGLE_TOKEN_URL", "https://oauth2.googleapis.com/token"),
    userinfo_endpoint=os.getenv("GOOGLE_USER_INFO_URL", "https://www.googleapis.com/oauth2/v3/userinfo"),
    client_kwargs={"scope": "openid email profile"},
)

# Dummy in-memory storage for tokens
dummy_access_tokens = [
    AccessToken(token_name="token_1", token_id="abc123", token_expiry=None)
]


@router.get("/google_oauth_url", summary="Get Google OAuth URL")
async def get_oauth_url(request: Request):
    """
    Returns the Google OAuth URL for redirecting users to authentication.
    """
    redirect_uri = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/api/v1/auth/google_oauth_callback")
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/google_oauth_callback", summary="Google OAuth Callback")
async def google_oauth_callback(request: Request):
    """
    Callback endpoint for handling Google OAuth authentication and extracting user info.
    """
    try:
        token = await oauth.google.authorize_access_token(request)
        user_info = await oauth.google.parse_id_token(request, token)

        if not user_info:
            raise HTTPException(status_code=400, detail="Invalid Google authentication response")

        #dummy data for user creation
        dummy_user = User(
            first_name=user_info.get("first_name", ""),
            last_name=user_info.get("last_name", ""),
            user_email=user_info["email"]
        )

        # Generate JWT token (replace with actual JWT handling)
        jwt_token = JWTService.get_instance().generate_token({"email": dummy_user.user_email})

        return {"user": dummy_user, "access_token": jwt_token}

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/token", response_model=AccessToken, summary="Create Access Token")
async def create_access_token(token_name: str):
    """
    Creates a new access token for programmatic API access.
    """
    new_token = AccessToken(token_name=token_name, token_id="newtoken123", token_expiry=None)
    dummy_access_tokens.append(new_token)
    return new_token


@router.delete("/token", summary="Delete Access Token")
async def delete_access_token(token_id: str):
    """
    Deletes an existing access token.
    """
    for token in dummy_access_tokens:
        if token.token_id == token_id:
            dummy_access_tokens.remove(token)
            return {"message": "Token deleted successfully."}
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Token not found")


@router.get("/tokens", response_model=List[AccessToken], summary="List Access Tokens")
async def list_access_tokens():
    """
    Retrieves active access tokens for the authenticated user.
    """
    return list(dummy_access_tokens)
