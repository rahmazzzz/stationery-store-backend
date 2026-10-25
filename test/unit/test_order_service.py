
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.exceptions import ConflictError, NotFoundError, ValidationError
from app.models.product import Product
from app.models.order import Order
from app.schemas.order import CheckoutCreate
from app.services.order_service import OrderService


@pytest.fixture
def checkout_setup(monkeypatch):
    session = MagicMock()
    reservation_result = MagicMock()
    reservation_result.scalar_one_or_none.return_value = 10
    session.execute.return_value = reservation_result
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
        stock_quantity=10,
        reserved_quantity=0,
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
    setup.session.execute.assert_called_once()


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


def make_pending_order(
    *,
    order_id: int = 1,
    customer_id: str | None = None,
    guest_token: str | None = "guest-token-long-enough",
    status: str = "pending",
    items: list | None = None,
):
    return SimpleNamespace(
        id=order_id,
        customer_id=customer_id,
        guest_token=guest_token,
        customer_name="Test Customer",
        phone_number="01012345678",
        city="Alexandria",
        delivery_address="123 Test Street",
        subtotal=Decimal("160.00"),
        shipping_fee=Decimal("25.00"),
        total=Decimal("185.00"),
        payment_method="cash_on_delivery",
        status=status,
        items=items or [],
    )

def setup_cancellation(monkeypatch, order: Order):
    session = MagicMock()
    query_result = MagicMock()
    query_result.scalar_one_or_none.return_value = order
    session.execute.return_value = query_result

    service = OrderService(session)

    return SimpleNamespace(
        service=service,
        session=session,
        order=order,
        query_result=query_result,
    )


def test_cancel_guest_order_releases_inventory(monkeypatch):
    item = SimpleNamespace(product_id=10, quantity=2)
    order = make_pending_order(items=[item])
    setup = setup_cancellation(monkeypatch, order)

    setup.service.cancel_order(
        order.id,
        guest_token="guest-token-long-enough",
    )

    assert order.status == "cancelled"
    assert setup.session.execute.call_count == 2
    setup.session.flush.assert_called_once()


def test_cancel_order_rejects_missing_owner(checkout_setup):
    with pytest.raises(ValidationError):
        checkout_setup.service.cancel_order(1)


def test_cancel_order_rejects_both_owner_types(monkeypatch):
    setup = setup_cancellation(
        monkeypatch,
        make_pending_order(),
    )

    with pytest.raises(ValidationError):
        setup.service.cancel_order(
            1,
            customer_id="customer-123",
            guest_token="guest-token-long-enough",
        )

    setup.session.execute.assert_not_called()


def test_cancel_order_rejects_order_not_found(monkeypatch):
    setup = setup_cancellation(monkeypatch, make_pending_order())
    setup.query_result.scalar_one_or_none.return_value = None

    with pytest.raises(NotFoundError):
        setup.service.cancel_order(
            999,
            guest_token="guest-token-long-enough",
        )


def test_cancel_order_rejects_non_pending_order(monkeypatch):
    order = make_pending_order(status="cancelled")
    setup = setup_cancellation(monkeypatch, order)

    with pytest.raises(ConflictError):
        setup.service.cancel_order(
            order.id,
            guest_token="guest-token-long-enough",
        )

    setup.session.flush.assert_not_called()


def test_cancel_order_rejects_missing_product_reference(monkeypatch):
    order = make_pending_order(
        items=[SimpleNamespace(product_id=None, quantity=2)]
    )
    setup = setup_cancellation(monkeypatch, order)

    with pytest.raises(ConflictError):
        setup.service.cancel_order(
            order.id,
            guest_token="guest-token-long-enough",
        )

    setup.session.flush.assert_not_called()


def test_cancel_order_rejects_inventory_release_failure(monkeypatch):
    item = SimpleNamespace(product_id=10, quantity=2)
    order = make_pending_order(items=[item])
    setup = setup_cancellation(monkeypatch, order)
    setup.session.execute.side_effect = [
        setup.query_result,
        MagicMock(
            **{
                "scalar_one_or_none.return_value": None,
            }
        ),
    ]

    with pytest.raises(ConflictError):
        setup.service.cancel_order(
            order.id,
            guest_token="guest-token-long-enough",
        )

    assert order.status == "pending"
    setup.session.flush.assert_not_called()
