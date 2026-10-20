
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas.category import CategoryCreate, CategoryResponse
from app.schemas.product import ProductCreate, ProductUpdate


def test_category_create_accepts_valid_data() -> None:
    category = CategoryCreate(
        name="Stickers",
        slug="stickers",
    )

    assert category.name == "Stickers"
    assert category.slug == "stickers"


def test_category_create_rejects_empty_name() -> None:
    with pytest.raises(ValidationError):
        CategoryCreate(name="", slug="stickers")


def test_category_response_supports_model_attributes() -> None:
    class CategoryObject:
        id = 1
        name = "Stickers"
        slug = "stickers"

    response = CategoryResponse.model_validate(CategoryObject())

    assert response.id == 1
    assert response.name == "Stickers"


def test_product_create_accepts_valid_data() -> None:
    product = ProductCreate(
        category_id=1,
        name="Floral Sticker",
        slug="floral-sticker",
        sku="STICKER-001",
        width_cm=Decimal("5.00"),
        height_cm=Decimal("5.00"),
        price=Decimal("50.00"),
        discount_type="percentage",
        discount_value=Decimal("10.00"),
    )

    assert product.price == Decimal("50.00")
    assert product.discount_value == Decimal("10.00")


@pytest.mark.parametrize(
    "price",
    [Decimal("0.00"), Decimal("-1.00")],
)
def test_product_create_rejects_nonpositive_price(
    price: Decimal,
) -> None:
    with pytest.raises(ValidationError):
        ProductCreate(
            category_id=1,
            name="Floral Sticker",
            slug="floral-sticker",
            sku="STICKER-001",
            width_cm=Decimal("5.00"),
            height_cm=Decimal("5.00"),
            price=price,
        )


def test_product_create_rejects_percentage_above_100() -> None:
    with pytest.raises(ValidationError):
        ProductCreate(
            category_id=1,
            name="Floral Sticker",
            slug="floral-sticker",
            sku="STICKER-001",
            width_cm=Decimal("5.00"),
            height_cm=Decimal("5.00"),
            price=Decimal("50.00"),
            discount_type="percentage",
            discount_value=Decimal("100.01"),
        )


def test_product_create_rejects_fixed_discount_above_price() -> None:
    with pytest.raises(ValidationError):
        ProductCreate(
            category_id=1,
            name="Floral Sticker",
            slug="floral-sticker",
            sku="STICKER-001",
            width_cm=Decimal("5.00"),
            height_cm=Decimal("5.00"),
            price=Decimal("50.00"),
            discount_type="fixed",
            discount_value=Decimal("50.01"),
        )


def test_product_update_accepts_partial_data() -> None:
    update = ProductUpdate(name="Updated Sticker")

    assert update.name == "Updated Sticker"
    assert update.price is None


def test_product_update_rejects_empty_name() -> None:
    with pytest.raises(ValidationError):
        ProductUpdate(name="")


def test_product_create_rejects_invalid_discount_type() -> None:
    with pytest.raises(ValidationError):
        ProductCreate(
            category_id=1,
            name="Floral Sticker",
            slug="floral-sticker",
            sku="STICKER-001",
            width_cm=Decimal("5.00"),
            height_cm=Decimal("5.00"),
            price=Decimal("50.00"),
            discount_type="invalid",
        )
