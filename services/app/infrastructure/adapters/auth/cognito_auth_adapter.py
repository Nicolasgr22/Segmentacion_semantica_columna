"""Adapter de autenticación usando AWS Cognito vía boto3.

Implementa AuthPort delegando login y validación de token al User Pool
configurado en settings. Los errores de Cognito se mapean a excepciones
del dominio para que el use case (y los routers) no dependan de boto3.
"""

from __future__ import annotations

import asyncio
import json
import logging
import urllib.request
from typing import Any

import boto3
from botocore.exceptions import ClientError
from jose import JWTError, jwt

from app.config import settings
from app.core.domain.entities.user import AuthSession, AuthUser
from app.core.domain.ports.auth_port import AuthPort
from app.core.use_cases.auth_use_case import (
    InvalidCredentialsError,
    TokenValidationError,
    UserNotConfirmedError,
)

logger = logging.getLogger(__name__)

_JWKS_URL_TEMPLATE = (
    "https://cognito-idp.{region}.amazonaws.com/{user_pool_id}/.well-known/jwks.json"
)

_COGNITO_INVALID_CODES = frozenset({"NotAuthorizedException", "UserNotFoundException"})


def _fetch_jwks_sync(url: str) -> dict[str, Any]:
    with urllib.request.urlopen(url) as resp:  # noqa: S310
        return json.loads(resp.read())


def _claims_to_user(claims: dict[str, Any]) -> AuthUser:
    email: str = claims.get("email", "")
    name: str = claims.get("cognito:username", claims.get("name", email))
    sub: str = claims.get("sub", "")
    return AuthUser(email=email, name=name, sub=sub)


class CognitoAuthAdapter(AuthPort):
    """Adapter que usa AWS Cognito USER_PASSWORD_AUTH flow."""

    def __init__(self) -> None:
        self._client = boto3.client(
            "cognito-idp",
            region_name=settings.cognito_region,
        )
        self._client_id = settings.cognito_client_id
        self._user_pool_id = settings.cognito_user_pool_id
        self._jwks_url = _JWKS_URL_TEMPLATE.format(
            region=settings.cognito_region,
            user_pool_id=settings.cognito_user_pool_id,
        )
        self._jwks: dict[str, Any] | None = None

    async def login(self, email: str, password: str) -> AuthSession:
        loop = asyncio.get_event_loop()
        try:
            response = await loop.run_in_executor(
                None,
                lambda: self._client.initiate_auth(
                    AuthFlow="USER_PASSWORD_AUTH",
                    AuthParameters={"USERNAME": email, "PASSWORD": password},
                    ClientId=self._client_id,
                ),
            )
        except ClientError as exc:
            error_code = exc.response["Error"]["Code"]
            logger.warning("Cognito login error [%s] for user %s", error_code, email)
            if error_code in _COGNITO_INVALID_CODES:
                raise InvalidCredentialsError("Credenciales inválidas") from exc
            if error_code == "UserNotConfirmedException":
                raise UserNotConfirmedError(
                    "El usuario no ha confirmado su cuenta"
                ) from exc
            raise

        auth_result = response["AuthenticationResult"]
        id_token: str = auth_result["IdToken"]
        access_token: str = auth_result["AccessToken"]
        refresh_token: str | None = auth_result.get("RefreshToken")

        try:
            user = _claims_to_user(jwt.get_unverified_claims(id_token))
        except JWTError as exc:
            raise TokenValidationError("IdToken inválido recibido de Cognito") from exc

        return AuthSession(
            user=user,
            id_token=id_token,
            access_token=access_token,
            refresh_token=refresh_token,
        )

    async def validate_token(self, token: str) -> AuthUser:
        jwks = await self._get_jwks()
        try:
            claims = jwt.decode(
                token,
                jwks,
                algorithms=["RS256"],
                audience=self._client_id,
                options={"verify_at_hash": False},
            )
        except JWTError as exc:
            raise TokenValidationError("Token inválido o expirado") from exc
        return _claims_to_user(claims)

    async def logout(self, access_token: str) -> None:
        loop = asyncio.get_event_loop()
        try:
            await loop.run_in_executor(
                None,
                lambda: self._client.global_sign_out(AccessToken=access_token),
            )
        except ClientError:
            logger.warning("global_sign_out failed — token may already be expired")

    async def _get_jwks(self) -> dict[str, Any]:
        if self._jwks is not None:
            return self._jwks
        loop = asyncio.get_event_loop()
        self._jwks = await loop.run_in_executor(
            None, _fetch_jwks_sync, self._jwks_url
        )
        return self._jwks  # type: ignore[return-value]
