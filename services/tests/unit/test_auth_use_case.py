"""Unit tests para LoginUseCase y ValidateTokenUseCase.

Los tests mockean AuthPort completo — boto3 nunca se llama.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.domain.entities.user import AuthSession, AuthUser
from app.core.domain.ports.auth_port import AuthPort
from app.core.use_cases.auth_use_case import (
    InvalidCredentialsError,
    LoginUseCase,
    LogoutUseCase,
    TokenValidationError,
    ValidateTokenUseCase,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_auth_port() -> AuthPort:
    port = MagicMock(spec=AuthPort)
    port.login = AsyncMock()
    port.validate_token = AsyncMock()
    port.logout = AsyncMock()
    return port


@pytest.fixture
def sample_user() -> AuthUser:
    return AuthUser(email="maia_groupo5", name="testuser", sub="sub-abc-123")


@pytest.fixture
def sample_session(sample_user) -> AuthSession:
    return AuthSession(
        user=sample_user,
        id_token="id.token.jwt",
        access_token="access.token.jwt",
        refresh_token="refresh.token.jwt",
    )


# ---------------------------------------------------------------------------
# LoginUseCase
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_login_returns_auth_session(mock_auth_port, sample_session):
    mock_auth_port.login.return_value = sample_session

    use_case = LoginUseCase(auth=mock_auth_port)
    result = await use_case.execute(username="maia_groupo5", password="secret")

    assert isinstance(result, AuthSession)
    assert result.id_token == "id.token.jwt"
    assert result.user.email == "maia_groupo5"


@pytest.mark.asyncio
async def test_login_delegates_to_port(mock_auth_port, sample_session):
    mock_auth_port.login.return_value = sample_session

    use_case = LoginUseCase(auth=mock_auth_port)
    await use_case.execute(username="maia_groupo5", password="secret")

    mock_auth_port.login.assert_called_once_with(
        username="maia_groupo5", password="secret"
    )


@pytest.mark.asyncio
async def test_login_propagates_invalid_credentials_error(mock_auth_port):
    mock_auth_port.login.side_effect = InvalidCredentialsError("Credenciales inválidas")

    use_case = LoginUseCase(auth=mock_auth_port)
    with pytest.raises(InvalidCredentialsError):
        await use_case.execute(username="wrong_user", password="wrong")


@pytest.mark.asyncio
async def test_login_session_contains_refresh_token(mock_auth_port, sample_session):
    mock_auth_port.login.return_value = sample_session

    use_case = LoginUseCase(auth=mock_auth_port)
    result = await use_case.execute(username="maia_groupo5", password="secret")

    assert result.refresh_token == "refresh.token.jwt"


@pytest.mark.asyncio
async def test_login_session_without_refresh_token(mock_auth_port, sample_user):
    session_no_refresh = AuthSession(
        user=sample_user,
        id_token="id.token.jwt",
        access_token="access.token.jwt",
        refresh_token=None,
    )
    mock_auth_port.login.return_value = session_no_refresh

    use_case = LoginUseCase(auth=mock_auth_port)
    result = await use_case.execute(username="maia_groupo5", password="secret")

    assert result.refresh_token is None


# ---------------------------------------------------------------------------
# ValidateTokenUseCase
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_validate_token_returns_auth_user(mock_auth_port, sample_user):
    mock_auth_port.validate_token.return_value = sample_user

    use_case = ValidateTokenUseCase(auth=mock_auth_port)
    result = await use_case.execute(token="valid.token.jwt")

    assert isinstance(result, AuthUser)
    assert result.email == "maia_groupo5"
    assert result.sub == "sub-abc-123"


@pytest.mark.asyncio
async def test_validate_token_delegates_to_port(mock_auth_port, sample_user):
    mock_auth_port.validate_token.return_value = sample_user

    use_case = ValidateTokenUseCase(auth=mock_auth_port)
    await use_case.execute(token="valid.token.jwt")

    mock_auth_port.validate_token.assert_called_once_with(token="valid.token.jwt")


@pytest.mark.asyncio
async def test_validate_token_raises_on_invalid_token(mock_auth_port):
    mock_auth_port.validate_token.side_effect = TokenValidationError(
        "Token inválido o expirado"
    )

    use_case = ValidateTokenUseCase(auth=mock_auth_port)
    with pytest.raises(TokenValidationError):
        await use_case.execute(token="bad.token")


@pytest.mark.asyncio
async def test_validate_token_raises_on_empty_token(mock_auth_port):
    mock_auth_port.validate_token.side_effect = TokenValidationError("Token vacío")

    use_case = ValidateTokenUseCase(auth=mock_auth_port)
    with pytest.raises(TokenValidationError):
        await use_case.execute(token="")


# ---------------------------------------------------------------------------
# LogoutUseCase
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_logout_delegates_to_port(mock_auth_port):
    use_case = LogoutUseCase(auth=mock_auth_port)
    await use_case.execute(access_token="access.token.jwt")

    mock_auth_port.logout.assert_called_once_with(access_token="access.token.jwt")


@pytest.mark.asyncio
async def test_logout_returns_none(mock_auth_port):
    mock_auth_port.logout.return_value = None

    use_case = LogoutUseCase(auth=mock_auth_port)
    result = await use_case.execute(access_token="access.token.jwt")

    assert result is None
