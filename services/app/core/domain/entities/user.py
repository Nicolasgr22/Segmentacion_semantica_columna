from __future__ import annotations

from dataclasses import dataclass


@dataclass
class AuthUser:
    email: str
    name: str
    sub: str  # Cognito user sub (unique ID)


@dataclass
class AuthSession:
    user: AuthUser
    id_token: str
    access_token: str
    refresh_token: str | None = None
