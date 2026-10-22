
from app.models import Cart, CartItem, Category, Product
from decimal import Decimal

import pytest

from app.exceptions import ValidationError
from app.models import Cart, CartItem, Category, Product
from app.services.cart_service import CartService


@pytest.fixture
def cart_service(db_session):
    return CartService(db_session)


@pytest.fixture
def active_product(db_session):
    category = Category(
        name="Test Category",
        slug="test-category",
    )
    db_session.add(category)
    db_session.flush()

    product = Product(
        category_id=category.id,
        name="Test Notebook",
        slug="test-notebook",
        sku="TEST-NOTEBOOK",
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


def test_add_item_creates_cart_item(
    cart_service,
    active_product,
    db_session,
):
    result = cart_service.add_item(
        product_id=active_product.id,
        quantity=2,
        guest_token="test-guest-token",
    )

    assert result["total_items"] == 2
    assert result["subtotal"] == Decimal("200.00")
    assert len(result["items"]) == 1

    item = db_session.query(CartItem).one()
    assert item.quantity == 2


def test_adding_same_product_increases_quantity(
    cart_service,
    active_product,
):
    cart_service.add_item(
        product_id=active_product.id,
        quantity=2,
        guest_token="test-guest-token",
    )

    result = cart_service.add_item(
        product_id=active_product.id,
        quantity=3,
        guest_token="test-guest-token",
    )

    assert result["total_items"] == 5
    assert len(result["items"]) == 1
    assert result["items"][0]["quantity"] == 5
    assert result["subtotal"] == Decimal("500.00")


def test_update_item_replaces_quantity(
    cart_service,
    active_product,
):
    cart_service.add_item(
        product_id=active_product.id,
        quantity=2,
        guest_token="test-guest-token",
    )

    result = cart_service.update_item(
        product_id=active_product.id,
        quantity=4,
        guest_token="test-guest-token",
    )

    assert result["total_items"] == 4
    assert result["items"][0]["quantity"] == 4
    assert result["subtotal"] == Decimal("400.00")


def test_remove_item_empties_cart(
    cart_service,
    active_product,
):
    cart_service.add_item(
        product_id=active_product.id,
        quantity=2,
        guest_token="test-guest-token",
    )

    result = cart_service.remove_item(
        product_id=active_product.id,
        guest_token="test-guest-token",
    )

    assert result["items"] == []
    assert result["total_items"] == 0
    assert result["subtotal"] == Decimal("0.00")
