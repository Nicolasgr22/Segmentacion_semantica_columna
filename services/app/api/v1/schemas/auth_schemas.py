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
