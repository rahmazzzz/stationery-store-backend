
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
    
    
    
# -------------------------
# Cloud image upload
# -------------------------

def test_upload_image_success(
    service_setup, product, product_image
):
    service, repository, session = service_setup
    session.get.return_value = product
    repository.get_by_storage_key.return_value = None
    repository.create.return_value = product_image

    storage = MagicMock()
    storage.upload.return_value = (
        "products/1/unique.png",
        "https://example.supabase.co/storage/v1/object/public/product-images/products/1/unique.png",
    )

    png_content = b"\x89PNG\r\n\x1a\n" + b"fake-image-content"

    result = service.upload(
        1,
        filename="sticker.png",
        content=png_content,
        content_type="image/png",
        alt_text="Floral sticker",
        storage=storage,
    )

    assert result is product_image
    storage.upload.assert_called_once_with(
        product_id=1,
        filename="sticker.png",
        content=png_content,
        content_type="image/png",
    )
    repository.create.assert_called_once()

    saved_values = repository.create.call_args.args[0]
    assert saved_values["product_id"] == 1
    assert saved_values["storage_key"] == "products/1/unique.png"
    assert saved_values["content_type"] == "image/png"
    assert saved_values["file_size_bytes"] == len(png_content)
    assert saved_values["alt_text"] == "Floral sticker"


def test_upload_image_rejects_unsupported_content(service_setup):
    service, repository, session = service_setup
    storage = MagicMock()

    with pytest.raises(ValidationError, match="Unsupported image file"):
        service.upload(
            1,
            filename="malicious.png",
            content=b"not actually an image",
            content_type="image/png",
            storage=storage,
        )

    storage.upload.assert_not_called()
    repository.create.assert_not_called()
    session.get.assert_not_called()


def test_upload_image_rejects_mismatched_content_type(service_setup):
    service, repository, session = service_setup
    storage = MagicMock()
    png_content = b"\x89PNG\r\n\x1a\n" + b"fake-image-content"

    with pytest.raises(ValidationError, match="does not match"):
        service.upload(
            1,
            filename="sticker.jpg",
            content=png_content,
            content_type="image/jpeg",
            storage=storage,
        )

    storage.upload.assert_not_called()
    repository.create.assert_not_called()


def test_upload_image_rejects_files_over_10_mb(service_setup):
    service, repository, session = service_setup
    storage = MagicMock()
    oversized_content = (
        b"\x89PNG\r\n\x1a\n" + b"x" * (10 * 1024 * 1024)
    )

    with pytest.raises(ValidationError, match="10 MB"):
        service.upload(
            1,
            filename="large.png",
            content=oversized_content,
            content_type="image/png",
            storage=storage,
        )

    storage.upload.assert_not_called()
    repository.create.assert_not_called()
    session.get.assert_not_called()


def test_upload_image_rejects_missing_product(service_setup):
    service, repository, session = service_setup
    session.get.return_value = None
    storage = MagicMock()
    png_content = b"\x89PNG\r\n\x1a\n" + b"fake-image-content"

    with pytest.raises(NotFoundError, match="Product not found"):
        service.upload(
            999,
            filename="sticker.png",
            content=png_content,
            content_type="image/png",
            storage=storage,
        )

    storage.upload.assert_not_called()
    repository.create.assert_not_called()


def test_upload_image_deletes_cloud_file_if_database_save_fails(
    service_setup, product
):
    service, repository, session = service_setup
    session.get.return_value = product
    repository.get_by_storage_key.return_value = None
    repository.create.side_effect = IntegrityError(
        "INSERT", {}, Exception("constraint violation")
    )

    storage = MagicMock()
    storage.upload.return_value = (
        "products/1/unique.png",
        "https://example.supabase.co/storage/v1/object/public/product-images/products/1/unique.png",
    )
    png_content = b"\x89PNG\r\n\x1a\n" + b"fake-image-content"

    with pytest.raises(ConflictError):
        service.upload(
            1,
            filename="sticker.png",
            content=png_content,
            content_type="image/png",
            storage=storage,
        )

    storage.upload.assert_called_once()
    storage.delete.assert_called_once_with("products/1/unique.png")

# -------------------------
# Upload
# -------------------------

