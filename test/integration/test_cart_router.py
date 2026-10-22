
from decimal import Decimal

import pytest

from app.models import Category, Product


@pytest.fixture
def active_product(db_session):
    category = Category(
        name="Cart Test Category",
        slug="cart-test-category",
    )
    db_session.add(category)
    db_session.flush()

    product = Product(
        category_id=category.id,
        name="Cart Test Notebook",
        slug="cart-test-notebook",
        sku="CART-TEST-NOTEBOOK",
        width_cm=Decimal("14.80"),
        height_cm=Decimal("21.00"),
        price=Decimal("100.00"),
        discount_type="none",
        discount_value=Decimal("0.00"),
        is_active=True,
    )
    db_session.add(product)
    db_session.flush()

    return product


def test_add_item_to_guest_cart(api_client, active_product):
    cart_response = api_client.get("/api/v1/cart")
    guest_token = cart_response.headers["X-Guest-Token"]

    response = api_client.post(
        "/api/v1/cart/items",
        headers={"X-Guest-Token": guest_token},
        json={"product_id": active_product.id, "quantity": 2},
    )

    assert response.status_code == 200

    data = response.json()
    assert data["total_items"] == 2
    assert data["subtotal"] == "200.00"
    assert len(data["items"]) == 1
    assert data["items"][0]["product_id"] == active_product.id
    assert data["items"][0]["quantity"] == 2
    assert data["items"][0]["unit_price"] == "100.00"


def test_adding_same_product_increases_quantity(api_client, active_product):
    cart_response = api_client.get("/api/v1/cart")
    guest_token = cart_response.headers["X-Guest-Token"]
    headers = {"X-Guest-Token": guest_token}

    first_response = api_client.post(
        "/api/v1/cart/items",
        headers=headers,
        json={"product_id": active_product.id, "quantity": 2},
    )
    assert first_response.status_code == 200

    second_response = api_client.post(
        "/api/v1/cart/items",
        headers=headers,
        json={"product_id": active_product.id, "quantity": 3},
    )

    assert second_response.status_code == 200

    data = second_response.json()
    assert data["total_items"] == 5
    assert data["subtotal"] == "500.00"
    assert len(data["items"]) == 1
    assert data["items"][0]["quantity"] == 5
    assert len(data["items"]) == 1
    assert data["items"][0]["quantity"] == 5




def test_get_cart_creates_guest_cart_and_returns_token(api_client):
    response = api_client.get("/api/v1/cart")

    assert response.status_code == 200

    data = response.json()
    guest_token = response.headers.get("X-Guest-Token")

    assert guest_token is not None
    assert len(guest_token) >= 20
    assert data["id"] is not None
    assert data["items"] == []
    assert data["total_items"] == 0
    assert data["subtotal"] == "0.00"


def test_get_cart_reuses_existing_guest_token(api_client):
    first_response = api_client.get("/api/v1/cart")

    assert first_response.status_code == 200

    guest_token = first_response.headers.get("X-Guest-Token")
    assert guest_token is not None

    first_cart_id = first_response.json()["id"]

    second_response = api_client.get(
        "/api/v1/cart",
        headers={"X-Guest-Token": guest_token},
    )

    assert second_response.status_code == 200
    assert second_response.json()["id"] == first_cart_id
    assert second_response.headers.get("X-Guest-Token") is None


def test_update_cart_item_quantity(api_client, active_product):
    cart_response = api_client.get("/api/v1/cart")
    guest_token = cart_response.headers["X-Guest-Token"]
    headers = {"X-Guest-Token": guest_token}

    add_response = api_client.post(
        "/api/v1/cart/items",
        headers=headers,
        json={"product_id": active_product.id, "quantity": 2},
    )
    assert add_response.status_code == 200

    update_response = api_client.patch(
        f"/api/v1/cart/items/{active_product.id}",
        headers=headers,
        json={"quantity": 4},
    )

    assert update_response.status_code == 200

    data = update_response.json()
    assert data["total_items"] == 4
    assert data["subtotal"] == "400.00"
    assert len(data["items"]) == 1
    assert data["items"][0]["quantity"] == 4


def test_remove_cart_item(api_client, active_product):
    cart_response = api_client.get("/api/v1/cart")
    guest_token = cart_response.headers["X-Guest-Token"]
    headers = {"X-Guest-Token": guest_token}

    add_response = api_client.post(
        "/api/v1/cart/items",
        headers=headers,
        json={"product_id": active_product.id, "quantity": 2},
    )
    assert add_response.status_code == 200

    delete_response = api_client.delete(
        f"/api/v1/cart/items/{active_product.id}",
        headers=headers,
    )

    assert delete_response.status_code == 200

    data = delete_response.json()
    assert data["total_items"] == 0
    assert data["subtotal"] == "0.00"
    assert data["items"] == []


def test_add_item_with_nonexistent_product_returns_not_found(api_client):
    cart_response = api_client.get("/api/v1/cart")
    guest_token = cart_response.headers["X-Guest-Token"]

    response = api_client.post(
        "/api/v1/cart/items",
        headers={"X-Guest-Token": guest_token},
        json={"product_id": 999999, "quantity": 1},
    )

    assert response.status_code == 404


@pytest.mark.parametrize("quantity", [0, -1])
def test_add_item_with_invalid_quantity_returns_validation_error(
    api_client,
    active_product,
    quantity,
):
    cart_response = api_client.get("/api/v1/cart")
    guest_token = cart_response.headers["X-Guest-Token"]

    response = api_client.post(
        "/api/v1/cart/items",
        headers={"X-Guest-Token": guest_token},
        json={"product_id": active_product.id, "quantity": quantity},
    )

    assert response.status_code == 422


def test_update_item_not_in_cart_returns_not_found(api_client, active_product):
    cart_response = api_client.get("/api/v1/cart")
    guest_token = cart_response.headers["X-Guest-Token"]

    response = api_client.patch(
        f"/api/v1/cart/items/{active_product.id}",
        headers={"X-Guest-Token": guest_token},
        json={"quantity": 3},
    )

    assert response.status_code == 404


def test_remove_item_not_in_cart_returns_not_found(api_client, active_product):
    cart_response = api_client.get("/api/v1/cart")
    guest_token = cart_response.headers["X-Guest-Token"]

    response = api_client.delete(
        f"/api/v1/cart/items/{active_product.id}",
        headers={"X-Guest-Token": guest_token},
    )

    assert response.status_code == 404


def test_update_without_guest_token_returns_not_found(api_client):
    response = api_client.patch(
        "/api/v1/cart/items/1",
        json={"quantity": 2},
    )

    assert response.status_code == 404
    assert "X-Guest-Token" not in response.headers


def test_remove_without_guest_token_returns_not_found(api_client):
    response = api_client.delete("/api/v1/cart/items/1")

    assert response.status_code == 404
    assert "X-Guest-Token" not in response.headers
