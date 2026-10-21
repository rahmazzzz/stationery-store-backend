
from collections.abc import Generator
from pathlib import Path

import pytest
from dotenv import dotenv_values
from sqlalchemy import create_engine
from sqlalchemy.engine import URL, make_url
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import Base
from app.models import Category, Product
from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.container.dependencies import (
    get_database_session,
    get_write_database_session,
)
from app.main import app


BACKEND_DIR = Path(__file__).resolve().parents[1]
TEST_ENV_FILE = BACKEND_DIR / ".env.test"
EXPECTED_TEST_DATABASE = "stationery_store_test"


def get_test_database_url() -> URL:
    """Load and validate the dedicated test database URL."""
    if not TEST_ENV_FILE.is_file():
        raise RuntimeError(
            f"Test environment file not found: {TEST_ENV_FILE}"
        )

    env_values = dotenv_values(TEST_ENV_FILE)
    database_url = env_values.get("DATABASE_URL")

    if not database_url:
        raise RuntimeError(
            f"DATABASE_URL is missing from {TEST_ENV_FILE}"
        )

    url = make_url(database_url)

    if url.database != EXPECTED_TEST_DATABASE:
        raise RuntimeError(
            "Refusing to run database tests. "
            f"Expected database '{EXPECTED_TEST_DATABASE}', "
            f"but configured database is '{url.database}'."
        )

    return url


@pytest.fixture(scope="session")
def test_engine():
    """
    Create the test database engine and manage test table lifecycle.

    This fixture must only target the dedicated test database.
    """
    database_url = get_test_database_url()

    engine = create_engine(
        database_url,
        pool_pre_ping=True,
    )

    try:
        # Verify the connection before creating or modifying tables.
        with engine.connect() as connection:
            connection.exec_driver_sql("SELECT 1")

        # Create the tables required by the tests.
        Base.metadata.create_all(engine)

        yield engine

    finally:
        try:
            # Never drop tables unless the target is the test database.
            if engine.url.database != EXPECTED_TEST_DATABASE:
                raise RuntimeError(
                    "Refusing to drop tables from a non-test database."
                )

            Base.metadata.drop_all(engine)

        finally:
            engine.dispose()


@pytest.fixture()
def db_session(test_engine) -> Generator[Session, None, None]:
    """
    Provide a database session isolated by an outer transaction.

    Session commits use savepoints, allowing the outer transaction
    to be rolled back after each test.
    """
    connection = test_engine.connect()
    outer_transaction = connection.begin()

    session_factory = sessionmaker(
        bind=connection,
        class_=Session,
        autoflush=False,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )

    session = session_factory()

    try:
        yield session

    finally:
        try:
            session.close()
        finally:
            try:
                if outer_transaction.is_active:
                    outer_transaction.rollback()
            finally:
                connection.close()


@pytest.fixture()
def database_models() -> tuple[type[Category], type[Product]]:
    """Provide the registered SQLAlchemy model classes."""
    return Category, Product


@pytest.fixture()
def api_client(
    db_session: Session,
) -> Generator[TestClient, None, None]:
    """Provide an API client backed by the isolated test session."""

    def override_database_session() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_database_session] = (
        override_database_session
    )
    app.dependency_overrides[get_write_database_session] = (
        override_database_session
    )

    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.pop(get_database_session, None)
        app.dependency_overrides.pop(
            get_write_database_session,
            None,
        )
