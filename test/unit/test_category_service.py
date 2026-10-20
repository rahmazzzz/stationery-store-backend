
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.exceptions import ConflictError, NotFoundError
from app.models import Category
from app.schemas.category import CategoryCreate, CategoryUpdate
from app.services.category_service import CategoryService


@pytest.fixture
def service_setup():
    """Create a service with a mocked repository."""
    with patch(
        "app.services.category_service.CategoryRepository"
    ) as repository_class:
        session = MagicMock(spec=Session)
        service = CategoryService(session)
        repository = repository_class.return_value

        yield service, repository, session


@pytest.fixture
def category() -> Category:
    """Provide a sample category for service tests."""
    return Category(id=1, name="Stickers", slug="stickers")


# -------------------------
# Create
# -------------------------

def test_create_category_success(service_setup, category):
    service, repository, _ = service_setup
    data = CategoryCreate(name="Stickers", slug="stickers")
    repository.name_exists.return_value = False
    repository.slug_exists.return_value = False
    repository.create.return_value = category

    result = service.create(data)

    assert result is category
    repository.create.assert_called_once_with(data)


def test_create_rejects_duplicate_name(service_setup):
    service, repository, _ = service_setup
    data = CategoryCreate(name="Stickers", slug="new-slug")
    repository.name_exists.return_value = True

    with pytest.raises(ConflictError, match="name already exists"):
        service.create(data)

    repository.create.assert_not_called()
    repository.slug_exists.assert_not_called()


def test_create_rejects_duplicate_slug(service_setup):
    service, repository, _ = service_setup
    data = CategoryCreate(name="New Category", slug="stickers")
    repository.name_exists.return_value = False
    repository.slug_exists.return_value = True

    with pytest.raises(ConflictError, match="slug already exists"):
        service.create(data)

    repository.create.assert_not_called()


def test_create_translates_integrity_error(service_setup):
    service, repository, _ = service_setup
    data = CategoryCreate(name="Stickers", slug="stickers")
    repository.name_exists.return_value = False
    repository.slug_exists.return_value = False
    repository.create.side_effect = IntegrityError(
        "INSERT", {}, Exception("unique constraint")
    )

    with pytest.raises(ConflictError, match="name or slug already exists"):
        service.create(data)


# -------------------------
# Retrieve
# -------------------------

def test_get_by_id_returns_category(service_setup, category):
    service, repository, _ = service_setup
    repository.get_by_id.return_value = category

    assert service.get_by_id(1) is category


def test_get_by_id_raises_when_missing(service_setup):
    service, repository, _ = service_setup
    repository.get_by_id.return_value = None

    with pytest.raises(NotFoundError, match="Category not found"):
        service.get_by_id(999)


def test_get_by_slug_returns_category(service_setup, category):
    service, repository, _ = service_setup
    repository.get_by_slug.return_value = category

    assert service.get_by_slug("stickers") is category


def test_get_by_slug_raises_when_missing(service_setup):
    service, repository, _ = service_setup
    repository.get_by_slug.return_value = None

    with pytest.raises(NotFoundError, match="Category not found"):
        service.get_by_slug("missing")


# -------------------------
# List and pagination
# -------------------------

def test_get_all_uses_pagination(service_setup, category):
    service, repository, _ = service_setup
    repository.get_all.return_value = [category]

    result = service.get_all(offset=10, limit=5)

    assert result == [category]
    repository.get_all.assert_called_once_with(offset=10, limit=5)


@pytest.mark.parametrize("offset", [-1, -10])
def test_get_all_rejects_negative_offset(service_setup, offset):
    service, repository, _ = service_setup

    with pytest.raises(ValueError, match="Offset cannot be negative"):
        service.get_all(offset=offset)

    repository.get_all.assert_not_called()


@pytest.mark.parametrize("limit", [0, -1, 101])
def test_get_all_rejects_invalid_limit(service_setup, limit):
    service, repository, _ = service_setup

    with pytest.raises(ValueError, match="Limit must be between 1 and 100"):
        service.get_all(limit=limit)

    repository.get_all.assert_not_called()


# -------------------------
# Update
# -------------------------

def test_update_category_success(service_setup, category):
    service, repository, _ = service_setup
    data = CategoryUpdate(name="New Stickers")
    repository.get_by_id.return_value = category
    repository.name_exists.return_value = False
    repository.update.return_value = category

    result = service.update(1, data)

    assert result is category
    repository.update.assert_called_once_with(category, data)


def test_update_rejects_duplicate_name(service_setup, category):
    service, repository, _ = service_setup
    data = CategoryUpdate(name="Notebooks")
    repository.get_by_id.return_value = category
    repository.name_exists.return_value = True

    with pytest.raises(ConflictError, match="name already exists"):
        service.update(1, data)

    repository.update.assert_not_called()


def test_update_rejects_duplicate_slug(service_setup, category):
    service, repository, _ = service_setup
    data = CategoryUpdate(slug="notebooks")
    repository.get_by_id.return_value = category
    repository.slug_exists.return_value = True

    with pytest.raises(ConflictError, match="slug already exists"):
        service.update(1, data)

    repository.update.assert_not_called()


def test_update_empty_data_returns_existing_category(
    service_setup, category
):
    service, repository, _ = service_setup
    repository.get_by_id.return_value = category
    data = CategoryUpdate()

    result = service.update(1, data)

    assert result is category
    repository.update.assert_not_called()


def test_update_missing_category_raises_not_found(service_setup):
    service, repository, _ = service_setup
    repository.get_by_id.return_value = None

    with pytest.raises(NotFoundError, match="Category not found"):
        service.update(999, CategoryUpdate(name="New Name"))

    repository.update.assert_not_called()


def test_update_translates_integrity_error(service_setup, category):
    service, repository, _ = service_setup
    data = CategoryUpdate(name="New Name")
    repository.get_by_id.return_value = category
    repository.name_exists.return_value = False
    repository.update.side_effect = IntegrityError(
        "UPDATE", {}, Exception("unique constraint")
    )

    with pytest.raises(ConflictError, match="name or slug already exists"):
        service.update(1, data)


# -------------------------
# Delete
# -------------------------

def test_delete_category_success(service_setup, category):
    service, repository, _ = service_setup
    repository.get_by_id.return_value = category

    result = service.delete(1)

    assert result is None
    repository.delete.assert_called_once_with(category)


def test_delete_missing_category_raises_not_found(service_setup):
    service, repository, _ = service_setup
    repository.get_by_id.return_value = None

    with pytest.raises(NotFoundError, match="Category not found"):
        service.delete(999)

    repository.delete.assert_not_called()


def test_delete_translates_integrity_error(service_setup, category):
    service, repository, _ = service_setup
    repository.get_by_id.return_value = category
    repository.delete.side_effect = IntegrityError(
        "DELETE", {}, Exception("foreign key constraint")
    )

    with pytest.raises(ConflictError, match="still has products|contain products"):
        service.delete(1)
