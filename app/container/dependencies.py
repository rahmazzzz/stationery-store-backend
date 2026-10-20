

from collections.abc import Generator

from sqlalchemy.orm import Session

from app.core.database import get_db, get_write_db


def get_database_session() -> Generator[Session, None, None]:
    """Provide a session for read operations."""
    yield from get_db()


def get_write_database_session() -> Generator[Session, None, None]:
    """Provide a session with a managed write transaction."""
    yield from get_write_db()
