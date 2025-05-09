import datetime
import json
import logging
from typing import Optional

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import FilePath

from app.models import User, PersonalAccessToken, WebsiteAccessToken
from app.models.token import UserToken, TokenType
from app.services import AzureBlobService

jwt_service: Optional["JWTService"] = None


class JWTService:
    _algorithm_: str
    _private_key_: str
    _public_key_: str
    _environment_secret: Optional[str]

    def __init__(self, jwt_secrets_file: FilePath, environment_secret: Optional[str] = None):
        with jwt_secrets_file.open('r') as f:
            jwt_secrets = json.load(f)
        self._algorithm_ = jwt_secrets['algorithm']
        self._private_key_ = jwt_secrets['private_key']
        self._public_key_ = jwt_secrets['public_key']
        self._environment_secret = environment_secret

    def create_user_jwt(
            self,
            user: User,
            token_expiry: datetime.datetime = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=30)
    ) -> str:
        """
        Creates a JSON Web Token (JWT) for the given user using standard claims.

        :param user: The user object containing user_email.
        :param token_expiry: The absolute expiration time for the token (timezone-aware recommended).
                               Defaults to 30 days from now.
        :return: The encoded JWT string.
        :raises jwt.PyJWTError: If encoding fails.
        """
        # Use standard JWT claims: 'exp' (expiration time), 'iat' (issued at), 'sub' (subject)
        payload = {
            "sub": user.user_email,  # Subject claim is standard for user identifier
            "exp": token_expiry,
            "iat": datetime.datetime.now(datetime.timezone.utc),
            "type": TokenType.WEBSITE_ACCESS_TOKEN.value,
        }
        token = jwt.encode(payload, self._private_key_, algorithm=self._algorithm_)
        return token

    def create_access_token(
            self,
            access_token: PersonalAccessToken,
    ) -> str:
        """
        Creates a named access token (e.g., for API keys) for a user.

        :param access_token: the personal access token
        :return: The encoded JWT string.
        :raises jwt.PyJWTError: If encoding fails.
        """
        payload = {
            # subject
            "sub": access_token.user_email,
            # expiry
            "exp": access_token.token_expiry,
            # issued at
            "iat": datetime.datetime.now(datetime.timezone.utc),
            # custom
            "type": TokenType.PERSONAL_ACCESS_TOKEN.value,
            "token_name": access_token.token_name,
        }
        token = jwt.encode(payload, self._private_key_, algorithm=self._algorithm_)
        return token

    def decode_jwt(self, token: str) -> Optional[dict]:
        """
        Decodes and validates a JWT using the public key.

        Validates signature, expiration ('exp'), not before ('nbf', if present),
        issued at ('iat', if present).

        :param token: The JWT string to decode.
        :return: The decoded payload dictionary if the token is valid, otherwise None.
        """
        try:
            payload = jwt.decode(
                token,
                self._public_key_,
                algorithms=[self._algorithm_],
                leeway=datetime.timedelta(seconds=30)  # Allow 30 seconds clock skew
            )
            return payload
        except jwt.ExpiredSignatureError:
            logging.warning("Token signature has expired.")
            return None
        except jwt.InvalidTokenError as e:
            # Covers various issues: invalid signature, invalid claims, etc.
            logging.warning(f"Invalid token received: {e}")
            return None
        except Exception as e:
            # Catch unexpected errors during decoding
            logging.error(f"Unexpected error decoding JWT: {e}", exc_info=True)
            return None

    def get_user_token_from_payload(self, payload: dict) -> Optional[UserToken]:
        """
        Extracts UserToken relevant information from a decoded JWT payload.
        Assumes standard 'exp' claim and custom 'user_email' claim.
        """
        if not payload:
            return None
        try:
            # Reconstruct the UserToken object based on the original structure
            # Note: The original UserToken had token_expiry. PyJWT validates 'exp'.
            # We extract 'exp' and 'user_email' (or 'sub') here.
            expiry_timestamp = payload.get('exp')
            user_email = payload.get('sub')
            token_type = payload.get('type')

            if not expiry_timestamp or not user_email:
                logging.warning("Decoded payload missing 'exp' or 'user_email'/'sub'.")
                return None

            # Convert UNIX timestamp ('exp') back to datetime object (UTC)
            token_expiry_dt = datetime.datetime.fromtimestamp(expiry_timestamp, tz=datetime.timezone.utc)

            if token_type.lower() == TokenType.PERSONAL_ACCESS_TOKEN.value:
                return PersonalAccessToken(
                    user_email=user_email,
                    token_expiry=token_expiry_dt,
                    token_name=payload.get('token_name')
                )
            else:
                return WebsiteAccessToken(
                    user_email=user_email,
                    token_expiry=token_expiry_dt
                )
        except (KeyError, ValueError, TypeError) as e:
            logging.error(f"Error extracting UserToken data from payload: {e}", exc_info=True)
            return None

    def from_authorization_header(self, credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())) -> UserToken:
        """
        FastAPI dependency to extract, decode, and validate a JWT from the
        'Authorization: Bearer <token>' header, returning a UserToken object.

        :param credentials: The HTTPAuthorizationCredentials injected by FastAPI.
        :return: A UserToken object if the token is valid and contains necessary info, otherwise None.
                 Returning None typically results in a 401/403 response in FastAPI.
        """

        token = credentials.credentials

        if self._environment_secret is not None and token == self._environment_secret:
            return UserToken(
                user_email=AzureBlobService.get_instance().get_default_user().user_email,
                token_expiry=datetime.datetime.max,
            )

        decoded_payload = self.decode_jwt(token)

        if decoded_payload is None:
            raise HTTPException(status_code=401, detail="Invalid authorization token.")

        # Extract user info from the valid payload
        user_token = self.get_user_token_from_payload(decoded_payload)
        if user_token is None:
            raise HTTPException(status_code=401, detail="Invalid or expired authorization token.")

        return user_token

    @staticmethod
    def init_singleton(jwt_secrets_file: FilePath, environment_secret: Optional[str] = None):
        global jwt_service
        jwt_service = JWTService(jwt_secrets_file, environment_secret=environment_secret)

    @staticmethod
    def get_instance() -> Optional["JWTService"]:
        global jwt_service
        return jwt_service