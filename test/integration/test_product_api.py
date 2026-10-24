import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.container.dependencies import get_current_user
from app.core.config import settings

def create_category(
    api_client: TestClient,
    *,
    name: str = "Notebooks",
    slug: str = "notebooks",
) -> int:
    """Create a category and return its database ID."""
    response = api_client.post(
        "/api/v1/categories",
        json={"name": name, "slug": slug},
    )

    assert response.status_code == 201
    return response.json()["id"]


def create_product(
    api_client: TestClient,
    *,
    category_id: int,
    name: str = "A5 Notebook",
    slug: str = "a5-notebook",
    sku: str = "NOTEBOOK-A5-001",
    price: str = "100.00",
    discount_type: str = "none",
    discount_value: str = "0.00",
) -> dict:
    """Create a product and return its response data."""
    response = api_client.post(
        "/api/v1/products",
        json={
            "category_id": category_id,
            "name": name,
            "slug": slug,
            "sku": sku,
            "description": "A notebook for everyday use.",
            "width_cm": "14.80",
            "height_cm": "21.00",
            "price": price,
            "discount_type": discount_type,
            "discount_value": discount_value,
        },
    )

    assert response.status_code == 201, response.text
    return response.json()

def authenticate_as(
    api_client: TestClient,
    monkeypatch,
    *,
    user_id: str,
) -> None:
    """Authenticate the test client as a specific user."""
    monkeypatch.setattr(settings, "admin_user_ids", "admin-test-user")

    api_client.app.dependency_overrides[get_current_user] = (
        lambda: {
            "user_id": user_id,
            "email": f"{user_id}@example.com",
        }
    )

def test_create_product_returns_201(api_client: TestClient) -> None:
    category_id = create_category(api_client)

    product = create_product(
        api_client,
        category_id=category_id,
    )

    assert product["name"] == "A5 Notebook"
    assert product["slug"] == "a5-notebook"
    assert product["sku"] == "NOTEBOOK-A5-001"
    assert product["category_id"] == category_id
    assert product["is_active"] is True
    assert product["price"] == "100.00"


def test_create_product_rejects_nonexistent_category(
    api_client: TestClient,
) -> None:
    response = api_client.post(
        "/api/v1/products",
        json={
            "category_id": 999999,
            "name": "A5 Notebook",
            "slug": "a5-notebook",
            "sku": "NOTEBOOK-A5-001",
            "width_cm": "14.80",
            "height_cm": "21.00",
            "price": "100.00",
        },
    )

    assert response.status_code == 404


def test_create_product_rejects_duplicate_slug(
    api_client: TestClient,
) -> None:
    category_id = create_category(api_client)

    create_product(api_client, category_id=category_id)

    response = api_client.post(
        "/api/v1/products",
        json={
            "category_id": category_id,
            "name": "Another Notebook",
            "slug": "a5-notebook",
            "sku": "NOTEBOOK-A5-002",
            "width_cm": "14.80",
            "height_cm": "21.00",
            "price": "120.00",
        },
    )

    assert response.status_code == 409


def test_create_product_rejects_duplicate_sku(
    api_client: TestClient,
) -> None:
    category_id = create_category(api_client)

    create_product(api_client, category_id=category_id)

    response = api_client.post(
        "/api/v1/products",
        json={
            "category_id": category_id,
            "name": "Another Notebook",
            "slug": "another-notebook",
            "sku": "NOTEBOOK-A5-001",
            "width_cm": "14.80",
            "height_cm": "21.00",
            "price": "120.00",
        },
    )

    assert response.status_code == 409


def test_get_product_by_id(api_client: TestClient) -> None:
    category_id = create_category(api_client)
    created = create_product(api_client, category_id=category_id)

    response = api_client.get(
        f"/api/v1/products/{created['id']}"
    )

    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


def test_get_product_by_slug(api_client: TestClient) -> None:
    category_id = create_category(api_client)
    create_product(api_client, category_id=category_id)

    response = api_client.get(
        "/api/v1/products/slug/a5-notebook"
    )

    assert response.status_code == 200
    assert response.json()["slug"] == "a5-notebook"


def test_get_nonexistent_product_returns_404(
    api_client: TestClient,
) -> None:
    response = api_client.get("/api/v1/products/999999")

    assert response.status_code == 404


def test_list_products_returns_active_products(
    api_client: TestClient,
) -> None:
    category_id = create_category(api_client)

    create_product(api_client, category_id=category_id)
    create_product(
        api_client,
        category_id=category_id,
        name="Sketchbook",
        slug="sketchbook",
        sku="SKETCHBOOK-001",
    )

    response = api_client.get("/api/v1/products")

    assert response.status_code == 200
    assert len(response.json()) == 2


