import datetime
import json
import os
import requests
from typing import List, Optional, Dict, Union # Add Dict 
import logging # Add import for logging

from fastapi import APIRouter, HTTPException, Query, status, Depends
from pydantic import EmailStr

from app.models.token import PersonalAccessToken, UserToken, WebsiteAccessToken
from app.models.user import User
<<<<<<< HEAD
# Assuming JWTService and AzureBlobService are correctly imported from app.utils
from app.utils import JWTService
from app.utils.azure_blob_service import AzureBlobService
=======
from app.services.azure_blob_service import AzureBlobService
from app.utils.jwt_service import JWTService
>>>>>>> 1e49de1db1886ead0ccd3ca3b8f1f43b7dedf5fb

# Setup basic logging if not configured elsewhere in your app setup
# logging.basicConfig(level=logging.INFO) # Consider configuring logging globally

router = APIRouter()

# Attempt to get singleton instances. Handle potential initialization errors.
try:
    jwt_service = JWTService.get_instance()
    blob_service = AzureBlobService.get_instance()
    user_from_auth = jwt_service.from_authorization_header # Get the dependency function
except RuntimeError as e:
    logging.critical(f"Failed to get service instances: {e}. Ensure services are initialized before defining routes.")
    # Depending on your setup, you might re-raise or exit, or handle this differently
    raise RuntimeError("Service initialization failed") from e


# Load Google OAuth client secrets - ensure file exists and is valid JSON
google_secrets_file = os.getenv("GOOGLE_OAUTH_CLIENT_FILE", "client_secret.json")
try:
    with open(google_secrets_file, "r") as f:
        google_oauth_config = json.load(f)
    GOOGLE_CLIENT_ID = google_oauth_config["web"]["client_id"]
    GOOGLE_CLIENT_SECRET = google_oauth_config["web"]["client_secret"]
    GOOGLE_REDIRECT_URI = google_oauth_config["web"]["redirect_uris"][0] # Using the first redirect URI
    GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
    logging.info(f"Loaded Google OAuth config from {google_secrets_file}")
except FileNotFoundError:
     logging.critical(f"Google OAuth secrets file not found at: {google_secrets_file}")
     raise FileNotFoundError(f"Google secrets file missing: {google_secrets_file}")
except (KeyError, json.JSONDecodeError) as e:
     logging.critical(f"Error reading or parsing Google OAuth secrets file: {e}")
     raise ValueError(f"Invalid Google secrets file format: {e}")


# --- Personal Access Token (PAT) Management Endpoints ---

