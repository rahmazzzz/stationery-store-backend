
from sqlalchemy.orm import configure_mappers

from app.models import Category, Product


def test_product_uses_correct_table_name() -> None:
    assert Product.__tablename__ == "products"


def test_product_has_expected_columns() -> None:
    expected_columns = {
        "id",
        "category_id",
        "name",
        "slug",
        "sku",
        "description",
        "width_cm",
        "height_cm",
        "price",
        "discount_type",
        "discount_value",
        "is_active",
        "created_at",
        "updated_at",
    }

    assert set(Product.__table__.columns.keys()) == expected_columns


def test_product_sku_is_unique() -> None:
    column = Product.__table__.c.sku

    assert column.unique is True
    assert column.nullable is False


def test_product_slug_is_unique() -> None:
    column = Product.__table__.c.slug

    assert column.unique is True
    assert column.nullable is False


def test_product_price_uses_numeric_type() -> None:
    column = Product.__table__.c.price

    assert column.type.precision == 10
    assert column.type.scale == 2


def test_product_dimensions_use_numeric_type() -> None:
    width = Product.__table__.c.width_cm
    height = Product.__table__.c.height_cm

    assert width.type.precision == 7
    assert width.type.scale == 2
    assert height.type.precision == 7
    assert height.type.scale == 2


def test_product_category_relationship(
    database_models: tuple[type[Category], type[Product]],
) -> None:
    configure_mappers()

    category_model, product_model = database_models
    relationship = product_model.category.property

    assert relationship.mapper.class_ is category_model
    assert relationship.back_populates == "products"


def test_product_has_discount_constraints() -> None:
    constraint_names = {
        constraint.name
        for constraint in Product.__table__.constraints
    }

    expected_constraints = {
        "ck_products_price_positive",
        "ck_products_dimensions_positive",
        "ck_products_discount_nonnegative",
        "ck_products_discount_type",
        "ck_products_percentage_max_100",
        "ck_products_fixed_discount_max_price",
    }

    assert expected_constraints.issubset(constraint_names)
