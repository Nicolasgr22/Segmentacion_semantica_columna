from __future__ import annotations

from app.core.domain.entities.user import AuthSession, AuthUser
from app.core.domain.ports.auth_port import AuthPort


class InvalidCredentialsError(ValueError):
    pass


class TokenValidationError(ValueError):
    pass


class UserNotConfirmedError(ValueError):
    pass


class LoginUseCase:
    def __init__(self, auth: AuthPort) -> None:
        self._auth = auth

    async def execute(self, email: str, password: str) -> AuthSession:
        return await self._auth.login(email=email, password=password)


class ValidateTokenUseCase:
    def __init__(self, auth: AuthPort) -> None:
        self._auth = auth

    async def execute(self, token: str) -> AuthUser:
        return await self._auth.validate_token(token=token)


class LogoutUseCase:
    def __init__(self, auth: AuthPort) -> None:
        self._auth = auth

    async def execute(self, access_token: str) -> None:
        await self._auth.logout(access_token=access_token)