@router.post(
    "/token",
    response_model=PersonalAccessToken,
    summary="Create Personal Access Token",
    description="Creates a new Personal Access Token (PAT) for programmatic API access. Requires website authentication.",
    responses={
        status.HTTP_400_BAD_REQUEST: {"detail": "Invalid parameters (e.g., duplicate name)."},
        status.HTTP_401_UNAUTHORIZED: {"detail": "Requester is not authenticated."},
        status.HTTP_403_FORBIDDEN: {"detail": "PATs cannot be used to create other tokens."},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"detail": "Failed to create or save token."},
    }
)
async def create_access_token(
        # Changed from Query to Body or Form for POST might be better? Sticking to Query for now.
        token_name: Optional[str] = Query(None, # Made default None to allow auto-generation
                                description="Friendly name for the token (alphanumeric/underscores). Defaults to 'token_n'. Max 50 chars."),
        token_expiry: Optional[datetime.datetime] = Query(None, description="Optional expiration (ISO format, UTC recommended). Defaults to never expire."),
        user_meta: UserToken = Depends(user_from_auth), # This performs authentication
):
    # Ensure only users logged in via website can create PATs
    if not isinstance(user_meta, WebsiteAccessToken):
        logging.warning(f"User {user_meta.user_email} attempted PAT creation using invalid token type: {type(user_meta)}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only website sessions can create Personal Access Tokens.")

    # Validate and normalize token name
    if token_name is not None:
        try:
             # Assuming validate_identifier is a static/classmethod on PersonalAccessToken
            token_name = PersonalAccessToken.validate_identifier(token_name)
        except ValueError as e:
             raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid token name: {e}")

    # Determine expiry (use max datetime for 'never') - Ensure timezone aware for JWT 'exp'
    effective_expiry = token_expiry or datetime.datetime.max.replace(tzinfo=datetime.timezone.utc)
    if effective_expiry.tzinfo is None: # Ensure timezone-aware if provided without one
        effective_expiry = effective_expiry.replace(tzinfo=datetime.timezone.utc) # Assume UTC

    # Check for duplicate token name or generate a unique one
    try:
        existing_tokens = blob_service.list_personal_access_tokens(user_meta.user_email)
        if token_name is not None:
            if any(token.token_name == token_name for token in existing_tokens):
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Token name already exists.")
        else:
            # Generate a unique name like 'token_0', 'token_1', etc.
            i = 0
            existing_names = {token.token_name for token in existing_tokens}
            while True:
                token_name = f'token_{i}'
                if token_name not in existing_names:
                    logging.info(f"Generated unique token name '{token_name}' for user {user_meta.user_email}")
                    break
                i += 1
                if i > 1000: # Safety break
                    logging.error(f"Could not generate unique token name for {user_meta.user_email} after 1000 attempts.")
                    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to generate unique token name.")

        # Create the PAT object
        new_token_obj = PersonalAccessToken(
            user_email=user_meta.user_email,
            token_name=token_name,
            token_expiry=effective_expiry
        )

        # Save PAT metadata to blob storage
        blob_service.upload_token(user_meta.user_email, new_token_obj)

        # Create the actual JWT string (the secret)
        jwt_secret = jwt_service.create_access_token(new_token_obj)

        # Return the metadata AND the secret (only time secret is shown)
        return {
            "access_token": new_token_obj, # The metadata object
            "secret": jwt_secret # The actual JWT string to be used by the client
        }
    except HTTPException: # Re-raise known HTTP exceptions
        raise
    except Exception as e:
        logging.error(f"Error creating token '{token_name}' for {user_meta.user_email}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create access token.")


@router.delete(
    "/token",
    summary="Delete Personal Access Token",
    description="Deletes an existing Personal Access Token (PAT) by its name.",
    status_code=status.HTTP_204_NO_CONTENT, # Use 204 for successful deletion with no body
    responses={
        status.HTTP_204_NO_CONTENT: {"description": "Token deleted successfully."},
        status.HTTP_400_BAD_REQUEST: {"detail": "Token name is missing or invalid."},
        status.HTTP_401_UNAUTHORIZED: {"detail": "Requester is not authenticated."},
        status.HTTP_403_FORBIDDEN: {"detail": "PATs cannot be used to delete tokens."},
        status.HTTP_404_NOT_FOUND: {"detail": "Token not found."},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"detail": "Failed to delete token."},
    }
)
async def delete_access_token(
        token_name: str = Query(..., description="Unique name of the access token to delete."),
        user_meta: UserToken = Depends(user_from_auth),
):
    # Authorization check
    if not isinstance(user_meta, WebsiteAccessToken):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only website sessions can delete Personal Access Tokens.")

    # Validate token name format (optional but good practice)
    try:
         PersonalAccessToken.validate_identifier(token_name)
    except ValueError as e:
         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid token name format: {e}")

    # Check if token exists before attempting delete
    if not blob_service.token_exists(user_meta.user_email, token_name):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Token not found.")

    # Perform deletion
    try:
        blob_service.delete_token(user_meta.user_email, token_name)
        logging.info(f"Deleted token '{token_name}' for user {user_meta.user_email}")
        # No content to return on success
        return None # FastAPI handles 204 automatically when None is returned with status_code=204
    except Exception as e:
        logging.error(f"Failed to delete token '{token_name}' for {user_meta.user_email}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete token.")


@router.get(
    "/tokens",
    response_model=List[PersonalAccessToken],
    summary="List Personal Access Tokens",
    description="Retrieves active Personal Access Tokens (PATs) for the authenticated user.",
    responses={
        status.HTTP_401_UNAUTHORIZED: {"detail": "Requester is not authenticated."},
        status.HTTP_403_FORBIDDEN: {"detail": "PATs cannot be used to list tokens."},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"detail": "Failed to list tokens."},
    }
)
async def list_access_tokens(user_meta: UserToken = Depends(user_from_auth)):
     # Authorization check
    if not isinstance(user_meta, WebsiteAccessToken):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only website sessions can list Personal Access Tokens.")

    try:
        tokens = blob_service.list_personal_access_tokens(user_meta.user_email)
        # Optionally filter out expired tokens here if needed, though list_personal_access_tokens might do it
        # active_tokens = [t for t in tokens if t.token_expiry > datetime.datetime.now(datetime.timezone.utc)]
        return tokens
    except Exception as e:
        logging.error(f"Failed to list tokens for user {user_meta.user_email}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve tokens.")


