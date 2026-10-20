
from sqlalchemy.orm import Session

from app.models import Category
from app.repositories.category_repository import CategoryRepository
from app.schemas.category import CategoryCreate, CategoryUpdate


def test_create_category(db_session: Session) -> None:
    repository = CategoryRepository(db_session)

    category = repository.create(
        CategoryCreate(
            name="Stickers",
            slug="stickers",
        )
    )

    assert category.id is not None
    assert category.name == "Stickers"
    assert category.slug == "stickers"


def test_get_category_by_id(db_session: Session) -> None:
    repository = CategoryRepository(db_session)

    created = repository.create(
        CategoryCreate(name="Notebooks", slug="notebooks")
    )

    found = repository.get_by_id(created.id)

    assert found is not None
    assert found.name == "Notebooks"


def test_get_category_by_slug(db_session: Session) -> None:
    repository = CategoryRepository(db_session)

    repository.create(
        CategoryCreate(name="Pens", slug="pens")
    )

    found = repository.get_by_slug("pens")

    assert found is not None
    assert found.name == "Pens"


def test_get_category_by_unknown_slug_returns_none(
    db_session: Session,
) -> None:
    repository = CategoryRepository(db_session)

    assert repository.get_by_slug("missing") is None


def test_get_all_categories_is_ordered_and_paginated(
    db_session: Session,
) -> None:
    repository = CategoryRepository(db_session)

    repository.create(CategoryCreate(name="Stickers", slug="stickers"))
    repository.create(CategoryCreate(name="Notebooks", slug="notebooks"))
    repository.create(CategoryCreate(name="Pens", slug="pens"))

    first_page = repository.get_all(offset=0, limit=2)
    second_page = repository.get_all(offset=2, limit=2)

    assert [item.name for item in first_page] == ["Stickers", "Notebooks"]
    assert [item.name for item in second_page] == ["Pens"]


def test_update_category_changes_only_supplied_fields(
    db_session: Session,
) -> None:
    repository = CategoryRepository(db_session)

    category = repository.create(
        CategoryCreate(name="Stickers", slug="stickers")
    )

    updated = repository.update(
        category,
        CategoryUpdate(name="Sticker Sheets"),
    )

    assert updated.name == "Sticker Sheets"
    assert updated.slug == "stickers"


def test_delete_category(db_session: Session) -> None:
    repository = CategoryRepository(db_session)

    category = repository.create(
        CategoryCreate(name="Temporary", slug="temporary")
    )
    category_id = category.id

    repository.delete(category)

    assert repository.get_by_id(category_id) is None
