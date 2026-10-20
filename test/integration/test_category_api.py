
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.container.dependencies import (
    get_database_session,
    get_write_database_session,
)
from app.main import app


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


def test_create_category_returns_201(
    api_client: TestClient,
) -> None:
    response = api_client.post(
        "/api/v1/categories",
        json={"name": "Stickers", "slug": "stickers"},
    )

    assert response.status_code == 201
    assert response.json()["name"] == "Stickers"
    assert response.json()["slug"] == "stickers"
    assert isinstance(response.json()["id"], int)


def test_list_categories_returns_created_categories(
    api_client: TestClient,
) -> None:
    api_client.post(
        "/api/v1/categories",
        json={"name": "Stickers", "slug": "stickers"},
    )
    api_client.post(
        "/api/v1/categories",
        json={"name": "Notebooks", "slug": "notebooks"},
    )

    response = api_client.get("/api/v1/categories")

    assert response.status_code == 200
    assert len(response.json()) == 2
    assert [item["name"] for item in response.json()] == [
        "Stickers",
        "Notebooks",
    ]


def test_list_categories_supports_pagination(
    api_client: TestClient,
) -> None:
    for name, slug in [
        ("Stickers", "stickers"),
        ("Notebooks", "notebooks"),
        ("Pens", "pens"),
    ]:
        response = api_client.post(
            "/api/v1/categories",
            json={"name": name, "slug": slug},
        )
        assert response.status_code == 201

    response = api_client.get(
        "/api/v1/categories",
        params={"offset": 1, "limit": 1},
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["name"] == "Notebooks"


def test_get_category_by_id(api_client: TestClient) -> None:
    created = api_client.post(
        "/api/v1/categories",
        json={"name": "Stickers", "slug": "stickers"},
    )
    category_id = created.json()["id"]

    response = api_client.get(f"/api/v1/categories/{category_id}")

    assert response.status_code == 200
    assert response.json()["name"] == "Stickers"


def test_get_category_by_slug(api_client: TestClient) -> None:
    api_client.post(
        "/api/v1/categories",
        json={"name": "Stickers", "slug": "stickers"},
    )

    response = api_client.get(
        "/api/v1/categories/slug/stickers"
    )

    assert response.status_code == 200
    assert response.json()["slug"] == "stickers"


def test_update_category_changes_supplied_fields(
    api_client: TestClient,
) -> None:
    created = api_client.post(
        "/api/v1/categories",
        json={"name": "Stickers", "slug": "stickers"},
    )
    category_id = created.json()["id"]

    response = api_client.patch(
        f"/api/v1/categories/{category_id}",
        json={"name": "Sticker Sheets"},
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Sticker Sheets"
    assert response.json()["slug"] == "stickers"


def test_delete_category_returns_204(
    api_client: TestClient,
) -> None:
    created = api_client.post(
        "/api/v1/categories",
        json={"name": "Temporary", "slug": "temporary"},
    )
    category_id = created.json()["id"]

    response = api_client.delete(
        f"/api/v1/categories/{category_id}"
    )

    assert response.status_code == 204
    assert response.content == b""


def test_create_category_rejects_invalid_input(
    api_client: TestClient,
) -> None:
    response = api_client.post(
        "/api/v1/categories",
        json={"name": "", "slug": "stickers"},
    )

    assert response.status_code == 422


def test_list_categories_rejects_invalid_pagination(
    api_client: TestClient,
) -> None:
    response = api_client.get(
        "/api/v1/categories",
        params={"offset": -1},
    )

    assert response.status_code == 422
    
    
def test_create_category_rejects_duplicate_name(
    api_client: TestClient,
) -> None:
    api_client.post(
        "/api/v1/categories",
        json={"name": "Stickers", "slug": "stickers"},
    )

    response = api_client.post(
        "/api/v1/categories",
        json={"name": "Stickers", "slug": "sticker-products"},
    )

    assert response.status_code == 409
    assert "detail" in response.json()


def test_create_category_rejects_duplicate_slug(
    api_client: TestClient,
) -> None:
    api_client.post(
        "/api/v1/categories",
        json={"name": "Stickers", "slug": "stickers"},
    )

    response = api_client.post(
        "/api/v1/categories",
        json={"name": "Sticker Sheets", "slug": "stickers"},
    )

    assert response.status_code == 409
    assert "detail" in response.json()


def test_get_nonexistent_category_returns_404(
    api_client: TestClient,
) -> None:
    response = api_client.get("/api/v1/categories/999999")

    assert response.status_code == 404
    assert "detail" in response.json()


def test_get_nonexistent_category_slug_returns_404(
    api_client: TestClient,
) -> None:
    response = api_client.get(
        "/api/v1/categories/slug/nonexistent-category"
    )

    assert response.status_code == 404
    assert "detail" in response.json()


def test_update_nonexistent_category_returns_404(
    api_client: TestClient,
) -> None:
    response = api_client.patch(
        "/api/v1/categories/999999",
        json={"name": "Updated Category"},
    )

    assert response.status_code == 404
    assert "detail" in response.json()


def test_delete_nonexistent_category_returns_404(
    api_client: TestClient,
) -> None:
    response = api_client.delete("/api/v1/categories/999999")

    assert response.status_code == 404
    assert "detail" in response.json()


def test_update_category_with_empty_body(
    api_client: TestClient,
) -> None:
    created = api_client.post(
        "/api/v1/categories",
        json={"name": "Stickers", "slug": "stickers"},
    )
    category_id = created.json()["id"]

    response = api_client.patch(
        f"/api/v1/categories/{category_id}",
        json={},
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Stickers"
    assert response.json()["slug"] == "stickers"