# --- Google OAuth Endpoints ---

@router.get(
    "/google_oauth_url",
    summary="Get Google OAuth Redirect URL",
    description="Returns the URL the frontend should redirect the user to for Google authentication.",
    response_model=Dict[str, str], # Explicitly define response model
    responses={
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"detail": "OAuth configuration error."},
    }
)
async def get_oauth_url():
    """
    Constructs the Google OAuth 2.0 authorization URL.
    """
    # Define required scopes
    scope = "openid email profile" # Standard scopes to get ID, email, and basic profile info
    try:
        # Construct the URL using loaded configuration
        # Adding 'access_type=offline' to request refresh token capability (optional but common)
        # Adding 'prompt=consent' can be useful for testing to always show the consent screen
        # Optional: Include 'state' parameter for CSRF protection
        # state_value = secrets.token_urlsafe(16) # Generate random state
        # Store state_value in user session or temporary storage to verify on callback
        oauth_url = (
            f"https://accounts.google.com/o/oauth2/auth?"
            f"client_id={GOOGLE_CLIENT_ID}&"
            f"redirect_uri={GOOGLE_REDIRECT_URI}&"
            f"response_type=code&" # Requesting authorization code
            f"scope={scope}&"
            f"access_type=offline&" # Request refresh token
            # f"state={state_value}&" # Optional state param
            f"prompt=consent" # Optional: force consent screen
        )
        logging.debug(f"Generated Google OAuth URL: {oauth_url}")
        return {"oauth_url": oauth_url}
    except Exception as e:
        logging.critical(f"Error generating Google OAuth URL - check configuration: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Server configuration error for OAuth.")


