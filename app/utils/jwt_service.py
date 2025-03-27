import datetime
import json
from typing import Optional

import jwt
from fastapi import HTTPException, Header
from pydantic import FilePath, BaseModel, EmailStr

from app.models import User
from app.utils.azure_blob_service import AzureBlobService

jwt_service: Optional["JWTService"] = None


class UserMeta(BaseModel):
    user_email: EmailStr
    token_id: Optional[str] = None


class JWTService:
    _algorithm_: str
    _private_key_: str
    _public_key_: str
    _azure_blob_service_: AzureBlobService

    def __init__(self, jwt_secrets_file: FilePath, azure_blob_service: AzureBlobService):
        with jwt_secrets_file.open('r') as f:
            jwt_secrets = json.load(f)
        self._algorithm_ = jwt_secrets['algorithm']
        self._private_key_ = jwt_secrets['private_key']
        self._public_key_ = jwt_secrets['public_key']
        self._azure_blob_service_ = azure_blob_service

    def create_user_jwt(
            self,
            user: User,
            token_expiry: datetime.datetime = datetime.datetime.now() + datetime.timedelta(days=30)
    ) -> str:
        """
        Creates a JSON Web Token from the given user.
        :param token_expiry:
        :param user: the user for whom to create the JSON Web Token for
        :return: the JWT token
        """
        payload = {
            "user_email": user.user_email,
            "exp": token_expiry,
        }
        token = jwt.encode(payload, self._private_key_, algorithm=self._algorithm_)
        return token

    def create_access_token(self, user: User, token_name: str, token_expiry: datetime.datetime) -> str:
        payload = {
            "user_email": user.user_email,
            "token_name": token_name,
            "exp": token_expiry,
        }
        token = jwt.encode(payload, self._private_key_, algorithm=self._algorithm_)
        return token

    def decode_jwt(self, token: str) -> Optional[UserMeta]:
        decoded_json = jwt.decode(token, self._public_key_, algorithms=[self._algorithm_])
        if decoded_json.exp < datetime.datetime.now():
            return None
        return UserMeta(user_email=decoded_json.user_email, token_id=decoded_json.token_id)

    def from_authorization_header(self, authorization_header: str = Header(None)) -> Optional[UserMeta]:
        """
        Extracts the token from the authorization header and then figures out requesting
        user from it. The authorization header is expected to be in the format "Bearer <token>".
        :param authorization_header: The raw authorization header
        :return: The user associated with the token
        """
        parts = authorization_header.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            raise HTTPException(status_code=401, detail="Invalid token format")
        token = parts[1]
        return self.decode_jwt(token)

    @staticmethod
    def init_singleton(jwt_secrets_file: FilePath, azure_blob_service: AzureBlobService):
        global jwt_service
        jwt_service = JWTService(jwt_secrets_file, azure_blob_service)

    @staticmethod
    def get_instance() -> Optional["JWTService"]:
        global jwt_service
        return jwt_service
