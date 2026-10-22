
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from supabase_auth.errors import AuthApiError

from app.exceptions import ConflictError, UnauthorizedError, ValidationError
from app.schemas.auth import LoginRequest, RegisterRequest
from app.services.auth_service import AuthService


def make_auth_error(message: str, status: int = 400, code: str = "auth_error"):
    return AuthApiError(message, status, code)


@patch("app.services.auth_service.auth_client")
def test_register_success(mock_client):
    mock_client.auth.sign_up.return_value = SimpleNamespace(
        user=SimpleNamespace(id="user-123", email="customer@example.com"),
        session=SimpleNamespace(access_token="test-token", expires_in=3600),
    )

    result = AuthService.register(
        RegisterRequest(email="customer@example.com", password="SecurePass123!")
    )

    assert result.user_id == "user-123"
    assert result.access_token == "test-token"



@patch("app.services.auth_service.auth_client")
def test_register_requires_email_confirmation(mock_client):
    mock_client.auth.sign_up.return_value = SimpleNamespace(
        user=SimpleNamespace(id="user-123", email="customer@example.com"),
        session=None,
    )

    result = AuthService.register(
        RegisterRequest(email="customer@example.com", password="SecurePass123!")
    )

    assert result.user_id == "user-123"
    assert result.access_token is None
    assert result.requires_email_confirmation is True


@patch("app.services.auth_service.auth_client")
def test_register_duplicate_email(mock_client):
    mock_client.auth.sign_up.side_effect = make_auth_error(
        "User already registered", 422, "user_already_exists"
    )

    with pytest.raises(ConflictError):
        AuthService.register(
            RegisterRequest(email="customer@example.com", password="SecurePass123!")
        )


@patch("app.services.auth_service.auth_client")
def test_login_success(mock_client):
    mock_client.auth.sign_in_with_password.return_value = SimpleNamespace(
        user=SimpleNamespace(id="user-123", email="customer@example.com"),
        session=SimpleNamespace(access_token="test-token", expires_in=3600),
    )

    result = AuthService.login(
        LoginRequest(email="customer@example.com", password="SecurePass123!")
    )

    assert result.user_id == "user-123"
    assert result.access_token == "test-token"


@patch("app.services.auth_service.auth_client")
def test_login_invalid_credentials(mock_client):
    mock_client.auth.sign_in_with_password.side_effect = make_auth_error(
        "Invalid login credentials", 400, "invalid_credentials"
    )

    with pytest.raises(UnauthorizedError):
        AuthService.login(
            LoginRequest(email="customer@example.com", password="wrong-password")
        )