@router.get(
    "/google_oauth", # This is the CALLBACK endpoint configured in Google Cloud Console
    summary="Google OAuth Callback Handler",
    description="Handles the redirect from Google after user authentication. Exchanges code for token, creates/logs in user, and returns app JWT.",
    response_model=Dict[str, Union[str, User]], # Define response { "authentication_token": str, "user": User }
    responses={
        status.HTTP_400_BAD_REQUEST: {"detail": "Missing or invalid 'code' parameter."},
        status.HTTP_401_UNAUTHORIZED: {"detail": "Failed to exchange code or fetch user info from Google."},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"detail": "Internal server error during login/user creation."},
    }
)
async def google_oauth_callback(code: str = Query(..., description="Authorization code provided by Google redirect.")): # Expect 'code'
    """
    Handles Google OAuth callback, exchanges code for tokens, gets user info,
    creates/retrieves user, and returns application JWT.
    """
    logging.info(f"Received Google OAuth callback with code: {code[:10]}...")

    # --- 1. Exchange Code for Tokens ---
    token_data = {
        "code": code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": GOOGLE_REDIRECT_URI, # Must match exactly what was used in the initial redirect
        "grant_type": "authorization_code"
    }
    logging.debug("Exchanging authorization code for Google tokens at %s", GOOGLE_TOKEN_URL)
    try:
        response = requests.post(GOOGLE_TOKEN_URL, data=token_data)
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
        tokens = response.json()
        google_access_token = tokens.get("access_token")
        google_id_token = tokens.get("id_token") # ID token often preferred for user info

        if not google_access_token: # Access token is usually needed
             raise KeyError("Missing 'access_token' in Google's response.")

        logging.info("Successfully exchanged code for Google tokens.")
        # Optionally log token types received for debugging
        # logging.debug(f"Google Tokens received: {list(tokens.keys())}")

    except requests.exceptions.RequestException as e:
        logging.error(f"HTTP error exchanging Google auth code: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Failed to exchange authorization code with Google: {e}"
        )
    except KeyError as e:
         logging.error(f"Google token response missing expected key: {e}. Response: {tokens}")
         raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Invalid token response from Google (missing {e}).")
    except Exception as e:
         logging.error(f"Unexpected error during Google token exchange: {e}", exc_info=True)
         raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error communicating with Google.")


    # --- 2. Get User Info (Prefer ID Token, fallback to UserInfo endpoint) ---
    userinfo = None
    email: Optional[EmailStr] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None

    if google_id_token:
        try:
            # Decode ID token (minimal validation, rely on Google's issuance)
            # You might want to add audience (aud) validation against your GOOGLE_CLIENT_ID
            id_payload = jwt.decode(google_id_token, options={"verify_signature": False, "verify_aud": False}) # Basic decode
            email = id_payload.get("email")
            first_name = id_payload.get("given_name")
            last_name = id_payload.get("family_name")
            logging.info(f"Extracted user info from Google ID token for: {email}")
            if not id_payload.get("email_verified", False):
                 logging.warning(f"Google account email not verified for: {email}")
                 # Decide policy: allow unverified emails? Or reject?
                 # raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Google email must be verified.")
        except jwt.PyJWTError as e:
             logging.warning(f"Could not decode Google ID token (falling back to UserInfo endpoint): {e}")
             # Fallback to UserInfo endpoint below
        except Exception as e:
             logging.error(f"Unexpected error decoding Google ID token: {e}", exc_info=True)
             # Fallback to UserInfo endpoint below

    # Fallback or if ID token didn't have all info
    if not email:
        logging.debug("Fetching user info from Google UserInfo endpoint...")
        userinfo_endpoint = "https://www.googleapis.com/oauth2/v3/userinfo"
        headers = {"Authorization": f"Bearer {google_access_token}"}
        try:
            userinfo_response = requests.get(userinfo_endpoint, headers=headers)
            userinfo_response.raise_for_status()
            userinfo = userinfo_response.json()

            email = userinfo.get("email")
            first_name = userinfo.get("given_name")
            last_name = userinfo.get("family_name")

            if not email: # Check again after UserInfo call
                logging.error(f"Could not get email from Google userinfo: {userinfo}")
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Could not retrieve email from Google profile.")

            logging.info(f"Retrieved user info from Google UserInfo endpoint for email: {email}")

        except requests.exceptions.RequestException as e:
             logging.error(f"Failed to fetch user info from Google UserInfo endpoint: {e}", exc_info=True)
             raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, # Indicate potential token issue
                detail=f"Failed to fetch user info from Google: {e}"
            )
        except Exception as e:
             logging.error(f"Unexpected error fetching/parsing Google userinfo: {e}", exc_info=True)
             raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error processing Google user profile.")


    # --- 3. Get or Create User in Our System ---
    try:
        user = blob_service.get_user(email) # get_user now has logging

        if user is None:
            logging.info(f"User {email} not found in storage. Creating new user.")
            user = User(
                user_email=email,
                first_name=first_name or "", # Use empty string if name is missing
                last_name=last_name or "",   # Use empty string if name is missing
                authenticated_courses=set(), # Start with empty set
                dark_mode=False, # Default preference
            )
            blob_service.upload_user(user)
            logging.info(f"Successfully created and uploaded new user data for {email}")
        else:
            logging.info(f"User {email} found in storage.")
            # Optional: Update names if they changed in Google?
            needs_update = False
            if first_name and user.first_name != first_name:
                user.first_name = first_name
                needs_update = True
            if last_name and user.last_name != last_name:
                user.last_name = last_name
                needs_update = True
            if needs_update:
                 logging.info(f"Updating user profile data for {email} from Google info.")
                 blob_service.upload_user(user) # Save updated info

    except Exception as e:
         logging.error(f"Error during user get/create for {email}: {e}", exc_info=True)
         raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error processing user profile.")


    # --- 4. Generate Our Application JWT ---
    try:
        # Create a standard Website Access Token for the session
        # Use default expiry (e.g., 30 days) set in create_user_jwt
        app_jwt_token = jwt_service.create_user_jwt(user)
        logging.info(f"Generated application JWT for user {email}")
    except jwt.PyJWTError as e:
        logging.error(f"Failed to create application JWT for {email}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to generate authentication token.")
    except Exception as e:
         logging.error(f"Unexpected error during JWT generation for {email}: {e}", exc_info=True)
         raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Token generation error.")

    # --- 5. Return Token and User Info ---
    # Frontend needs the token to store. Including user info can be useful.
    return {"authentication_token": app_jwt_token, "user": user.model_dump()} # Return user as dict