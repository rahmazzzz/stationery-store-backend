
import pytest
from sqlalchemy.orm import Session

from app.exceptions import ConflictError
from app.schemas.category import CategoryCreate
from app.services.category_service import CategoryService
from decimal import Decimal

from app.models import Category
from app.schemas.product import ProductCreate
from app.services.product_service import ProductService


def test_session_recovers_after_category_integrity_error(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = CategoryService(db_session)

    # Create a category whose slug is already in the database.
    service.create(
        CategoryCreate(name="Stickers", slug="stickers")
    )

    # Simulate a race: the preliminary slug check misses
    # the duplicate, so the database constraint catches it.
    monkeypatch.setattr(
        service._repository,
        "slug_exists",
        lambda slug, **kwargs: False,
    )

    with pytest.raises(ConflictError):
        service.create(
            CategoryCreate(name="Notebooks", slug="stickers")
        )

    # The failed write must not leave the session unusable.
    created = service.create(
        CategoryCreate(name="Pens", slug="pens")
    )

    assert created.name == "Pens"
    assert created.slug == "pens"

    # Confirm that the original record is still available.
    original = service.get_by_slug("stickers")
    assert original.name == "Stickers"


def test_session_recovers_after_product_integrity_error(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Create a category for the products.
    category = Category(name="Notebooks", slug="notebooks")
    db_session.add(category)
    db_session.flush()

    service = ProductService(db_session)

    def product_data(
        *,
        name: str,
        slug: str,
        sku: str,
    ) -> ProductCreate:
        return ProductCreate(
            category_id=category.id,
            name=name,
            slug=slug,
            sku=sku,
            width_cm=Decimal("14.80"),
            height_cm=Decimal("21.00"),
            price=Decimal("100.00"),
        )

    # Create the original product.
    service.create(
        product_data(
            name="A5 Notebook",
            slug="a5-notebook",
            sku="NOTEBOOK-A5-001",
        )
    )

    # Simulate a race: the preliminary SKU check misses
    # the duplicate, so the database constraint catches it.
    monkeypatch.setattr(
        service.products,
        "sku_exists",
        lambda sku, **kwargs: False,
    )

    with pytest.raises(ConflictError):
        service.create(
            product_data(
                name="Another Notebook",
                slug="another-notebook",
                sku="NOTEBOOK-A5-001",
            )
        )

    # The same session should remain usable after the failure.
    created = service.create(
        product_data(
            name="Sketchbook",
            slug="sketchbook",
            sku="SKETCHBOOK-001",
        )
    )

    assert created.name == "Sketchbook"
    assert created.sku == "SKETCHBOOK-001"

    # The original product should still exist.
    original = service.get_by_slug("a5-notebook")
    assert original.sku == "NOTEBOOK-A5-001"
