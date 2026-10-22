
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.exceptions import NotFoundError, ValidationError
from app.models.order import Order
from app.schemas.order import CheckoutCreate
from app.services.order_service import OrderService


@pytest.fixture
def checkout_setup(monkeypatch):
    session = MagicMock()

    product = SimpleNamespace(
        id=10,
        name="Notebook",
        price=Decimal("100.00"),
        discount_type="percentage",
        discount_value=Decimal("20.00"),
        is_active=True,
    )
    cart_item = SimpleNamespace(product=product, quantity=2)
    cart = SimpleNamespace(items=[cart_item])

    cart_repository = MagicMock()
    cart_repository.get_by_guest_token.return_value = cart
    cart_repository.get_by_customer_id.return_value = cart

    delivery_service = MagicMock()
    delivery_service.get_shipping_fee.return_value = Decimal("25.00")

    monkeypatch.setattr(
        "app.services.order_service.CartRepository",
        lambda session: cart_repository,
    )
    monkeypatch.setattr(
        "app.services.order_service.DeliveryCityService",
        lambda session: delivery_service,
    )

    service = OrderService(session)

    data = CheckoutCreate(
        customer_name="Test Customer",
        phone_number="01012345678",
        city="Alexandria",
        delivery_address="123 Test Street",
    )

    return SimpleNamespace(
        service=service,
        session=session,
        cart=cart,
        cart_repository=cart_repository,
        delivery_service=delivery_service,
        data=data,
    )


def test_guest_checkout_creates_order_and_clears_cart(checkout_setup):
    setup = checkout_setup

    order = setup.service.checkout(
        setup.data,
        guest_token="guest-token-long-enough",
    )

    assert isinstance(order, Order)
    assert order.guest_token == "guest-token-long-enough"
    assert order.customer_id is None
    assert order.subtotal == Decimal("160.00")
    assert order.shipping_fee == Decimal("25.00")
    assert order.total == Decimal("185.00")
    assert order.payment_method == "cash_on_delivery"
    assert order.status == "pending"

    assert len(order.items) == 1
    assert order.items[0].product_name == "Notebook"
    assert order.items[0].unit_price == Decimal("80.00")
    assert order.items[0].quantity == 2
    assert order.items[0].line_total == Decimal("160.00")

    assert setup.cart.items == []
    setup.session.add.assert_called_once_with(order)
    assert setup.session.flush.call_count == 2


def test_authenticated_checkout_uses_customer_id(checkout_setup):
    setup = checkout_setup

    order = setup.service.checkout(
        setup.data,
        customer_id="customer-123",
    )

    assert order.customer_id == "customer-123"
    assert order.guest_token is None
    setup.cart_repository.get_by_customer_id.assert_called_once_with(
        "customer-123"
    )


def test_checkout_rejects_missing_owner(checkout_setup):
    with pytest.raises(ValidationError):
        checkout_setup.service.checkout(checkout_setup.data)


def test_checkout_rejects_both_owner_types(checkout_setup):
    with pytest.raises(ValidationError):
        checkout_setup.service.checkout(
            checkout_setup.data,
            customer_id="customer-123",
            guest_token="guest-token-long-enough",
        )


def test_checkout_rejects_missing_cart(checkout_setup):
    setup = checkout_setup
    setup.cart_repository.get_by_guest_token.return_value = None

    with pytest.raises(NotFoundError):
        setup.service.checkout(
            setup.data,
            guest_token="guest-token-long-enough",
        )


def test_checkout_rejects_empty_cart(checkout_setup):
    setup = checkout_setup
    setup.cart.items.clear()

    with pytest.raises(ValidationError):
        setup.service.checkout(
            setup.data,
            guest_token="guest-token-long-enough",
        )

    setup.session.add.assert_not_called()


def test_checkout_rejects_unavailable_city(checkout_setup):
    setup = checkout_setup
    setup.delivery_service.get_shipping_fee.side_effect = NotFoundError(
        "Delivery is not available in this city."
    )

    with pytest.raises(NotFoundError):
        setup.service.checkout(
            setup.data,
            guest_token="guest-token-long-enough",
        )

    setup.session.add.assert_not_called()


def test_checkout_rejects_inactive_product(checkout_setup):
    setup = checkout_setup
    setup.cart.items[0].product.is_active = False

    with pytest.raises(ValidationError):
        setup.service.checkout(
            setup.data,
            guest_token="guest-token-long-enough",
        )

    setup.session.add.assert_not_called()
