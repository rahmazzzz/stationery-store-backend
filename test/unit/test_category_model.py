
from sqlalchemy.orm import configure_mappers

from app.models import Category, Product


def test_category_uses_correct_table_name() -> None:
    assert Category.__tablename__ == "categories"


def test_category_has_expected_columns() -> None:
    expected_columns = {"id", "name", "slug"}

    assert set(Category.__table__.columns.keys()) == expected_columns


def test_category_name_is_unique() -> None:
    column = Category.__table__.c.name

    assert column.unique is True
    assert column.nullable is False


def test_category_slug_is_unique() -> None:
    column = Category.__table__.c.slug

    assert column.unique is True
    assert column.nullable is False


def test_category_product_relationship(
    database_models: tuple[type[Category], type[Product]],
) -> None:
    configure_mappers()

    category_model, product_model = database_models
    relationship = category_model.products.property

    assert relationship.mapper.class_ is product_model
    assert relationship.back_populates == "category"
