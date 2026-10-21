
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Category, Product


def create_category(
    db_session: Session,
    *,
    name: str = "Stickers",
    slug: str = "stickers",
) -> Category:
    category = Category(name=name, slug=slug)
    db_session.add(category)
    db_session.flush()
    return category


def create_product(
    db_session: Session,
    category_id: int,
    *,
    name: str = "Test Sticker",
    slug: str = "test-sticker",
    sku: str = "STICKER-001",
    price: Decimal = Decimal("50.00"),
    width_cm: Decimal = Decimal("5.00"),
    height_cm: Decimal = Decimal("5.00"),
    discount_type: str = "none",
    discount_value: Decimal = Decimal("0.00"),
) -> Product:
    product = Product(
        category_id=category_id,
        name=name,
        slug=slug,
        sku=sku,
        price=price,
        width_cm=width_cm,
        height_cm=height_cm,
        discount_type=discount_type,
        discount_value=discount_value,
    )
    db_session.add(product)
    db_session.flush()
    return product


def test_category_rejects_duplicate_name(db_session: Session) -> None:
    create_category(db_session)

    db_session.add(
        Category(name="Stickers", slug="different-stickers")
    )

    with pytest.raises(IntegrityError):
        db_session.flush()

    db_session.rollback()


def test_category_rejects_duplicate_slug(db_session: Session) -> None:
    create_category(db_session)

    db_session.add(
        Category(name="Other Category", slug="stickers")
    )

    with pytest.raises(IntegrityError):
        db_session.flush()

    db_session.rollback()


def test_product_rejects_duplicate_sku(db_session: Session) -> None:
    category = create_category(db_session)

    create_product(db_session, category.id)

    db_session.add(
        Product(
            category_id=category.id,
            name="Another Sticker",
            slug="another-sticker",
            sku="STICKER-001",
            width_cm=Decimal("5.00"),
            height_cm=Decimal("5.00"),
            price=Decimal("50.00"),
            discount_type="none",
            discount_value=Decimal("0.00"),
        )
    )

    with pytest.raises(IntegrityError):
        db_session.flush()

    db_session.rollback()


def test_product_rejects_duplicate_slug(db_session: Session) -> None:
    category = create_category(db_session)

    create_product(db_session, category.id)

    db_session.add(
        Product(
            category_id=category.id,
            name="Another Sticker",
            slug="test-sticker",
            sku="STICKER-002",
            width_cm=Decimal("5.00"),
            height_cm=Decimal("5.00"),
            price=Decimal("50.00"),
            discount_type="none",
            discount_value=Decimal("0.00"),
        )
    )

    with pytest.raises(IntegrityError):
        db_session.flush()

    db_session.rollback()


@pytest.mark.parametrize(
    "price",
    [
        Decimal("0.00"),
        Decimal("-1.00"),
    ],
)
def test_product_rejects_nonpositive_price(
    db_session: Session,
    price: Decimal,
) -> None:
    category = create_category(db_session)

    with pytest.raises(IntegrityError):
        create_product(db_session, category.id, price=price)

    db_session.rollback()


@pytest.mark.parametrize(
    ("width_cm", "height_cm"),
    [
        (Decimal("0.00"), Decimal("5.00")),
        (Decimal("-1.00"), Decimal("5.00")),
        (Decimal("5.00"), Decimal("0.00")),
        (Decimal("5.00"), Decimal("-1.00")),
    ],
)
def test_product_rejects_nonpositive_dimensions(
    db_session: Session,
    width_cm: Decimal,
    height_cm: Decimal,
) -> None:
    category = create_category(db_session)

    with pytest.raises(IntegrityError):
        create_product(
            db_session,
            category.id,
            width_cm=width_cm,
            height_cm=height_cm,
        )

    db_session.rollback()


def test_product_rejects_negative_discount(
    db_session: Session,
) -> None:
    category = create_category(db_session)

    with pytest.raises(IntegrityError):
        create_product(
            db_session,
            category.id,
            discount_type="fixed",
            discount_value=Decimal("-1.00"),
        )

    db_session.rollback()


def test_product_rejects_nonzero_discount_when_type_is_none(
    db_session: Session,
) -> None:
    category = create_category(db_session)

    with pytest.raises(IntegrityError):
        create_product(
            db_session,
            category.id,
            discount_type="none",
            discount_value=Decimal("10.00"),
        )

    db_session.rollback()



def test_product_rejects_invalid_discount_type(
    db_session: Session,
) -> None:
    category = create_category(db_session)

    with pytest.raises(IntegrityError):
        create_product(
            db_session,
            category.id,
            discount_type="invalid",
        )

    db_session.rollback()


def test_product_rejects_percentage_discount_above_100(
    db_session: Session,
) -> None:
    category = create_category(db_session)

    with pytest.raises(IntegrityError):
        create_product(
            db_session,
            category.id,
            discount_type="percentage",
            discount_value=Decimal("100.01"),
        )

    db_session.rollback()


def test_product_rejects_fixed_discount_above_price(
    db_session: Session,
) -> None:
    category = create_category(db_session)

    with pytest.raises(IntegrityError):
        create_product(
            db_session,
            category.id,
            price=Decimal("50.00"),
            discount_type="fixed",
            discount_value=Decimal("50.01"),
        )

    db_session.rollback()


def test_product_rejects_nonexistent_category(
    db_session: Session,
) -> None:
    with pytest.raises(IntegrityError):
        create_product(db_session, category_id=999999)

    db_session.rollback()


def test_valid_discount_is_stored_correctly(
    db_session: Session,
) -> None:
    category = create_category(db_session)

    product = create_product(
        db_session,
        category.id,
        discount_type="percentage",
        discount_value=Decimal("10.00"),
    )

    saved_product = db_session.scalars(
        select(Product).where(Product.sku == "STICKER-001")
    ).one()

    assert saved_product.id == product.id
    assert saved_product.discount_type == "percentage"
    assert saved_product.discount_value == Decimal("10.00")
