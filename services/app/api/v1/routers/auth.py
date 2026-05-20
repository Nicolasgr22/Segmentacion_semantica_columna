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
    ConfirmPasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    LoginResponse,
    LogoutRequest,
    UserResponse,
)
from app.config import settings
from app.core.domain.entities.user import AuthUser
from app.core.use_cases.auth_use_case import (
    ConfirmPasswordUseCase,
    ForgotPasswordUseCase,
    InvalidCredentialsError,
    LoginUseCase,
    LogoutUseCase,
    OtpCodeError,
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
        session = await use_case.execute(username=body.username, password=body.password)
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


@router.post(
    "/forgot-password",
    summary="Solicitar código OTP para recuperar contraseña",
    description="Envía un código OTP de 6 dígitos al email registrado en Cognito.",
    responses={
        200: {"description": "OTP enviado — revisar el correo registrado"},
        404: {"description": "Usuario no encontrado"},
    },
)
@limiter.limit("5/minute")
async def forgot_password(
    request: Request,
    body: ForgotPasswordRequest,
    auth_port=Depends(get_auth_port),
) -> dict[str, str]:
    try:
        await ForgotPasswordUseCase(auth=auth_port).execute(username=body.username)
    except InvalidCredentialsError:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    except Exception:
        logger.exception("Error inesperado en forgot-password")
        raise HTTPException(status_code=500, detail="Error interno del servidor")
    return {"message": "Código OTP enviado al correo registrado"}


@router.post(
    "/confirm-password",
    summary="Confirmar OTP y establecer nueva contraseña",
    responses={
        200: {"description": "Contraseña actualizada — ya puedes iniciar sesión"},
        400: {"description": "Código OTP incorrecto o expirado"},
        404: {"description": "Usuario no encontrado"},
    },
)
@limiter.limit("10/minute")
async def confirm_password(
    request: Request,
    body: ConfirmPasswordRequest,
    auth_port=Depends(get_auth_port),
) -> dict[str, str]:
    try:
        await ConfirmPasswordUseCase(auth=auth_port).execute(
            username=body.username,
            otp_code=body.otp_code,
            new_password=body.new_password,
        )
    except OtpCodeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except InvalidCredentialsError:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    except Exception:
        logger.exception("Error inesperado en confirm-password")
        raise HTTPException(status_code=500, detail="Error interno del servidor")
    return {"message": "Contraseña actualizada correctamente"}


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
