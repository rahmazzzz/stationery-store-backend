
from collections.abc import Generator
from typing import TypedDict

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from supabase_auth.errors import AuthApiError

from app.clients.auth_client import auth_client
from app.core.database import get_db, get_write_db
from app.exceptions import UnauthorizedError


class CurrentUser(TypedDict):
    user_id: str
    email: str | None


class Dependencies:
    """Centralize FastAPI dependencies for database access and authentication."""

    _bearer_scheme = HTTPBearer(auto_error=False)

    @staticmethod
    def get_database_session() -> Generator[Session, None, None]:
        """Provide a session for read operations."""
        yield from get_db()

    @staticmethod
    def get_write_database_session() -> Generator[Session, None, None]:
        """Provide a session with a managed write transaction."""
        yield from get_write_db()

    @staticmethod
    def get_current_user(
        credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    ) -> CurrentUser:
        """Validate a Supabase access token and return the authenticated user."""
        if credentials is None:
            raise UnauthorizedError("Authentication is required.")

        try:
            response = auth_client.auth.get_user(credentials.credentials)
        except AuthApiError as exc:
            raise UnauthorizedError(
                "Invalid or expired access token."
            ) from exc

        user = response.user

        if user is None:
            raise UnauthorizedError("Invalid or expired access token.")

        return {
            "user_id": str(user.id),
            "email": user.email,
        }


# Preserve the existing dependency function names so current routers
# and tests do not need to change.
get_database_session = Dependencies.get_database_session
get_write_database_session = Dependencies.get_write_database_session
get_current_user = Dependencies.get_current_user
