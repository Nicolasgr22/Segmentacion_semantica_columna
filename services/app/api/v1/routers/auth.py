"""Router de autenticación.

Endpoints:
  POST /api/vertebraai/auth/login   → LoginResponse
  POST /api/vertebraai/auth/logout  → {"message": "ok"}
  GET  /api/vertebraai/auth/me      → UserResponse  (requiere Bearer token)
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request

from app.api.v1.schemas.auth_schemas import (
    LoginRequest,
    LoginResponse,
    LogoutRequest,
    UserResponse,
)
from app.config import settings
from app.core.domain.entities.user import AuthUser
from app.core.use_cases.auth_use_case import (
    InvalidCredentialsError,
    LoginUseCase,
    LogoutUseCase,
    UserNotConfirmedError,
)
from app.dependencies import get_auth_port, get_current_user
from app.rate_limit import limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Iniciar sesión con email y contraseña",
    responses={
        401: {"description": "Credenciales inválidas"},
        403: {"description": "Usuario no confirmado"},
    },
)
@limiter.limit("10/minute")
async def login(
    request: Request,
    body: LoginRequest,
    auth_port=Depends(get_auth_port),
) -> LoginResponse:
    use_case = LoginUseCase(auth=auth_port)
    try:
        session = await use_case.execute(email=body.email, password=body.password)
    except InvalidCredentialsError:
        raise HTTPException(status_code=401, detail="Credenciales inválidas")
    except UserNotConfirmedError:
        raise HTTPException(
            status_code=403, detail="El usuario no ha confirmado su cuenta"
        )
    except Exception:
        logger.exception("Error inesperado en login")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

    return LoginResponse(
        token=session.id_token,
        user=UserResponse(
            email=session.user.email,
            name=session.user.name,
            sub=session.user.sub,
        ),
    )


@router.post(
    "/logout",
    summary="Cerrar sesión (revoca el access token en Cognito)",
)
@limiter.limit(settings.rate_limit_default)
async def logout(
    request: Request,
    body: LogoutRequest,
    auth_port=Depends(get_auth_port),
) -> dict[str, str]:
    await LogoutUseCase(auth=auth_port).execute(access_token=body.access_token)
    return {"message": "ok"}


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Obtener datos del usuario autenticado",
    responses={401: {"description": "Token inválido o ausente"}},
)
@limiter.limit(settings.rate_limit_default)
async def me(
    request: Request,
    current_user: AuthUser = Depends(get_current_user),
) -> UserResponse:
    return UserResponse(
        email=current_user.email,
        name=current_user.name,
        sub=current_user.sub,
    )
