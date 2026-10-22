from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.models import Category, DeliveryCity, Order, Product


@pytest.fixture
def checkout_product(db_session):
    category = Category(
        name="Checkout Test Category",
        slug="checkout-test-category",
    )
    db_session.add(category)
    db_session.flush()

    product = Product(
        category_id=category.id,
        name="Checkout Test Notebook",
        slug="checkout-test-notebook",
        sku="CHECKOUT-TEST-NOTEBOOK",
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


@pytest.fixture
def active_delivery_city(db_session):
    city = DeliveryCity(
        name="Checkout Test City",
        shipping_fee=Decimal("35.00"),
        is_active=True,
    )
    db_session.add(city)
    db_session.flush()
    return city


def add_product_to_guest_cart(
    api_client: TestClient,
    product_id: int,
) -> str:
    cart_response = api_client.get("/api/v1/cart")
    assert cart_response.status_code == 200

    guest_token = cart_response.headers["X-Guest-Token"]

    response = api_client.post(
        "/api/v1/cart/items",
        headers={"X-Guest-Token": guest_token},
        json={"product_id": product_id, "quantity": 2},
    )
    assert response.status_code == 200

    return guest_token


def checkout_payload(city: str = "Checkout Test City") -> dict:
    return {
        "customer_name": "Test Customer",
        "phone_number": "01012345678",
        "city": city,
        "delivery_address": "12 Test Street, Apartment 3",
        "delivery_instructions": "Call upon arrival",
        "payment_method": "cash_on_delivery",
    }


def test_guest_checkout_creates_order_and_clears_cart(
    api_client: TestClient,
    db_session,
    checkout_product,
    active_delivery_city,
):
    guest_token = add_product_to_guest_cart(
        api_client,
        checkout_product.id,
    )

    response = api_client.post(
        "/api/v1/checkout",
        headers={"X-Guest-Token": guest_token},
        json=checkout_payload(),
    )

    assert response.status_code == 201
    data = response.json()

    assert data["customer_name"] == "Test Customer"
    assert data["city"] == "Checkout Test City"
    assert data["subtotal"] == "200.00"
    assert data["shipping_fee"] == "35.00"
    assert data["total"] == "235.00"
    assert data["payment_method"] == "cash_on_delivery"
    assert data["status"] == "pending"

    assert len(data["items"]) == 1
    assert data["items"][0]["product_name"] == "Checkout Test Notebook"
    assert data["items"][0]["unit_price"] == "100.00"
    assert data["items"][0]["quantity"] == 2
    assert data["items"][0]["line_total"] == "200.00"

    # The order and its item snapshots should be persisted in the session.
    order = db_session.get(Order, data["id"])
    assert order is not None
    assert order.guest_token == guest_token
    assert order.customer_id is None
    assert len(order.items) == 1

    # Checkout should empty the cart but preserve the guest cart itself.
    cart_response = api_client.get(
        "/api/v1/cart",
        headers={"X-Guest-Token": guest_token},
    )
    assert cart_response.status_code == 200
    assert cart_response.json()["items"] == []
    assert cart_response.json()["total_items"] == 0


def test_checkout_rejects_missing_guest_token(
    api_client: TestClient,
):
    response = api_client.post(
        "/api/v1/checkout",
        json=checkout_payload(),
    )

    assert response.status_code == 422


def test_checkout_rejects_empty_cart(
    api_client: TestClient,
    active_delivery_city,
):
    cart_response = api_client.get("/api/v1/cart")
    guest_token = cart_response.headers["X-Guest-Token"]

    response = api_client.post(
        "/api/v1/checkout",
        headers={"X-Guest-Token": guest_token},
        json=checkout_payload(),
    )

    assert response.status_code == 422


def test_checkout_rejects_unavailable_city_and_keeps_cart(
    api_client: TestClient,
    checkout_product,
    active_delivery_city,
):
    guest_token = add_product_to_guest_cart(
        api_client,
        checkout_product.id,
    )

    response = api_client.post(
        "/api/v1/checkout",
        headers={"X-Guest-Token": guest_token},
        json=checkout_payload(city="Unconfigured Test City"),
    )

    assert response.status_code == 404

    # A failed checkout must not remove items from the cart.
    cart_response = api_client.get(
        "/api/v1/cart",
        headers={"X-Guest-Token": guest_token},
    )
    assert cart_response.status_code == 200
    assert cart_response.json()["total_items"] == 2
    assert len(cart_response.json()["items"]) == 1