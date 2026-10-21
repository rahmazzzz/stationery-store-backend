
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.exceptions import ConflictError, NotFoundError, ValidationError
from app.models import Product, ProductImage
from app.schemas.product_image import ProductImageCreate, ProductImageUpdate
from app.services.product_image_service import ProductImageService


@pytest.fixture
def service_setup():
    """Create the service with a mocked repository and session."""
    with patch(
        "app.services.product_image_service.ProductImageRepository"
    ) as repository_class:
        session = MagicMock(spec=Session)
        service = ProductImageService(session)
        repository = repository_class.return_value

        yield service, repository, session


@pytest.fixture
def product() -> Product:
    """Provide a sample product."""
    return Product(id=1, name="Floral Sticker", slug="floral-sticker")


@pytest.fixture
def product_image() -> ProductImage:
    """Provide sample image metadata."""
    return ProductImage(
        id=10,
        product_id=1,
        image_url="https://cdn.example.com/images/sticker.png",
        storage_key="products/sticker.png",
        sort_order=0,
        is_primary=False,
    )


@pytest.fixture
def create_data() -> ProductImageCreate:
    return ProductImageCreate(
        image_url="https://cdn.example.com/images/sticker.png",
        storage_key="products/sticker.png",
    )


# -------------------------
# Product validation
# -------------------------

def test_list_images_rejects_missing_product(service_setup):
    service, repository, session = service_setup
    session.get.return_value = None

    with pytest.raises(NotFoundError, match="Product not found"):
        service.list_for_product(999)

    repository.get_for_product.assert_not_called()


def test_get_image_rejects_image_from_another_product(
    service_setup, product_image
):
    service, repository, session = service_setup
    session.get.return_value = Product(id=2)
    repository.get_by_id.return_value = product_image

    with pytest.raises(NotFoundError, match="Product image not found"):
        service.get_for_product(2, 10)


# -------------------------
# Create
# -------------------------

def test_create_image_success(
    service_setup, product, product_image, create_data
):
    service, repository, session = service_setup
    session.get.return_value = product
    repository.get_by_storage_key.return_value = None
    repository.create.return_value = product_image

    result = service.create(1, create_data)

    assert result is product_image
    repository.create.assert_called_once()
    values = repository.create.call_args.args[0]
    assert values["product_id"] == 1
    assert values["storage_key"] == "products/sticker.png"
    assert values["image_url"] == (
        "https://cdn.example.com/images/sticker.png"
    )


def test_create_image_rejects_missing_product(service_setup, create_data):
    service, repository, session = service_setup
    session.get.return_value = None

    with pytest.raises(NotFoundError, match="Product not found"):
        service.create(999, create_data)

    repository.create.assert_not_called()


def test_create_image_rejects_duplicate_storage_key(
    service_setup, product, create_data, product_image
):
    service, repository, session = service_setup
    session.get.return_value = product
    repository.get_by_storage_key.return_value = product_image

    with pytest.raises(ConflictError, match="storage key already exists"):
        service.create(1, create_data)

    repository.create.assert_not_called()


def test_create_primary_image_clears_previous_primary(
    service_setup, product, product_image, create_data
):
    service, repository, session = service_setup
    session.get.return_value = product
    repository.get_by_storage_key.return_value = None
    repository.create.return_value = product_image

    data = ProductImageCreate(
        image_url="https://cdn.example.com/images/primary.png",
        storage_key="products/primary.png",
        is_primary=True,
    )

    service.create(1, data)

    repository.clear_primary_for_product.assert_called_once_with(1)


def test_create_translates_integrity_error(
    service_setup, product, create_data
):
    service, repository, session = service_setup
    session.get.return_value = product
    repository.get_by_storage_key.return_value = None
    repository.create.side_effect = IntegrityError(
        "INSERT", {}, Exception("constraint violation")
    )

    with pytest.raises(ConflictError, match="conflicts with an existing record"):
        service.create(1, create_data)


# -------------------------
# Retrieve and list
# -------------------------

def test_list_images_returns_repository_results(
    service_setup, product, product_image
):
    service, repository, session = service_setup
    session.get.return_value = product
    repository.get_for_product.return_value = [product_image]

    result = service.list_for_product(1)

    assert result == [product_image]
    repository.get_for_product.assert_called_once_with(1)


def test_get_image_returns_matching_image(
    service_setup, product, product_image
):
    service, repository, session = service_setup
    session.get.return_value = product
    repository.get_by_id.return_value = product_image

    result = service.get_for_product(1, 10)

    assert result is product_image


# -------------------------
# Update
# -------------------------

def test_update_image_success(
    service_setup, product, product_image
):
    service, repository, session = service_setup
    session.get.return_value = product
    repository.get_by_id.return_value = product_image
    repository.update.return_value = product_image

    data = ProductImageUpdate(alt_text="Updated description")
    result = service.update(1, 10, data)

    assert result is product_image
    repository.update.assert_called_once_with(
        product_image,
        {"alt_text": "Updated description"},
    )


def test_update_image_rejects_empty_data(
    service_setup, product, product_image
):
    service, repository, session = service_setup
    session.get.return_value = product
    repository.get_by_id.return_value = product_image

    with pytest.raises(ValidationError, match="At least one field"):
        service.update(1, 10, ProductImageUpdate())

    repository.update.assert_not_called()


def test_update_image_rejects_duplicate_storage_key(
    service_setup, product, product_image
):
    service, repository, session = service_setup
    session.get.return_value = product
    repository.get_by_id.return_value = product_image

    another_image = ProductImage(id=11, product_id=1)
    repository.get_by_storage_key.return_value = another_image

    data = ProductImageUpdate(storage_key="products/other.png")

    with pytest.raises(ConflictError, match="storage key already exists"):
        service.update(1, 10, data)

    repository.update.assert_not_called()


def test_update_primary_image_clears_other_primary_images(
    service_setup, product, product_image
):
    service, repository, session = service_setup
    session.get.return_value = product
    repository.get_by_id.return_value = product_image
    repository.update.return_value = product_image

    service.update(1, 10, ProductImageUpdate(is_primary=True))

    repository.clear_primary_for_product.assert_called_once_with(
        1,
        except_id=10,
    )


# -------------------------
# Set primary
# -------------------------

def test_set_primary_image_clears_others_and_updates_target(
    service_setup, product, product_image
):
    service, repository, session = service_setup
    session.get.return_value = product
    repository.get_by_id.return_value = product_image
    repository.update.return_value = product_image

    result = service.set_primary(1, 10)

    assert result is product_image
    repository.clear_primary_for_product.assert_called_once_with(
        1,
        except_id=10,
    )
    repository.update.assert_called_once_with(
        product_image,
        {"is_primary": True},
    )


# -------------------------
# Delete
# -------------------------

def test_delete_image_success(
    service_setup, product, product_image
):
    service, repository, session = service_setup
    session.get.return_value = product
    repository.get_by_id.return_value = product_image

    result = service.delete(1, 10)

    assert result is None
    repository.delete.assert_called_once_with(product_image)


def test_delete_image_rejects_missing_image(
    service_setup, product
):
    service, repository, session = service_setup
    session.get.return_value = product
    repository.get_by_id.return_value = None

    with pytest.raises(NotFoundError, match="Product image not found"):
        service.delete(1, 999)

    repository.delete.assert_not_called()
