
from unittest.mock import patch

import pytest

from app.container.dependencies import Dependencies
from app.exceptions import UnauthorizedError


def test_get_current_user_rejects_missing_credentials():
    with pytest.raises(UnauthorizedError) as exc_info:
        Dependencies.get_current_user(credentials=None)

    assert exc_info.value.message == "Authentication is required."


def test_get_current_user_rejects_invalid_token():
    from supabase_auth.errors import AuthApiError

    credentials = type(
        "Credentials",
        (),
        {"credentials": "invalid-token"},
    )()

    with patch(
        "app.container.dependencies.auth_client.auth.get_user",
        side_effect=AuthApiError(
    "Invalid token",
    401,
    "invalid_token",
),
    ):
        with pytest.raises(UnauthorizedError) as exc_info:
            Dependencies.get_current_user(credentials=credentials)

    assert exc_info.value.message == "Invalid or expired access token."
    

def test_get_current_user_returns_authenticated_user():
    from types import SimpleNamespace

    credentials = type(
        "Credentials",
        (),
        {"credentials": "valid-test-token"},
    )()

    mock_response = SimpleNamespace(
        user=SimpleNamespace(
            id="user-123",
            email="customer@example.com",
        )
    )

    with patch(
        "app.container.dependencies.auth_client.auth.get_user",
        return_value=mock_response,
    ) as mock_get_user:
        result = Dependencies.get_current_user(credentials=credentials)

    mock_get_user.assert_called_once_with("valid-test-token")
    assert result == {
        "user_id": "user-123",
        "email": "customer@example.com",
    }

