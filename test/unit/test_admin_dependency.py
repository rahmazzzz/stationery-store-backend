
import pytest
from fastapi import HTTPException

from app.container.dependencies import get_current_admin
from app.core.config import settings


def test_admin_is_allowed(monkeypatch):
    monkeypatch.setattr(settings, "admin_user_ids", "admin-123")

    user = {"user_id": "admin-123", "email": "admin@example.com"}

    result = get_current_admin(user)

    assert result == user


def test_non_admin_is_rejected(monkeypatch):
    monkeypatch.setattr(settings, "admin_user_ids", "admin-123")

    user = {"user_id": "customer-456", "email": "customer@example.com"}

    with pytest.raises(HTTPException) as exc_info:
        get_current_admin(user)

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Administrator access is required."


def test_empty_admin_allowlist_rejects_everyone(monkeypatch):
    monkeypatch.setattr(settings, "admin_user_ids", "")

    user = {"user_id": "admin-123", "email": "admin@example.com"}

    with pytest.raises(HTTPException) as exc_info:
        get_current_admin(user)

    assert exc_info.value.status_code == 403
