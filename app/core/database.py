
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings


engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
)


SessionLocal = sessionmaker(
    bind=engine,
    class_=Session,
    autoflush=False,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""


def get_db() -> Generator[Session, None, None]:
    """Provide a session for read-only database operations."""
    with SessionLocal() as session:
        try:
            yield session
        except Exception:
            session.rollback()
            raise


def get_write_db() -> Generator[Session, None, None]:
    """Provide a session with an explicit write transaction."""
    with SessionLocal() as session:
        try:
            with session.begin():
                yield session
        except Exception:
            session.rollback()
            raise
