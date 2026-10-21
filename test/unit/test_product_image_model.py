
from sqlalchemy.orm import configure_mappers

from app.models import Category, Product, ProductImage


def test_product_image_uses_correct_table_name() -> None:
    assert ProductImage.__tablename__ == "product_images"


def test_product_image_has_expected_columns() -> None:
    expected_columns = {
        "id",
        "product_id",
        "image_url",
        "storage_key",
        "alt_text",
        "sort_order",
        "is_primary",
        "content_type",
        "file_size_bytes",
        "created_at",
        "updated_at",
    }

    assert set(ProductImage.__table__.columns.keys()) == expected_columns


def test_product_image_product_id_is_required_and_references_products() -> None:
    column = ProductImage.__table__.c.product_id

    assert column.nullable is False
    assert any(
        foreign_key.target_fullname == "products.id"
        and foreign_key.ondelete == "CASCADE"
        for foreign_key in column.foreign_keys
    )


def test_product_image_storage_key_is_unique() -> None:
    column = ProductImage.__table__.c.storage_key

    assert column.unique is True
    assert column.nullable is False


def test_product_image_sort_order_defaults_to_zero() -> None:
    column = ProductImage.__table__.c.sort_order

    assert column.nullable is False
    assert column.default.arg == 0
    assert column.server_default is not None


def test_product_image_has_expected_check_constraints() -> None:
    constraint_names = {
        constraint.name
        for constraint in ProductImage.__table__.constraints
    }

    expected_constraints = {
        "ck_product_images_sort_order_nonnegative",
        "ck_product_images_file_size_positive",
    }

    assert expected_constraints.issubset(constraint_names)


def test_product_image_relationships_are_configured() -> None:
    configure_mappers()

    product_images = Product.images.property
    image_product = ProductImage.product.property

    assert product_images.mapper.class_ is ProductImage
    assert product_images.back_populates == "product"
    assert product_images.cascade.delete_orphan

    assert image_product.mapper.class_ is Product
    assert image_product.back_populates == "images"


def test_product_image_product_relationship_uses_expected_models() -> None:
    assert Category.__tablename__ == "categories"
    assert Product.__tablename__ == "products"
    assert ProductImage.__tablename__ == "product_images"
