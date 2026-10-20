
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Category, Product


def test_database_connection(test_engine) -> None:
    with test_engine.connect() as connection:
        result = connection.exec_driver_sql("SELECT 1").scalar_one()

    assert result == 1


def test_insert_and_retrieve_category(db_session: Session) -> None:
    category = Category(
        name="Stickers",
        slug="stickers",
    )

    db_session.add(category)
    db_session.flush()

    saved_category = db_session.scalars(
        select(Category).where(Category.slug == "stickers")
    ).one()

    assert saved_category.name == "Stickers"
    assert saved_category.id is not None


def test_insert_product_and_load_category(db_session: Session) -> None:
    category = Category(
        name="Notebooks",
        slug="notebooks",
    )
    db_session.add(category)
    db_session.flush()

    product = Product(
        category_id=category.id,
        name="Floral Notebook",
        slug="floral-notebook",
        sku="NOTEBOOK-001",
        description="A floral stationery notebook.",
        width_cm=Decimal("14.80"),
        height_cm=Decimal("21.00"),
        price=Decimal("120.00"),
        discount_type="percentage",
        discount_value=Decimal("10.00"),
        is_active=True,
    )

    db_session.add(product)
    db_session.flush()

    saved_product = db_session.scalars(
        select(Product).where(Product.sku == "NOTEBOOK-001")
    ).one()

    assert saved_product.price == Decimal("120.00")
    assert saved_product.category.name == "Notebooks"
    assert saved_product.discount_type == "percentage"
    

def test_committed_data_is_rolled_back_after_test(
    db_session: Session,
) -> None:
    category = Category(
        name="Temporary Test Category",
        slug="temporary-test-category",
    )

    db_session.add(category)
    db_session.commit()

    saved_category = db_session.scalars(
        select(Category).where(
            Category.slug == "temporary-test-category"
        )
    ).one()

    assert saved_category.name == "Temporary Test Category"
    

def test_committed_category_does_not_leak_between_tests(
    db_session: Session,
) -> None:
    category = db_session.scalars(
        select(Category).where(
            Category.slug == "temporary-test-category"
        )
    ).first()

    assert category is None


