from abc import ABC, abstractmethod

from app.core.domain.entities.user import AuthSession, AuthUser


class AuthPort(ABC):
    @abstractmethod
    async def login(self, username: str, password: str) -> AuthSession: ...

    @abstractmethod
    async def validate_token(self, token: str) -> AuthUser: ...

    @abstractmethod
    async def logout(self, access_token: str) -> None: ...

    @abstractmethod
    async def forgot_password(self, username: str) -> None: ...

    @abstractmethod
    async def confirm_password(self, username: str, otp_code: str, new_password: str) -> None: ...
