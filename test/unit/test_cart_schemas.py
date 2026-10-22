
import pytest
from pydantic import ValidationError

from app.schemas.cart import CartItemCreate, CartItemUpdate


def test_cart_item_create_defaults_quantity_to_one():
    item = CartItemCreate(product_id=1)

    assert item.product_id == 1
    assert item.quantity == 1


def test_cart_item_create_accepts_positive_quantity():
    item = CartItemCreate(product_id=2, quantity=3)

    assert item.quantity == 3


@pytest.mark.parametrize(
    ("product_id", "quantity"),
    [
        (0, 1),
        (-1, 1),
        (1, 0),
        (1, -1),
    ],
)
def test_cart_item_create_rejects_invalid_values(product_id, quantity):
    with pytest.raises(ValidationError):
        CartItemCreate(product_id=product_id, quantity=quantity)


@pytest.mark.parametrize("quantity", [0, -1])
def test_cart_item_update_rejects_non_positive_quantity(quantity):
    with pytest.raises(ValidationError):
        CartItemUpdate(quantity=quantity)
