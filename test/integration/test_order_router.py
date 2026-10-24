from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.models import Category, DeliveryCity, Order, Product
from app.container.dependencies import get_optional_current_user
from app.main import app


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
        stock_quantity=10,
        reserved_quantity=0,
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
    db_session.refresh(checkout_product)

    assert checkout_product.stock_quantity == 10
    assert checkout_product.reserved_quantity == 2
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


def test_authenticated_checkout_creates_order_and_clears_cart(
    api_client: TestClient,
    db_session,
    checkout_product,
    active_delivery_city,
):
    def override_current_user():
        return {
            "user_id": "customer-123",
            "email": "customer@example.com",
        }

    app.dependency_overrides[get_optional_current_user] = (
        override_current_user
    )

    try:
        # Add a product to the authenticated customer's cart.
        cart_response = api_client.post(
            "/api/v1/cart/items",
            json={
                "product_id": checkout_product.id,
                "quantity": 2,
            },
        )

        assert cart_response.status_code == 200

        # Checkout without a guest token.
        response = api_client.post(
            "/api/v1/checkout",
            json=checkout_payload(),
        )

        assert response.status_code == 201
        data = response.json()

        assert data["customer_name"] == "Test Customer"
        assert data["subtotal"] == "200.00"
        assert data["shipping_fee"] == "35.00"
        assert data["total"] == "235.00"
        assert data["payment_method"] == "cash_on_delivery"
        assert data["status"] == "pending"

        # Verify that the order belongs to the authenticated customer.
        order = db_session.get(Order, data["id"])
        assert order is not None
        assert order.customer_id == "customer-123"
        assert order.guest_token is None
        db_session.refresh(checkout_product)

        assert checkout_product.stock_quantity == 10
        assert checkout_product.reserved_quantity == 2

        # The authenticated customer's cart should now be empty.
        cart_response = api_client.get("/api/v1/cart")

        assert cart_response.status_code == 200
        assert cart_response.json()["items"] == []
        assert cart_response.json()["total_items"] == 0

    finally:
        app.dependency_overrides.pop(
            get_optional_current_user,
            None,
        )


def test_checkout_rejects_insufficient_stock_and_keeps_cart(
    api_client: TestClient,
    db_session,
    checkout_product,
    active_delivery_city,
):
    # The cart contains 2 units, but only 1 unit is available.
    checkout_product.stock_quantity = 1
    checkout_product.reserved_quantity = 0
    db_session.flush()

    guest_token = add_product_to_guest_cart(
        api_client,
        checkout_product.id,
    )

    response = api_client.post(
        "/api/v1/checkout",
        headers={"X-Guest-Token": guest_token},
        json=checkout_payload(),
    )

    assert response.status_code == 422

    # No inventory should have been reserved.
    db_session.refresh(checkout_product)
    assert checkout_product.stock_quantity == 1
    assert checkout_product.reserved_quantity == 0

    # The failed checkout must not create an order.
    assert db_session.query(Order).count() == 0

    # The cart must retain its two units.
    cart_response = api_client.get(
        "/api/v1/cart",
        headers={"X-Guest-Token": guest_token},
    )
    assert cart_response.status_code == 200
    assert cart_response.json()["total_items"] == 2
    assert len(cart_response.json()["items"]) == 1
