
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.exceptions import ValidationError
from app.services.cart_service import CartService


@pytest.fixture
def service():
    """Create a service instance for testing price calculations."""
    return CartService.__new__(CartService)


@pytest.mark.parametrize(
    ("price", "discount_type", "discount_value", "expected"),
    [
        ("100.00", "none", "0.00", "100.00"),
        ("100.00", "percentage", "20.00", "80.00"),
        ("100.00", "fixed", "15.00", "85.00"),
        ("10.00", "percentage", "12.50", "8.75"),
        ("10.00", "fixed", "10.00", "0.00"),
    ],
)
def test_calculate_unit_price(
    service,
    price,
    discount_type,
    discount_value,
    expected,
):
    product = SimpleNamespace(
        price=Decimal(price),
        discount_type=discount_type,
        discount_value=Decimal(discount_value),
    )

    result = service.calculate_unit_price(product)

    assert result == Decimal(expected)


def test_calculate_unit_price_rounds_to_two_decimal_places(service):
    product = SimpleNamespace(
        price=Decimal("10.00"),
        discount_type="percentage",
        discount_value=Decimal("33.33"),
    )

    result = service.calculate_unit_price(product)

    assert result == Decimal("6.67")


def test_get_or_create_cart_rejects_missing_owner(service):
    with pytest.raises(ValidationError):
        service.get_or_create_cart()


def test_get_or_create_cart_rejects_both_owner_types(service):
    with pytest.raises(ValidationError):
        service.get_or_create_cart(
            customer_id="customer-123",
            guest_token="guest-token-123",
        )