def test_list_products_filters_by_category(
    api_client: TestClient,
) -> None:
    first_category_id = create_category(api_client)

    second_category_id = create_category(
        api_client,
        name="Pens",
        slug="pens",
    )

    create_product(api_client, category_id=first_category_id)
    create_product(
        api_client,
        category_id=second_category_id,
        name="Blue Pen",
        slug="blue-pen",
        sku="PEN-BLUE-001",
    )

    response = api_client.get(
        "/api/v1/products",
        params={"category_id": second_category_id},
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["name"] == "Blue Pen"


def test_list_products_supports_pagination(
    api_client: TestClient,
) -> None:
    category_id = create_category(api_client)

    create_product(api_client, category_id=category_id)
    create_product(
        api_client,
        category_id=category_id,
        name="Sketchbook",
        slug="sketchbook",
        sku="SKETCHBOOK-001",
    )

    response = api_client.get(
        "/api/v1/products",
        params={"offset": 1, "limit": 1},
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["name"] == "Sketchbook"


def test_list_products_rejects_invalid_pagination(
    api_client: TestClient,
) -> None:
    response = api_client.get(
        "/api/v1/products",
        params={"limit": 0},
    )

    assert response.status_code == 422


def test_update_product_changes_supplied_fields(
    api_client: TestClient,
) -> None:
    category_id = create_category(api_client)
    created = create_product(
        api_client,
        category_id=category_id,
    )

    response = api_client.patch(
        f"/api/v1/products/{created['id']}",
        json={"name": "Premium A5 Notebook"},
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Premium A5 Notebook"
    assert response.json()["slug"] == "a5-notebook"


def test_update_product_rejects_price_below_fixed_discount(
    api_client: TestClient,
) -> None:
    category_id = create_category(api_client)

    created = create_product(
        api_client,
        category_id=category_id,
        price="100.00",
        discount_type="fixed",
        discount_value="20.00",
    )

    response = api_client.patch(
        f"/api/v1/products/{created['id']}",
        json={"price": "10.00"},
    )

    assert response.status_code == 422

    # The rejected update must not change the stored price.
    unchanged = api_client.get(
        f"/api/v1/products/{created['id']}"
    )

    assert unchanged.status_code == 200
    assert unchanged.json()["price"] == "100.00"


def test_update_product_rejects_duplicate_sku(
    api_client: TestClient,
) -> None:
    category_id = create_category(api_client)

    first = create_product(api_client, category_id=category_id)
    second = create_product(
        api_client,
        category_id=category_id,
        name="Sketchbook",
        slug="sketchbook",
        sku="SKETCHBOOK-001",
    )

    response = api_client.patch(
        f"/api/v1/products/{second['id']}",
        json={"sku": first["sku"]},
    )

    assert response.status_code == 409


def test_deactivate_product_removes_it_from_public_catalog(
    api_client: TestClient,
) -> None:
    category_id = create_category(api_client)
    created = create_product(api_client, category_id=category_id)

    response = api_client.patch(
        f"/api/v1/products/{created['id']}/deactivate"
    )

    assert response.status_code == 200
    assert response.json()["is_active"] is False

    detail_response = api_client.get(
        f"/api/v1/products/{created['id']}"
    )
    assert detail_response.status_code == 404

    list_response = api_client.get("/api/v1/products")
    assert list_response.status_code == 200
    assert list_response.json() == []


def test_create_product_rejects_invalid_price(
    api_client: TestClient,
) -> None:
    category_id = create_category(api_client)

    response = api_client.post(
        "/api/v1/products",
        json={
            "category_id": category_id,
            "name": "Invalid Notebook",
            "slug": "invalid-notebook",
            "sku": "NOTEBOOK-INVALID",
            "width_cm": "14.80",
            "height_cm": "21.00",
            "price": "0.00",
        },
    )

    assert response.status_code == 422


def test_create_product_rejects_nonzero_discount_when_type_is_none(
    api_client: TestClient,
) -> None:
    category_id = create_category(api_client)

    response = api_client.post(
        "/api/v1/products",
        json={
            "category_id": category_id,
            "name": "Invalid Notebook",
            "slug": "invalid-discount-notebook",
            "sku": "NOTEBOOK-DISCOUNT-001",
            "width_cm": "14.80",
            "height_cm": "21.00",
            "price": "100.00",
            "discount_type": "none",
            "discount_value": "20.00",
        },
    )

    assert response.status_code == 422


def test_changing_discount_type_to_none_resets_discount_value(
    api_client: TestClient,
) -> None:
    category_id = create_category(api_client)

    created = create_product(
        api_client,
        category_id=category_id,
        price="100.00",
        discount_type="fixed",
        discount_value="20.00",
    )

    response = api_client.patch(
        f"/api/v1/products/{created['id']}",
        json={"discount_type": "none"},
    )

    assert response.status_code == 200
    assert response.json()["discount_type"] == "none"
    assert response.json()["discount_value"] == "0.00"

def test_update_product_rejects_null_price(api_client: TestClient) -> None:
    category_id = create_category(api_client)
    product = create_product(api_client, category_id=category_id)

    response = api_client.patch(
        f"/api/v1/products/{product['id']}",
        json={"price": None},
    )

    assert response.status_code == 422


def test_update_product_allows_clearing_description(
    api_client: TestClient,
) -> None:
    category_id = create_category(api_client)
    product = create_product(api_client, category_id=category_id)

    response = api_client.patch(
        f"/api/v1/products/{product['id']}",
        json={"description": None},
    )

    assert response.status_code == 200
    assert response.json()["description"] is None




def test_update_product_rejects_empty_patch(
    api_client: TestClient,
) -> None:
    category_id = create_category(api_client)
    product = create_product(
        api_client,
        category_id=category_id,
    )

    response = api_client.patch(
        f"/api/v1/products/{product['id']}",
        json={},
    )
    assert response.status_code == 422



def test_update_product_clears_discount_when_type_changes_to_none(
    api_client: TestClient,
) -> None:
    category_id = create_category(api_client)

    product = create_product(
        api_client,
        category_id=category_id,
        discount_type="percentage",
        discount_value="20.00",
    )

    response = api_client.patch(
        f"/api/v1/products/{product['id']}",
        json={"discount_type": "none"},
    )

    assert response.status_code == 200, response.text

    updated_product = response.json()
    assert updated_product["discount_type"] == "none"
    assert updated_product["discount_value"] == "0.00"


def test_update_product_rejects_price_below_existing_fixed_discount(
    api_client: TestClient,
) -> None:
    category_id = create_category(api_client)

    product = create_product(
        api_client,
        category_id=category_id,
        price="100.00",
        discount_type="fixed",
        discount_value="80.00",
    )

    response = api_client.patch(
        f"/api/v1/products/{product['id']}",
        json={"price": "50.00"},
    )

    assert response.status_code == 422, response.text



def test_update_product_allows_price_above_existing_fixed_discount(
    api_client: TestClient,
) -> None:
    category_id = create_category(api_client)

    product = create_product(
        api_client,
        category_id=category_id,
        price="100.00",
        discount_type="fixed",
        discount_value="20.00",
    )

    response = api_client.patch(
        f"/api/v1/products/{product['id']}",
        json={"price": "50.00"},
    )

    assert response.status_code == 200, response.text

    updated_product = response.json()
    assert updated_product["price"] == "50.00"
    assert updated_product["discount_type"] == "fixed"
    assert updated_product["discount_value"] == "20.00"


def test_admin_can_update_product_inventory(
    api_client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    authenticate_as(
        api_client,
        monkeypatch,
        user_id="admin-test-user",
    )

    category_id = create_category(api_client)
    product = create_product(api_client, category_id=category_id)

    response = api_client.patch(
        f"/api/v1/products/{product['id']}/inventory",
        json={"stock_quantity": 25},
    )

    assert response.status_code == 200, response.text
    assert response.json()["stock_quantity"] == 25
    assert response.json()["reserved_quantity"] == 0


def test_non_admin_cannot_update_product_inventory(
    api_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    authenticate_as(
        api_client,
        monkeypatch,
        user_id="customer-test-user",
    )

    category_id = create_category(api_client)
    product = create_product(api_client, category_id=category_id)

    response = api_client.patch(
        f"/api/v1/products/{product['id']}/inventory",
        json={"stock_quantity": 25},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Administrator access is required."


def test_admin_cannot_set_negative_inventory(
    api_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    authenticate_as(
        api_client,
        monkeypatch,
        user_id="admin-test-user",
    )

    category_id = create_category(api_client)
    product = create_product(api_client, category_id=category_id)

    response = api_client.patch(
        f"/api/v1/products/{product['id']}/inventory",
        json={"stock_quantity": -1},
    )

    assert response.status_code == 422


def test_admin_cannot_update_inventory_for_nonexistent_product(
    api_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    authenticate_as(
        api_client,
        monkeypatch,
        user_id="admin-test-user",
    )

    response = api_client.patch(
        "/api/v1/products/999999/inventory",
        json={"stock_quantity": 25},
    )

    assert response.status_code == 404

def test_admin_cannot_reduce_inventory_below_reserved_quantity(
    api_client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    authenticate_as(
        api_client,
        monkeypatch,
        user_id="admin-test-user",
    )

    category_id = create_category(api_client)
    product = create_product(api_client, category_id=category_id)

    # Simulate 5 units already reserved for orders.
    from app.models import Product

    db_product = db_session.get(Product, product["id"])
    assert db_product is not None

    db_product.stock_quantity = 10
    db_product.reserved_quantity = 5
    db_session.flush()

    response = api_client.patch(
        f"/api/v1/products/{product['id']}/inventory",
        json={"stock_quantity": 4},
    )

    assert response.status_code == 422, response.text
    assert "reserved" in response.json()["detail"].lower()

    # The failed update must not change the existing stock.
    db_session.refresh(db_product)
    assert db_product.stock_quantity == 10
    assert db_product.reserved_quantity == 5