def test_detect_image_type():
    assert ProductImageService._detect_image_type(
        b"\xff\xd8\xff" + b"jpeg-data"
    ) == "image/jpeg"

    assert ProductImageService._detect_image_type(
        b"\x89PNG\r\n\x1a\n" + b"png-data"
    ) == "image/png"

    assert ProductImageService._detect_image_type(
        b"RIFF" + b"\x00\x00\x00\x00" + b"WEBP" + b"webp-data"
    ) == "image/webp"

    assert ProductImageService._detect_image_type(b"not an image") is None


@pytest.mark.parametrize(
    ("content", "content_type", "message"),
    [
        (b"", "image/png", "cannot be empty"),
        (b"not an image", "image/png", "Unsupported image file"),
        (
            b"\x89PNG\r\n\x1a\nfake-png",
            "image/jpeg",
            "does not match",
        ),
    ],
)
def test_upload_rejects_invalid_image(
    service_setup, product, content, content_type, message
):
    service, repository, session = service_setup
    session.get.return_value = product
    storage = MagicMock()

    with pytest.raises(ValidationError, match=message):
        service.upload(
            1,
            filename="image.png",
            content=content,
            content_type=content_type,
            storage=storage,
        )

    storage.upload.assert_not_called()
    repository.create.assert_not_called()


def test_upload_rejects_oversized_image(service_setup, product):
    service, repository, session = service_setup
    session.get.return_value = product
    storage = MagicMock()

    with pytest.raises(ValidationError, match="must not exceed 10 MB"):
        service.upload(
            1,
            filename="large.png",
            content=b"\x89PNG\r\n\x1a\n" + b"x" * (10 * 1024 * 1024),
            content_type="image/png",
            storage=storage,
        )

    storage.upload.assert_not_called()
    repository.create.assert_not_called()


def test_upload_rejects_negative_sort_order(service_setup, product):
    service, repository, session = service_setup
    session.get.return_value = product
    storage = MagicMock()

    with pytest.raises(ValidationError, match="zero or greater"):
        service.upload(
            1,
            filename="image.png",
            content=b"\x89PNG\r\n\x1a\nvalid-test-data",
            content_type="image/png",
            sort_order=-1,
            storage=storage,
        )

    storage.upload.assert_not_called()
    repository.create.assert_not_called()


def test_upload_rejects_missing_product(service_setup):
    service, repository, session = service_setup
    session.get.return_value = None
    storage = MagicMock()

    with pytest.raises(NotFoundError, match="Product not found"):
        service.upload(
            999,
            filename="image.png",
            content=b"\x89PNG\r\n\x1a\nvalid-test-data",
            content_type="image/png",
            storage=storage,
        )

    storage.upload.assert_not_called()
    repository.create.assert_not_called()


def test_upload_success(service_setup, product, product_image):
    service, repository, session = service_setup
    session.get.return_value = product
    repository.get_by_storage_key.return_value = None
    repository.create.return_value = product_image
    storage = MagicMock()
    storage.upload.return_value = (
        "products/1/unique.png",
        "https://example.com/products/1/unique.png",
    )

    result = service.upload(
        1,
        filename="sticker.png",
        content=b"\x89PNG\r\n\x1a\nvalid-test-data",
        content_type="image/png",
        alt_text="Sticker",
        is_primary=True,
        storage=storage,
    )

    assert result is product_image
    storage.upload.assert_called_once()
    repository.create.assert_called_once()

    values = repository.create.call_args.args[0]
    assert values["product_id"] == 1
    assert values["storage_key"] == "products/1/unique.png"
    assert values["content_type"] == "image/png"
    assert values["file_size_bytes"] == len(
        b"\x89PNG\r\n\x1a\nvalid-test-data"
    )
    assert values["alt_text"] == "Sticker"
    assert values["is_primary"] is True
    storage.delete.assert_not_called()


def test_upload_cleans_up_storage_when_database_write_fails(
    service_setup, product
):
    service, repository, session = service_setup
    session.get.return_value = product
    repository.get_by_storage_key.return_value = None
    repository.create.side_effect = IntegrityError(
        "INSERT", {}, Exception("constraint violation")
    )
    storage = MagicMock()
    storage.upload.return_value = (
        "products/1/unique.png",
        "https://example.com/products/1/unique.png",
    )

    with pytest.raises(ConflictError):
        service.upload(
            1,
            filename="sticker.png",
            content=b"\x89PNG\r\n\x1a\nvalid-test-data",
            content_type="image/png",
            storage=storage,
        )

    storage.upload.assert_called_once()
    storage.delete.assert_called_once_with("products/1/unique.png")

