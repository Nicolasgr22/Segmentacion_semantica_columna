from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    email: str
    name: str
    sub: str


class LoginResponse(BaseModel):
    token: str  # IdToken (JWT)
    user: UserResponse
    token_type: str = "Bearer"


class LogoutRequest(BaseModel):
    access_token: str  # Cognito access token for global sign-out


class ForgotPasswordRequest(BaseModel):
    username: str  # nombre de usuario o email alias registrado en Cognito


class ConfirmPasswordRequest(BaseModel):
    username: str
    otp_code: str   # código de 6 dígitos enviado al email por Cognito
    new_password: str
