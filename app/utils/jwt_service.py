import datetime
import json
from typing import Optional

import jwt
from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import FilePath, BaseModel, EmailStr

from app.models import User

jwt_service: Optional["JWTService"] = None


class UserToken(BaseModel):
    user_email: EmailStr
    token_expiry: datetime.datetime


class JWTService:
    _algorithm_: str
    _private_key_: str
    _public_key_: str

    def __init__(self, jwt_secrets_file: FilePath):
        with jwt_secrets_file.open('r') as f:
            jwt_secrets = json.load(f)
        self._algorithm_ = jwt_secrets['algorithm']
        self._private_key_ = jwt_secrets['private_key']
        self._public_key_ = jwt_secrets['public_key']

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
            "token_expiry": token_expiry,
        }
        token = jwt.encode(payload, self._private_key_, algorithm=self._algorithm_)
        return token

    def create_access_token(self, user: User, token_name: str, token_expiry: datetime.datetime) -> str:
        payload = {
            "user_email": user.user_email,
            "token_name": token_name,
            "token_expiry": token_expiry,
        }
        token = jwt.encode(payload, self._private_key_, algorithm=self._algorithm_)
        return token

    def decode_jwt(self, token: str) -> Optional[UserToken]:
        decoded_json = jwt.decode(token, self._public_key_, algorithms=[self._algorithm_])
        if decoded_json.exp < datetime.datetime.now():
            return None
        return UserToken(user_email=decoded_json.user_email, token_id=decoded_json.token_id)

    def from_authorization_header(self, credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())) -> Optional[UserToken]:
        """
        Extracts the token from the authorization header and then figures out requesting
        user from it. The authorization header is expected to be in the format "Bearer <token>".
        :param credentials: The bearer token
        :return: The user associated with the token
        """
        # TODO, this was temp
        return UserToken(
            user_email="bobross@gmail.com",
            token_expiry=datetime.datetime.now().__add__(datetime.timedelta(days=30)),
        )
        return self.decode_jwt(credentials.credentials)

    @staticmethod
    def init_singleton(jwt_secrets_file: FilePath):
        global jwt_service
        jwt_service = JWTService(jwt_secrets_file)

    @staticmethod
    def get_instance() -> Optional["JWTService"]:
        global jwt_service
        return jwt_service
